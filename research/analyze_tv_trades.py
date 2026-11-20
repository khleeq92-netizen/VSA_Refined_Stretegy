"""Analyse a TradingView 'List of Trades' export (times in chart time zone, here IST UTC+5:30)."""
import sys, numpy as np, pandas as pd
from zoneinfo import ZoneInfo
p = sys.argv[1]; TZ = sys.argv[2] if len(sys.argv) > 2 else "Asia/Kolkata"
t = pd.read_csv(p)
en = t[t.Type.str.startswith("Entry")].set_index("Trade number")
ex = t[t.Type.str.startswith("Exit")].groupby("Trade number").agg(exit_time=("Date and time", "last"), pnl=("Net PnL USD", "first"),
                                                                    signal=("Signal", "last"), mfe=("Favorable excursion USD", "first"), mae=("Adverse excursion USD", "first"))
T = en[["Date and time", "Price USD", "Size (qty)"]].join(ex)
T["time"] = pd.to_datetime(T["Date and time"]).dt.tz_localize(TZ)
T["R"] = T.pnl / 100.0
T["win"] = T.pnl > 0
utc = T.time.dt.tz_convert("UTC")
lon = T.time.dt.tz_convert("Europe/London"); ny = T.time.dt.tz_convert("America/New_York")
lh = lon.dt.hour + lon.dt.minute / 60; nh = ny.dt.hour + ny.dt.minute / 60
inl = (lh >= 7) & (lh < 16.5); inn = (nh >= 8) & (nh < 17)
T["session"] = np.where(inl & inn & (lh >= 8), "Overlap", np.where(inl, "London", np.where(inn, "NY", "Asia")))
def s(g):
    r = g.R.values; eq = np.cumsum(r); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max() if len(r) else 0
    streak = max((len(x) for x in "".join("L" if w else "W" for w in ~g.win.values).split("W")), default=0)
    gl = -r[r < 0].sum()
    return pd.Series(dict(trades=len(r), win_pct=round(g.win.mean() * 100, 1), total_R=round(r.sum(), 2), avg_R=round(r.mean(), 3),
                          PF=round(r[r > 0].sum() / gl, 2) if gl else np.inf, maxDD_R=round(dd, 2), max_losing_streak=streak))
print("ALL"); print(s(T).to_string())
DEV = pd.Timestamp("2026-08-16", tz="UTC")
print("\nBy period"); print(pd.DataFrame({"Unseen (before 16-Aug-2026)": s(T[utc < DEV]), "Development window (16-Aug..20-Nov-2026)": s(T[utc >= DEV])}).T.to_string())
print("\nBy market phase (gold: up to ~3-Mar-2026 peak, then down)")
ph = np.where(utc < pd.Timestamp("2026-03-04", tz="UTC"), "1 Bull (Dec-Feb)", np.where(utc < pd.Timestamp("2026-08-16", tz="UTC"), "2 Top & decline (Mar-mid Aug)", "3 Bear (mid Aug-Nov)"))
print(T.groupby(ph).apply(s).to_string())
print("\nBy quarter"); print(T.groupby(utc.dt.to_period("Q").astype(str)).apply(s).to_string())
print("\nBy session"); print(T.groupby("session").apply(s).to_string())
print("\nBy IST entry hour"); print(T.groupby(T.time.dt.hour).apply(s)[["trades", "win_pct", "total_R"]].T.to_string())
print("\nExit reasons", T.signal.value_counts().to_dict(), "| loss trades' best excursion (USD, median):", T[~T.win].mfe.median())
T.to_csv(p.replace(".csv", "_parsed.csv"))
