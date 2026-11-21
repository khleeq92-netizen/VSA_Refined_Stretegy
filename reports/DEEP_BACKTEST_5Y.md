# 5-year Deep Backtest (2021-01 → 2026-11), Direction = Both, fixed-pip exits (SL 160 / TP 100)

Data `data/deep_backtest/run_5y.csv`; analysis `research/analyze_5y.py`.

| | Trades | Win % | Total R | PF | Max DD (R) | Max losing streak | Time exits |
|---|---|---|---|---|---|---|---|
| All | 832 | 48.6 | −30.5 | 0.84 | 43.9 | 9 | 47% |
| BUY | 400 | 55.5 | +7.4 | 1.07 | 14.7 | 11 | 45% |
| SELL | 432 | 42.1 | −37.9 | 0.61 | — | 10 | 46% |
| BUY 2025–26 | 115 | 70.4 | +17.6 | 1.59 | 3.2 | 3 | 9% |

## What went wrong
1. **SELL model failed in every year, every session and both trend states** (PF 0.26–0.94). Its good Aug–Nov 2026 result was
   specific to that window (overfitting). Removed from the defaults.
2. **Fixed-pip exits do not scale.** Gold was $1,800–2,400 in 2021–24 with much smaller candles; a 160-pip stop and
   100-pip target were rarely reached within 8 hours → 45–74% of trades ended on the time exit, at roughly zero.
   In 2025–26 (gold $3,300–4,400) the same BUY rules won 70% with PF 1.59. Fix: ATR-scaled exits / minimum-volatility filter.
3. **BUY works better with the higher-timeframe trend:** gold up over the prior 60 days → PF 1.23 (222 trades);
   gold down → PF 0.94 (166 trades).

## Sessions (BUY; SELL lost in all sessions)
| Session | 5y trades | Win % | Total R | PF | 2025–26 win % / PF |
|---|---|---|---|---|---|
| Asia | 153 | 54.9 | +1.0 | 1.03 | 70.0 / 1.92 |
| London (before NY) | 73 | 56.2 | −0.4 | 0.98 | 75.0 / 1.76 |
| London–NY overlap | 157 | 52.9 | +2.9 | 1.07 | 66.7 / 1.24 |
| NY after London close | 17 | 82.4 | +4.0 | 2.72 | 87.5 / 3.55 |
Hours to watch (IST): 06:00–06:59 best (+6.5R, 59 trades); 07:00–08:59 worst (−5.5R, 68 trades); 12:00–12:59 weak (−3.5R, 27 trades).

---
# Run: ATR-multiple exits, BUY only, 2023-01 → 2026-11 (`data/deep_backtest/run_2023_now.csv`)

| Year | Trades | Win % | Total R | PF | Median SL (pips) | Time exits |
|---|---|---|---|---|---|---|
| 2023 | 62 | 58.1 | −4.2 | 0.82 | 46 | 11% |
| 2024 | 63 | 60.3 | −4.8 | 0.82 | 63 | 3% |
| 2025 | 60 | 68.3 | +7.2 | 1.43 | 114 | 10% |
| 2026 | 55 | 67.3 | +7.5 | 1.50 | 210 | 13% |
| All | 240 | 63.3 | +5.7 | 1.07 | 83 | 9% |

ATR exits removed the time-exit problem but did not rescue 2023–24 (fixed pips, same period: PF 1.22 overall).
The setup itself has no edge in quieter years with all sessions included.

Session filters (BUY), checked in both runs:
| Filter | ATR run 2023–26 | Fixed-pip run 2021–26 |
|---|---|---|
| none | PF 1.07, 240 tr | PF 1.07, 400 tr |
| skip 07:00–08:59 IST | PF 1.22 (2023–24 0.88, 2025–26 1.82) | PF 1.16 |
| **skip Asia session** | **PF 1.38, 67% win, DD 7.7R (2023–24 1.16, 2025–26 1.70)** | PF 1.10 |
| London + NY-after-London only | PF 1.92, 77% win, 52 tr | PF 1.15 |
Pine default now: skip Asia ON (candidate; must be confirmed on 2021–22, which this filter was not chosen on).

---
# TradingView confirmation: defaults (BUY, ATR exits, skip Asia), OANDA:XAUUSD, 2023-01 → 2026-11
File `data/deep_backtest/run_2023_now_skipAsia_OANDA.csv` (labelled by the trader as GC, but symbol and prices are OANDA spot).

| Year | Trades | Win % | Total R | PF | Max DD (R) |
|---|---|---|---|---|---|
| 2023 | 47 | 57.4 | −1.9 | 0.88 | 7.7 |
| 2024 | 35 | 74.3 | +6.0 | 1.67 | 2.1 |
| 2025 | 38 | 68.4 | +5.6 | 1.59 | 3.7 |
| 2026 | 37 | 70.3 | +6.6 | 1.74 | 3.8 |
| All | 157 | 66.9 | +16.2 | 1.37 | 7.7 (max 6 losses in a row) |
Matches the offline estimate (158 trades, PF 1.38). 2023 is the only losing year.
