# Running the research strategy with Deep Backtesting (TradingView Premium)

Defaults now follow the rules rebuilt from your 19-Nov example (v5): the UHV candle is the volume peak of the climax,
the sweep of the UHV extreme is required, entry is a stop order at the UHV extreme, SL 160 pips, half off at 120 pips,
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

Leave every other input at its default. Keep **Risk per trade = $100**, so profit ÷ 100 = R.
