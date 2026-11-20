# Deep Backtest run A: BUY, default settings, OANDA:XAUUSD M5, Dec 2025 – Nov 2026 (TradingView)

Settings: volume-peak red UHV ≥ 2× average, UHV range ≥ 2× ATR, sweep of the UHV low, candle close above the UHV high,
SL 160 pips, 100% exit at 100 pips, $100 risk per trade, $0.40/oz round-trip commission.
Data: `data/deep_backtest/A_buy_365d.csv`. Analysis: `research/analyze_tv_trades.py`.

| Period | Trades | Win % | Total R | Avg R | PF | Max DD (R) | Max losing streak |
|---|---|---|---|---|---|---|---|
| All | 58 | 70.7 | +8.09 | +0.14 | 1.49 | 2.47 | 2 |
| **Unseen (before 16 Aug 2026)** | **38** | **65.8** | **+1.68** | **+0.04** | **1.13** | 2.47 | 2 |
| Development window (16 Aug – 20 Nov 2026) | 20 | 80.0 | +6.41 | +0.32 | 3.01 | 1.45 | 1 |

| Market phase | Trades | Win % | Total R | PF |
|---|---|---|---|---|
| Bull (Dec – Feb) | 14 | 57.1 | −1.35 | 0.78 |
| Top & decline (Mar – mid Aug) | 24 | 70.8 | +3.03 | 1.42 |
| Bear (mid Aug – Nov) | 20 | 80.0 | +6.41 | 3.01 |

Reading: breakeven win rate for +100/−160 pips after costs ≈ 63%. On data never used to build the rules, the BUY
model won 65.8%, a thin but positive edge (≈ +7 pips/trade). Most of the headline performance comes from the
window the rules were tuned on, as expected. Drawdowns and losing streaks are small (max 2 losses in a row).
The model lost in the Dec–Feb bull phase (14 trades), so a bullish market is not automatically good for this
reversal buy. Next: 2021–2026 run (custom date range) and the SELL run (B).
