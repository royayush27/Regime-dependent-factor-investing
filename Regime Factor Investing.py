import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt
from fredapi import Fred
from arch import arch_model  
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, accuracy_score
import seaborn as sns
import warnings
from dotenv import load_dotenv
import os
from pathlib import Path

warnings.filterwarnings('ignore')

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")

print("-" * 80)
print("REGIME-ADAPTIVE FACTOR ALLOCATION")
print("Analysis: GARCH & ML-based Regime Switching")
print("-" * 80)

# ------------------------------------------------------------------------------
# 1. DATA LOADING AND ALIGNMENT
# ------------------------------------------------------------------------------
print("\n[1/6] Loading and aligning data...")

def clean_idx(df):
    """Ensures index is datetime and set to month-end."""
    df.index = pd.to_datetime(df.index)
    df.index = df.index + pd.offsets.MonthEnd(0)
    return df[~df.index.duplicated(keep='last')]

def load_aqr(sheet, name):
    df = pd.read_excel("Betting Against Beta Equity Factors Monthly.xlsx", 
                       sheet_name=sheet, skiprows=18)
    df = df.iloc[:, [0, 1]].dropna() 
    df.columns = ["Date", name]
    df = df.set_index("Date")
    return clean_idx(df)

def fetch_fred_monthly(series_id, start, end, fred_client):
    s = fred_client.get_series(series_id, start, end)
    return s.resample('ME').last()

# Load AQR factors
print("  Loading AQR factors...")
bab = load_aqr("BAB Factors", "BAB")
mkt = load_aqr("MKT", "MKT")
umd = load_aqr("UMD", "UMD")
smb = load_aqr("SMB", "SMB")
hml = load_aqr("HML FF", "HML")

rf = pd.read_excel("Betting Against Beta Equity Factors Monthly.xlsx", 
                   sheet_name="RF", skiprows=18).iloc[:, [0, 1]].dropna()
rf.columns = ["Date", "RF"]
rf = clean_idx(rf.set_index("Date"))

# Load Fama-French 5
print("  Loading Fama-French factors...")
ff5 = pd.read_csv("F-F_Research_Data_5_Factors_2x3.csv", index_col=0, skiprows=4)
ff5.index = pd.to_datetime(ff5.index.astype(str), format="%Y%m", errors='coerce')
ff5 = ff5.apply(pd.to_numeric, errors='coerce').dropna() / 100
ff5 = clean_idx(ff5)

# Load VIX
print("  Loading VIX...")
vix_path = Path("VIXCLS.csv")
if vix_path.exists():
    vix = pd.read_csv(vix_path, index_col=0, parse_dates=True)
    vix.columns = ["VIX"]
    vix['VIX'] = pd.to_numeric(vix['VIX'], errors='coerce')
    vix = vix.resample('ME').last()
    vix = clean_idx(vix)
else:
    exit()

# Join all base factors
factors = bab.join([mkt, umd, smb, hml, rf, ff5[['RMW', 'CMA']], vix], how="inner")
print(f"  Base dataset: {len(factors)} months ({factors.index[0].date()} to {factors.index[-1].date()})")

# Load FRED data
print("  Fetching FRED macro data...")
fred = Fred(api_key=FRED_API_KEY)
fred_series = {'BBB_SPREAD': 'BAA10Y', 'TERM_SPREAD': 'T10Y2Y', 'NFCI': 'NFCI'}

for name, s_id in fred_series.items():
    try:
        s_monthly = fetch_fred_monthly(s_id, factors.index.min(), factors.index.max(), fred)
        factors[name] = s_monthly.ffill(limit=2)
        print(f"    Loaded {name}")
    except Exception as e:
        print(f"    Error loading {name}: {e}")

# Drop rows with missing critical data
missing_cols = [c for c in ['BBB_SPREAD', 'TERM_SPREAD', 'NFCI', 'VIX'] if c not in factors.columns]
if missing_cols:
    raise RuntimeError(f"Missing required data columns after loading: {missing_cols}")

factors = factors.dropna(subset=['BBB_SPREAD', 'TERM_SPREAD', 'NFCI', 'VIX'])
print(f"  Final dataset: {len(factors)} months")

# ------------------------------------------------------------------------------
# 2. DEFINE MARKET STRESS STATE
# ------------------------------------------------------------------------------
print("\n[2/6] Defining market stress state...")

# Method 1: VIX threshold
factors['VIX_High'] = (factors['VIX'] > 20).astype(int)

# Method 2: GARCH volatility
print("  Computing GARCH volatility...")
try:
    am = arch_model(factors['MKT'] * 100, vol='Garch', p=1, q=1, dist='normal')
    res = am.fit(disp='off', show_warning=False)
    factors['GARCH_Vol'] = res.conditional_volatility / 100
    
    # Rolling Z-score for relative volatility stress
    factors['GARCH_Z'] = (factors['GARCH_Vol'] - 
                          factors['GARCH_Vol'].rolling(24, min_periods=12).mean()) / \
                          factors['GARCH_Vol'].rolling(24, min_periods=12).std()
    
    factors['GARCH_High'] = (factors['GARCH_Z'] > 1.0).astype(int)
    print("    GARCH volatility computed")
except Exception as e:
    print(f"    GARCH failed: {e}")
    factors['GARCH_Vol'] = np.nan
    factors['GARCH_Z'] = np.nan
    factors['GARCH_High'] = 0

# VIX Z-score
factors['VIX_Z'] = (factors['VIX'] - 
                    factors['VIX'].rolling(24, min_periods=12).mean()) / \
                    factors['VIX'].rolling(24, min_periods=12).std()

# Combined indicator
factors['Stress_Current'] = ((factors['VIX_High'] == 1) | 
                             (factors['GARCH_High'] == 1)).astype(int)

print(f"  Stress distribution: {factors['Stress_Current'].mean():.1%} stress months")

# ------------------------------------------------------------------------------
# 3. FACTOR PERFORMANCE BY REGIME
# ------------------------------------------------------------------------------
print("\n[3/6] Analyzing factor performance by regime...")

factor_cols = ['MKT', 'SMB', 'HML', 'RMW', 'CMA', 'UMD', 'BAB']

# Partition by stress state
normal = factors[factors['Stress_Current'] == 0]
stress = factors[factors['Stress_Current'] == 1]

regime_stats = []
for factor in factor_cols:
    n_ret = normal[factor].mean() * 12 * 100
    n_sharpe = (normal[factor].mean() / normal[factor].std()) * np.sqrt(12) if normal[factor].std() > 0 else 0
    s_ret = stress[factor].mean() * 12 * 100
    s_sharpe = (stress[factor].mean() / stress[factor].std()) * np.sqrt(12) if stress[factor].std() > 0 else 0
    
    regime_stats.append({
        'Factor': factor,
        'Normal_Return': n_ret,
        'Normal_Sharpe': n_sharpe,
        'Stress_Return': s_ret,
        'Stress_Sharpe': s_sharpe,
        'Regime_Gap': n_ret - s_ret
    })

regime_df = pd.DataFrame(regime_stats)

print("-" * 80)
print(regime_df.to_string(index=False))
print("-" * 80)

offensive = regime_df[regime_df['Regime_Gap'] > 3]['Factor'].tolist()
defensive = regime_df[regime_df['Regime_Gap'] < -3]['Factor'].tolist()

regime_df.to_csv('factor_regime_analysis.csv', index=False)

# ------------------------------------------------------------------------------
# 4. ML STRESS PREDICTOR (WALK-FORWARD)
# ------------------------------------------------------------------------------
print("\n[4/6] Training predictive ML model...")

factors['Stress_Next'] = factors['Stress_Current'].shift(-1)
ml_features = ['BBB_SPREAD', 'TERM_SPREAD', 'NFCI']
ml_data = factors[ml_features + ['Stress_Next']].dropna()

min_train = 60
predictions = []
print("len(factors):", len(factors))
print("len(ml_data):", len(ml_data))
print("min_train:", min_train)
print(ml_data[['Stress_Next']].value_counts(dropna=False))
for i in range(min_train, len(ml_data)):
    train_data = ml_data.iloc[:i]
    test_data = ml_data.iloc[i:i+1]
    
    X_train = train_data[ml_features].values
    y_train = train_data['Stress_Next'].values
    X_test = test_data[ml_features].values
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    if len(np.unique(y_train)) < 2:
        prob = float(np.mean(y_train))
    else:
        clf = LogisticRegression(max_iter=200, random_state=42)
        clf.fit(X_train_scaled, y_train)
        prob = clf.predict_proba(X_test_scaled)[0][1]

    predictions.append({
        'Date': test_data.index[0],
        'P_Stress_Next': prob
    })

pred_df = pd.DataFrame(predictions)
pred_df.to_csv('predictions_GARCH.csv')
if pred_df.empty:
    factors['P_Stress_Next'] = np.nan
    factors['P_Stress'] = np.nan
else:
    pred_df['Date'] = pd.to_datetime(pred_df['Date'])
    pred_df = pred_df.set_index('Date')
    factors = factors.join(pred_df, how='left')
    factors['P_Stress'] = factors['P_Stress_Next'].shift(1)

# ------------------------------------------------------------------------------
# 5. PORTFOLIO STRATEGIES
# ------------------------------------------------------------------------------
print("\n[5/6] Implementing portfolio strategies...")

off_weights = {f: 1.0/len(offensive[:4]) for f in offensive[:4]} if len(offensive) >= 3 else {'MKT': 0.3, 'BAB': 0.3, 'UMD': 0.3, 'SMB': 0.1}
def_weights = {f: 1.0/len(defensive[:2]) for f in defensive[:2]} if len(defensive) >= 2 else {'RMW': 0.5, 'CMA': 0.5}

# 1. Baseline: Equal-weight all factors
factors['Strat_Static_EW'] = factors[factor_cols].mean(axis=1)

# 2. VIX-based Switching
factors['Strat_VIX_Rule'] = 0.0
for idx in factors.index:
    choice = off_weights if factors.loc[idx, 'VIX'] <= 20 else def_weights
    factors.loc[idx, 'Strat_VIX_Rule'] = sum(factors.loc[idx, f] * w for f, w in choice.items() if f in factors.columns and pd.notna(factors.loc[idx, f]))

# 3. ML-based Tactical
factors['Strat_ML_Tactical'] = 0.0
for idx in factors.index:
    p = factors.loc[idx, 'P_Stress']
    if pd.notna(p):
        off_ret = sum(factors.loc[idx, f] * w for f, w in off_weights.items() if f in factors.columns and pd.notna(factors.loc[idx, f]))
        def_ret = sum(factors.loc[idx, f] * w for f, w in def_weights.items() if f in factors.columns and pd.notna(factors.loc[idx, f]))
        factors.loc[idx, 'Strat_ML_Tactical'] = (1 - p) * off_ret + p * def_ret

factors['Bench_MKT'] = factors['MKT']
factors['Bench_BAB'] = factors['BAB']

# ------------------------------------------------------------------------------
# 6. PERFORMANCE REVIEW
# ------------------------------------------------------------------------------
print("\n[6/6] Final performance review...")

def calc_metrics(returns, name):
    rets = returns.dropna()
    if len(rets) < 12: return None
    
    ann_ret = rets.mean() * 12
    ann_vol = rets.std() * np.sqrt(12)
    sharpe = (rets.mean() / rets.std()) * np.sqrt(12) if rets.std() > 0 else 0
    cum = (1 + rets).cumprod()
    max_dd = ((cum / cum.cummax()) - 1).min()
    
    return {
        'Strategy': name,
        'Return': ann_ret * 100,
        'Vol': ann_vol * 100,
        'Sharpe': sharpe,
        'MaxDD': max_dd * 100
    }

strategies = {
    'ML Tactical': factors['Strat_ML_Tactical'],
    'VIX Rule': factors['Strat_VIX_Rule'],
    'Static EW': factors['Strat_Static_EW'],
    'Market Index': factors['Bench_MKT'],
    'BAB Factor': factors['Bench_BAB']
}

results = []
for name, rets in strategies.items():
    m = calc_metrics(rets, name)
    if m: results.append(m)

results_df = pd.DataFrame(results).sort_values('Sharpe', ascending=False)

print("-" * 80)
print(results_df.to_string(index=False))
print("-" * 80)

results_df.to_csv('strategy_performance.csv', index=False)

# ------------------------------------------------------------------------------
# VISUALIZATIONS
# ------------------------------------------------------------------------------
print("\nGenerating final plots...")
sns.set_style("whitegrid")

# 1. Regime Performance
plt.figure(figsize=(10, 6))
x = np.arange(len(regime_df))
plt.bar(x - 0.2, regime_df['Normal_Return'], 0.4, label='Normal', color='steelblue')
plt.bar(x + 0.2, regime_df['Stress_Return'], 0.4, label='Stress', color='darkred')
plt.xticks(x, regime_df['Factor'])
plt.title('Factor Returns by Regime')
plt.legend()
plt.tight_layout()
plt.savefig('chart1_factor_regime_performance.png', dpi=150)

# 2. Cumulative Growth
plt.figure(figsize=(12, 6))
for name, rets in strategies.items():
    plt.plot((1 + rets.dropna()).cumprod(), label=name)
plt.yscale('log')
plt.title('Growth Comparison (Log Scale)')
plt.legend()
plt.tight_layout()
plt.savefig('chart2_cumulative_returns.png', dpi=150)

# 3. Model and Timeline
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
ax1.plot(factors['VIX'], color='black', alpha=0.5, label='VIX')
ax1.fill_between(factors.index, 0, 80, where=factors['Stress_Current']==1, color='red', alpha=0.1, label='Stress')
ax1.set_title('Market VIX and Stress Periods')
ax1.legend()

ax2.plot(factors['P_Stress_Next'], color='blue', label='ML Stress Prob')
ax2.fill_between(factors.index, 0, 1, where=factors['Stress_Current']==1, color='red', alpha=0.1, label='Stress')
ax2.set_title('Predicted Probability of Stress')
ax2.legend()
plt.tight_layout()
plt.savefig('chart3_regime_timeline.png', dpi=150)

# 4. Sharpe Comparison
plt.figure(figsize=(8, 6))
plt.barh(results_df['Strategy'], results_df['Sharpe'], color='gray', alpha=0.8)
plt.title('Strategy Sharpe Ratios')
plt.tight_layout()
plt.savefig('chart4_sharpe_comparison.png', dpi=150)

print("\n" + "-" * 80)
print("ANALYSIS COMPLETE")
print(f"Top Strategy: {results_df.iloc[0]['Strategy']}")
print("-" * 80)

plt.show()