# UHV Sweep Reversal — next Deep Backtest runs (2021-01-01 → today, OANDA:XAUUSD 5m)

Paste the new `UHV_Sweep_Reversal_Strategy.txt`. New defaults: **Buy only**, **Exit mode = ATR multiples**
(SL 3.5 × ATR, TP 2.25 × ATR — equal to 160 / 100 pips at 2026 volatility, smaller in quiet years).
Export **List of Trades** for each run:

| Run | Change from the new defaults | File |
|---|---|---|
| E | none (ATR exits) | `E_buy_atr.csv` |
| F | Regime filters → Daily trend filter **on** | `F_buy_atr_trend.csv` |
| G | Regime filters → Minimum M5 ATR = **2.5** | `G_buy_atr_minatr.csv` |
| H | Exit mode = **Fixed pips** + Minimum M5 ATR = **2.5** | `H_buy_pips_minatr.csv` |

Keep Risk per trade = $100.
