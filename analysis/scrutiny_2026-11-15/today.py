# Today's inputs for the python port of the live model (analysis/sim_models.py)
import numpy as np, pandas as pd, sys
def load_today(S, REPO):
    d = pd.read_csv(S + '/teams_today.csv').sort_values('team').reset_index(drop=True)
    g = pd.read_csv(S + '/games_2627.csv'); r = g[(g.status == 'STATUS_SCHEDULED') & g.home.isin(d.team) & g.away.isin(d.team) & ~g.note.fillna('').str.contains('Championship')]
    ti = {t: i for i, t in enumerate(d.team)}
    hi, ai = r.home.map(ti).values, r.away.map(ti).values
    W = d.wins.values.astype(float); L = (d.g - d.wins).values.astype(float)
    phantom = (82 - W - L) - (np.bincount(hi, minlength=30) + np.bincount(ai, minlength=30))
    players = ['Adam', 'Brian', 'Eristeo']; pid = d.player.map({p: i for i, p in enumerate(players)}).values
    side = np.where(d.pick == 'W', 1, -1)
    return d, W, L, pid, side, hi, ai, phantom, players
if __name__ == '__main__':
    S, REPO = sys.argv[1], sys.argv[2]; sys.path.insert(0, REPO + '/analysis'); import sim_models as M
    d, W, L, pid, side, hi, ai, phantom, players = load_today(S, REPO)
    print('remaining listed games', len(hi), 'phantom', phantom.sum(), phantom.min(), phantom.max())
    M.TALENT_SD = 8.2461485031649
    import time; t = time.time()
    fw, k, rs = M.sim_m2_cal(W, L, d.weighted.values, pid, side, 0.25, 10000, np.random.default_rng(1), hi, ai, phantom)
    tot, wp = M.player_outcomes(fw, pid, side, 3)
    print('M2c port', dict(zip(players, wp.round(4))), 'rho_s %.3f k %.3f  %.1fs' % (rs, k, time.time() - t))
    print('mean', tot.mean(1).round(1), 'sd', tot.std(1).round(1), 'corr', np.corrcoef(tot).round(2).tolist())
    dEB = tot[2] - tot[1]; dEA = tot[2] - tot[0]
    print('E-B mean %.1f sd %.1f | E-A mean %.1f sd %.1f | corr %.2f' % (dEB.mean(), dEB.std(), dEA.mean(), dEA.std(), np.corrcoef(dEB, dEA)[0, 1]))
    print('team sd mean %.2f' % fw.std(1).mean(), 'P(E>B) %.3f P(E>A) %.3f' % ((dEB > 0).mean(), (dEA > 0).mean()))
    fw1 = M.sim_m0_m1(W, L, d.weighted.values, pid, side, 0.25, 10000, np.random.default_rng(1), True); print('M1', M.player_outcomes(fw1, pid, side, 3)[1].round(4))
