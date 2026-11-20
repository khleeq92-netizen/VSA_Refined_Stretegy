"""Backtest of the trader's own model (as described) + bearish mirror + CISD/sweep/UHV ablations.

Trader's BUY rules (as stated):
  1. Price sweeps a prior liquidity level: previous session low or a prior swing low.
  2. An ultra-high-volume (UHV) candle prints: volume >= ~2x the normal candles before it
     (e.g. normal 4-5k -> 7-8k+). Coded as volume / mean(volume of prior N bars) >= UHV_MULT.
  3. Wait for M5 CISD; the trigger candle must not be an inside bar.
  4. Entry when a bullish candle CLOSES above both the UHV candle high and the CISD level.
  5. SL = below the UHV candle low. TP1 = 1R (partial), final TP = 2R.
  6. Traded in the US session.
SELL = exact mirror.

Interpretations (flagged to the trader):
  - CISD level = open of the first candle of the last consecutive run of bearish candles that
    led into the lowest low since the sweep (bullish CISD = close above that open). Mirror for sells.
  - "US session" = New York 08:00-17:00 local time (DST-aware), which includes the London overlap.
  - Entry is filled at the OPEN of the bar after the trigger close (no same-bar fill).
  - Stop and target touched in the same bar -> counted as stop (conservative).
"""
import numpy as np, pandas as pd, sys
from vsa_lib import load, features

COST = 0.40          # $ per round trip: OANDA spread ~0.30-0.35 + slippage
SL_BUF = 0.10        # $ beyond UHV extreme
MAX_HOLD = 96        # bars (8h) then exit at close
PIVOT_K = 3          # swing = lowest/highest of +-3 bars, known 3 bars later
SWING_LOOKBACK = 150 # bars a swing level stays valid
W_UHV = 6            # UHV must appear within 6 bars of the sweep (sweep bar itself allowed)
W_TRIG = 12          # trigger must come within 12 bars of the UHV bar


def session_blocks(f):
    lab = f.session.values
    blk = np.cumsum(np.r_[True, lab[1:] != lab[:-1]])
    return blk


def prev_session_levels(d, f):
    blk = session_blocks(f)
    g = pd.DataFrame({"h": d.high.values, "l": d.low.values, "b": blk})
    agg = g.groupby("b").agg(h=("h", "max"), l=("l", "min"))
    ph = agg.h.shift(1).reindex(blk).values   # previous completed session block
    pl = agg.l.shift(1).reindex(blk).values
    return ph, pl


def pivots(d):
    h, l = d.high.values, d.low.values
    n = len(h); k = PIVOT_K
    ph = np.zeros(n, bool); pl = np.zeros(n, bool)
    for j in range(k, n - k):
        if h[j] == h[j - k:j + k + 1].max(): ph[j] = True
        if l[j] == l[j - k:j + k + 1].min(): pl[j] = True
    return ph, pl   # confirmed at j+k


def run(d, f, side, uhv_mult=1.75, vol_n=10, use_sweep=True, use_uhv=True, use_cisd=True,
        sessions=("NY", "Overlap"), r_targets=(1.0, 2.0), be_after_tp1=False, partial=0.5,
        inside_rule="cisd", cisd_ref="high"):
    o, h, l, c, v = (d[x].values for x in ("open", "high", "low", "close", "volume"))
    v = v.astype(float)
    n = len(d)
    vr = v / pd.Series(v).rolling(vol_n).mean().shift(1).values
    sess = f.session.values
    atr = f.atr.values
    psh, psl = prev_session_levels(d, f)
    pvh, pvl = pivots(d)
    s = 1 if side == "BUY" else -1
    # mirror price for sells so that one code path handles both
    H, L = (h, l) if s == 1 else (-l, -h)
    O, C = (o, c) if s == 1 else (-o, -c)
    PSL = psl if s == 1 else -psh
    PIV = pvl if s == 1 else pvh
    trades = []
    i = 300
    state = None
    while i < n - 1:
        # --- liquidity levels known at bar i (from bars < i) ---
        swept = False; lvl_name = None
        if not use_sweep:
            swept = True; lvl_name = "none"
        else:
            if np.isfinite(PSL[i]) and L[i] < PSL[i] and L[i - 1] >= PSL[i]:
                swept, lvl_name = True, "prev_session"
            else:
                lo = max(0, i - SWING_LOOKBACK)
                js = np.where(PIV[lo:i - PIVOT_K])[0] + lo   # pivots confirmed by bar i-1
                for j in js[::-1]:
                    lev = L[j]
                    if L[i] < lev and L[j + 1:i].min() >= lev:
                        swept, lvl_name = True, "swing"; break
        if state is None and swept:
            state = dict(sweep=i, lvl=lvl_name, uhv=None)
        if state is not None:
            # look for UHV
            if use_uhv:
                if vr[i] >= uhv_mult and i - state["sweep"] <= W_UHV:
                    state["uhv"] = i          # latest UHV in window
                if state["uhv"] is None and i - state["sweep"] > W_UHV:
                    state = None; i += 1; continue
            else:
                if state["uhv"] is None:
                    state["uhv"] = i          # anchor = sweep bar
            u = state["uhv"]
            if u is not None and i > u:
                # invalidation: close beyond UHV extreme
                if C[i] < L[u]:
                    state = None; i += 1; continue
                if i - u > W_TRIG:
                    state = None; i += 1; continue
                # CISD level
                lo_bar = state["sweep"] + int(np.argmin(L[state["sweep"]:i]))
                j = lo_bar
                while j > 0 and not (C[j] < O[j]): j -= 1       # nearest bearish candle at/before low
                while j > 0 and C[j - 1] < O[j - 1]: j -= 1     # start of that bearish run
                # CISD candle = first candle of that bearish run; it must not be an inside candle:
                # if it is, step back to its mother candle (the candle whose range contains it).
                if inside_rule == "cisd":
                    while j > 0 and H[j] <= H[j - 1] and L[j] >= L[j - 1]: j -= 1
                cisd = H[j] if cisd_ref == "high" else O[j]
                level = max(H[u], cisd) if use_cisd else H[u]
                inside = inside_rule == "trigger" and (H[i] <= H[i - 1]) and (L[i] >= L[i - 1])
                if C[i] > O[i] and C[i] > level and not inside and sess[i] in sessions:
                    t = trade(d, i, u, s, H, L, O, C, atr, r_targets, be_after_tp1, partial,
                              dict(sweep_bar=state["sweep"], level=state["lvl"], uhv_ratio=vr[u],
                                   cisd_level=s * cisd, session=sess[i]))
                    state = None
                    if t:
                        trades.append(t); i = t["exit_i"] + 1; continue
        i += 1
    return pd.DataFrame(trades)


def trade(d, i, u, s, H, L, O, C, atr, r_targets, be, partial, info):
    n = len(H)
    if i + 1 >= n: return None
    e = O[i + 1]
    sl = L[u] - SL_BUF
    risk = e - sl
    if risk <= 0.2: return None
    tp1, tp2 = e + r_targets[0] * risk, e + r_targets[-1] * risk
    got1 = False; stop = sl; realised = 0.0
    mfe = mae = 0.0
    for k in range(i + 1, min(n, i + 1 + MAX_HOLD)):
        mfe = max(mfe, (H[k] - e) / risk); mae = max(mae, (e - L[k]) / risk)
        if L[k] <= stop:                         # stop first (conservative)
            realised += (1 - partial if got1 else 1.0) * ((stop - e) / risk); exit_k, why = k, ("BE/SL after TP1" if got1 else "SL")
            break
        if not got1 and H[k] >= tp1 and len(r_targets) > 1:
            got1 = True; realised += partial * r_targets[0]
            if be: stop = e
        if H[k] >= tp2:
            realised += (1 - partial if got1 and len(r_targets) > 1 else 1.0) * r_targets[-1]; exit_k, why = k, "TP"
            break
    else:
        exit_k = min(n, i + 1 + MAX_HOLD) - 1
        realised += (1 - partial if got1 and len(r_targets) > 1 else 1.0) * ((C[exit_k] - e) / risk); why = "time"
    realised -= 0.40 / risk                       # costs in R
    t = d.index
    return dict(time=t[i + 1], side="BUY" if s == 1 else "SELL", entry=s * e, sl=s * sl,
                tp1=s * tp1, tp2=s * tp2, risk_usd=risk, risk_atr=risk / atr[i], R=realised,
                mfe_R=mfe, mae_R=mae, exit_time=t[exit_k], exit_reason=why, exit_i=exit_k,
                bars_held=exit_k - i, uhv_time=t[u], **info)


def summary(tr, label):
    if len(tr) == 0:
        return dict(model=label, n=0)
    r = tr.R.values
    eq = np.cumsum(r); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    losses = r <= 0
    mcl = max((len(x) for x in "".join("L" if z else "W" for z in losses).split("W")), default=0)
    gp, gl = r[r > 0].sum(), -r[r <= 0].sum()
    wk = max(1, (tr.time.iloc[-1] - tr.time.iloc[0]).days / 7)
    return dict(model=label, n=len(r), per_wk=round(len(r) / wk, 1), win=round((r > 0).mean() * 100, 1),
                avgR=round(r.mean(), 3), sumR=round(r.sum(), 1), PF=round(gp / gl, 2) if gl else np.inf,
                maxDD_R=round(dd, 1), max_consec_L=mcl, avg_win=round(r[r > 0].mean(), 2) if (r > 0).any() else 0,
                avg_loss=round(r[r <= 0].mean(), 2) if losses.any() else 0, med_risk_atr=round(tr.risk_atr.median(), 2),
                med_mae=round(tr.mae_R.median(), 2))


if __name__ == "__main__":
    d = load("../data/OANDA_XAUUSD_M5.csv"); f = features(d)
    SPLIT = pd.Timestamp("2026-10-01", tz="UTC")
    rows = []; logs = []
    US = ("NY", "Overlap"); ALL = ("Asia", "London", "NY", "Overlap")
    configs = [
        ("D: Sweep+UHV+CISD (YOUR MODEL)", dict()),
        ("D, CISD level = open of CISD candle", dict(cisd_ref="open")),
        ("D-old: no-inside on entry candle, CISD=open", dict(inside_rule="trigger", cisd_ref="open")),
        ("A: Sweep+UHV, no CISD (close>UHV high)", dict(use_cisd=False)),
        ("B: UHV+CISD, no sweep", dict(use_sweep=False)),
        ("C: Sweep+CISD, no UHV", dict(use_uhv=False)),
        ("D, all sessions", dict(sessions=ALL)),
        ("D, UHV 2.0x", dict(uhv_mult=2.0)),
        ("D, UHV 1.5x", dict(uhv_mult=1.5)),
        ("D, vol baseline 20 bars", dict(vol_n=20)),
        ("D, fixed 1R", dict(r_targets=(1.0,))),
        ("D, fixed 1.5R", dict(r_targets=(1.5,))),
        ("D, fixed 2R", dict(r_targets=(2.0,))),
        ("D, 50%@1R + 50%@2R, BE after TP1", dict(be_after_tp1=True)),
    ]
    for side in ("BUY", "SELL"):
        for name, kw in configs:
            tr = run(d, f, side, **kw)
            for per, sub in (("ALL", tr), ("IS <Oct", tr[tr.time < SPLIT] if len(tr) else tr),
                             ("OOS >=Oct", tr[tr.time >= SPLIT] if len(tr) else tr)):
                rows.append(dict(side=side, period=per, **summary(sub, name)))
            if name.startswith("D: "):
                logs.append(tr)
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(R.to_string(index=False))
    R.to_csv("../reports/user_model_results.csv", index=False)
    L = pd.concat(logs); L.to_csv("../reports/user_model_trade_log.csv", index=False)
    print("\nBy session (all-session variant):")
    for side in ("BUY", "SELL"):
        tr = run(d, f, side, sessions=ALL)
        print(side, tr.groupby("session").R.agg(["count", "mean", "sum"]).round(2).to_dict("index"))
        print(side, "by level", tr.groupby("level").R.agg(["count", "mean"]).round(2).to_dict("index"))
