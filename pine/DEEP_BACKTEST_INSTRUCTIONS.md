# Running the research strategy with Deep Backtesting (TradingView Premium)

Defaults follow the rules rebuilt from your chart examples (v7): the UHV candle is the volume peak of the climax,
the sweep of the UHV extreme is required, entry after a candle CLOSES beyond the opposite UHV extreme, SL 160 pips, half off at 120 pips,
rest at 2 × SL, all sessions.

1. Open `OANDA:XAUUSD`, timeframe **5m**.
2. Pine Editor → delete everything → paste `UHV_Sweep_Reversal_Strategy.txt` → **Save** → **Add to chart**.
   If it shows an error, send Claude the line number and message.
3. Strategy Tester → **Deep Backtesting** on → date range **2021-01-01 → today** → Generate report.
4. Run each row (gear icon → Inputs), then **List of Trades → Export (CSV)**:

| Run | Direction | Move SL to breakeven after TP1 | SELL UHV multiplier | File name |
|---|---|---|---|---|
| 1 | Buy only | off | — | `run1_buy.csv` |
| 2 | Buy only | on | — | `run2_buy_be.csv` |
| 3 | Sell only | off | 2.0 | `run3_sell.csv` |
| 4 | Sell only | on | 2.0 | `run4_sell_be.csv` |
| 5 | Sell only | off | 2.5 | `run5_sell_25.csv` |

Quality-filter runs (settings group "Quality filters"), all with breakeven ON:

| Run | Direction | Filter settings | File name |
|---|---|---|---|
| 6 | Buy only | BUY: UHV candle range >= **2.0** ATR | `run6_buy_range2.csv` |
| 7 | Sell only | SELL UHV multiplier **2.5** + Skip London–NY overlap **on** | `run7_sell_vol25_noovl.csv` |

Leave every other input at its default. Keep **Risk per trade = $100**, so profit ÷ 100 = R.
