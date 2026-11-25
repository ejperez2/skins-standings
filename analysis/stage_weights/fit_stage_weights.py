# Source weights for each fifth of the season (Vegas / TeamRankings / ESPN BPI / CBS), fit on past seasons.
# Data: player-level snapshots where all four sources exist (2023-24, 2024-25 from archive/history, 2025-26 from
# archive/2025-26), scored against each roster's final skins. Error = blend of the four player totals - final skins.
# With 3 seasons (17 rosters) a free fit per fifth overfits, so each fifth's weights are shrunk toward equal weights:
#   w_f = argmin  mean_season MSE_f(w) + lam * |w - 1/4|^2 * S_f,   S_f = that fifth's MSE under equal weights
# lam is picked by leave-one-season-out (fit on two seasons, score the third, every fifth). Seasons count equally.
# Usage: python3 analysis/stage_weights/fit_stage_weights.py   (run from the repo root)
import pandas as pd, numpy as np, itertools
X = ['V', 'TR', 'E', 'C']
p = pd.read_csv('archive/history/player_snapshots_2022-25.csv')
p = p[p.season != '2022-23'].rename(columns={'vegas': 'V', 'tr': 'TR', 'espn': 'E', 'cbs': 'C'})
p['date'] = p.timestamp.str[:10]
a = pd.read_csv('archive/2025-26/standings_history.csv').rename(
    columns={'vegas_consensus': 'V', 'team_rankings': 'TR', 'espn_bpi': 'E', 'cbs_sports': 'C', 'actual_skins': 'skins'})
a['season'] = '2025-26'; a['games_played'] = a.skins / a.skins_pct
r = pd.read_csv('archive/history/rosters_and_finals_2022-26.csv')
r['sk'] = np.where(r.pick == 'W', r.final_wins, 82 - r.final_wins)
fin = r.groupby(['season', 'player']).agg(final=('sk', 'sum'), n=('sk', 'size')).reset_index()
cols = ['season', 'date', 'player', 'games_played'] + X
D = pd.concat([p[cols], a[cols]]).merge(fin, on=['season', 'player']).dropna(subset=X)
D = D.groupby(['season', 'date', 'player']).last().reset_index()          # one snapshot per player per day
D['gpt'] = D.games_played / D.n
D = D[(D.gpt >= 0) & (D.gpt < 82)]
EDGES = np.arange(0, 82.01, 82 / 5)
D['fifth'] = np.clip(np.digitize(D.gpt, EDGES[1:-1]) + 1, 1, 5)
print('Player-days by season x fifth:')
print(D.groupby(['season', 'fifth']).size().unstack(fill_value=0).to_string(), '\n')

GRID = np.array([[*w, 1 - sum(w)] for w in itertools.product(np.arange(0, 1.0001, 0.05), repeat=3) if sum(w) <= 1.0001])
EQ, CUR = np.full(4, .25), np.array([.4, .2, .2, .2])
def season_mse(df, W):            # W: (k, 4) -> (k,) mean over seasons of MSE
    out = []
    for _, g in df.groupby('season'):
        out.append((((g[X].values @ W.T) - g.final.values[:, None]) ** 2).mean(0))
    return np.mean(out, 0)
def fit(df, lam):
    m = season_mse(df, GRID)
    s = season_mse(df, EQ[None])[0]
    return GRID[np.argmin(m + lam * s * ((GRID - EQ) ** 2).sum(1))]

LAMS = [0, 1, 2, 5, 10, 20, 50, 100, 1e9]
seasons = sorted(D.season.unique())
res = []
for lam in LAMS:
    for f in range(1, 6):
        for test in seasons:
            tr, te = D[(D.fifth == f) & (D.season != test)], D[(D.fifth == f) & (D.season == test)]
            if te.empty or tr.empty:
                continue
            w = fit(tr, lam)
            res.append(dict(lam=lam, fifth=f, test=test, mse=season_mse(te, w[None])[0],
                            mse_eq=season_mse(te, EQ[None])[0], mse_cur=season_mse(te, CUR[None])[0]))
R = pd.DataFrame(res)
print('Held-out RMSE of final player skins by shrinkage (lam=0 free fit, lam=1e9 equal weights), mean over seasons:')
T = R.groupby(['lam', 'fifth']).mse.mean().unstack().pow(.5)
T['all fifths'] = R.groupby('lam').mse.mean().pow(.5)
print(T.round(2).to_string())
base = R[R.lam == 0].groupby('fifth')[['mse_eq', 'mse_cur']].mean().pow(.5).T
base['all fifths'] = R[R.lam == 0][['mse_eq', 'mse_cur']].mean().pow(.5).values
print('\nFor reference, equal weights and the current 40/20/20/20:')
print(base.rename(index={'mse_eq': 'equal', 'mse_cur': 'current 40/20/20/20'}).round(2).to_string())
best_lam = R.groupby('lam').mse.mean().idxmin()
wins = R[R.lam == best_lam].assign(beat_cur=lambda d: d.mse < d.mse_cur, beat_eq=lambda d: d.mse < d.mse_eq)
print(f'\nChosen lam = {best_lam:g}: beats current in {wins.beat_cur.sum()}/{len(wins)} held-out season-fifths, '
      f'beats equal in {wins.beat_eq.sum()}/{len(wins)}')

print('\nFinal weights (all three seasons, chosen lam), V / TR / E / C, and unshrunk fit for comparison:')
out = []
for f in range(1, 6):
    df = D[D.fifth == f]
    w, w0 = fit(df, best_lam), fit(df, 0)
    single = {x: np.sqrt(season_mse(df, np.eye(4)[i][None])[0]) for i, x in enumerate(X)}
    out.append(dict(fifth=f, games=f'{EDGES[f-1]:.1f}-{EDGES[f]:.1f}', **{x: w[i] for i, x in enumerate(X)},
                    free_fit='/'.join(f'{v:.2f}' for v in w0), **{f'rmse_{x}_only': v for x, v in single.items()}))
W = pd.DataFrame(out)
print(W.round(2).to_string(index=False))
W[['fifth', 'games'] + X].round(2).to_csv('analysis/stage_weights/stage_weights.csv', index=False)
