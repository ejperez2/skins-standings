# "League transplant": put this league's exact shape (who owns the k-th best projected team, and on which side)
# onto each of 24 past seasons at the same point of the season, project every team with a results-blind-to-the-future
# formula (preseason line + record so far, coefficients fit on the other 23 seasons), run the live model
# (python port, schedule simulation, roster correlation 0.25), and compare with what actually happened.
# Usage: transplant.py CODE_DIR REPO SCRATCH OUT.csv   (env: STAGES, NJIT, NSIM)
import numpy as np, pandas as pd, sys, os
from multiprocessing import Pool
sys.path.insert(0, sys.argv[1]); from hist import *
REPO, S, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, REPO + '/analysis'); import sim_models as M
STAGES = [float(x) for x in os.environ.get('STAGES', '12.6').split(',')]; NJIT = int(os.environ.get('NJIT', 10)); NSIM = int(os.environ.get('NSIM', 4000))
RHO = float(os.environ.get('RHO', 0.25)); REFIT = int(os.environ.get('REFIT', 1)); JSD = 2.0
ou, G = load(); tg = team_games(G).merge(ou[['season_end', 'team', 'ou_adj', 'w', 'n']], on=['season_end', 'team']); tg['p0'] = tg.ou_adj / 82
seasons = np.sort(ou.season_end.unique())
# leave-one-season-out blend coefficients by games played: rest-of-season rate = p0 + c*(p0-.5) + x*(record - p0)
GR = np.arange(1, 80)
def coefs(excl):
    out = np.zeros((len(GR), 2)); d0 = tg[tg.season_end != excl]
    for j, g in enumerate(GR):
        d = d0[d0.k == g]; left = d.n - g; X = np.c_[d.p0 - .5, d.cw / g - d.p0]; y = (d.w - d.cw) / left - d.p0
        out[j] = np.linalg.lstsq(X, y, rcond=None)[0]
    return out
def c0(excl):
    d = ou[ou.season_end != excl]; x = d.ou_adj / 82 - .5; return ((d.w / 82 - d.ou_adj / 82) * x).sum() / (x**2).sum()
today = pd.read_csv(S + '/teams_today.csv').sort_values('weighted', ascending=False).reset_index(drop=True)
T_PID = today.player.map({'Adam': 0, 'Brian': 1, 'Eristeo': 2}).values; T_SIDE = np.where(today.pick == 'W', 1, -1)
def job(a):
    se, stage, jit = a
    B = coefs(se); b0 = c0(se)
    o = ou[ou.season_end == se].sort_values('team').reset_index(drop=True); teams = o.team.tolist(); ti = {t: i for i, t in enumerate(teams)}; nT = len(teams)
    if nT != 30: return None
    gs = G[G.season_end == se]; dates = np.sort(gs.date.unique())
    cnt = gs.groupby('date').size().reindex(dates).cumsum().shift(1).fillna(0) * 2 / nT     # mean games before each date
    d = dates[np.argmin(np.abs(cnt.values - stage))]
    done, rest = gs[gs.date < d], gs[gs.date >= d]
    W = np.zeros(nT); L = np.zeros(nT)
    np.add.at(W, done.home.map(ti).values, done.home_win.values); np.add.at(L, done.home.map(ti).values, 1 - done.home_win.values)
    np.add.at(W, done.away.map(ti).values, 1 - done.home_win.values); np.add.at(L, done.away.map(ti).values, done.home_win.values)
    g = W + L; left = 82 - g; p0 = o.ou_adj.values / 82
    gi = np.clip(g.astype(int), 1, 79) - 1
    ros = np.where(g > 0, p0 + B[gi, 0] * (p0 - .5) + B[gi, 1] * (W / np.maximum(g, 1) - p0), p0 + b0 * (p0 - .5))
    proj = W + left * np.clip(ros, .03, .97); proj += (left.sum() / 2 - (proj - W).sum()) * left / left.sum()      # league adds up
    rng = np.random.default_rng(se * 1000 + int(stage * 10) + jit * 7919)
    order = np.argsort(-(proj + (rng.normal(0, JSD, nT) if jit > 0 else 0)))
    pid = np.empty(nT, int); side = np.empty(nT, int); pid[order] = T_PID; side[order] = T_SIDE
    final = o.w.values.astype(float)
    # live in-season refit of TALENT_SD (index.qmd): opening line vs record so far, blended in from 12 games
    T = 8.6
    if REFIT and g.mean() >= 12:
        rate = np.clip(p0, .01, .99); resid = W - rate * g; t_hat = np.sqrt(max(0, ((resid**2).sum() - (g * rate * (1 - rate)).sum()) / ((g / 82)**2).sum()))
        T = (1 - min(1, g.mean() / 41)) * 8.6 + min(1, g.mean() / 41) * float(np.clip(t_hat, 4, 14))
    M.TALENT_SD = T
    hi, ai = rest.home.map(ti).values, rest.away.map(ti).values
    fw, k, rs = M.sim_m2_cal(W, L, proj, pid, side, RHO, NSIM, rng, hi, ai, np.zeros(nT))
    tot, wp = M.player_outcomes(fw, pid, side, 3)
    sk_f = np.where(side == 1, final, 82 - final); act = np.array([sk_f[pid == i].sum() for i in range(3)])
    sk_p = np.where(side == 1, proj, 82 - proj); prj = np.array([sk_p[pid == i].sum() for i in range(3)])
    sk_n = np.where(side == 1, W, L); now = np.array([sk_n[pid == i].sum() for i in range(3)])
    r = dict(season_end=se, stage=stage, jit=jit, date=d, g=g.mean(), T=T, rho_s=rs,
             team_rmse=np.sqrt(((final - proj)**2).mean()), team_sd_model=np.sqrt(fw.var(1).mean()), team_z2=(((final - fw.mean(1)) / fw.std(1))**2).mean(),
             team_in80=np.mean((final >= np.percentile(fw, 10, 1)) & (final <= np.percentile(fw, 90, 1))))
    win = act == act.max()
    for i, nm in enumerate('ABE'):
        r.update({f'act_{nm}': act[i], f'prj_{nm}': prj[i], f'now_{nm}': now[i], f'mu_{nm}': tot[i].mean(), f'sd_{nm}': tot[i].std(), f'wp_{nm}': wp[i], f'won_{nm}': win[i] / win.sum(),
                  f'pit_{nm}': ((tot[i] < act[i]).mean() + (tot[i] <= act[i]).mean()) / 2,
                  f'in80_{nm}': float(np.percentile(tot[i], 10) <= act[i] <= np.percentile(tot[i], 90)), f'in50_{nm}': float(np.percentile(tot[i], 25) <= act[i] <= np.percentile(tot[i], 75))})
    for (i, j), nm in zip([(2, 1), (2, 0), (1, 0)], ['EB', 'EA', 'BA']):
        dd = tot[i] - tot[j]
        r.update({f'dact_{nm}': act[i] - act[j], f'dprj_{nm}': prj[i] - prj[j], f'dmu_{nm}': dd.mean(), f'dsd_{nm}': dd.std(), f'dp_{nm}': ((dd > 0) + .5 * (dd == 0)).mean()})
    return r
if __name__ == '__main__':
    jobs = [(se, st, j) for se in seasons for st in STAGES for j in range(NJIT + 1)]
    with Pool(4) as p: res = [r for r in p.imap_unordered(job, jobs, chunksize=2) if r]
    pd.DataFrame(res).sort_values(['stage', 'season_end', 'jit']).to_csv(OUT, index=False); print('done', len(res))
