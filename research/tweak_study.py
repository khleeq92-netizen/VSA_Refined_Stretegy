"""Win-rate tweak study on the v7 model (close entry, no cancel, SL160/TP1 120 50%/2R, breakeven, 8h).
Each candidate filter is measured on its own, with first-half (Aug-Sep) and second-half (Oct-Nov) results.
All features are known at the entry decision (trigger candle close) -> no lookahead."""
import numpy as np, pandas as pd
import backtest_v5 as V
d, f = V.d, V.f
c, h, l, o = V.c, V.h, V.l, V.o
atr = f.atr.values
e50 = pd.Series(c).ewm(span=50, adjust=False).mean().values
e200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
# "H1 trend" on M5: EMA 600 (= ~50 H1 bars) slope over 12 bars
e600 = pd.Series(c).ewm(span=600, adjust=False).mean().values
# developing day range (UTC day) known at bar t: position of the close
day = d.index.normalize()
dh = d.high.groupby(day).cummax().values; dl = d.low.groupby(day).cummin().values
rows = []
for side in ("BUY", "SELL"):
    r = V.run(side, entry="close", cancel_opp=False, be=True)
    s = 1 if side == "BUY" else -1
    for _, x in r.iterrows():
        u, sw, t = int(x.u), int(x.sw), int(x.t) - 1     # t-1 = trigger candle (decision time)
        ext = l[u] if s == 1 else h[u]
        sweep_ext = l[u:t + 1].min() if s == 1 else h[u:t + 1].max()
        rows.append(dict(side=side, time=x.entry_time, pips=x.pips, win=x.pips > 0, session=x.session,
            trend=s * (e50[t] - e200[t]) / atr[t],                       # >0 = trend agrees with trade
            htf=s * (e600[t] - e600[t - 12]) / atr[t],                   # >0 = slow trend agrees
            dpos=(c[t] - dl[t]) / max(dh[t] - dl[t], 1e-9),              # 0 = day low, 1 = day high
            sweep_depth=abs(ext - sweep_ext) / atr[t],                   # how far beyond the UHV extreme
            bars_to_sweep=sw - u, bars_to_trig=t - sw,
            chase=s * (c[t] - (h[u] if s == 1 else l[u])) / atr[t],      # trigger close beyond UHV extreme
            uhv_vol=d.volume.values[u] / d.volume.values[u - 40:u].mean(),
            uhv_range=(h[u] - l[u]) / atr[u]))
T = pd.DataFrame(rows); SPLIT = pd.Timestamp("2026-10-01", tz="UTC")
T.to_csv("../reports/tweak_features.csv", index=False)

def rep(mask, label):
    out = []
    for side in ("BUY", "SELL"):
        a = T[(T.side == side)]; m = a[mask.loc[a.index]]
        h1 = m[m.time < SPLIT]; h2 = m[m.time >= SPLIT]
        out.append(f"{side}: n={len(m):2d} win={m.win.mean()*100:4.0f}% avg={m.pips.mean():+6.1f} | H1 {h1.win.mean()*100 if len(h1) else np.nan:3.0f}%/{h1.pips.mean() if len(h1) else np.nan:+5.0f}  H2 {h2.win.mean()*100 if len(h2) else np.nan:3.0f}%/{h2.pips.mean() if len(h2) else np.nan:+5.0f}")
    print(f"{label:48s} " + "   ".join(out))

ALL = pd.Series(True, index=T.index)
rep(ALL, "BASELINE (v7 + breakeven)")
rep(T.trend > -3, "M5 trend not strongly against (EMA50-200 > -3 ATR)")
rep(T.trend > 0, "M5 trend agrees (EMA50 > EMA200 for buys)")
rep(T.htf > 0, "Slow trend agrees (EMA600 rising for buys)")
rep(T.htf > -1, "Slow trend not falling hard (>-1 ATR/hr)")
rep(T.session == "Asia", "Asia session only")
rep(T.session.isin(["Asia", "NY"]), "Asia + NY (no London/overlap)")
rep(T.session != "Overlap", "Skip London-NY overlap")
rep(((T.side == "BUY") & (T.dpos <= 0.5)) | ((T.side == "SELL") & (T.dpos >= 0.5)), "Discount for buys / premium for sells (day 50%)")
rep(T.sweep_depth <= 1.0, "Sweep depth <= 1 ATR beyond UHV extreme")
rep(T.sweep_depth <= 0.5, "Sweep depth <= 0.5 ATR")
rep(T.bars_to_sweep <= 6, "Sweep within 6 candles of UHV")
rep(T.bars_to_trig <= 6, "Trigger within 6 candles of sweep")
rep(T.chase <= 0.5, "Trigger close <= 0.5 ATR beyond UHV extreme (no chasing)")
rep(T.uhv_vol >= 2.5, "UHV volume >= 2.5x")
rep(T.uhv_vol >= 3.0, "UHV volume >= 3.0x")
rep(T.uhv_range >= 2.0, "UHV range >= 2 ATR")
