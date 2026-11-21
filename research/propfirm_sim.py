"""Monte-Carlo: days to pass a 2-phase prop challenge using the real trade results (R) of the best candidate:
BUY only, ATR exits, skip Asia session (TradingView Deep Backtest 2023-01..2026-11).
Trades are resampled with their real R values; time between trades resampled from the real gaps.
Rules modelled: Phase 1 +8%, Phase 2 +5%, max overall loss 10% (static), max daily loss 5%."""
import numpy as np, pandas as pd
rng = np.random.default_rng(7)
T = pd.read_csv('../data/deep_backtest/run_2023_now_parsed.csv', parse_dates=['time']).sort_values('time')
T = T[~T.session.str.contains('Asia')]
gaps = T.time.diff().dt.total_seconds().dropna().values / 86400  # calendar days between trades
sets = {"All 2023-2026 (realistic)": T, "2023-2024 only (quiet market)": T[T['Date and time'] < '2025'],
        "2025-2026 only (volatile market)": T[T['Date and time'] >= '2025']}
def phase(R, g, risk, target, dd=10, daily=5, max_days=365):
    eq = 0.0; day = 0.0
    while day < max_days:
        day += rng.choice(g)
        r = rng.choice(R) * risk
        if r <= -daily: return "fail", day
        eq += r
        if eq <= -dd: return "fail", day
        if eq >= target: return "pass", day
    return "timeout", day
rows = []
for name, S in sets.items():
    R = S.R.values
    for risk in (0.5, 1.0, 1.5, 2.0):
        res = []
        for _ in range(4000):
            a, d1 = phase(R, gaps, risk, 8)
            if a != "pass": res.append((a, d1)); continue
            b, d2 = phase(R, gaps, risk, 5)
            res.append((b, d1 + d2))
        st = np.array([r[0] for r in res]); dd = np.array([r[1] for r in res])
        ok = dd[st == "pass"]
        rows.append(dict(sample=name, risk_pct=risk, pass_pct=round((st == "pass").mean() * 100), fail_pct=round((st == "fail").mean() * 100),
                         not_done_1yr_pct=round((st == "timeout").mean() * 100),
                         median_days=round(np.median(ok)) if len(ok) else None,
                         fast_25pct_days=round(np.percentile(ok, 25)) if len(ok) else None,
                         slow_75pct_days=round(np.percentile(ok, 75)) if len(ok) else None))
R = pd.DataFrame(rows); pd.set_option('display.width', 200); print(R.to_string(index=False))
R.to_csv('../reports/propfirm_sim.csv', index=False)
print("\ntrades/week:", round(len(T) / ((T.time.max() - T.time.min()).days / 7), 2), "| avg R:", round(T.R.mean(), 3))
