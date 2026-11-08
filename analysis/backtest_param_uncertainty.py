# Real leagues, 2022-26, every archived snapshot: schedule model (M2c) with and without parameter uncertainty
# (M2c+P: per simulated season, TALENT_SD x lognormal(0, 0.28) and roster correlation ~ Beta(mean 0.25, sd 0.10)).
# Usage: python3 analysis/backtest_param_uncertainty.py SEASON -> analysis/param_unc_SEASON.csv
import numpy as np, pandas as pd, sys
sys.path.insert(0, 'analysis'); import synthetic_leagues as sl
sl.RHO = RHO = 0.25; SIG_T, RHO_SD, N = 0.28, 0.10, 6000
season = sys.argv[1]
r = sl.ros[sl.ros.season == season].sort_values('team_bbr').reset_index(drop=True)
teams = r.team_bbr.tolist(); ti = {t: i for i, t in enumerate(teams)}; final = r.final_wins.values
players = sorted(r.player.unique()); pid = r.player.map({p: i for i, p in enumerate(players)}).values; side = np.where(r.pick == 'W', 1, -1)
fsk = np.array([np.where(side == 1, final, 82 - final)[pid == i].sum() for i in range(len(players))])
win = (fsk == fsk.max()) / (fsk == fsk.max()).sum()
sg = sl.snaps[sl.snaps.season == season]; gs = sl.games[sl.games.season == season]; rows = []
for d in sorted(sg.date.unique()):
    W, L, hi, ai = sl.records(gs, d, ti); gm = (W + L).mean()
    proj = sg[sg.date == d].set_index('team_bbr').loc[teams, 'proj_wins'].values.astype(float)
    Hm = np.zeros((30, len(hi)), np.float32); Hm[hi, np.arange(len(hi))] = 1
    Am = np.zeros((30, len(ai)), np.float32); Am[ai, np.arange(len(ai))] = 1
    cal = sl.calibrate(W, L, proj, hi, ai, Hm, Am, pid, side)
    lr = np.random.default_rng(int(pd.Timestamp(d).value // 86400e9))
    a_ = RHO * (RHO * (1 - RHO) / RHO_SD ** 2 - 1); b_ = (1 - RHO) * (RHO * (1 - RHO) / RHO_SD ** 2 - 1)
    outs = {'M2c': sl.m2_run(cal['s'], cal['V'], cal['tsd'], cal['k'], hi, ai, Hm, Am, W, pid, side, cal['rho_s'], N, lr),
            'M2c+P': sl.m2_run(cal['s'], cal['V'], cal['tsd'], cal['k'], hi, ai, Hm, Am, W, pid, side, cal['rho_s'], N, lr,
                               np.exp(lr.normal(0, SIG_T, N)), np.clip(cal['rho_s'] * lr.beta(a_, b_, N) / RHO, 0, 0.98))}
    for m, fw in outs.items():
        sk = np.where(side[:, None] == 1, fw, 82 - fw); tot = np.vstack([sk[pid == i].sum(0) for i in range(len(players))])
        top = tot == tot.max(0); wp = (top / top.sum(0)).mean(1)
        lo, hi80 = np.percentile(tot, [10, 90], axis=1)
        pair = [-np.log(np.clip(((tot[i] > tot[j]) + .5 * (tot[i] == tot[j])).mean() if fsk[i] > fsk[j] else ((tot[j] > tot[i]) + .5 * (tot[i] == tot[j])).mean(), 1e-3, 1))
                for i in range(len(players)) for j in range(i + 1, len(players)) if fsk[i] != fsk[j]]
        rows.append(dict(season=season, date=d, games=gm, model=m, ll=-np.log(max(wp @ win, 1e-3)), pair_ll=np.mean(pair),
                         in80=np.mean((fsk >= lo) & (fsk <= hi80)), fav=wp.max()))
    print(d, 'done', flush=True)
pd.DataFrame(rows).to_csv(f'analysis/param_unc_{season}.csv', index=False)   # combined in param_uncertainty_results.csv
