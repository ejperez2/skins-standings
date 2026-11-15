import numpy as np, pandas as pd, sys
sys.path.insert(0, sys.argv[1]); from hist import *
from scipy import stats
ou, G = load()
print('team-seasons', len(ou), 'seasons', ou.season_end.nunique())
e = ou.err
print('RMSE %.2f  MAE %.2f  mean %.2f  skew %.2f  excess kurt %.2f  beyond 2.5sd: %d (normal expects %.1f)' % (
    np.sqrt((e**2).mean()), e.abs().mean(), e.mean(), stats.skew(e), stats.kurtosis(e), (e.abs() > 2.5 * e.std()).sum(), len(e) * 2 * stats.norm.sf(2.5)))
print('model-implied preseason SD with T=8.6: %.2f' % np.sqrt((82 * (ou.ou_adj / 82) * (1 - ou.ou_adj / 82) + 8.6**2).mean()))
T2 = ((e**2) - 82 * (ou.ou_adj / 82) * (1 - ou.ou_adj / 82)).mean(); print('method-of-moments T over 24 seasons: %.2f' % np.sqrt(T2))
# by season
bs = ou.groupby('season_end').apply(lambda d: pd.Series(dict(rmse=np.sqrt((d.err**2).mean()),
      T=np.sqrt(max(((d.err**2) - 82 * (d.ou_adj / 82) * (1 - d.ou_adj / 82)).mean(), 0)),
      slope=np.polyfit(d.ou_adj - 41, d.w - 41, 1)[0], sd_ou=d.ou_adj.std(), sd_w=d.w.std())))
print(bs.round(2).to_string())
print('T by season: mean %.2f sd %.2f; log-sd %.2f' % (bs['T'].mean(), bs['T'].std(), np.log(bs['T']).std()))
# is the season-to-season spread in RMSE more than chance? simulate under homogeneous T
rng = np.random.default_rng(1); T = np.sqrt(T2); sims = []
for _ in range(4000):
    x = []
    for s, d in ou.groupby('season_end'):
        p = d.ou_adj.values / 82; tal = rng.normal(0, T / 82, len(d)); w = rng.binomial(82, np.clip(p + tal, .02, .98)); x.append(np.sqrt(((w - d.ou_adj.values)**2).mean()))
    sims.append(np.std(x, ddof=1))
print('sd of season RMSE: observed %.2f, under one fixed T (independent teams) %.2f +/- %.2f, p=%.3f' % (bs.rmse.std(), np.mean(sims), np.std(sims), np.mean(np.array(sims) >= bs.rmse.std())))
# slope actual vs line (is the line too extreme?) with season-cluster bootstrap
def slope(d): return np.polyfit(d.ou_adj - 41, d.w - 41, 1)[0]
seasons = ou.season_end.unique(); bsl = [slope(pd.concat([ou[ou.season_end == s] for s in rng.choice(seasons, len(seasons))])) for _ in range(2000)]
print('pooled slope of final wins on line: %.3f  (season-bootstrap 95%% CI %.3f to %.3f); slope sd across seasons %.3f' % (slope(ou), *np.percentile(bsl, [2.5, 97.5]), bs.slope.std()))
# by line level: bias, sd, skew
ou['bin'] = pd.cut(ou.ou_adj, [0, 25, 30, 35, 41, 47, 52, 57, 90])
print(ou.groupby('bin', observed=True).err.agg(n='size', mean='mean', se=lambda x: x.std() / np.sqrt(len(x)), sd='std', skew=lambda x: stats.skew(x), p_under=lambda x: (x < 0).mean()).round(2).to_string())
for lab, d in [('2000-2011', ou[ou.season_end <= 2011]), ('2013-2019', ou[ou.season_end.between(2013, 2019)]), ('2022-2026', ou[ou.season_end >= 2022])]:
    print(lab, 'RMSE %.2f' % np.sqrt((d.err**2).mean()), 'slope %.3f' % slope(d), 'low-line (<30) mean err %.2f (n=%d)' % (d[d.ou_adj < 30].err.mean(), (d.ou_adj < 30).sum()), 'high-line (>=52) mean err %.2f (n=%d)' % (d[d.ou_adj >= 52].err.mean(), (d.ou_adj >= 52).sum()))
# "skins-side" error: for a pick on the favoured side (W if line >= 41 else L), error in skins
ou['sk_err'] = np.where(ou.ou_adj >= 41, ou.err, -ou.err)
print('skins error of side-aligned picks: mean %.2f (se by season %.2f), skew %.2f' % (ou.sk_err.mean(), ou.groupby('season_end').sk_err.mean().std() / np.sqrt(24), stats.skew(ou.sk_err)))
print('season mean of side-aligned skins error (the league-wide "spread" factor): sd across seasons %.2f; expected from independent team errors %.2f' % (ou.groupby('season_end').sk_err.mean().std(), np.sqrt((e**2).mean() / 30)))
# same-season correlation of side-aligned errors (the common factor every drafter shares)
