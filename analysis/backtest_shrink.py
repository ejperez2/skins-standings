# Should rest-of-season projections be pulled toward (or pushed away from) .500 by stage of season?
# Team level, 2022-26, every archived snapshot: rest-of-season wins = left * (0.5 + lambda * (rate - 0.5)),
# lambda per stage fit on the other seasons (leave-one-season-out), scored by squared error of final wins.
import numpy as np, pandas as pd, sys
sys.path.insert(0, 'analysis'); from synthetic_leagues import ros, snaps, games, records, shrink_factors, STAGES, stage_of
rows = []
for season in sorted(snaps.season.unique()):
    lam = shrink_factors(season)
    r = ros[ros.season == season].sort_values('team_bbr'); teams = r.team_bbr.tolist(); ti = {t: i for i, t in enumerate(teams)}
    final = r.final_wins.values; gs = games[games.season == season]
    for d, s in snaps[snaps.season == season].groupby('date'):
        W, L, _, _ = records(gs, d, ti); left = 82 - W - L; st = stage_of((W + L).mean())
        proj = np.clip(s.set_index('team_bbr').loc[teams, 'proj_wins'].values, W, W + left)
        shr = W + 0.5 * left + lam[st] * (proj - W - 0.5 * left)
        rows.append(dict(season=season, stage=['<15', '15-30', '30-50', '50+'][st], lam=lam[st],
                         mse_proj=np.mean((final - proj) ** 2), mse_shrunk=np.mean((final - shr) ** 2)))
R = pd.DataFrame(rows)
print('Held-out mean squared error of final team wins (lower is better):')
T = R.groupby(['stage', 'season']).agg(lam=('lam', 'first'), proj=('mse_proj', 'mean'), shrunk=('mse_shrunk', 'mean')).round(2)
print(T.to_string())
print('\nBy stage, mean over seasons:'); print(T.groupby('stage')[['proj', 'shrunk']].mean().round(2).to_string())
print('seasons improved by stage:', T.assign(b=T.shrunk < T.proj).groupby('stage').b.sum().to_dict())
