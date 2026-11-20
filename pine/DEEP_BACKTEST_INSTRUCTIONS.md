# Running the research strategy with Deep Backtesting (TradingView Premium)

1. Open `OANDA:XAUUSD`, timeframe **5m**.
2. Pine Editor → paste `UHV_Sweep_Reversal_Strategy.pine` → **Add to chart**. If it fails to compile, copy the
   exact error message (line number + text) back to Claude.
3. Open **Strategy Tester** → turn on **Deep Backtesting** → set the date range **2021-01-01 → today** → Generate report.
4. Run these four settings (gear icon → Inputs), one at a time, and export each **List of Trades**
   (Strategy Tester → List of Trades → export / download icon → CSV):

| Run | Direction | Trade in | Require HTF zone | SELL UHV multiplier | File name to use |
|---|---|---|---|---|---|
| 1 | Buy only | All sessions | off | — | `run1_buy_all.csv` |
| 2 | Sell only | All sessions | off | 2.0 | `run2_sell_all.csv` |
| 3 | Buy only | US session | on | — | `run3_buy_us_zone.csv` |
| 4 | Sell only | US session | on | 2.0 | `run4_sell_us_zone.csv` |

5. Upload the CSVs here (or to the repo `data/deep_backtest/`). Keep **Risk per trade = $100** so that
   profit ÷ 100 = R. Do not change other inputs: the point is to test the rules chosen BEFORE seeing 2021–2025 data.

What Claude will do with them: per-year / per-regime / per-session statistics, walk-forward check (2021–2023 vs 2024–2026),
drawdown and losing streaks, and a check that 16 Aug – 20 Nov 2026 trades match the Python engine.

Known small differences from the Python engine: TP prices are computed from the signal candle's close (Python uses
the next bar's open; gold M5 gaps are usually cents); while a setup is waiting, a newer UHV candle does not replace it.
