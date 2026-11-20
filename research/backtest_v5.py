"""v5: rules reverse-engineered from the trader's 19 Nov 2026 example (08:30 IST BUY).
UHV candle = the VOLUME PEAK of a selling climax (not necessarily the biggest body):
  red (close <= open), volume >= VM x SMA40, volume >= each of the previous 2 bars and > the next bar
  (so it is confirmed one bar later), range >= 1.2 x SMA40(range), close in the lower 65% of the last
  50 bars, and the indicator's selling-run rule (>= 4 red of previous 6, or exceptional-volume override).
Sweep: a later bar trades below the UHV low (while no close above the UHV high happened first).
Entry: ENTRY="stop" -> buy-stop at UHV high + $0.10, active from the bar after the sweep for 12 bars;
       ENTRY="close" -> bullish close above the UHV high, fill next bar open.
Exits (fixed pips, 1 pip = $0.10): SL 160, TP1 120 (50%), final 2 x SL; optional breakeven after TP1.
SELL = exact mirror. Cost $0.40 per round trip. Stop-first when both are touched in the same bar."""
import numpy as np, pandas as pd
from vsa_lib import load, features
from uhv_indicator import uhv

d = load("../data/OANDA_XAUUSD_M5.csv"); f = features(d)
o, h, l, c, v = (d[x].values.astype(float) for x in ("open", "high", "low", "close", "volume"))
n = len(d); sess = f.session.values; SPLIT = pd.Timestamp("2026-10-01", tz="UTC")

def climax_peak(side, vm=2.0):
    # reuse the indicator rules but with the body-size test switched off (body_k=0)
    m, _ = uhv(d, side, vmult=vm, body_k=0.0)
    vs = pd.Series(v)
    peak = (vs >= vs.shift(1)) & (vs >= vs.shift(2)) & (vs > vs.shift(-1))  # shift(-1): confirmed at t+1
    against = (c <= o) if side == "BUY" else (c >= o)
    return m & peak.values & against

def run(side, entry="stop", sessions=None, sl_p=160, tp1_p=120, tp2_mult=2.0, be=False, part=0.5, vm=2.0, w_trig=12, cancel_opp=True, w_sweep=288, hold=96):
    s = 1 if side == "BUY" else -1
    H, L, O, C = (h, l, o, c) if s == 1 else (-l, -h, -o, -c)
    mask = climax_peak(side, vm)
    out = []; i = 300
    while i < n - 3:
        if not mask[i]: i += 1; continue
        u = i
        sw = None
        for k in range(u + 1, min(n, u + 1 + w_sweep)):
            if L[k] < L[u]: sw = k; break
            if cancel_opp and C[k] > H[u]: break
        if sw is None: i += 1; continue
        lvl = H[u] + 0.10; ent = None
        for t in range(sw + 1, min(n - 1, sw + 1 + w_trig)):
            if entry == "stop" and H[t] >= lvl:
                ent = (t, max(O[t], lvl)); break
            if entry == "close" and C[t] > O[t] and C[t] > H[u]:
                ent = (t + 1, O[t + 1]); break
        if ent is None: i = sw + 1; continue
        t, e = ent
        if sessions and sess[t] not in sessions: i = t; continue
        risk = sl_p * 0.1; stop = e - risk; t1 = e + tp1_p * 0.1; t2 = e + tp2_mult * risk
        got1 = False; pnl = 0.0; mae = 0.0; why = "time"
        first = True
        for k in range(t, min(n, t + hold)):
            lo = L[k] if not (first and entry == "stop") else min(L[k], e)  # on the fill bar only count moves after fill (approx.)
            mae = max(mae, e - L[k])
            if L[k] <= stop:
                pnl += (1 - part if got1 else 1) * (stop - e); why = "BE" if got1 and be else "SL"; break
            if part > 0 and not got1 and H[k] >= t1:
                got1 = True; pnl += part * (t1 - e)
                if be: stop = e
            if H[k] >= t2:
                pnl += (1 - part if got1 else 1) * (t2 - e); why = "TP"; break
            first = False
        else:
            pnl += (1 - part if got1 else 1) * (C[k] - e)
        pnl -= 0.40
        out.append(dict(side=side, u=u, sw=sw, t=t, uhv=d.index[u], entry_time=d.index[t], entry=s * e, session=sess[t],
                        pips=pnl / 0.1, tp1_hit=got1, mae_pips=mae / 0.1, why=why))
        i = k + 1
    return pd.DataFrame(out)

def st(r, lab):
    if not len(r): return dict(variant=lab, n=0)
    p = r.pips.values; eq = np.cumsum(p); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    gl = -p[p <= 0].sum()
    return dict(variant=lab, n=len(p), win=round((p > 0).mean() * 100), tp1_hit=round(r.tp1_hit.mean() * 100),
                avg_pips=round(p.mean(), 1), total=round(p.sum()), PF=round(p[p > 0].sum() / gl, 2) if gl else np.inf,
                maxDD=round(dd), IS=round(r[r.entry_time < SPLIT].pips.mean(), 1), OOS=round(r[r.entry_time >= SPLIT].pips.mean(), 1))

if __name__ == "__main__":
    US = ("NY", "Overlap"); rows = []; logs = []
    for side in ("BUY", "SELL"):
        for lab, kw in [("ALL sessions, stop entry, SL160/TP1 120/2R", {}),
                        ("ALL sessions, stop entry, + breakeven", dict(be=True)),
                        ("ALL sessions, close entry", dict(entry="close")),
                        ("ALL sessions, single TP 120", dict(part=1.0, tp2_mult=1.2 * 0 + 120 / 160)),
                        ("Asia only, stop entry", dict(sessions=("Asia",))),
                        ("London only, stop entry", dict(sessions=("London",))),
                        ("US (NY+overlap), stop entry", dict(sessions=US)),
                        ("ALL sessions, UHV 2.5x", dict(vm=2.5))]:
            r = run(side, **kw); rows.append(dict(side=side, **st(r, lab)))
            if lab.startswith("ALL sessions, stop entry, SL"): logs.append(r)
    R = pd.DataFrame(rows); pd.set_option("display.width", 220)
    print(R.to_string(index=False)); R.to_csv("../reports/v5_results.csv", index=False)
    L = pd.concat(logs); L.to_csv("../reports/v5_trade_log.csv", index=False)
    x = L[(L.entry_time >= "2026-11-18 20:00") & (L.entry_time <= "2026-11-19 08:00")].copy()
    for col in ("uhv", "entry_time"): x[col] = x[col].dt.tz_convert("Asia/Kolkata")
    print("\n19 Nov example (IST):\n", x.to_string(index=False))
