\# Regime-Dependent Factor Investing



A regime-aware factor investing project that studies how factor premia change across volatility states and tests whether adaptive allocation can improve portfolio performance.



\## Overview



This project explores whether factor investing strategies behave differently across market regimes and whether regime-dependent allocation can outperform a static approach on a risk-adjusted basis.



The analysis combines factor return data, volatility information, and GARCH-based forecasting to classify market conditions and evaluate how factor performance shifts across those environments.



\## Project Motivation



Traditional factor investing often assumes that factor premia are stable through time. In practice, factor behavior can change meaningfully during periods of high uncertainty, rising volatility, or changing macro conditions.



This project was built to test a simple idea: if factor performance depends on regime, then portfolio exposure should adapt to regime as well.



\## Highlights



\- Built a regime classification workflow using volatility-related market signals.

\- Integrated Fama-French factor data, VIX data, and Betting Against Beta data.

\- Applied GARCH-based forecasting as part of the regime identification framework.

\- Evaluated factor behavior across different market states.

\- Compared cumulative returns and Sharpe ratios across strategies.

\- Generated visual outputs and structured CSV files for analysis.



\## Data Sources



This repository uses the following files:



\- `F-F\_Research\_Data\_5\_Factors\_2x3.csv`: Fama-French five-factor data.

\- `VIXCLS.csv`: CBOE VIX time-series data.

\- `Betting Against Beta Equity Factors Monthly.xlsx`: Betting Against Beta factor data.



\## Methodology



\### 1. Data Preparation



The raw factor, volatility, and BAB datasets were cleaned, aligned by date, and merged into a unified monthly time series for analysis.



\### 2. Regime Identification



Market regimes were identified using volatility behavior and regime classification logic informed by market conditions. GARCH-based forecasts were used to capture changing risk dynamics.



\### 3. Factor Analysis



Factor returns were analyzed conditionally by regime to determine whether premia differ across low-volatility and high-volatility environments.



\### 4. Strategy Construction



A regime-dependent allocation framework was implemented to tilt toward factors that historically performed better in each identified regime.



\### 5. Performance Evaluation



Strategy performance was assessed using cumulative return comparisons, regime-level summaries, and Sharpe ratio analysis.



\## Visual Results



\### Factor Performance by Regime



This plot shows how factor returns differ across identified market regimes.



<p align="center">

&#x20; <img src="./Plots/chart1_factor_regime_performance.png" alt="Factor performance across market regimes" width="850">

</p>



\### Cumulative Strategy Returns



This chart compares the cumulative return path of the regime-dependent strategy against alternative allocations.



<p align="center">

&#x20; <img src="./Plots/chart2_cumulative_returns.png" alt="Cumulative strategy returns" width="850">

</p>

\### Regime Timeline



This figure visualizes the market regime classification over time.



<p align="center">

&#x20; <img src="./Plots/chart3_regime_timeline.png" alt="Market regime timeline" width="850">

</p>



\### Sharpe Ratio Comparison



This plot compares the risk-adjusted performance of the tested strategies.



<p align="center">

&#x20; <img src="./Plots/chart4_sharpe_comparison.png" alt="Sharpe ratio comparison across strategies" width="850">

</p>



\## Output Files



The project generates the following outputs:



\- `factor\_regime\_analysis.csv`

\- `predictions\_GARCH.csv`

\- `strategy\_performance.csv`

\- `chart1\_factor\_regime\_performance.png`

\- `chart2\_cumulative\_returns.png`

\- `chart3\_regime\_timeline.png`

\- `chart4\_sharpe\_comparison.png`



\## Repository Structure



```text

.

├── .gitignore

├── Betting Against Beta Equity Factors Monthly.xlsx

├── F-F\_Research\_Data\_5\_Factors\_2x3.csv

├── Regime Factor Investing.py

├── VIXCLS.csv

├── chart1\_factor\_regime\_performance.png

├── chart2\_cumulative\_returns.png

├── chart3\_regime\_timeline.png

├── chart4\_sharpe\_comparison.png

├── factor\_regime\_analysis.csv

├── predictions\_GARCH.csv

└── strategy\_performance.csv

```



\## How to Run



Make sure all required data files are stored in the same project directory, then run:



```bash

python "Regime Factor Investing.py"

```



\## Tools and Libraries



This project is built in Python and uses a standard quantitative research workflow with data analysis, time-series modeling, and visualization tools.



Typical libraries include:



\- `pandas`

\- `numpy`

\- `matplotlib`

\- `statsmodels`

\- `arch` or equivalent time-series packages



\## Key Takeaways



\- Factor premia are not necessarily stable across different market environments.

\- Volatility-aware regime classification can provide a structured framework for adaptive allocation.

\- Regime-dependent factor investing may improve decision-making by aligning exposure with market state.



\## Future Improvements



\- Add transaction costs and turnover analysis.

\- Test alternative regime definitions.

\- Compare results against benchmark portfolios more formally.

\- Expand the framework using macroeconomic indicators.

\- Refactor the script into a cleaner modular research pipeline or notebook version.



\## Author



Built as a quantitative finance research project focused on regime-aware investing and factor timing.



\## License



This project currently has no license attached. Add an open-source license if you want others to reuse or modify the code.

