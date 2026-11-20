# UHV Sweep Reversal — how to load and test

## Load
1. Chart: `OANDA:XAUUSD`, **5m**.
2. Pine Editor → delete everything → paste `UHV_Sweep_Reversal_Strategy.txt` → **Save** → **Add to chart**.
   If an error appears, send Claude the line number and message.

## Default settings (current best candidates from the Aug–Nov 2026 research)
| | BUY | SELL |
|---|---|---|
| UHV candle | red, volume peak of the climax, ≥ 2.0× avg volume, **range ≥ 2× ATR** | green, volume peak, **≥ 2.5× avg volume** |
| Trigger | UHV low swept → candle **closes** above the UHV high | UHV high swept → candle **closes** below the UHV low |
| Sessions | all | all except the London–NY overlap |
| Stop | 160 pips | 160 pips |
| Target | **100% at 100 pips** | **50% at 100 pips, rest at 320 pips** (no breakeven) |

## Deep Backtesting (Strategy Tester → Deep Backtesting → 2021-01-01 → today)
Run each row and export **List of Trades** as CSV:

| Run | Direction | Change from defaults | File name |
|---|---|---|---|
| A | Buy only | none | `A_buy.csv` |
| B | Sell only | none | `B_sell.csv` |
| C | Buy only | Quality filters → BUY range = **0** (filter off) | `C_buy_nofilter.csv` |
| D | Sell only | SELL multiplier **2.0** and SELL skip overlap **off** | `D_sell_nofilter.csv` |

A and B are the recommended setups; C and D show whether the filters help across 2021–2026.
Keep **Risk per trade = $100** (profit ÷ 100 = R).
