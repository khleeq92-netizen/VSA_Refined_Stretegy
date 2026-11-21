# UHV Sweep Reversal — test plan for the current version

Paste the new `UHV_Sweep_Reversal_Strategy.txt` (replace all old code) → Save → Add to chart (OANDA:XAUUSD, 5m).

**Defaults = recommended setup:** Buy only · Setup A (UHV sweep reversal) · UHV range ≥ 2× ATR · skip Asia session ·
ATR exits (SL 3.5 ATR, TP 2.25 ATR, 100% at TP) · Risk $100.

Run each row with Deep Backtesting and export **List of Trades** (CSV). Change only what the row says, then put it back.

| Run | Date range | Change from defaults | Tests |
|---|---|---|---|
| 1 | 2021-01-01 → 2022-12-31 | none | **Key test**: do the defaults work on years they were not chosen on? |
| 2 | 2021-01-01 → today | none | Full 5-year picture |
| 3 | 2021-01-01 → today | Exits: Exit mode = **Structural (R)**, Structural TP1 (R) = **1.5** | Tighter stop below the sweep low, 1:1.5 RR |
| 4 | 2021-01-01 → today | Quality filters: BUY UHV range = **1.5** | More trades? |
| 5 | 2021-01-01 → today | UHV detector: BUY UHV multiplier = **2.5** | Higher win rate? |
| 6 | 2021-01-01 → today | General: Setups = **B only** | Second setup (pullback) on its own |

Name the files run1.csv … run6.csv when you send them.
