"""Model v2: trader's refined rules (message of 2026-11-20).

BUY
  1. UHV candle is RED (close < open), volume >= UHV_MULT x mean(prior 10 bars).
  2. Background "at the bottom": the BG_N (3) candles immediately before it are also red.
  3. Location: the UHV candle overlaps an active higher-timeframe bullish FVG or demand zone (H1 / H4).
     A red UHV candle anywhere else (e.g. at the top) is ignored.
  4. A later candle trades BELOW the UHV low (sweep of the UHV low), within W_SWEEP bars.
  5. A LATER candle (not the sweep candle) is bullish and closes ABOVE the UHV high
     (and above the CISD level when the CISD variant is on), within W_TRIG bars of the sweep.
  6. Entry next bar open. SL = lowest low since the UHV candle - $0.10. TP 50% @1R, rest @2R.
SELL = mirror: big GREEN UHV after 3 green candles, inside a bearish HTF FVG / supply zone,
sweep of the UHV high, later bearish close below the UHV low.

Objective HTF zone definitions (completed HTF candles only, no lookahead):
  FVG (bullish): HTF candle k low > HTF candle k-2 high -> zone [high(k-2), low(k)]; usable from the
      close of candle k; dead once an M5 candle closes below the zone bottom. Max age 5 days.
  Demand zone (H1 order block): the last red H1 candle before an H1 displacement candle that is bullish,
      has range >= 1.5 x H1 ATR(14) and closes above that red candle's high. Zone = [low, high] of the
      red candle; usable from the displacement candle's close; dead on an M5 close below its low.
"""
import numpy as np, pandas as pd
from vsa_lib import load, features
from backtest_user_model import prev_session_levels, summary

COST = 0.40; SL_BUF = 0.10; MAX_HOLD = 96
ZONE_MAX_AGE = pd.Timedelta(days=5)


def htf(d, rule):
    g = d.resample(rule, label="left", closed="left")
    b = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(),
                      "close": g.close.last()}).dropna()
    b["avail"] = b.index + pd.Timedelta(rule)   # known only after the HTF candle closes
    return b


def zones(d, kinds=("fvg_H1", "fvg_H4", "ob_H1")):
    """Return list of zones: dict(side, bot, top, avail, kind)."""
    Z = []
    for tf, name in (("1h", "fvg_H1"), ("4h", "fvg_H4")):
        if name not in kinds:
            continue
        b = htf(d, tf); h, l, a = b.high.values, b.low.values, b.avail.values
        for k in range(2, len(b)):
            if l[k] > h[k - 2]:
                Z.append(dict(side=1, bot=h[k - 2], top=l[k], avail=a[k], kind=name))
            if h[k] < l[k - 2]:
                Z.append(dict(side=-1, bot=h[k], top=l[k - 2], avail=a[k], kind=name))
    if "ob_H1" in kinds:
        b = htf(d, "1h"); o, h, l, c, a = (b[x].values for x in ("open", "high", "low", "close", "avail"))
        tr = np.maximum(h - l, np.maximum(abs(h - np.r_[np.nan, c[:-1]]), abs(l - np.r_[np.nan, c[:-1]])))
        atr = pd.Series(tr).rolling(14).mean().shift(1).values
        for k in range(15, len(b)):
            if not np.isfinite(atr[k]) or (h[k] - l[k]) < 1.5 * atr[k]:
                continue
            if c[k] > o[k]:      # bullish displacement -> demand = last red candle before it
                j = k - 1
                while j > k - 6 and not (c[j] < o[j]): j -= 1
                if c[j] < o[j] and c[k] > h[j]:
                    Z.append(dict(side=1, bot=l[j], top=h[j], avail=a[k], kind="ob_H1"))
            if c[k] < o[k]:
                j = k - 1
                while j > k - 6 and not (c[j] > o[j]): j -= 1
                if c[j] > o[j] and c[k] < l[j]:
                    Z.append(dict(side=-1, bot=l[j], top=h[j], avail=a[k], kind="ob_H1"))
    return Z


def zone_hits(d, Z, side):
    """For each M5 bar: kind of an active same-side zone overlapping the bar ('' if none)."""
    idx = d.index; h, l, c = d.high.values, d.low.values, d.close.values
    out = np.full(len(d), "", dtype=object)
    for z in Z:
        if z["side"] != side:
            continue
        i0 = idx.searchsorted(pd.Timestamp(z["avail"]).tz_localize("UTC") if pd.Timestamp(z["avail"]).tzinfo is None else pd.Timestamp(z["avail"]))
        i1 = idx.searchsorted(idx[min(i0, len(idx) - 1)] + ZONE_MAX_AGE)
        for i in range(i0, min(i1, len(d))):
            if (side == 1 and c[i] < z["bot"]) or (side == -1 and c[i] > z["top"]):
                if l[i] <= z["top"] and h[i] >= z["bot"] and out[i] == "":
                    out[i] = z["kind"]        # the bar that kills the zone still touched it
                break
            if l[i] <= z["top"] and h[i] >= z["bot"] and out[i] == "":
                out[i] = z["kind"]
    return out


def run(d, f, side, zone_kinds=("fvg_H1", "fvg_H4", "ob_H1"), use_zone=True, bg_n=3, uhv_mult=1.75,
        vol_n=10, big=0.0, use_cisd=False, w_sweep=6, w_trig=12, sweep_next_only=False, strong_body=0.0,
        sessions=("NY", "Overlap"), r_targets=(1.0, 2.0), partial=0.5, zcache={}):
    o, h, l, c, v = (d[x].values for x in ("open", "high", "low", "close", "volume"))
    n = len(d); s = 1 if side == "BUY" else -1
    vr = v / pd.Series(v.astype(float)).rolling(vol_n).mean().shift(1).values
    rs = f.rs.values; sess = f.session.values; atr = f.atr.values
    key = (tuple(zone_kinds), s)
    if key not in zcache:
        zcache[key] = zone_hits(d, zones(d, zone_kinds), s)
    zh = zcache[key]
    H, L = (h, l) if s == 1 else (-l, -h)
    O, C = (o, c) if s == 1 else (-o, -c)
    red = C < O   # "against" candle (red for BUY, green for SELL) in mirrored space
    trades = []; i = 300
    while i < n - 2:
        u = i
        ok = red[u] and vr[u] >= uhv_mult and rs[u] >= big and red[u - bg_n:u].all() if bg_n else red[u] and vr[u] >= uhv_mult and rs[u] >= big
        if ok and use_zone and zh[u] == "":
            ok = False
        if not ok:
            i += 1; continue
        # sweep of UHV extreme
        sw = None
        rng = range(u + 1, min(n, u + 2)) if sweep_next_only else range(u + 1, min(n, u + 1 + w_sweep))
        for k in rng:
            if L[k] < L[u]:
                sw = k; break
            if C[k] > H[u]:       # broke out the other way before any sweep -> no setup
                break
        if sw is None:
            i += 1; continue
        # CISD level: open of the run of red candles that ends at the UHV candle
        j = u
        while j > 0 and red[j - 1]: j -= 1
        while j > 0 and H[j] <= H[j - 1] and L[j] >= L[j - 1]: j -= 1   # CISD candle must not be inside
        cisd = H[j]
        level = max(H[u], cisd) if use_cisd else H[u]
        trig = None
        for t in range(sw + 1, min(n - 1, sw + 1 + w_trig)):
            body = abs(C[t] - O[t]) / max(H[t] - L[t], 1e-9)
            if C[t] > O[t] and C[t] > level and body >= strong_body:
                trig = t; break
        if trig is None or sess[trig] not in sessions:
            i = sw + 1; continue
        sl = L[u:trig + 1].min() - SL_BUF
        tr = trade(d, trig, sl, s, H, L, O, C, atr, r_targets, partial)
        if tr:
            tr.update(uhv_time=d.index[u], uhv_ratio=vr[u], zone=zh[u], sweep_time=d.index[sw], session=sess[trig],
                      bars_uhv_to_trig=trig - u)
            trades.append(tr); i = tr["exit_i"] + 1
        else:
            i = trig + 1
    return pd.DataFrame(trades)


def trade(d, i, sl, s, H, L, O, C, atr, r_targets, partial):
    n = len(H)
    e = O[i + 1]; risk = e - sl
    if risk <= 0.2: return None
    tp1, tp2 = e + r_targets[0] * risk, e + r_targets[-1] * risk
    two = len(r_targets) > 1
    got1 = False; R = 0.0; mfe = mae = 0.0
    for k in range(i + 1, min(n, i + 1 + MAX_HOLD)):
        mfe = max(mfe, (H[k] - e) / risk); mae = max(mae, (e - L[k]) / risk)
        if L[k] <= sl:
            R += (1 - partial if got1 else 1.0) * -1.0; why = "SL"; break
        if two and not got1 and H[k] >= tp1:
            got1 = True; R += partial * r_targets[0]
        if H[k] >= tp2:
            R += (1 - partial if got1 else 1.0) * r_targets[-1]; why = "TP"; break
    else:
        k = min(n, i + 1 + MAX_HOLD) - 1
        R += (1 - partial if got1 else 1.0) * (C[k] - e) / risk; why = "time"
    R -= COST / risk
    return dict(time=d.index[i + 1], side="BUY" if s == 1 else "SELL", entry=s * e, sl=s * sl,
                tp1=s * tp1, tp2=s * tp2, risk_usd=risk, risk_atr=risk / atr[i], R=R, mfe_R=mfe, mae_R=mae,
                exit_time=d.index[k], exit_reason=why, exit_i=k)


if __name__ == "__main__":
    d = load("../data/OANDA_XAUUSD_M5.csv"); f = features(d)
    SPLIT = pd.Timestamp("2026-10-01", tz="UTC")
    ALL = ("Asia", "London", "NY", "Overlap")
    configs = [
        ("V2 as described (zone+3 bg+sweep UHV ext+close beyond UHV)", {}),
        ("V2 + CISD close required", dict(use_cisd=True)),
        ("V2, sweep must be next candle", dict(sweep_next_only=True)),
        ("V2, big UHV (range>=1.5 ATR)", dict(big=1.5)),
        ("V2, strong trigger body>=50%", dict(strong_body=0.5)),
        ("V2, all sessions", dict(sessions=ALL)),
        ("V2, no zone filter", dict(use_zone=False)),
        ("V2, no 3-candle background", dict(bg_n=0)),
        ("V2, no zone, no background", dict(use_zone=False, bg_n=0)),
        ("V2, FVG only (no OB)", dict(zone_kinds=("fvg_H1", "fvg_H4"))),
        ("V2, fixed 1R", dict(r_targets=(1.0,))),
        ("V2, fixed 1.5R", dict(r_targets=(1.5,))),
        ("V2, fixed 2R", dict(r_targets=(2.0,))),
        ("V2, all sessions, no zone", dict(sessions=ALL, use_zone=False)),
    ]
    rows = []; logs = []
    for side in ("BUY", "SELL"):
        for name, kw in configs:
            tr = run(d, f, side, **kw)
            for per, sub in (("ALL", tr), ("IS", tr[tr.time < SPLIT] if len(tr) else tr),
                             ("OOS", tr[tr.time >= SPLIT] if len(tr) else tr)):
                rows.append(dict(side=side, period=per, **summary(sub, name)))
            if name.startswith("V2 as described") or name == "V2, all sessions":
                tr["variant"] = name; logs.append(tr)
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    cols = ["side", "period", "model", "n", "per_wk", "win", "avgR", "sumR", "PF", "maxDD_R", "max_consec_L", "med_risk_atr"]
    print(R[cols].to_string(index=False))
    R.to_csv("../reports/v2_results.csv", index=False)
    L = pd.concat(logs); L.to_csv("../reports/v2_trade_log.csv", index=False)
    for side in ("BUY", "SELL"):
        tr = L[(L.side == side) & (L.variant == "V2, all sessions")]
        if len(tr):
            print(side, "by session", tr.groupby("session").R.agg(["count", "mean", "sum"]).round(2).to_dict("index"))
            print(side, "by zone", tr.groupby("zone").R.agg(["count", "mean"]).round(2).to_dict("index"))
