# Synthetic-league backtest: re-draft each real season (2022-26) into many 3-player, 10-team leagues and score the
# model's Chance to Win on all of them, so decisions rest on thousands of outcomes instead of four league winners.
#   Draft: snake, random first pick; each drafter sees every team's earliest archived projection with +/-2 wins of
#   personal noise and takes the team/side with the most projected skins above 41 (this reproduces the 2026-27
#   draft's rank correlation of 0.91 between pick number and value, and 93% better-side picks).
#   Forecasts on every other archived snapshot, using that day's real records and remaining schedule.
# Models (all TALENT_SD 8.6, shrink 1.5, effective roster correlation 0.25; no in-season refits):
#   M1     league-total method
#   M2c    schedule method (live since 2026-11-08)
#   M2c+S  M2c with rest-of-season projections pulled toward .500 by a stage factor fit leave-one-season-out
#   M2c+P  M2c with parameter uncertainty: each simulated season draws its own TALENT_SD (lognormal, sd 0.28 on
#          the log scale) and roster correlation (Beta, mean 0.25, sd 0.10)
# Usage: python3 analysis/synthetic_leagues.py SEASON [N_LEAGUES] [RHO] [OUT_CSV]  (default analysis/synthetic_results_SEASON.csv)
import numpy as np, pandas as pd, sys
sys.path.insert(0, 'analysis'); from sim_models import team_inputs, fit_strengths, sigmoid, sim_m0_m1
RHO, H_EDGE, N, N_PILOT = 0.25, 0.22, 2000, 3000
SIG_T, RHO_SD = 0.28, 0.10
games = pd.read_csv('archive/history/games_2022-26.csv'); snaps = pd.read_csv('archive/history/team_snapshots_2022-26.csv')
ros = pd.read_csv('archive/history/rosters_and_finals_2022-26.csv')
STAGES = [0, 15, 30, 50, 82]
def stage_of(g): return int(np.digitize(g, STAGES[1:-1]))

def records(gs, d, ti):
    done = gs[gs.date_et < d]; W = np.zeros(30); L = np.zeros(30)
    h, a, hw = done.home.map(ti).values, done.away.map(ti).values, done.home_win.values.astype(float)
    np.add.at(W, h, hw); np.add.at(L, h, 1 - hw); np.add.at(W, a, 1 - hw); np.add.at(L, a, hw)
    rest = gs[gs.date_et >= d]
    return W, L, rest.home.map(ti).values, rest.away.map(ti).values

# --- shrink factors by stage, fit on the OTHER seasons (team level, rest-of-season wins) ---
def shrink_factors(exclude):
    num = np.zeros(4); den = np.zeros(4)
    for season, sg in snaps[snaps.season != exclude].groupby('season'):
        r = ros[ros.season == season].sort_values('team_bbr'); teams = r.team_bbr.tolist(); ti = {t: i for i, t in enumerate(teams)}
        final = r.final_wins.values; gs = games[games.season == season]
        for d, s in sg.groupby('date'):
            W, L, _, _ = records(gs, d, ti); left = 82 - W - L
            proj = np.clip(s.set_index('team_bbr').loc[teams, 'proj_wins'].values, W, W + left)
            ok = left > 0; st = stage_of((W + L).mean())
            x = (proj - W)[ok] - 0.5 * left[ok]; y = (final - W)[ok] - 0.5 * left[ok]
            num[st] += (x * y).sum(); den[st] += (x * x).sum()
    return np.clip(num / np.maximum(den, 1e-9), 0.5, 1.2)

# --- draft synthetic leagues ---
def draft_leagues(teams, proj0, n_leagues, rng):
    out = []
    for _ in range(n_leagues):
        view = proj0[None, :] + rng.normal(0, 2, (3, 30))            # each drafter's own view
        order = rng.permutation(3); seq = [order[j] if (rnd % 2 == 0) else order[2 - j] for rnd in range(10) for j in range(3)]
        taken = np.zeros(30, bool); pid = np.zeros(30, int); side = np.zeros(30, int)
        for dft in seq:
            val = np.where(taken, -np.inf, np.abs(view[dft] - 41)); t = int(np.argmax(val))
            taken[t] = True; pid[t] = dft; side[t] = 1 if view[dft, t] >= 41 else -1
        out.append((pid, side))
    return out

# --- schedule model pieces ---
def m2_run(s, V, tsd, k, hi, ai, Hm, Am, W, pid, side, rho_s, n, rng, tmult=None, rho_vec=None):
    z = rng.standard_normal((30, n)); u = rng.standard_normal((pid.max() + 1, n))
    rs = rho_s if rho_vec is None else rho_vec[None, :]
    z = np.sqrt(1 - rs) * z + np.sqrt(rs) * side[:, None] * u[pid]
    delta = (k * tsd / np.maximum(V, 1e-6))[:, None] * z
    if tmult is not None: delta = delta * tmult[None, :]
    sh = s[:, None] + delta
    hw = (rng.random((len(hi), n)) < sigmoid(sh[hi] - sh[ai] + H_EDGE)).astype(np.float32)
    return W[:, None] + Hm @ hw + Am @ (1 - hw)
def roster_corr(fw, pid, side):
    c = np.corrcoef(side[:, None] * fw); same = (pid[:, None] == pid[None, :]) & ~np.eye(30, dtype=bool)
    return np.nanmean(c[same])
def calibrate(W, L, proj, hi, ai, Hm, Am, ref_pid, ref_side):
    """Base strengths, talent scale k, re-centring and strength-scale roster correlation, using the real
    league's rosters as the reference (roster identity barely matters for these)."""
    left, proj, rate, tsd, sd = team_inputs(W, L, proj)
    s0, V, tgt = fit_strengths(W, proj, hi, ai, np.zeros(30), H_EDGE)
    def fit(rho_s):
        v0 = m2_run(s0, V, tsd, 0, hi, ai, Hm, Am, W, ref_pid, ref_side, rho_s, N_PILOT, np.random.default_rng(12345)).var(1).sum()
        v1 = m2_run(s0, V, tsd, 1, hi, ai, Hm, Am, W, ref_pid, ref_side, rho_s, N_PILOT, np.random.default_rng(12345)).var(1).sum()
        k = np.sqrt(max(sd @ sd - v0, 0) / max(v1 - v0, 1e-9)); s = s0.copy()
        for _ in range(6):
            gap = tgt - (m2_run(s, V, tsd, k, hi, ai, Hm, Am, W, ref_pid, ref_side, rho_s, N_PILOT, np.random.default_rng(4321)).mean(1) - W)
            if np.abs(gap).max() < 0.03: break
            s = s + gap / np.maximum(V, 1e-6)
        return s, k
    rho_s = min(0.95, RHO * 1.6)
    for _ in range(3):
        s, k = fit(rho_s)
        eff = roster_corr(m2_run(s, V, tsd, k, hi, ai, Hm, Am, W, ref_pid, ref_side, rho_s, N_PILOT, np.random.default_rng(777)), ref_pid, ref_side)
        if not np.isfinite(eff) or eff <= 0: break
        rho_s = float(np.clip(rho_s * RHO / eff, 0, 0.95))
    s, k = fit(rho_s)
    return dict(s=s, k=k, rho_s=rho_s, V=V, tsd=tsd, proj=proj)

def score(fw, pid, side, final):
    sk = np.where(side[:, None] == 1, fw, 82 - fw)
    tot = np.vstack([sk[pid == i].sum(0) for i in range(3)])
    top = tot == tot.max(0); wp = (top / top.sum(0)).mean(1)
    fsk = np.array([np.where(side == 1, final, 82 - final)[pid == i].sum() for i in range(3)])
    win = fsk == fsk.max(); win = win / win.sum()
    lo, hi_ = np.percentile(tot, [10, 90], axis=1)
    return wp, win, np.mean((fsk >= lo) & (fsk <= hi_))

# --- main ---
if __name__ == '__main__':
    SEASON = sys.argv[1]; NL = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    RHO = float(sys.argv[3]) if len(sys.argv) > 3 else RHO
    OUT = sys.argv[4] if len(sys.argv) > 4 else f'analysis/synthetic_results_{SEASON}.csv'   # raw results are git-ignored; summarise with synthetic_summary.py
    rng = np.random.default_rng(abs(hash(SEASON)) % 2**32)
    r = ros[ros.season == SEASON].sort_values('team_bbr').reset_index(drop=True)
    teams = r.team_bbr.tolist(); ti = {t: i for i, t in enumerate(teams)}; final = r.final_wins.values
    ref_pid = r.player.map({p: i for i, p in enumerate(sorted(r.player.unique()))}).values % 3   # real rosters folded to 3 groups
    ref_side = np.where(r.pick == 'W', 1, -1)
    sg = snaps[snaps.season == SEASON]; gs = games[games.season == SEASON]
    dates = sorted(sg.date.unique())
    proj0 = sg[sg.date == dates[0]].set_index('team_bbr').loc[teams, 'proj_wins'].values
    leagues = draft_leagues(teams, proj0, NL, rng)
    lam = shrink_factors(SEASON)
    print(SEASON, 'leagues', NL, 'snapshots', len(dates[::2]), 'shrink factors by stage (fit on other seasons):', lam.round(2), flush=True)
    rows = []
    for d in dates[::2]:
        W, L, hi, ai = records(gs, d, ti); gm = (W + L).mean(); st = stage_of(gm)
        proj = sg[sg.date == d].set_index('team_bbr').loc[teams, 'proj_wins'].values.astype(float)
        Hm = np.zeros((30, len(hi)), np.float32); Hm[hi, np.arange(len(hi))] = 1
        Am = np.zeros((30, len(ai)), np.float32); Am[ai, np.arange(len(ai))] = 1
        left = 82 - W - L
        proj_c = np.clip(proj, W, W + left)
        proj_s = W + 0.5 * left + lam[st] * (proj_c - W - 0.5 * left)
        cal = calibrate(W, L, proj, hi, ai, Hm, Am, ref_pid, ref_side)
        cal_s = calibrate(W, L, proj_s, hi, ai, Hm, Am, ref_pid, ref_side)
        for li, (pid, side) in enumerate(leagues):
            lr = np.random.default_rng(li * 1000 + dates.index(d))
            out = {}
            out['M1'] = sim_m0_m1(W, L, proj, pid, side, RHO, N, lr, True)
            out['M2c'] = m2_run(cal['s'], cal['V'], cal['tsd'], cal['k'], hi, ai, Hm, Am, W, pid, side, cal['rho_s'], N, lr)
            out['M2c+S'] = m2_run(cal_s['s'], cal_s['V'], cal_s['tsd'], cal_s['k'], hi, ai, Hm, Am, W, pid, side, cal_s['rho_s'], N, lr)
            tmult = np.exp(lr.normal(0, SIG_T, N))
            a_ = RHO * (RHO * (1 - RHO) / RHO_SD ** 2 - 1); b_ = (1 - RHO) * (RHO * (1 - RHO) / RHO_SD ** 2 - 1)
            rho_vec = np.clip(cal['rho_s'] * lr.beta(a_, b_, N) / RHO, 0, 0.98)
            out['M2c+P'] = m2_run(cal['s'], cal['V'], cal['tsd'], cal['k'], hi, ai, Hm, Am, W, pid, side, cal['rho_s'], N, lr, tmult, rho_vec)
            for m, fw in out.items():
                wp, win, in80 = score(fw, pid, side, final)
                rows.append(dict(season=SEASON, date=d, games=gm, league=li, model=m, ll=-np.log(max((wp * win).sum(), 1e-3)),
                                 brier=((wp - win) ** 2).sum(), p_fav=wp.max(), fav_won=win[wp.argmax()] > 0, in80=in80,
                                 p0=wp[0], p1=wp[1], p2=wp[2], w0=win[0], w1=win[1], w2=win[2]))
        print(d, 'games %.1f done' % gm, flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
