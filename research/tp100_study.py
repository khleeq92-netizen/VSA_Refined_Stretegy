"""Win rate with a 100-pip 'safer' target (TP1), current rules vs. quality filters.
Win definitions: TP1-hit = price reached +100 pips before the 160-pip stop; net win = trade closed in profit."""
import numpy as np, pandas as pd
import backtest_v5 as V
SPLIT = pd.Timestamp("2026-10-01", tz="UTC")
atr = V.f.atr.values; vol = V.d.volume.values; h, l = V.h, V.l

def go(side, filt, **kw):
    r = V.run(side, entry="close", cancel_opp=False, tp1_p=100, **kw)
    if filt == "range2":
        keep = [(h[u] - l[u]) / atr[u] >= 2.0 for u in r.u]
    elif filt == "vol25_noovl":
        keep = [(vol[u] / vol[u - 40:u].mean() >= 2.5) and s != "Overlap" for u, s in zip(r.u, r.session)]
    else:
        keep = [True] * len(r)
    return r[np.array(keep, bool)] if len(r) else r
# NOTE: filters are applied after simulation; a filtered-out trade could have blocked a later one, so
# filtered results here are a close approximation (the Pine strategy applies the filter before the trade).

def line(r, lab):
    p = r.pips.values; eq = np.cumsum(p); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    a, b = r[r.entry_time < SPLIT], r[r.entry_time >= SPLIT]
    return dict(model=lab, n=len(r), per_wk=round(len(r) / 13.5, 1), tp1_hit=round(r.tp1_hit.mean() * 100),
                net_win=round((p > 0).mean() * 100), avg_pips=round(p.mean(), 1), total=round(p.sum()),
                maxDD=round(dd), H1_tp1=round(a.tp1_hit.mean() * 100), H2_tp1=round(b.tp1_hit.mean() * 100),
                H1_avg=round(a.pips.mean(), 1), H2_avg=round(b.pips.mean(), 1))
rows = []
for side, filt, fl in (("BUY", None, "current rules"), ("BUY", "range2", "UHV range >= 2 ATR"),
                       ("SELL", None, "current rules"), ("SELL", "vol25_noovl", "vol >= 2.5x, no overlap")):
    for ex, kw in (("50% @100, rest @320, BE", dict(be=True)), ("50% @100, rest @320, no BE", dict()),
                   ("100% @100 (single target)", dict(part=1.0, tp2_mult=100 / 160))):
        rows.append(dict(side=side, **line(go(side, filt, **kw), f"{fl} | {ex}")))
R = pd.DataFrame(rows); pd.set_option("display.width", 230); print(R.to_string(index=False))
R.to_csv("../reports/tp100_results.csv", index=False)
