# Do real rosters' teams miss together more than synthetic (re-drafted) rosters' teams do?
# Same estimator as the page: standardized skins misses from a start snapshot to final, rho = mean same-roster
# product / mean square. Start snapshot: first archived date with 20+ games (as the page) and the first date overall.
import numpy as np, pandas as pd, sys
sys.path.insert(0, 'analysis'); from sim_models import team_inputs
from synthetic_leagues import ros, snaps, games, records, draft_leagues
def rho_est(z, pid):
    num = den = 0
    for p in np.unique(pid):
        zz = z[pid == p]; num += (zz.sum() ** 2 - (zz ** 2).sum()) / 2; den += len(zz) * (len(zz) - 1) / 2
    return (num / den) / np.mean(z ** 2)
rng = np.random.default_rng(5)
for season in sorted(ros.season.unique()):
    r = ros[ros.season == season].sort_values('team_bbr').reset_index(drop=True)
    teams = r.team_bbr.tolist(); ti = {t: i for i, t in enumerate(teams)}; final = r.final_wins.values
    sg = snaps[snaps.season == season]; gs = games[games.season == season]; dates = sorted(sg.date.unique())
    real_pid = r.player.map({p: i for i, p in enumerate(sorted(r.player.unique()))}).values; real_side = np.where(r.pick == 'W', 1, -1)
    proj0 = sg[sg.date == dates[0]].set_index('team_bbr').loc[teams, 'proj_wins'].values
    leagues = draft_leagues(teams, proj0, 2000, rng)
    out = []
    for d in [dates[0]] + [x for x in dates if records(gs, x, ti)[0].sum() + records(gs, x, ti)[1].sum() >= 2 * 20 * 30 / 2][:1]:
        W, L, _, _ = records(gs, d, ti)
        proj = sg[sg.date == d].set_index('team_bbr').loc[teams, 'proj_wins'].values.astype(float)
        left, pj, rate, tsd, sd = team_inputs(W, L, proj)
        miss = (final - pj) / sd
        real = rho_est(real_side * miss, real_pid)
        syn = np.array([rho_est(side * miss, pid) for pid, side in leagues])
        rand = np.array([rho_est(real_side * miss, rng.permutation(real_pid)) for _ in range(2000)])
        out.append(f'from {d} ({(W + L).mean():.0f} g): real rosters {real:+.2f} | re-drafted 3-player leagues mean {syn.mean():+.2f} (90% {np.percentile(syn, 5):+.2f} to {np.percentile(syn, 95):+.2f}) | real picks, shuffled rosters {rand.mean():+.2f}, real beats {np.mean(rand < real):.0%}')
    print(season, *out, sep='\n  ')
