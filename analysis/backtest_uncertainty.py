# Can the model's weak mid-season skill be reflected in its uncertainty? Player-level backtest 2022-26 of
# the live model (league-total constraint, roster corr from day 1) with variants:
#   EXP: talent-miss shrink exponent, TALENT_SD * (left/82)^EXP (live: 1.5)
#   RHO: roster correlation (live: 0.15 floor)
#   shrink: final odds pulled toward equal odds, p' = (1-w) p + w / n_players, w fit per stage band
# Scored by winner log loss with leave-one-season-out (fit on 3 seasons, score the 4th).
import pandas as pd, numpy as np, itertools
exec(open('analysis/backtest_spread.py').read().split('rows=[]')[0])   # loads D
TS, N = 8.6, 12000
def wp(g, EXP, RHO, rng):
    left = 82 - g.gpt.values; n = g.n.values.astype(int); s = g.actual.values
    proj = np.clip(g.proj.values, s, s + left * n); p = np.clip((proj - s) / np.maximum(left * n, 1e-9), .01, .99)
    v = left * p * (1 - p) + (TS * (left / 82) ** EXP) ** 2
    nW = g.nW.values.astype(int); E = []; Ssum = 0; cov = []; varS = 0
    for i in range(len(g)):
        side = np.r_[np.ones(nW[i]), -np.ones(n[i] - nW[i])]
        e = np.sqrt(v[i]) * (np.sqrt(1 - RHO) * rng.standard_normal((n[i], N)) + np.sqrt(RHO) * rng.standard_normal(N))
        E.append(e.sum(0)); Ssum = Ssum + (side[:, None] * e).sum(0)
        k = side.sum(); cov.append(v[i] * (k + RHO * (k * n[i] - k))); varS += v[i] * (n[i] + RHO * (k * k - n[i]))
    E = np.array(E) - np.array(cov)[:, None] / varS * Ssum[None, :]
    f = np.clip(proj[:, None] + E, s[:, None], (s + left * n)[:, None])
    w = (f == f.max(0)); w = w / w.sum(0); return w.mean(1), proj, n * v * (1 + (n - 1) * RHO)
snaps = [(se, t, g) for (se, t), g in D.groupby(['season', 'timestamp']) if len(g) >= 5 and g.gpt.mean() < 75]
snaps = snaps[::2]                                    # every other day: neighbours are nearly identical
BANDS = [0, 15, 30, 50, 75]; band = lambda gm: np.digitize(gm, BANDS[1:-1])
rows = []
for EXP, RHO in itertools.product([1.5, 1.25, 1.0, 0.75], [0.15, 0.25, 0.35]):
    rng = np.random.default_rng(1)
    for se, t, g in snaps:
        p, proj, var = wp(g, EXP, RHO, rng); win = (g.final == g.final.max()).values
        z = (g.final.values - proj) / np.sqrt(var)
        rows.append(dict(EXP=EXP, RHO=RHO, season=se, band=band(g.gpt.mean()), pw=p[win].sum(), n=len(g), z2=(z ** 2).mean()))
R_ = pd.DataFrame(rows)
WS = np.linspace(0, 1, 21)
def ll(pw, n, w): return -np.log(np.maximum((1 - w) * pw + w / n, 1e-3))
# per (EXP, RHO): leave-one-season-out, choosing w per band on the other 3 seasons (w=0 = no shrink)
res = []
for (EXP, RHO), g in R_.groupby(['EXP', 'RHO']):
    for shrink in [False, True]:
        out = []
        for test in g.season.unique():
            tr, te = g[g.season != test], g[g.season == test]
            for b, teb in te.groupby('band'):
                trb = tr[tr.band == b]
                w = 0.0
                if shrink:
                    w = WS[np.argmin([trb.groupby('season').apply(lambda x: ll(x.pw, x.n, w_).mean()).mean() for w_ in WS])]
                out.append(dict(season=test, band=b, w=w, ll=ll(teb.pw, teb.n, w).mean(), ll_eq=np.log(teb.n).mean()))
        O = pd.DataFrame(out)
        byb = O.groupby('band').ll.mean()       # mean over seasons
        res.append(dict(EXP=EXP, RHO=RHO, shrink=shrink, overall=O.groupby('season').ll.mean().mean(),
                        **{f'g{BANDS[b]}-{BANDS[b+1]}': byb[b] for b in byb.index},
                        rmsz=np.sqrt(g.z2.mean()), worst_season=O.groupby('season').ll.mean().max()))
T = pd.DataFrame(res).sort_values('overall')
print('Winner log loss, held-out season (lower = better). Equal odds =', round(np.log(R_.n).mean(), 3))
print(T.round(3).to_string(index=False))
live = R_[(R_.EXP == 1.5) & (R_.RHO == 0.15)]
print('\nRMS z of player final skins by band, live settings:', live.groupby('band').z2.mean().pow(.5).round(2).to_dict())

# Per-season check for the candidates, and pairwise spread (what the winner depends on)
print('\nPer-season winner log loss (mean over held-out snapshots, no shrink):')
P_ = R_.groupby(['EXP', 'RHO', 'season']).apply(lambda x: ll(x.pw, x.n, 0).mean()).unstack().round(3)
print(P_.loc[[(1.5, .15), (1.5, .25), (1.5, .35), (1.0, .15), (1.0, .25), (1.0, .35)]].to_string())
