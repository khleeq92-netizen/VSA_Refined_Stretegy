"""Setup B (BUY): low-volume pullback (No Supply) after a bullish UHV displacement.
1. Displacement: green candle, volume >= 2x SMA40, range >= 1.5x ATR20, close in the top 30% of its range.
2. Within the next 24 candles: a No Supply candle = red, range <= 0.8x ATR20, volume < each of the 2 previous
   candles and <= 0.8x SMA40, its low above the displacement candle's midpoint (pullback holds).
3. Trigger: within 6 candles, a candle CLOSES above the No Supply candle's high -> enter next open.
4. Exits identical to setup A: SL 3.5x ATR, TP 2.25x ATR (ATR mode), 8h time exit, $0.40 cost.
Sessions: skip Asia (as setup A). One position at a time."""
import numpy as np, pandas as pd
from vsa_lib import load, features
d = load("../data/OANDA_XAUUSD_M5.csv"); f = features(d)
o, h, l, c, v = (d[x].values.astype(float) for x in ("open", "high", "low", "close", "volume"))
atr = f.atr.values; sess = f.session.values; n = len(d)
vavg = pd.Series(v).rolling(40).mean().values
def run(sl_k=3.5, tp_k=2.25, skip_asia=True, hold=96, ns_rng=0.8, ns_vol=0.8):
    out = []; i = 300
    while i < n - 2:
        disp = c[i] > o[i] and v[i] >= 2 * vavg[i] and (h[i] - l[i]) >= 1.5 * atr[i] and (c[i] - l[i]) >= 0.7 * (h[i] - l[i])
        if not disp: i += 1; continue
        mid = (h[i] + l[i]) / 2; done = False
        for k in range(i + 1, min(n - 2, i + 25)):
            if l[k] < mid: break
            ns = c[k] < o[k] and (h[k] - l[k]) <= ns_rng * atr[k] and v[k] < v[k - 1] and v[k] < v[k - 2] and v[k] <= ns_vol * vavg[k]
            if not ns: continue
            for t in range(k + 1, min(n - 1, k + 7)):
                if l[t] < mid: break
                if c[t] > h[k]:
                    if skip_asia and sess[t + 1] == "Asia": break
                    e = o[t + 1]; risk = sl_k * atr[t]; stop = e - risk; tp = e + tp_k * atr[t]; pnl = None
                    for j in range(t + 1, min(n, t + 1 + hold)):
                        if l[j] <= stop: pnl = -risk; break
                        if h[j] >= tp: pnl = tp - e; break
                    if pnl is None: pnl = c[j] - e
                    out.append(dict(time=d.index[t + 1], R=(pnl - 0.4) / risk, session=sess[t + 1])); i = j; done = True
                    break
            if done: break
        i += 1
    return pd.DataFrame(out)
SPLIT = pd.Timestamp("2026-10-01", tz="UTC")
for lab, kw in (("Setup B, skip Asia", {}), ("Setup B, all sessions", dict(skip_asia=False))):
    r = run(**kw); a, b = r[r.time < SPLIT], r[r.time >= SPLIT]; gl = -r.R[r.R < 0].sum()
    print(f"{lab:24s} n={len(r)} ({len(r)/13.5:.1f}/wk) win={(r.R>0).mean()*100:.0f}% avgR={r.R.mean():+.3f} PF={r.R[r.R>0].sum()/gl:.2f} | Aug-Sep {(a.R>0).mean()*100:.0f}%/{a.R.mean():+.2f}R  Oct-Nov {(b.R>0).mean()*100:.0f}%/{b.R.mean():+.2f}R")
