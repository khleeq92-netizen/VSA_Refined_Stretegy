# Phase 1: Data audit and initial VSA signal findings (OANDA:XAUUSD M5)

Status: **exploratory / hypothesis-generating**. This is NOT a validated backtest.

## 1. Data

| Item | Value |
|---|---|
| Source | TradingView export of `OANDA:XAUUSD`, M5, five uploads merged |
| Consistency | All five files identical on overlapping bars (0 OHLC / volume mismatches) |
| Range | 2026-08-09 22:00 UTC → 2026-11-20 20:40 UTC (still-forming last bar dropped) |
| Bars | 20,655 (19,215 after indicator warm-up) |
| Volume | OANDA tick volume, as shown on your chart |
| Price path | 4,377 → peak 4,603 (21 Aug) → 3,506. About −24%, 11 of 15 weeks down |
| Median M5 ATR(20) | ≈ $3.7–4.5 |

**Main limitation:** Premium's 20k-bar cap means we have ~15 weeks, and they are dominated by one regime (bearish).
Bar Replay exports did not extend history, since all files end on the same bar. By your own research rules, nothing from this
sample can be called robust across regimes. Multi-regime validation will need TradingView **Deep Backtesting**
on a Pine `strategy()` version of the final rules (see §6).

## 2. Volume behaviour on OANDA M5

Median tick volume by session (DST-aware; London/NY local times):

| Session | Bars | Median vol | 90th pct | 98th pct | Median ATR $ |
|---|---|---|---|---|---|
| Asia (incl. NY rollover) | 6,300 | 1,768 | 4,059 | 7,077 | 3.9 |
| London (07:00–NY open) | 4,620 | 2,042 | 3,398 | 4,834 | 4.1 |
| London–NY overlap | 2,790 | 4,163 | 8,014 | 11,362 | 6.0 |
| NY (after London close) | 4,065 | 2,127 | 4,629 | 7,457 | 4.0 |

Hour-of-day (UTC) median volume peaks at 13:00–14:00 (~4,600–4,800) and bottoms at 22:00 (~640).

**Finding 1, validated descriptively: fixed volume thresholds are not appropriate.**
"Volume > 5,000" flags 35.6% of overlap bars but only 2.0% of London bars.
"Volume > 2× 20-bar average" over-fires in Asia (10.2% of bars) because Asian volume is low and spiky.
A time-of-day-normalised measure (volume ÷ median volume of the same 5-min slot over prior 20 sessions,
combined with ÷ 20-bar average) fires evenly (2–5% of bars in every session). All further work uses this
composite relative volume `rv`. A UHV candle = `rv ≥ 2.0` (to be tuned only on in-sample data).

**Finding 2:** tick volume and candle range are strongly correlated (Spearman 0.73 raw, 0.49 normalised).
A big-volume bar is usually just a big-range bar. Only the *disagreement* between volume and spread
(effort vs result) carries information beyond "volatility happened".

## 3. Objective signal definitions tested (all causal, evaluated at bar close, entry next bar open)

`rs` = range ÷ prior ATR(20); `clv` = (close−low)/(high−low); `rv` as above; up/down bar = close vs previous close.
Low volume = `rv ≤ 0.8` and volume below each of the previous 2 bars. Wide = `rs ≥ 1.5`. Narrow = `rs ≤ 0.7`.

| Signal | Rule | Implied dir |
|---|---|---|
| Buying Climax | up bar, UHV, wide, new 50-bar high | SELL |
| Upthrust | high > prior 24-bar high, clv ≤ 0.3, UHV | SELL |
| No Demand | up bar, narrow, low volume, clv ≤ 0.6 | SELL |
| Failed test of demand | higher high, clv ≤ 0.35, low volume | SELL |
| Bear WRB + UHV | down bar, UHV, wide, clv ≤ 0.3 | SELL (continuation) |
| Selling Climax | down bar, UHV, wide, new 50-bar low | BUY |
| Spring | low < prior 24-bar low, clv ≥ 0.7, UHV | BUY |
| No Supply | down bar, narrow, low volume, clv ≥ 0.4 | BUY |
| Test of Supply | lower low, clv ≥ 0.65, low volume | BUY |
| Stopping Volume | down bar, UHV, clv ≥ 0.5 | BUY |
| Bull WRB + UHV | up bar, UHV, wide, clv ≥ 0.7 | BUY (continuation) |

Regime context (M5 only): EMA50 − EMA200 in ATR units; > +3 Bull, < −3 Bear, else Range.

## 4. Results: forward response (full table: `phase1_signal_table.csv`)

`r12` = move after 12 bars (1 hour) in the signal's direction, in ATR. `hit1R` = % of times +1 ATR
was reached before −1 ATR within 24 bars. Baseline = the same measure for *every* bar in that direction
(SELL baseline is positive here only because the sample fell 24%).

| Signal | Dir | n | r12 | hit1R | Baseline hit | Read |
|---|---|---|---|---|---|---|
| Baseline (all bars) | SELL | 19,215 | +0.11 | 52.0 | — | bear drift |
| No Demand | SELL | 304 | +0.12 | 58.8 | 52.0 | ≈ baseline on r12; hit rate better, esp. in Bear regime (68%, n=64) |
| Failed test of demand | SELL | 428 | +0.19 | 53.4 | 52.0 | marginal |
| Buying Climax | SELL | 99 | **−0.43** | 45.5 | 52.0 | price kept rising. Not a reversal signal by itself |
| Upthrust | SELL | 43 | +0.13 | 37.2 | 52.0 | weak, small n |
| Bear WRB + UHV | SELL | 154 | **−0.47** | 42.2 | 52.0 | selling into it fails. Mean reversion follows |
| Selling Climax | BUY | 128 | **+0.65** | 51.6 | 47.0 | best raw BUY response, even inside a bear market |
| Stopping Volume | BUY | 65 | **+0.76** | 58.5 | 47.0 | promising, small n |
| Bull WRB + UHV | BUY | 187 | +0.36 | 44.1 | 47.0 | mixed |
| Spring | BUY | 57 | −0.76 | 49.1 | 47.0 | failed in this sample |
| No Supply | BUY | 320 | **−0.45** | 43.5 | 47.0 | worst. Should not be used stand-alone in a bear market |
| Test of Supply | BUY | 425 | −0.19 | 45.4 | 47.0 | negative |

### What this means (hypotheses, not conclusions)

1. **No single-bar VSA signal shows a statistically reliable stand-alone edge.** Best |t| ≈ 1.9, and
   t-stats are overstated because events cluster and outcomes overlap. With ~40 signal/regime cells tested,
   values like these are expected by chance.
2. **Your intuition about the buy side is partly confirmed:** downside UHV events (Selling Climax, Stopping
   Volume) were followed by up-moves even in a −24% market. That is the edge your BUY strategy likely
   exploits. It is a **mean-reversion** effect, not proof of "institutional buying".
3. **The bearish mirror is NOT symmetric.** A Buying Climax (UHV wide up-bar at a new high) did not
   mark tops; price continued. Selling the high-volume bar is wrong on M5 gold. Bearish edges appear in
   **low-volume rallies** (No Demand, failed tests) **inside a bearish regime**, which suggests the sell model
   should be built around *pullback + No Demand + trigger*, not climaxes. This is the key structural
   difference to explore in Phase 2.
4. **Selling right after a big UHV bearish displacement bar is bad timing** (−0.47 ATR). Continuation sells
   should wait for the retracement, which supports a "displacement → low-volume pullback → trigger" model.
5. **No Supply / Test of Supply alone should be removed as BUY triggers** unless the regime is bullish (to be
   retested once bullish data exists).
6. Costs matter: OANDA's XAUUSD spread (~$0.3–0.5) ≈ 0.1 ATR per round trip on M5. Several "edges" above are
   smaller than that.

## 5. Next research steps

- Phase 2/3/4: composite setups (liquidity sweep → VSA → objective CISD → entry) with chronological split:
  **in-sample 16 Aug–30 Sep 2026, out-of-sample 1 Oct–20 Nov 2026**, parameters fixed before OOS is run.
- Objective CISD definition to test: after a run of ≥ N same-colour candles, CISD = first close beyond the
  **open of the first candle of that run** (bearish CISD: close below the open of the up-run that made the high).
- Full trade simulation with stops (sweep extreme / signal bar / ATR), targets 1R / 1.5R / 2R / partial / trail,
  and spread + slippage.

## 6. What is needed from the trader

1. Your exact current rules: UHV definition, high-spread definition, how you mark CISD, entry/SL/TP habits.
2. Your local time zone and the hours you actually trade.
3. Later: running the Pine `strategy()` version with **Deep Backtesting** (Premium) over 2021–2026 and exporting
   the *List of Trades*. This is the only way to test on OANDA volume across bull, bear and range regimes.
