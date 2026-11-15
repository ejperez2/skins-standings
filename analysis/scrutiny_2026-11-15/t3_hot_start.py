# This season: how far did the sources move on ~13 games, against what 24 seasons say is optimal?
import numpy as np, pandas as pd, sys
sys.path.insert(0, sys.argv[1]); from hist import *
REPO, S = sys.argv[2], sys.argv[3]
ou, G = load(); tg = team_games(G).merge(ou[['season_end', 'team', 'ou_adj', 'w', 'n']], on=['season_end', 'team'])
tg['p0'] = tg.ou_adj / 82
PT = 0.0325   # win pct per point of average margin (fit below)
h = tg[~tg.nm]; fin = h[h.k == h.n]; print('win pct per point of season margin: %.4f' % np.polyfit(fin.cm / fin.n, fin.cw / fin.n - .5, 1)[0])
def fit(g, cols, data):
    d = data[data.k == g].copy(); left = d.n - g
    d['x'] = d.cw / g - d.p0; d['m'] = d.cm / g * PT - (d.p0 - .5); d['c'] = d.p0 - .5; d['y'] = (d.w - d.cw) / left - d.p0
    X = d[cols].values; b = np.linalg.lstsq(X, d.y.values, rcond=None)[0]
    return b, d
print('\nHistory (seasons with scores, n=19): rest-of-season rate minus line = b_c*(line-.5) + b_x*(record - line) + b_m*(margin-implied pct - line)')
for g in [8, 10, 13, 16, 20, 30, 41]:
    b1, d = fit(g, ['x'], h); b2, _ = fit(g, ['c', 'x'], h); b3, d3 = fit(g, ['c', 'x', 'm'], h); b4, _ = fit(g, ['c', 'm'], h)
    r = lambda cols, b: np.sqrt((((d3.y - d3[cols].values @ b) * (d3.n - g))**2).mean())
    print('g=%2d  record only %.3f | +line shrink: c %.3f x %.3f | +margin: c %.3f x %.3f m %.3f | RMSE wins: %.2f / %.2f / %.2f' % (g, b1[0], *b2, *b3, r(['x'], b1), r(['c', 'x'], b2), r(['c', 'x', 'm'], b3)))
# season-cluster bootstrap of the g=13 full model
rng = np.random.default_rng(3); b3, d3 = fit(13, ['c', 'x', 'm'], h); ss = d3.season_end.unique(); bb = []
for _ in range(1000):
    q = pd.concat([d3[d3.season_end == s] for s in rng.choice(ss, len(ss))]); bb.append(np.linalg.lstsq(q[['c', 'x', 'm']].values, q.y.values, rcond=None)[0])
print('g=13 full model 95%% CIs: c %s x %s m %s; total weight on results (x+m) %.3f %s' % (np.percentile(bb, [2.5, 97.5], 0)[:, 0].round(3), np.percentile(bb, [2.5, 97.5], 0)[:, 1].round(3), np.percentile(bb, [2.5, 97.5], 0)[:, 2].round(3), b3[1] + b3[2], np.percentile(np.array(bb)[:, 1] + np.array(bb)[:, 2], [2.5, 97.5]).round(3)))

# ---- this season
dr = pd.read_csv(S + '/draft_2627.csv'); p = pd.read_csv(REPO + '/team_projection_history.csv'); g27 = pd.read_csv(S + '/games_2627.csv')
f = g27[g27.status == 'STATUS_FINAL'].copy(); f['mg'] = f.hs.astype(float) - f.as_.astype(float)
tm = pd.concat([pd.DataFrame(dict(team=f.home, win=(f.mg > 0) * 1, mg=f.mg)), pd.DataFrame(dict(team=f.away, win=(f.mg < 0) * 1, mg=-f.mg))]).groupby('team').agg(g=('win', 'size'), w=('win', 'sum'), mg=('mg', 'mean'))
o = p[p.date == '2026-10-19'].set_index('team'); c = p[p.date == p.date.max()].set_index('team')
d = dr.set_index('team').join(tm).join(o[['weighted', 'vegas', 'tr', 'espn']].add_suffix('_0')).join(c[['wins', 'losses', 'weighted', 'vegas', 'tr', 'espn', 'cbs', 'opta', 'darko', 'dnt', 'crafted', 'br']])
print('\nrecords match saved snapshot:', (d.w == d.wins).mean().round(2), '(ESPN games fetched now vs morning snapshot)')
d['wins'] = d.w; d['g'] = d.g; d['left'] = 82 - d.g
d['p0'] = d.weighted_0 / 82; d['x'] = d.wins / d.g - d.p0; d['m'] = d.mg * PT - (d.p0 - .5); d['c'] = d.p0 - .5
print('This season, weight each source put on results so far (slope of change in rest-of-season rate on record minus opening line):')
for s, s0 in [('weighted', 'weighted_0'), ('vegas', 'vegas_0'), ('tr', 'tr_0'), ('espn', 'espn_0'), ('cbs', 'weighted_0'), ('opta', 'weighted_0'), ('darko', 'weighted_0'), ('dnt', 'weighted_0'), ('crafted', 'weighted_0'), ('br', 'weighted_0')]:
    y = (d[s] - d.wins) / d.left - d[s0] / 82; xx = d.wins / d.g - d[s0] / 82
    b = np.polyfit(xx, y, 1); r = np.corrcoef(xx, y)[0, 1]
    X = np.c_[d[s0] / 82 - .5, xx, d.mg * PT - (d[s0] / 82 - .5)]; b3s = np.linalg.lstsq(X, y, rcond=None)[0]
    print('  %-9s slope %.3f (r %.2f)%s | on line %.3f record %.3f margin %.3f' % (s, b[0], r, '' if s0 != 'weighted_0' or s == 'weighted' else ' [vs opening weighted avg]', *b3s))
# history-optimal projection of final wins for each team today, three versions
bx, _ = fit(13, ['x'], tg); bcx, _ = fit(13, ['c', 'x'], tg)
def interp(cols, data):
    gs = np.array([10, 13, 16]); B = np.array([fit(g, cols, data)[0] for g in gs]); return lambda g: np.array([np.interp(g, gs, B[:, j]) for j in range(B.shape[1])])
iX, iCX, iCXM = interp(['x'], tg), interp(['c', 'x'], tg), interp(['c', 'x', 'm'], h)
d['h_x'] = [r.wins + r.left * (r.p0 + iX(r.g) @ [r.x]) for r in d.itertuples()]
d['h_cx'] = [r.wins + r.left * (r.p0 + iCX(r.g) @ [r.c, r.x]) for r in d.itertuples()]
d['h_cxm'] = [r.wins + r.left * (r.p0 + iCXM(r.g) @ [r.c, r.x, r.m]) for r in d.itertuples()]
d['pre'] = d.wins + d.left * d.p0
sg = np.where(d.pick == 'W', 1, -1)
tab = {}
for k in ['pre', 'h_x', 'h_cx', 'h_cxm', 'weighted', 'vegas', 'tr', 'espn', 'cbs', 'opta', 'darko', 'dnt', 'crafted', 'br']:
    sk = np.where(d.pick == 'W', d[k], 82 - d[k]); tab[k] = pd.Series(sk, index=d.index).groupby(d.player).sum()
T = pd.DataFrame(tab).T; T['E-A'] = T.Eristeo - T.Adam; T['E-B'] = T.Eristeo - T.Brian; T['league sum wins'] = [d[k].sum() for k in T.index]
print('\nProjected final skins by method (today):'); print(T.round(1).to_string())
d['sk_w'] = np.where(d.pick == 'W', d.weighted, 82 - d.weighted); d['sk_h'] = np.where(d.pick == 'W', d.h_cxm, 82 - d.h_cxm)
d['mg_w82'] = 41 + d.mg * PT * 82
print('\nPer team: opening line, record, margin-implied 82-game wins, history-optimal final wins, weighted avg; skins difference (weighted - history-optimal)')
print(d.sort_values(['player', 'dp'])[['player', 'abbr', 'pick', 'weighted_0', 'wins', 'g', 'mg', 'mg_w82', 'h_cxm', 'weighted']].assign(skins_gap=(d.sk_w - d.sk_h)).round(1).to_string())
d.to_csv(S + '/teams_today.csv')
