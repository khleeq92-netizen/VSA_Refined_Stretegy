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
