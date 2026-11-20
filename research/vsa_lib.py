"""Objective, causal (no-lookahead) VSA / structure feature library for XAUUSD M5.

Every feature at bar t uses only bars <= t. Signals are evaluated at the CLOSE of
bar t; any trade enters at the OPEN of bar t+1.
"""
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

LON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")


def load(path):
    d = pd.read_csv(path)
    d.index = pd.to_datetime(d.pop("time"), unit="s", utc=True)
    d.index.name = "time"
    return d


def session_labels(idx):
    """DST-aware session buckets.
    Overlap : London 08:00-16:30 AND New York 08:00-17:00 (local times)
    London  : London 07:00-16:30 local, not overlap
    NY      : New York 08:00-17:00 local, not overlap
    Asia    : everything else (Tokyo/Sydney hours, incl. 17:00-19:00 NY rollover)
    """
    lon = idx.tz_convert(LON)
    ny = idx.tz_convert(NY)
    lh = lon.hour + lon.minute / 60
    nh = ny.hour + ny.minute / 60
    in_lon = (lh >= 7) & (lh < 16.5)
    in_ny = (nh >= 8) & (nh < 17)
    lab = np.where(in_lon & in_ny & (lh >= 8), "Overlap",
          np.where(in_lon, "London", np.where(in_ny, "NY", "Asia")))
    return pd.Series(lab, index=idx)


def features(d, atr_n=20, vol_n=20, tod_days=20):
    f = pd.DataFrame(index=d.index)
    o, h, l, c, v = d.open, d.high, d.low, d.close, d.volume.astype(float)
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    f["range"] = h - l
    f["atr"] = tr.rolling(atr_n).mean().shift(1)            # prior bars only
    f["rs"] = f["range"] / f["atr"]                          # relative spread
    f["clv"] = ((c - l) / (h - l)).where(h > l, 0.5)         # close location 0=low 1=high
    f["up"] = c > pc
    f["dn"] = c < pc
    f["bull"] = c > o
    f["bear"] = c < o
    # relative volume vs previous 20 bars (simple)
    f["rv20"] = v / v.rolling(vol_n).mean().shift(1)
    # relative volume vs the SAME 5-min time-of-day slot over previous N sessions
    slot = d.index.hour * 12 + d.index.minute // 5
    tod_med = v.groupby(slot).transform(lambda s: s.rolling(tod_days, min_periods=5).median().shift(1))
    f["rvt"] = v / tod_med
    # composite: geometric mean of both views (robust to session and to local bursts)
    f["rv"] = np.sqrt(f["rv20"] * f["rvt"])
    f["vol"] = v
    f["v_lt_prev2"] = (v < v.shift(1)) & (v < v.shift(2))
    # structure
    for n in (12, 24, 50):
        f[f"hh{n}"] = h.rolling(n).max().shift(1)   # prior n-bar high (excludes current)
        f[f"ll{n}"] = l.rolling(n).min().shift(1)
    # trend context (M5 only): EMA50 vs EMA200 distance in ATR, and 1-day return in ATR
    e50 = c.ewm(span=50, adjust=False).mean()
    e200 = c.ewm(span=200, adjust=False).mean()
    f["ema50"], f["ema200"] = e50, e200
    f["trend"] = (e50 - e200) / f["atr"]
    f["ret288"] = (c - c.shift(288)) / f["atr"]
    f["session"] = session_labels(d.index)
    return f


def regime(f, thr=3.0):
    """Simple M5 trend regime: Bull if EMA50 > EMA200 by > thr ATR, Bear if < -thr, else Range."""
    return pd.Series(np.where(f.trend > thr, "Bull", np.where(f.trend < -thr, "Bear", "Range")), index=f.index)


def vsa_signals(d, f, uhv=2.0, wide=1.5, narrow=0.7, low_vol=0.8):
    """Objective VSA definitions. Each returns a boolean Series and a hypothesised direction.
    Direction +1 = bullish implication, -1 = bearish implication."""
    h, l, c = d.high, d.low, d.close
    S = {}
    hi_v = f.rv >= uhv
    lo_v = (f.rv <= low_vol) & f.v_lt_prev2
    W = f.rs >= wide
    N = f.rs <= narrow
    at_high = h >= f.hh50          # makes a new 50-bar high
    at_low = l <= f.ll50
    # --- bearish implications ---
    S["BuyingClimax"] = (f.up & hi_v & W & at_high, -1)
    S["Upthrust"] = ((h > f.hh24) & (f.clv <= 0.3) & hi_v, -1)
    S["NoDemand"] = (f.up & N & lo_v & (f.clv <= 0.6), -1)
    S["TestOfDemand_fail"] = ((h > h.shift(1)) & (f.clv <= 0.35) & lo_v, -1)
    S["UpEffortNoResult"] = (f.up & hi_v & N, -1)             # absorption of buying
    S["BearWRB_UHV"] = (f.dn & hi_v & W & (f.clv <= 0.3), -1)  # supply / displacement
    # --- bullish implications ---
    S["SellingClimax"] = (f.dn & hi_v & W & at_low, +1)
    S["Spring"] = ((l < f.ll24) & (f.clv >= 0.7) & hi_v, +1)
    S["NoSupply"] = (f.dn & N & lo_v & (f.clv >= 0.4), +1)
    S["TestOfSupply"] = ((l < l.shift(1)) & (f.clv >= 0.65) & lo_v, +1)
    S["StoppingVolume"] = (f.dn & hi_v & (f.clv >= 0.5), +1)
    S["DownEffortNoResult"] = (f.dn & hi_v & N, +1)            # absorption of selling
    S["BullWRB_UHV"] = (f.up & hi_v & W & (f.clv >= 0.7), +1)  # demand / displacement
    return {k: (v.fillna(False), s) for k, (v, s) in S.items()}


def forward_outcomes(d, f, horizons=(6, 12, 24), barrier=1.0, max_bars=24):
    """Forward moves measured from NEXT bar open (realistic entry), in ATR units of the signal bar.
    Also a first-touch test: +barrier*ATR vs -barrier*ATR within max_bars (ties -> loss)."""
    o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    atr = f.atr.values
    n = len(d)
    entry = np.full(n, np.nan); entry[:-1] = o[1:]
    out = {}
    for H in horizons:
        fc = np.full(n, np.nan); fc[:-H] = c[H:]
        out[f"r{H}"] = (fc - entry) / atr
    # first touch, long and short
    up_first = np.full(n, np.nan); dn_first = np.full(n, np.nan)
    mfe_l = np.full(n, np.nan); mae_l = np.full(n, np.nan)
    for i in range(n - max_bars - 1):
        e, a = entry[i], atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        hh = h[i + 1:i + 1 + max_bars]; ll = l[i + 1:i + 1 + max_bars]
        up_hit = np.argmax(hh >= e + barrier * a) if (hh >= e + barrier * a).any() else 10**9
        dn_hit = np.argmax(ll <= e - barrier * a) if (ll <= e - barrier * a).any() else 10**9
        # long wins if up barrier strictly first; short wins if down barrier strictly first
        up_first[i] = 1.0 if up_hit < dn_hit else (0.0 if dn_hit < 10**9 or up_hit < 10**9 else np.nan)
        dn_first[i] = 1.0 if dn_hit < up_hit else (0.0 if up_hit < 10**9 or dn_hit < 10**9 else np.nan)
        mfe_l[i] = (hh.max() - e) / a
        mae_l[i] = (e - ll.min()) / a
    out["long_win"] = up_first
    out["short_win"] = dn_first
    out["mfe_long"] = mfe_l; out["mae_long"] = mae_l
    return pd.DataFrame(out, index=d.index)
