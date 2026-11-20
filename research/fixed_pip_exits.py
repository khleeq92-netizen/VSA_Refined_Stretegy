"""Re-test BUY (and SELL for comparison) setups with the trader's fixed-pip exit plan.
1 pip = $0.10 on XAUUSD. Entry = open of the bar after the trigger (same entries as the research engine).
One position at a time: signals that arrive while a position is open are skipped.
Cost: $0.40 (4 pips) per round trip. Stop and target touched in the same bar -> stop first (conservative)."""
import numpy as np, pandas as pd
from vsa_lib import load, features
from uhv_indicator import uhv
import backtest_v2 as v2, backtest_user_model as v1

PIP = 0.10; COST = 0.40; MAX_HOLD = 96
d = load("../data/OANDA_XAUUSD_M5.csv"); f = features(d)
o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
ALL = ("Asia", "London", "NY", "Overlap"); SPLIT = pd.Timestamp("2026-10-01", tz="UTC")

def entries(name):
    if name.startswith("Indicator UHV"):
        sess = ALL if "all" in name else ("NY", "Overlap")
        out = {}
        for side in ("BUY", "SELL"):
            m, _ = uhv(d, side, vmult=2.0)
            v2.MAX_HOLD = 1
            out[side] = v2.run(d, f, side, uhv_mask=m, use_zone=False, sessions=sess)
        v2.MAX_HOLD = 96
        return out
    v1.MAX_HOLD = 1
    out = {s: v1.run(d, f, s) for s in ("BUY", "SELL")}
    v1.MAX_HOLD = 96
    return out

def sim(times, side, sl, tp1, tp2, part=0.5, be=False, struct_sl=None):
    idx = d.index.get_indexer(pd.DatetimeIndex(times))
    s = 1 if side == "BUY" else -1
    res = []; busy_until = -1
    for n_, i in enumerate(idx):
        if i <= busy_until or i < 0: continue
        e = o[i]
        risk = sl if struct_sl is None else abs(e - struct_sl[n_])
        stop = e - s * risk; t1 = e + s * tp1; t2 = e + s * (tp2 if tp2 else tp1)
        got1 = False; pnl = 0.0; mae = 0.0; why = "time"
        for k in range(i, min(len(d), i + MAX_HOLD)):
            adv = (e - l[k]) if s == 1 else (h[k] - e)
            mae = max(mae, adv)
            hit_sl = (l[k] <= stop) if s == 1 else (h[k] >= stop)
            if hit_sl:
                pnl += (1 - part if got1 else 1) * (stop - e) * s; why = "BE" if (got1 and be) else "SL"; break
            if tp2 and not got1 and ((h[k] >= t1) if s == 1 else (l[k] <= t1)):
                got1 = True; pnl += part * tp1
                if be: stop = e
            if (h[k] >= t2) if s == 1 else (l[k] <= t2):
                pnl += (1 - part if got1 else 1) * abs(t2 - e); why = "TP"; break
        else:
            pnl += (1 - part if got1 else 1) * (c[k] - e) * s
        pnl -= COST; busy_until = k
        res.append(dict(time=d.index[i], pips=pnl / PIP, R=pnl / risk, mae_pips=mae / PIP, why=why, tp1_hit=got1))
    return pd.DataFrame(res)

def stats(r, label):
    p = r.pips.values; eq = np.cumsum(p); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    s = "".join("L" if x <= 0 else "W" for x in p); mcl = max(len(x) for x in s.split("W"))
    gp, gl = p[p > 0].sum(), -p[p <= 0].sum()
    return dict(plan=label, n=len(p), win=round((p > 0).mean() * 100, 1), avg_pips=round(p.mean(), 1),
                total_pips=round(p.sum()), PF=round(gp / gl, 2) if gl else np.inf, maxDD_pips=round(dd),
                max_consec_L=mcl, IS_avg=round(r[r.time < SPLIT].pips.mean(), 1), OOS_avg=round(r[r.time >= SPLIT].pips.mean(), 1),
                pct_mae_over_100=round((r.mae_pips >= 100).mean() * 100))

plans = [
    ("SL 150 / TP1 100 (50%) / final 2R=300", dict(sl=15, tp1=10, tp2=30)),
    ("SL 150 / TP1 120 (50%) / final 2R=300", dict(sl=15, tp1=12, tp2=30)),
    ("SL 160 / TP1 130 (50%) / final 2R=320", dict(sl=16, tp1=13, tp2=32)),
    ("SL 150 / TP1 120 (50%) + BE / final 300", dict(sl=15, tp1=12, tp2=30, be=True)),
    ("SL 150 / single TP 120", dict(sl=15, tp1=12, tp2=None)),
    ("SL 150 / single TP 150 (1:1)", dict(sl=15, tp1=15, tp2=None)),
    ("SL 150 / single TP 300 (1:2)", dict(sl=15, tp1=30, tp2=None)),
    ("SL 100 / single TP 120", dict(sl=10, tp1=12, tp2=None)),
]
rows = []
for name in ("Indicator UHV setups, all sessions", "Indicator UHV setups, US session", "Sweep+UHV+CISD (first model), US session"):
    E = entries(name)
    for side in ("BUY", "SELL"):
        tr = E[side]
        if not len(tr): continue
        for pl, kw in plans:
            rows.append(dict(setups=name, side=side, **stats(sim(tr.time, side, **kw), pl)))
R = pd.DataFrame([r for r in rows if r])
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 20)
print(R.to_string(index=False))
R.to_csv("../reports/fixed_pip_exits.csv", index=False)
