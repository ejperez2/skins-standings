# Team-level backtest 2022-26 of M0 / M1 / M2 / M2c (analysis/sim_models.py) on every archived team snapshot:
# records and remaining schedule from archive/history/games_2022-26.csv, projections from team_snapshots,
# rosters and final records from rosters_and_finals. Live settings: TALENT_SD 8.6, shrink 1.5, roster corr 0.25.
# M2c = M2 with the strength-scale roster correlation calibrated to an effective 0.25 (the live page's method).
# Env: RHO (default 0.25), MODELS (default M0,M1,M2,M2c), OUT (results CSV). Takes ~15 min for all four.
import numpy as np, pandas as pd, sys
sys.path.insert(0, 'analysis'); from sim_models import *
import os; RHO, N = float(os.environ.get("RHO", 0.25)), 6000; MODELS = os.environ.get("MODELS", "M0,M1,M2,M2c").split(",")
games = pd.read_csv('archive/history/games_2022-26.csv')
snaps = pd.read_csv('archive/history/team_snapshots_2022-26.csv')
ros = pd.read_csv('archive/history/rosters_and_finals_2022-26.csv')
rows, teamrows, RS = [], [], []
for season, sg in snaps.groupby('season'):
    r = ros[ros.season == season].sort_values('team_bbr').reset_index(drop=True)
    teams = r.team_bbr.tolist(); ti = {t: i for i, t in enumerate(teams)}
    players = sorted(r.player.unique()); pid = r.player.map({p: i for i, p in enumerate(players)}).values
    side = np.where(r.pick == 'W', 1, -1); final = r.final_wins.values
    final_sk = np.array([np.where(side == 1, final, 82 - final)[pid == i].sum() for i in range(len(players))])
    winner = final_sk == final_sk.max()
    gs = games[games.season == season]
    for d, s in sg.groupby('date'):
        done, rest = gs[gs.date_et < d], gs[gs.date_et >= d]
        W = np.zeros(30); L = np.zeros(30)
        np.add.at(W, done.home.map(ti).values, done.home_win.values); np.add.at(L, done.home.map(ti).values, 1 - done.home_win.values)
        np.add.at(W, done.away.map(ti).values, 1 - done.home_win.values); np.add.at(L, done.away.map(ti).values, done.home_win.values)
        proj = s.set_index('team_bbr').loc[teams, 'proj_wins'].values.astype(float)
        hi, ai = rest.home.map(ti).values, rest.away.map(ti).values
        gm = (W + L).mean()
        out = {}
        rng = np.random.default_rng(int(pd.Timestamp(d).value // 86400e9))
        k = np.nan
        if 'M0' in MODELS: out['M0'] = sim_m0_m1(W, L, proj, pid, side, RHO, N, rng, False)
        rng = np.random.default_rng(int(pd.Timestamp(d).value // 86400e9))
        if 'M1' in MODELS: out['M1'] = sim_m0_m1(W, L, proj, pid, side, RHO, N, rng, True)
        rng = np.random.default_rng(int(pd.Timestamp(d).value // 86400e9))
        if 'M2' in MODELS: out['M2'], k = sim_m2(W, L, proj, pid, side, RHO, N, rng, hi, ai, np.zeros(30))
        if 'M2c' in MODELS:
            rng = np.random.default_rng(int(pd.Timestamp(d).value // 86400e9))
            out['M2c'], k, rho_s = sim_m2_cal(W, L, proj, pid, side, RHO, N, rng, hi, ai, np.zeros(30)); RS.append(rho_s)
        for m, fw in out.items():
            tot, wp = player_outcomes(fw, pid, side, len(players))
            lo80, hi80 = np.percentile(tot, [10, 90], axis=1); lo50, hi50 = np.percentile(tot, [25, 75], axis=1)
            # pairwise order: P(i ends above j) for every pair, scored against the real order
            pair_ll = []
            for i in range(len(players)):
                for j in range(i + 1, len(players)):
                    if final_sk[i] == final_sk[j]: continue
                    pij = np.clip(((tot[i] > tot[j]) + 0.5 * (tot[i] == tot[j])).mean(), 1e-3, 1 - 1e-3)
                    pair_ll.append(-np.log(pij if final_sk[i] > final_sk[j] else 1 - pij))
            cm = np.corrcoef(tot)
            rows.append(dict(season=season, date=d, games=gm, model=m, k=k if m == 'M2' else np.nan,
                             ll=-np.log(max(wp[winner].sum(), 1e-3)), p_winner=wp[winner].sum(), fav=wp.max(),
                             fav_won=bool(winner[wp.argmax()]), pair_ll=np.mean(pair_ll),
                             in80=np.mean((final_sk >= lo80) & (final_sk <= hi80)), in50=np.mean((final_sk >= lo50) & (final_sk <= hi50)),
                             mean_offdiag_corr=(cm.sum() - len(players)) / (len(players) * (len(players) - 1)),
                             league_sd=fw.sum(0).std()))
            lo, hi_ = np.percentile(fw, [10, 90], axis=1)
            teamrows.append(dict(season=season, date=d, games=gm, model=m, team_in80=np.mean((final >= lo) & (final <= hi_)),
                                 team_rmsz=np.sqrt(np.mean(((final - fw.mean(1)) / np.maximum(fw.std(1), 1e-9)) ** 2))))
    print(season, 'done', flush=True)
print('calibrated strength-space rho: mean %.2f range %.2f-%.2f' % (np.mean(RS), np.min(RS), np.max(RS))) if RS else None
R = pd.DataFrame(rows); TR = pd.DataFrame(teamrows)
R.to_csv(os.environ.get('OUT', 'analysis/backtest_schedule_results.csv'), index=False)
R['stage'] = pd.cut(R.games, [0, 15, 30, 50, 82], labels=['<15', '15-30', '30-50', '50+'])
TR['stage'] = pd.cut(TR.games, [0, 15, 30, 50, 82], labels=['<15', '15-30', '30-50', '50+'])
def season_mean(df, col): return df.groupby(['model', 'season'])[col].mean().groupby('model').mean()
print('\nSnapshots per season:', R[R.model == 'M0'].groupby('season').size().to_dict())
print('M2 talent scale k: mean %.2f (range %.2f-%.2f)' % (R.k.mean(), R.k.min(), R.k.max()))
print('\n== Overall (mean over seasons of per-season mean) ==')
print(pd.DataFrame({c: season_mean(R, c) for c in ['ll', 'pair_ll', 'p_winner', 'in80', 'in50', 'mean_offdiag_corr', 'league_sd']}).round(3).to_string())
print('\nTeam level:', pd.DataFrame({c: season_mean(TR, c) for c in ['team_in80', 'team_rmsz']}).round(3).to_string())
print('\n== Winner log loss by season ==')
print(R.groupby(['season', 'model']).ll.mean().unstack().round(3).to_string())
print('\n== Pairwise order log loss by season (more outcomes per snapshot) ==')
print(R.groupby(['season', 'model']).pair_ll.mean().unstack().round(4).to_string())
print('\n== By stage (mean over seasons) ==')
for c in ['ll', 'pair_ll', 'in80']:
    print(c); print(R.groupby(['stage', 'season', 'model'], observed=True)[c].mean().groupby(['stage', 'model'], observed=True).mean().unstack().round(3).to_string())
