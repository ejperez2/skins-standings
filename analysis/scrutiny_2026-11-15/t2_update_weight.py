# How much weight should g games of results get against the preseason line? And how big is the remaining error?
import numpy as np, pandas as pd, sys
sys.path.insert(0, sys.argv[1]); from hist import *
ou, G = load(); tg = team_games(G)
tg = tg.merge(ou[['season_end', 'team', 'ou_adj', 'w', 'n']], on=['season_end', 'team'])
rng = np.random.default_rng(0); seasons = np.sort(ou.season_end.unique())
out = []
for g in [5, 8, 10, 13, 16, 20, 25, 30, 41, 50, 60]:
    d = tg[tg.k == g].copy(); left = d.n - g
    d['p0'] = d.ou_adj / 82; d['x'] = d.cw / g - d.p0; d['y'] = (d.w - d.cw) / left - d.p0; d['left'] = left
    d['mx'] = d.cm / g                                     # average margin so far
    w = (d.x * d.y).sum() / (d.x**2).sum()
    # season-cluster bootstrap CI and leave-one-season-out weights
    bw = []
    for _ in range(1000):
        bb = pd.concat([d[d.season_end == s] for s in rng.choice(seasons, len(seasons))]); bw.append((bb.x * bb.y).sum() / (bb.x**2).sum())
    wl = d.season_end.map({s: (d[d.season_end != s].x * d[d.season_end != s].y).sum() / (d[d.season_end != s].x**2).sum() for s in seasons})
    res = (d.y - wl * d.x) * left                          # error in wins over the rest of the season (held-out weight)
    phat = np.clip(d.p0 + wl * d.x, .05, .95)
    luck = (left * phat * (1 - phat)).mean()
    tau = np.sqrt(max((res**2).mean() - luck, 0))
    res0 = d.y * left; tau0 = np.sqrt(max((res0**2).mean() - (left * d.p0 * (1 - d.p0)).mean(), 0))   # ignoring results entirely
    res1 = ((d.w - d.cw) / left - d.cw / g) * left         # pure pace
    # slope of rest-of-season rate on the blended projection (around .500): is the blend too extreme?
    q = d.p0 + wl * d.x - .5; sl = (q * (d.y + d.p0 - .5)).sum() / (q**2).sum()
    # with margin (seasons that have scores)
    dm = d[~d.nm]; X = np.c_[dm.x, dm.mx / 100]; b = np.linalg.lstsq(X, dm.y, rcond=None)[0]
    resm = (dm.y - X @ b) * dm.left; res_same = (dm.y - wl[dm.index] * dm.x) * dm.left
    out.append(dict(g=g, w=w, lo=np.percentile(bw, 2.5), hi=np.percentile(bw, 97.5), theory86=g / (g + .25 / (8.6 / 82)**2), theory72=g / (g + .25 / (7.19 / 82)**2),
                    rmse_blend=np.sqrt((res**2).mean()), rmse_ignore=np.sqrt((res0**2).mean()), rmse_pace=np.sqrt((res1**2).mean()),
                    tau_emp=tau, tau_ignore=tau0, tau_model=8.6 * ((82 - g) / 82)**1.5, sd_model=np.sqrt(luck + (8.6 * ((82 - g) / 82)**1.5)**2), slope=sl,
                    b_wl=b[0], b_margin_per_pt=b[1] / 100, rmse_wl_only=np.sqrt((res_same**2).mean()), rmse_with_margin=np.sqrt((resm**2).mean()),
                    kurt=pd.Series(res).kurt(), skew=pd.Series(res).skew()))
R = pd.DataFrame(out); pd.set_option('display.width', 250)
print(R.round(3).to_string(index=False))
R.to_csv(sys.argv[2], index=False)
