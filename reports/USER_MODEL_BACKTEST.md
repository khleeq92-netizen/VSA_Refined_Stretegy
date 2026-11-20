# Backtest of the trader's model (as described) and its bearish mirror

Data: OANDA:XAUUSD M5 (TradingView export), 2026-08-16 → 2026-11-20 (~13.5 weeks after warm-up).
Market: −24%, mostly bearish. **One regime, small samples: results are indicative, not validated.**
In-sample (IS) = before 1 Oct 2026; out-of-sample (OOS) = 1 Oct → 20 Nov 2026. No parameters were tuned on OOS.
Costs: $0.40 per round trip (spread + slippage), entry at the next bar's open, stop assumed hit first when stop and target fall in the same bar.

## Rules as coded (please confirm)
BUY: (1) sweep of the previous session low or a prior swing low (±3-bar pivot); (2) UHV candle within 6 bars of the sweep,
UHV = volume ≥ 1.75 × average of the prior 10 bars; (3) within 12 bars, a bullish, non-inside candle closes above
**both** the UHV high and the CISD level (the open of the bearish run that made the low); (4) enter at the next open,
SL = UHV low − $0.10, 50% off at 1R, the rest at 2R; (5) trigger inside NY hours 08:00–17:00 New York time.
Setup cancelled if price closes below the UHV low first. SELL = exact mirror.

## Headline results (full table: user_model_results.csv, trade log: user_model_trade_log.csv)

| Model | Side | Trades | Win % | Avg R | Total R | PF | Max DD (R) | Max consec. L | IS avg R | OOS avg R |
|---|---|---|---|---|---|---|---|---|---|---|
| Your model (sweep + UHV + CISD) | BUY | 40 | 32.5 | −0.25 | −10.1 | 0.56 | 11.4 | 8 | −0.45 | −0.11 |
| Mirror (sweep + UHV + CISD) | SELL | 41 | 51.2 | +0.21 | +8.4 | 1.53 | 6.4 | 8 | +0.23 | +0.18 |

Typical stop = **2.5 × ATR** (~$10–11), because the stop sits beyond a large UHV candle and the entry comes after a close above its high.

## Ablations (Phase 4: is each ingredient pulling its weight?) — avg R, all periods

| Variant | BUY | SELL |
|---|---|---|
| D: sweep + UHV + CISD (yours) | −0.25 (n 40) | +0.21 (n 41) |
| A: sweep + UHV, no CISD (close > UHV high only) | −0.07 (n 56) | +0.08 (n 61) |
| B: UHV + CISD, no sweep | −0.08 (n 80) | +0.11 (n 88) |
| C: sweep + CISD, no UHV | **−0.26 (n 100)** | **−0.02 (n 104)** |

## Exit comparison (your entry rules)

| Exit | BUY avg R | SELL avg R |
|---|---|---|
| 50% @1R + 50% @2R (yours) | −0.25 | +0.21 |
| Fixed 1R | −0.15 | +0.11 |
| Fixed 1.5R | −0.28 | +0.19 |
| Fixed 2R | −0.35 | +0.24 |
| 50/50 with breakeven after TP1 | −0.26 | +0.13 |

## Reading the evidence
1. **Your BUY model lost in this period** in both halves. In a −24% market that is the expected failure of a
   counter-trend reversal model with no regime filter. It is the problem you described.
2. **The exact mirror made money on the SELL side** in both IS and OOS (+0.23 / +0.18 R). The sample is small
   (t ≈ 1.3, n = 41), and part of the gain is simply the bearish drift. The mechanics are not broken; their direction
   needs to follow the regime.
3. **UHV matters.** Removing the UHV condition (variant C) gave the worst results on both sides. Your volume filter is
   doing real work.
4. **CISD is inconsistent.** It hurt BUY results and helped SELL results. Requiring a close above both the UHV high and
   the CISD level makes entries late and stops wide (2.5 ATR). Not yet proven helpful.
5. **The sweep requirement did not clearly add value** (B ≈ D) except for **previous-session-level sweeps on SELL**
   (+1.08 R avg, n = 12). That is a hypothesis worth testing on more data.
6. **Exit choice:** no exit is clearly superior. Differences are within noise at this sample size.
7. **Sessions** (all-session SELL variant): Asia +0.25 R (n 40), NY +0.31 (n 13), Overlap +0.16 (n 27), London −0.45 (n 10).
   BUY during the overlap was the single worst bucket (−0.53 R, n 21).

## Not yet possible with this data
Bull and range-regime validation, walk-forward over multiple years, and statistically significant conclusions.
Requires TradingView Deep Backtesting of a Pine `strategy()` implementation on OANDA:XAUUSD.

---
# Model v2: refined rules (red UHV at the bottom inside a zone / green UHV at the top)

Code: `research/backtest_v2.py`. Results: `v2_results.csv` / `v2_results.txt`. Trades: `v2_trade_log.csv`.
Rules: UHV ≥ 1.75 × the prior-10-bar average; it must be the 4th+ consecutive candle against the trade (3 before it);
it must overlap an active H1/H4 FVG or H1 order block; a later candle sweeps the UHV extreme within 6 bars; a candle
after the sweep closes beyond the opposite UHV extreme within 12 bars; trigger in NY 08:00–17:00 local time.
SL beyond the lowest low (highest high) since the UHV candle; 50% @1R, rest @2R.

| Variant | BUY n / avg R | SELL n / avg R |
|---|---|---|
| As described (US session) | 6 / −0.19 | 8 / −0.19 |
| All sessions | 22 / −0.42 | 22 / +0.11 |
| No zone filter | 10 / −0.28 | 12 / −0.19 |
| No 3-candle background | 21 / −0.26 | 28 / −0.12 |
| No zone, no background | 45 / −0.27 | 71 / −0.03 |
| + CISD close required | 1 / — | 4 / −0.35 |

**Conclusion:** as described, the model fires only about 0.5–0.6 times per week per side in the US session. Fourteen
trades in 13.5 weeks cannot show whether it has an edge. Every number above is within random noise. Validation
requires the multi-year Deep Backtest.

---
# Correction: the no-inside rule applies to the CISD candle (trader clarification)

CISD candle = the first candle of the opposite-colour run that made the extreme. If it is an inside candle (its range
sits within the previous candle's range), use its mother candle instead. Entry requires a close beyond both the
UHV candle and the CISD candle (its high for buys / low for sells; the open is tested as a variant).

| Simple model (sweep + UHV + CISD), US session | BUY n / avg R / PF | SELL n / avg R / PF |
|---|---|---|
| Earlier coding (no-inside on entry candle, CISD = open) | 40 / −0.25 / 0.56 | 41 / +0.21 / 1.53 |
| **Corrected: no-inside on CISD candle, close above its high/low** | 37 / −0.35 / 0.40 | 38 / +0.17 / 1.44 |
| Corrected, CISD level = the CISD candle's open | 40 / −0.25 / 0.56 | 44 / +0.19 / 1.51 |
| Without CISD (close beyond the UHV candle only) | 56 / −0.08 / 0.86 | 62 / +0.08 / 1.18 |

The conclusions are unchanged: BUY loses in this bearish sample and the SELL mirror is positive in both halves, but
neither is statistically significant. Using the CISD candle's high (instead of its open) makes entries slightly later
and slightly worse. v2 (zone-filtered) is unaffected in practice: 6 BUY / 8 SELL trades.

---
# Sweep timing (trader clarification: "anywhere within the range")
The sweep of the UHV extreme may come at any time while price stays inside the UHV candle's range. The setup dies
if a candle closes beyond the opposite UHV extreme first (practical cap: 288 bars = 1 day). Tested windows of
6 / 24 / 48 / 96 / 288 bars: results are identical or nearly so (`v2_sweep_window.csv`). Sweeps almost always happen
within 6 candles, or price breaks out the other way first. This rule does not change trade frequency or results.

---
# v3: zones on M15 / H1 / H4 (FVG + demand/supply) and a higher UHV threshold for sells

Zones now include M15, H1 and H4 FVGs, plus M15, H1 and H4 demand/supply zones (last opposite candle before a ≥1.5×ATR
displacement candle on that timeframe). Sell-side UHV thresholds of 1.75×, 2.0×, 2.5× and 3.0× were tested
(`v3_zones_uhv.csv`, `v3_trade_log.csv`).

| Variant | BUY n / avg R | SELL n / avg R |
|---|---|---|
| Old zones, US session | 6 / −0.19 | 8 / −0.19 |
| M15+H1+H4 zones, UHV 1.75×, US session | 7 / −0.31 | 11 / −0.11 |
| M15+H1+H4 zones, UHV 1.75×, all sessions | 29 / −0.27 | 34 / +0.20 |
| SELL UHV 2.0×, all sessions | — | 18 / +0.02 |
| SELL UHV 2.5×, all sessions | — | 9 / +0.27 |
| SELL UHV 3.0×, all sessions | — | 4 / +0.02 |

Findings: adding M15 zones barely raises trade count in the US session. The binding constraints are the 3-candle
run and the sweep of the UHV extreme. A higher sell-side volume threshold cuts trades without clearly improving
results; nothing here exceeds noise. Most zone hits come from M15 FVGs.
