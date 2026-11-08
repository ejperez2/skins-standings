# New model (2026-11-08: league-total constraint + roster correlation 0.15 from day 1), player-level backtest
# on 2022-26. Prints each season's odds at ~9 games per team, then accuracy by stage of the season.
import pandas as pd, numpy as np
exec(open('analysis/backtest_spread.py').read().split('rows=[]')[0])   # loads D (player snapshots + finals)
RHO, TS, N = 0.15, 8.6, 40000
rng = np.random.default_rng(11)
def wp(g):
    left = 82 - g.gpt.values; n = g.n.values.astype(int); s = g.actual.values
    proj = np.clip(g.proj.values, s, s + left * n); p = np.clip((proj - s) / np.maximum(left * n, 1e-9), .01, .99)
    v = left * p * (1 - p) + (TS * (left / 82) ** 1.5) ** 2          # per-team variance (equal within roster)
    nW = g.nW.values.astype(int); E = []; Ssum = 0; cov = []; varS = 0
    for i in range(len(g)):
        side = np.r_[np.ones(nW[i]), -np.ones(n[i] - nW[i])]
        e = np.sqrt(v[i]) * (np.sqrt(1 - RHO) * rng.standard_normal((n[i], N)) + np.sqrt(RHO) * rng.standard_normal(N))
        E.append(e.sum(0)); Ssum = Ssum + (side[:, None] * e).sum(0)
        k = side.sum(); cov.append(v[i] * (k + RHO * (k * n[i] - k))); varS += v[i] * (n[i] + RHO * (k * k - n[i]))
    E = np.array(E) - np.array(cov)[:, None] / varS * Ssum[None, :]
    f = np.clip(proj[:, None] + E, s[:, None], (s + left * n)[:, None])
    w = (f == f.max(0)); w = w / w.sum(0); return w.mean(1)
rows = []
for (season, t), g in D.groupby(['season', 'timestamp']):
    if len(g) < 5 or g.gpt.mean() >= 81: continue
    g = g.copy(); g['p'] = wp(g); g['gm'] = g.gpt.mean(); g['t'] = t; g['win'] = g.final == g.final.max(); rows.append(g)
B = pd.concat(rows)
# 1) each season at ~8.9 games per team (today's point)
print('=== ~9 games per team ===')
for season, g in B.groupby('season'):
    t = g.groupby('t').gm.first().sub(8.9).abs().idxmin(); h = g[g.t == t].sort_values('p', ascending=False)
    print(season, t[:10], '%.1f g/team |' % h.gm.iloc[0], ', '.join(f"{r.player} {100*r.p:.0f}%{'*' if r.win else ''}" for r in h.itertuples()))
# 2) accuracy by stage: one snapshot per season per stage (nearest), so seasons count equally
print('\n=== by stage (nearest snapshot per season; * = eventual winner) ===')
out = []
for stage in [5, 9, 15, 20, 25, 30, 35, 41, 50, 60, 70]:
    for season, g in B.groupby('season'):
        gm = g.groupby('t').gm.first(); t = gm.sub(stage).abs().idxmin()
        if abs(gm[t] - stage) > 3: continue
        h = g[g.t == t]; pw = h.p[h.win].sum()
        out.append(dict(stage=stage, season=season, n=len(h), p_winner=pw, top_hit=h.p.idxmax() == h.p[h.win].idxmax(),
                        fav=h.p.max(), ll=-np.log(max(pw, 1e-3)), ll_uniform=np.log(len(h))))
O = pd.DataFrame(out)
print(O.pivot(index='stage', columns='season', values='p_winner').mul(100).round(0).astype('Int64').to_string())
S_ = O.groupby('stage').agg(seasons=('season', 'size'), mean_p_winner=('p_winner', 'mean'), min_p_winner=('p_winner', 'min'),
                            top_pick_won=('top_hit', 'sum'), mean_fav=('fav', 'mean'), ll=('ll', 'mean'), ll_uniform=('ll_uniform', 'mean'),
                            beats_uniform=('ll', lambda s: (s < O.loc[s.index, 'll_uniform']).sum()))
print('\n(probability given to the eventual winner, %, by stage x season above; summary below)')
print(S_.round(3).to_string())
# 3) calibration across all snapshots by stage band
B['band'] = pd.cut(B.gm, [0, 15, 30, 50, 82], labels=['<15', '15-30', '30-50', '50+'])
B['bin'] = pd.cut(B.p, [0, .1, .25, .5, .75, .9, 1.0])
print('\n=== calibration, all daily snapshots (rows overlap heavily; 4 seasons) ===')
print(B.groupby(['band', 'bin'], observed=True).agg(n=('p', 'size'), predicted=('p', 'mean'), won=('win', 'mean')).round(2).to_string())
