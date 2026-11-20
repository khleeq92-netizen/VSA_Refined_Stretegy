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
