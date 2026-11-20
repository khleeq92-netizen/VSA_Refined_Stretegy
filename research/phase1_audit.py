import sys, numpy as np, pandas as pd
from vsa_lib import *
d = load("../data/OANDA_XAUUSD_M5.csv")
f = features(d); f["regime"] = regime(f)
fo = forward_outcomes(d, f)
X = f.join(fo).iloc[300:]  # warm-up
X = X[X.atr.notna() & X.rvt.notna()]
P = lambda *a: print(*a)
WEEKS=(X.index[-1]-X.index[0]).days/7
P("bars analysed", len(X), X.index[0], X.index[-1])
P("\n## 1. Volume by session (OANDA tick volume)")
P(X.groupby("session").agg(bars=("vol","size"), med_vol=("vol","median"), p95_vol=("vol",lambda s:s.quantile(.95)), med_atr=("atr","median"), med_range=("range","median")).round(1).to_string())
P("\n## 2. Hour-of-day (UTC) median volume")
hv = X.groupby(X.index.hour).vol.median(); P(hv.round(0).to_dict())
P("\n## 3. Does a fixed volume threshold work? share of bars above fixed thresholds by session")
for t in (5000, 8000, 10000):
    P(t, (X.vol>t).groupby(X.session).mean().mul(100).round(1).to_dict())
P("share of bars rv20>=2 by session", (X.rv20>=2).groupby(X.session).mean().mul(100).round(1).to_dict())
P("share of bars rv>=2 (TOD-normalised composite) by session", (X.rv>=2).groupby(X.session).mean().mul(100).round(1).to_dict())
P("\n## 4. Volume vs spread relationship (Spearman)", round(X.vol.corr(X.range, method="spearman"),3), "rv vs rs", round(X.rv.corr(X.rs, method="spearman"),3))
P("\n## 5. Regime share of bars", X.regime.value_counts(normalize=True).round(3).to_dict())

def stat(mask, sgn, label):
    s = X[mask]
    if len(s) < 15:
        return None
    r12 = sgn * s.r12; r24 = sgn * s.r24
    win = s.long_win if sgn > 0 else s.short_win
    base = (X.long_win if sgn > 0 else X.short_win)
    bw = base.mean()
    # baseline within same regime mix
    t = r12.mean() / (r12.std() / np.sqrt(len(r12)))
    return dict(signal=label, dir="BUY" if sgn>0 else "SELL", n=len(s), per_wk=round(len(s)/WEEKS,1),
                hit1R=round(win.mean()*100,1), base_hit=round(bw*100,1),
                r12=round(r12.mean(),3), r24=round(r24.mean(),3), t12=round(t,2),
                H1_r12=round((sgn*s.r12[s.index<"2026-10-01"]).mean(),3), H2_r12=round((sgn*s.r12[s.index>="2026-10-01"]).mean(),3))

S = vsa_signals(d, f)
rows = []
for k, (m, sgn) in S.items():
    m = m.reindex(X.index).fillna(False)
    rows.append(stat(m, sgn, k))
    for rg in ("Bull","Bear","Range"):
        rows.append(stat(m & (X.regime==rg), sgn, f"  {k} | {rg}"))
# baselines: every bar in each direction, per regime
for sgn in (1,-1):
    rows.append(stat(pd.Series(True,index=X.index), sgn, "BASELINE all bars"))
    for rg in ("Bull","Bear","Range"):
        rows.append(stat(X.regime==rg, sgn, f"  BASELINE | {rg}"))
R = pd.DataFrame([r for r in rows if r])
pd.set_option("display.width", 200)
P("\n## 6. Forward response of VSA signals (entry next open; r = move in ATR in signal direction; hit1R = +1ATR before -1ATR within 24 bars)")
P(R.to_string(index=False))
R.to_csv("../reports/phase1_signal_table.csv", index=False)
