# This season's first fifth, team level: how well did each source's projection on a given early date predict each
# team's win rate over the games played since? (Only check available before finals; game luck dominates.)
# Error per team = (projected remaining win rate - actual win rate since) * 82, so it reads in wins over a season.
# Usage: python3 analysis/stage_weights/first_fifth_2026.py   (run from the repo root)
import pandas as pd, numpy as np
t = pd.read_csv('team_projection_history.csv', parse_dates=['date'])
last = t[t.date == t.date.max()].set_index('team')
S = ['vegas', 'tr', 'espn', 'cbs', 'darko', 'crafted']
def blend(df, w):
    v = df[list(w)].values; m = ~np.isnan(v); w = np.array(list(w.values()))
    return np.nansum(v * w, 1) / (m * w).sum(1)
print(f'Scored against records through {t.date.max().date()}')
for origin in ['2026-10-24', '2026-10-28', '2026-11-01', '2026-11-05']:
    o = t[t.date == origin].set_index('team')
    o['equal'] = blend(o, dict(vegas=.25, tr=.25, espn=.25, cbs=.25))
    o['current'] = blend(o, dict(vegas=.4, tr=.2, espn=.2, cbs=.2))
    g0 = o.wins + o.losses; g1 = last.wins + last.losses - g0
    actual = (last.wins - o.wins) / g1
    gp = g0.mean(); luck = np.sqrt((actual * (1 - actual)).mean() / g1.mean()) * 82
    row = {}
    for s in S + ['current', 'equal']:
        rate = (o[s] - o.wins) / (82 - g0)
        e = ((rate - actual) * 82).dropna()
        row[s] = f'{np.sqrt((e ** 2).mean()):.2f}' + ('' if len(e) == 30 else f' (n={len(e)})')
    print(f'origin {origin} ({gp:.1f} games played, {g1.mean():.1f} since; game luck alone ~{luck:.1f}):', row)
