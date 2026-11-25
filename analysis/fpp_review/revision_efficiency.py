# FPP2 3.3 ("residuals should be uncorrelated and have zero mean") applied to a forecast that is revised daily.
# If the projection P_t of a team's final wins uses all information, then
#   (a) the remaining miss, final - P_t, has mean 0 and is unrelated to the most recent revision P_t - P_{t-lag};
#   (b) successive revisions are uncorrelated (the projection is a martingale).
# A positive slope in (a) or correlation in (b) means the source under-reacts: it should move further than it does.
# Usage: python3 analysis/fpp_review/revision_efficiency.py   (run from the repo root)
import pandas as pd, numpy as np

r = pd.read_csv('archive/history/rosters_and_finals_2022-26.csv')
fin = r.drop_duplicates(['season', 'team_bbr'])[['season', 'team_bbr', 'final_wins']]
s = pd.read_csv('archive/history/team_snapshots_2022-26.csv', parse_dates=['date'])
s = s.merge(fin, on=['season', 'team_bbr'])

def boot_ci(df, f, n=2000, seed=1):
    """Season-and-team block bootstrap: resample team-seasons (snapshots of one team in one season move together)."""
    rng = np.random.default_rng(seed)
    keys = df[['season', 'team_bbr']].drop_duplicates().values
    g = {tuple(k): d for k, d in df.groupby(['season', 'team_bbr'])}
    out = []
    for _ in range(n):
        pick = keys[rng.integers(0, len(keys), len(keys))]
        out.append(f(pd.concat([g[tuple(k)] for k in pick])))
    return np.percentile(out, [2.5, 97.5])

def slope(d, x, y):
    return np.polyfit(d[x], d[y], 1)[0]

print('Sources by season:', s.groupby('season').source.agg(lambda x: ', '.join(sorted(set(x)))).to_dict(), '\n')
rows = []
for lag in (7, 14, 21):
    pairs = []
    for (season, team), d in s.sort_values('date').groupby(['season', 'team_bbr']):
        d = d.set_index('date')
        for t, row in d.iterrows():
            prev = d[(d.index <= t - pd.Timedelta(days=lag)) & (d.index >= t - pd.Timedelta(days=lag + 4))]
            nxt = d[(d.index >= t + pd.Timedelta(days=lag)) & (d.index <= t + pd.Timedelta(days=lag + 4))]
            if prev.empty or prev.source.iloc[-1] != row.source:
                continue
            rec = dict(season=season, team_bbr=team, gp=row.approx_games_played, P=row.proj_wins,
                       rev_past=row.proj_wins - prev.proj_wins.iloc[-1], miss=row.final_wins - row.proj_wins)
            rec['rev_next'] = (nxt.proj_wins.iloc[0] - row.proj_wins) if (not nxt.empty and nxt.source.iloc[0] == row.source) else np.nan
            pairs.append(rec)
    P = pd.DataFrame(pairs)
    P = P[P.gp < 70]
    for stage, d in P.groupby(pd.cut(P.gp, [-1, 20, 40, 70], labels=['<20', '20-40', '40-70']), observed=True):
        b = slope(d, 'rev_past', 'miss')
        lo, hi = boot_ci(d, lambda z: slope(z, 'rev_past', 'miss'), n=500)
        dn = d.dropna(subset=['rev_next'])
        c = dn.rev_past.corr(dn.rev_next) if len(dn) > 30 else np.nan
        rows.append(dict(lag_days=lag, games=stage, n=len(d), mean_miss=d.miss.mean(), sd_past_rev=d.rev_past.std(),
                         slope_miss_on_rev=b, ci_lo=lo, ci_hi=hi, corr_rev_next=c))
R = pd.DataFrame(rows)
print('Archive 2022-26 (team snapshots, final wins known). slope > 0 = the source under-reacts.')
print(R.round(3).to_string(index=False))

# This season: per-source daily projections, no finals yet, so only the martingale test (b).
t = pd.read_csv('team_projection_history.csv', parse_dates=['date'])
print('\n2026-27 so far: corr(revision over previous 7 days, revision over next 7 days), pooled over teams')
for src in ['vegas', 'tr', 'espn', 'cbs', 'weighted', 'darko', 'crafted']:
    x = t.pivot_table(index='date', columns='team', values=src)
    x = x.asfreq('D').ffill(limit=2)
    past, nxt = x - x.shift(7), x.shift(-7) - x
    a = pd.DataFrame({'p': past.stack(), 'n': nxt.stack()}).dropna()
    a = a[a.index.get_level_values(0).weekday == 0]          # non-overlapping weekly windows (Mondays)
    if len(a) > 30:
        print(f'  {src:9s} n={len(a):3d}  corr={a.p.corr(a.n):+.2f}  slope={np.polyfit(a.p, a.n, 1)[0]:+.2f}')
