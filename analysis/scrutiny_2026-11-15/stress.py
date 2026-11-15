# Stress test of today's Chance to Win: python port of the live model on today's inputs, one assumption changed at a time.
import numpy as np, pandas as pd, sys
S, REPO, CODE = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, CODE); sys.path.insert(0, REPO + '/analysis'); import sim_models as M; from today import load_today
from multiprocessing import Pool
d, W, L, pid, side, hi, ai, phantom, players = load_today(S, REPO)
T_LIVE = 8.2461485031649; N = 8000
left = 82 - W - L
def shrink(p, lam):   # pull rest-of-season rate toward .500 by lam
    r = (p - W) / left; return W + left * (.5 + (1 - lam) * (r - .5))
P = dict(weighted=d.weighted.values, vegas=d.vegas.values, formula=d.h_cxm.values, pre=d.pre.values,
         avg_all=d[['vegas', 'tr', 'espn', 'cbs', 'opta', 'darko', 'dnt', 'crafted', 'br']].mean(1).values,
         low4=d[['opta', 'darko', 'br', 'dnt']].mean(1).values)
P['shrink10'] = shrink(P['weighted'], .10); P['shrink20'] = shrink(P['weighted'], .20)
def run(a):
    name, proj, T, rho, exp, tdf = a
    M.TALENT_SD = T; M.EXP = exp
    rng = np.random.default_rng(20261115)
    if tdf:      # fat tails: scale each season's talent draws by a chi-square mixing variable (multivariate t)
        orig = M.roster_z
        def rz(pid_, side_, rho_, n, rng_):
            z = orig(pid_, side_, rho_, n, rng_); s = np.sqrt(tdf / rng_.chisquare(tdf, n)) * np.sqrt((tdf - 2) / tdf); return z * s[None, :]
        M.roster_z = rz
    if rho > 0: fw, k, rs = M.sim_m2_cal(W, L, proj, pid, side, rho, N, rng, hi, ai, phantom)
    else: fw, k = M.sim_m2(W, L, proj, pid, side, 0.0, N, rng, hi, ai, phantom)
    tot, wp = M.player_outcomes(fw, pid, side, 3)
    dEB, dEA = tot[2] - tot[1], tot[2] - tot[0]
    return dict(case=name, T=T, rho=rho, exp=exp, tdf=tdf, Adam=wp[0], Brian=wp[1], Eristeo=wp[2], sdE=tot[2].std(), gapEB=dEB.mean(), sdEB=dEB.std(), gapEA=dEA.mean(), sdEA=dEA.std(),
                lo80=np.percentile(tot[2], 10), hi80=np.percentile(tot[2], 90))
if __name__ == '__main__':
    jobs = [('live', P['weighted'], T_LIVE, .25, 1.5, 0)]
    jobs += [('rho', P['weighted'], T_LIVE, r, 1.5, 0) for r in [0, .05, .10, .15, .35, .45]]
    jobs += [('T', P['weighted'], t, .25, 1.5, 0) for t in [6.0, 7.2, 8.6, 10.0, 11.5]]
    jobs += [('exp1.0', P['weighted'], T_LIVE, .25, 1.0, 0), ('exp1.0+T7.2', P['weighted'], 7.2, .25, 1.0, 0)]
    jobs += [('t5 tails', P['weighted'], T_LIVE, .25, 1.5, 5)]
    jobs += [('proj:' + k, P[k], T_LIVE, .25, 1.5, 0) for k in ['vegas', 'formula', 'avg_all', 'low4', 'shrink10', 'shrink20', 'pre']]
    jobs += [('history-fit: T7.2 rho.10', P['weighted'], 7.2, .10, 1.5, 0), ('history-fit + formula proj', P['formula'], 7.2, .10, 1.5, 0),
             ('pessimist: formula, T10, rho.35', P['formula'], 10.0, .35, 1.5, 0), ('pessimist2: shrink20, T10, rho.35', P['shrink20'], 10.0, .35, 1.5, 0),
             ('worst: pre, T10, rho.35', P['pre'], 10.0, .35, 1.5, 0)]
    # leave-one-team-out: each of Eristeo's teams reverts to its opening-line pace
    for i in np.where(pid == 2)[0]:
        p = P['weighted'].copy(); p[i] = d.pre.values[i]; jobs.append(('revert ' + d.abbr[i], p, T_LIVE, .25, 1.5, 0))
    with Pool(4) as pool: R = pd.DataFrame(pool.map(run, jobs, chunksize=1))
    pd.set_option('display.width', 250); print(R.round(3).to_string(index=False)); R.to_csv(S + '/stress.csv', index=False)
