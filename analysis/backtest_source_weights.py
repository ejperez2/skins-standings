# Re-fit the weighted-average blend (Vegas / TeamRankings / ESPN BPI / CBS) on 2023-26 player-level snapshots,
# by stage of season, leave-one-season-out. Error = projected final skins (blend of each source's player total)
# minus final skins. Only rows where all four sources exist.
import pandas as pd, numpy as np, itertools
p = pd.read_csv('archive/history/player_snapshots_2022-25.csv')
p = p[p.season != '2022-23'].rename(columns={'vegas': 'V', 'tr': 'TR', 'espn': 'E', 'cbs': 'C', 'skins': 'actual'})
p['date'] = p.timestamp.str[:10]
a = pd.read_csv('archive/2025-26/standings_history.csv')
a = a.rename(columns={'vegas_consensus': 'V', 'team_rankings': 'TR', 'espn_bpi': 'E', 'cbs_sports': 'C', 'actual_skins': 'actual'})
a['season'] = '2025-26'; a['games_played'] = a.actual / a.skins_pct
r = pd.read_csv('archive/history/rosters_and_finals_2022-26.csv')
r['sk'] = np.where(r.pick == 'W', r.final_wins, 82 - r.final_wins)
fin = r.groupby(['season', 'player']).agg(final=('sk', 'sum'), n=('sk', 'size')).reset_index()
cols = ['season', 'date', 'player', 'actual', 'games_played', 'V', 'TR', 'E', 'C']
D = pd.concat([p[cols], a[cols]]).merge(fin, on=['season', 'player']).dropna(subset=['V', 'TR', 'E', 'C'])
D['gpt'] = D.games_played / D.n
D['stage'] = pd.cut(D.gpt, [-1, 15, 30, 50, 82], labels=['<15', '15-30', '30-50', '50+'])
D = D[D.gpt < 75]
print('rows by season x stage:'); print(D.groupby(['season', 'stage'], observed=True).size().unstack().to_string())
grid = [w for w in itertools.product(np.arange(0, 1.0001, 0.05), repeat=3) if sum(w) <= 1.0001]
grid = np.array([[w[0], w[1], w[2], 1 - sum(w)] for w in grid])
X = ['V', 'TR', 'E', 'C']
def mse(df, w): return (((df[X].values @ w) - df.final.values) ** 2).mean()
def season_mse(df, w): return np.mean([mse(g, w) for _, g in df.groupby('season')])   # seasons weigh equally
cur = np.array([.4, .2, .2, .2]); eq = np.array([.25] * 4)
rows = []
for st, ds in D.groupby('stage', observed=True):
    for test in ds.season.unique():
        tr, te = ds[ds.season != test], ds[ds.season == test]
        best = grid[np.argmin([season_mse(tr, w) for w in grid])]
        rows.append(dict(stage=st, test=test, fit_on_others='/'.join(f'{x:.2f}' for x in best),
                         rmse_current=np.sqrt(mse(te, cur)), rmse_equal=np.sqrt(mse(te, eq)), rmse_refit=np.sqrt(mse(te, best)),
                         **{f'rmse_{x}_only': np.sqrt(mse(te, np.eye(4)[i])) for i, x in enumerate(X)}))
R = pd.DataFrame(rows)
print('\nHeld-out RMSE of final player skins (weights V/TR/E/C fit on the other two seasons):')
print(R.round(2).to_string(index=False))
print('\nMean over held-out seasons:'); print(R.groupby('stage', observed=True)[[c for c in R.columns if c.startswith('rmse')]].mean().round(2).to_string())
print('\nAll three seasons, best weights by stage:')
for st, ds in D.groupby('stage', observed=True):
    best = grid[np.argmin([season_mse(ds, w) for w in grid])]
    print(st, 'V/TR/E/C =', best.round(2), 'rmse %.2f vs current %.2f' % (np.sqrt(season_mse(ds, best)), np.sqrt(season_mse(ds, cur))))
