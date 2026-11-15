# (1) Real sources vs the history formula on the 4 archived seasons; (2) errors by projection level (floor effects for deep L picks);
# (3) does the early-season size of misses predict later misses (the live TALENT_SD refit)?
import numpy as np, pandas as pd, sys
sys.path.insert(0, sys.argv[1]); from hist import *
from scipy import stats
REPO = sys.argv[2]
ou, G = load(); tg = team_games(G).merge(ou[['season_end', 'team', 'ou_adj', 'w', 'n']], on=['season_end', 'team']); tg['p0'] = tg.ou_adj / 82
seasons = np.sort(ou.season_end.unique())
def loso_proj(g):
    d = tg[tg.k == g].copy(); d['left'] = d.n - g; d['c'] = d.p0 - .5; d['x'] = d.cw / g - d.p0; d['y'] = (d.w - d.cw) / d.left - d.p0
    d['ros'] = np.nan
    for s in seasons:
        tr = d[d.season_end != s]; b = np.linalg.lstsq(tr[['c', 'x']].values, tr.y.values, rcond=None)[0]
        d.loc[d.season_end == s, 'ros'] = d.p0 + d[['c', 'x']].values @ b
    d['proj'] = d.cw + d.left * d.ros; d['err'] = d.w - d.proj
    return d
print('== Errors by projected final wins (history formula, held-out season, 24 seasons) ==')
for g in [13, 30, 50]:
    d = loso_proj(g); d['bin'] = pd.cut(d.proj, [0, 22, 27, 33, 41, 49, 55, 60, 90])
    t = d.groupby('bin', observed=True).err.agg(n='size', mean='mean', se=lambda x: x.std() / np.sqrt(len(x)), sd='std', skew=lambda x: stats.skew(x), p10=lambda x: x.quantile(.1), p90=lambda x: x.quantile(.9))
    print('after %d games' % g); print(t.round(2).to_string())
    lo = d[d.proj < 27]; print('  teams projected under 27 wins: mean miss %+.2f wins (se by season %.2f), share finishing above projection %.0f%%' % (lo.err.mean(), lo.groupby('season_end').err.mean().std() / np.sqrt(lo.season_end.nunique()), 100 * (lo.err > 0).mean()))
# real sources, archived seasons
print('\n== Real sources (archive/history/team_snapshots) vs history formula, same seasons and dates ==')
CODE = {'ATL':'Atlanta Hawks','BOS':'Boston Celtics','BRK':'Brooklyn Nets','CHO':'Charlotte Hornets','CHI':'Chicago Bulls','CLE':'Cleveland Cavaliers','DAL':'Dallas Mavericks','DEN':'Denver Nuggets','DET':'Detroit Pistons',
 'GSW':'Golden State Warriors','HOU':'Houston Rockets','IND':'Indiana Pacers','LAC':'Los Angeles Clippers','LAL':'Los Angeles Lakers','MEM':'Memphis Grizzlies','MIA':'Miami Heat','MIL':'Milwaukee Bucks','MIN':'Minnesota Timberwolves',
 'NOP':'New Orleans Pelicans','NYK':'New York Knicks','OKC':'Oklahoma City Thunder','ORL':'Orlando Magic','PHI':'Philadelphia 76ers','PHO':'Phoenix Suns','POR':'Portland Trail Blazers','SAC':'Sacramento Kings',
 'SAS':'San Antonio Spurs','TOR':'Toronto Raptors','UTA':'Utah Jazz','WAS':'Washington Wizards'}
sn = pd.read_csv(REPO + '/archive/history/team_snapshots_2022-26.csv'); sn['season_end'] = sn.season.str[:4].astype(int) + 1; sn['team'] = sn.team_bbr.map(CODE)
rows = []
for (se, d), s in sn.groupby(['season_end', 'date']):
    t = tg[(tg.season_end == se) & (tg.date < d)].groupby('team').agg(g=('k', 'max'), cw=('win', 'sum'))
    m = s.set_index('team').join(t).join(ou[ou.season_end == se].set_index('team')[['ou_adj', 'w']]).fillna({'g': 0, 'cw': 0})
    if m.g.mean() < 3 or m.g.mean() > 70: continue
    p0 = m.ou_adj / 82; left = 82 - m.g
    # formula coefficients at this snapshot's mean games, fit on the other seasons
    gg = int(round(m.g.mean())); tr = tg[(tg.k == gg) & (tg.season_end != se)]; lt = tr.n - gg
    b = np.linalg.lstsq(np.c_[tr.p0 - .5, tr.cw / gg - tr.p0], (tr.w - tr.cw) / lt - tr.p0, rcond=None)[0]
    f = m.cw + left * (p0 + b[0] * (p0 - .5) + b[1] * (m.cw / np.maximum(m.g, 1) - p0))
    real = m.proj_wins.clip(m.cw, m.cw + left)
    rows.append(dict(season_end=se, date=d, g=m.g.mean(), rmse_real=np.sqrt(((m.w - real)**2).mean()), rmse_formula=np.sqrt(((m.w - f)**2).mean()),
                     slope_real=np.polyfit((real - m.cw) / left - .5, (m.w - m.cw) / left - .5, 1)[0], sd_real=real.std(), sd_formula=f.std(),
                     lowerr_real=(m.w - real)[real < 27].mean(), n_low=(real < 27).sum()))
R = pd.DataFrame(rows); R['stage'] = pd.cut(R.g, [0, 9, 17, 25, 35, 45, 55, 70])
print(R.groupby(['stage'], observed=True)[['rmse_real', 'rmse_formula', 'slope_real', 'sd_real', 'sd_formula', 'lowerr_real']].mean().round(2).to_string())
print(R.groupby(['season_end', 'stage'], observed=True)[['rmse_real', 'rmse_formula', 'slope_real']].mean().round(2).unstack(0).to_string())
# (3) TALENT_SD refit: does the size of misses so far predict the size of misses to come?
print('\n== Does the size of early misses predict later misses? (24 seasons) ==')
for g in [13, 20, 30, 41]:
    d = tg[tg.k == g].copy(); rate = d.p0.clip(.01, .99); d['r2'] = (d.cw - rate * g)**2; d['luck'] = g * rate * (1 - rate)
    that = d.groupby('season_end').apply(lambda q: np.sqrt(max(0, (q.r2.sum() - q.luck.sum()) / (len(q) * (g / 82)**2))))
    dd = loso_proj(g); later = dd.groupby('season_end').apply(lambda q: np.sqrt((q.err**2).mean()))
    live = (1 - min(1, g / 41)) * 8.6 + min(1, g / 41) * that.clip(4, 14)
    print('after %d games: refit estimate ranges %.1f-%.1f (sd %.2f; blended value sd %.2f); correlation with the RMS miss over the rest of that season: %.2f (Spearman %.2f)' % (
        g, that.min(), that.max(), that.std(), live.std(), np.corrcoef(that, later)[0, 1], stats.spearmanr(that, later)[0]))
