"""Python port of the trader's existing Pine indicator UHV detector (INDICATOR_GUIDE.md, Part 4),
plus an exact mirror for SELL setups. Causal: uses only the current and earlier bars (the UHV candle is
known at its close).

BUY (red UHV at exhaustion), defaults from the guide:
  red candle; volume > 2.0 x SMA40(volume); body >= 1.2 x SMA40(body); range >= 1.2 x SMA40(range);
  close position within the last 50 bars' high-low range <= 0.65;
  selling run: NORMAL = >= 4 red of the previous 6 candles AND their avg volume >= 0.8 x SMA40(volume)
               OVERRIDE = exceptional volume (>= 4 x SMA40 or highest volume of the last 400 bars)
                          AND >= 2 of 3 bearish-background tests over 12 bars
                          (close < EMA50, close < close[12], red share >= 55%) AND >= 2 reds of the previous 6.
SELL mirror: green candle, same size/volume rules (separate volume multiplier), position >= 0.35,
             buying run of green candles, bullish background.
Assumptions where the guide is silent: SMA40 includes the current bar (Pine ta.sma default); "previous 6"
excludes the UHV candle; run volume = mean volume of the same-colour candles in that window; position uses the close.
"""
import numpy as np, pandas as pd


def uhv(d, side="BUY", vmult=2.0, n=40, body_k=1.2, range_k=1.2, pos_n=50, pos_max=0.65,
        run_n=6, run_min=4, run_vol=0.8, override=True, exc_k=4.0, exc_n=400, ov_reds=2,
        bg_n=12, ema_n=50, bg_share=0.55, bg_need=2):
    o, h, l, c, v = (d[x].astype(float) for x in ("open", "high", "low", "close", "volume"))
    s = 1 if side == "BUY" else -1
    against = (c < o) if s == 1 else (c > o)          # red for BUY, green for SELL
    vavg = v.rolling(n).mean()
    body = (c - o).abs(); rng = h - l
    big = (body >= body_k * body.rolling(n).mean()) & (rng >= range_k * rng.rolling(n).mean())
    spike = v > vmult * vavg
    hh, ll = h.rolling(pos_n).max(), l.rolling(pos_n).min()
    pos = (c - ll) / (hh - ll)
    loc = (pos <= pos_max) if s == 1 else (pos >= 1 - pos_max)
    a_prev = against.shift(1).astype(float)
    cnt = a_prev.rolling(run_n).sum()
    run_v = (v.shift(1) * a_prev).rolling(run_n).sum() / cnt.replace(0, np.nan)
    normal = (cnt >= run_min) & (run_v >= run_vol * vavg)
    exc = (v >= exc_k * vavg) | (v >= v.rolling(exc_n).max())
    ema = c.ewm(span=ema_n, adjust=False).mean()
    t1 = (c < ema) if s == 1 else (c > ema)
    t2 = (c < c.shift(bg_n)) if s == 1 else (c > c.shift(bg_n))
    t3 = against.astype(float).rolling(bg_n).mean() >= bg_share
    bg = (t1.astype(int) + t2.astype(int) + t3.astype(int)) >= bg_need
    ov = override & exc & bg & (cnt >= ov_reds)
    m = against & spike & big & loc & (normal | ov)
    return m.fillna(False).values, (ov & ~normal).fillna(False).values
