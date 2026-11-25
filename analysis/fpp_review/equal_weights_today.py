# FPP2 12.4 ("a simple average has proven hard to beat"): what the blend would say today with equal weights,
# and whether the 2025-26 blend (the only past season with the live sources) under-reacted early.
# Usage: python3 analysis/fpp_review/equal_weights_today.py   (run from the repo root)
import pandas as pd, numpy as np
t = pd.read_csv('team_projection_history.csv', parse_dates=['date'])
dr = pd.read_csv('analysis/scrutiny_2026-11-15/results/draft_2627.csv')[['team', 'player', 'pick']]
last = t[t.date == t.date.max()].merge(dr, on='team')
S = ['vegas', 'tr', 'espn', 'cbs']
def blend(df, w):
    v = df[S].values; m = ~np.isnan(v); w = np.array(w)
    return np.nansum(v * w, 1) / (m * w).sum(1)
last['cur'] = blend(last, [.4, .2, .2, .2]); last['eq'] = blend(last, [.25] * 4)
for c in ['cur', 'eq', 'weighted']:
    last[c + '_sk'] = np.where(last.pick == 'W', last[c], 82 - last[c])
print('Date', t.date.max().date(), '- sources present:', {s: int(last[s].notna().sum()) for s in S})
print('Projected skins today (check: cur_sk should match the page\'s weighted_sk):')
print(last.groupby('player')[['weighted_sk', 'cur_sk', 'eq_sk']].sum().round(1).to_string())
print('Largest team differences, equal minus current (wins):')
last['d'] = last['eq'] - last['cur']
print(last.reindex(last.d.abs().sort_values(ascending=False).index)[['team', 'player', 'pick', 'vegas', 'tr', 'espn', 'cbs', 'cur', 'eq', 'd']].head(6).round(1).to_string(index=False))

# Revisions of an equal-weight blend this season (martingale check, as in revision_efficiency.py)
t['eq'] = blend(t, [.25] * 4)
for c in ['weighted', 'eq']:
    x = t.pivot_table(index='date', columns='team', values=c).asfreq('D').ffill(limit=2)
    a = pd.DataFrame({'p': (x - x.shift(7)).stack(), 'n': (x.shift(-7) - x).stack()}).dropna()
    a = a[a.index.get_level_values(0).weekday == 0]
    print(f'2026-27 weekly revision autocorrelation, {c:8s}: {a.p.corr(a.n):+.2f} (n={len(a)})')

# 2025-26 player level: does the live blend's recent move predict its remaining miss?
a = pd.read_csv('archive/2025-26/standings_history.csv', parse_dates=['date'])
r = pd.read_csv('archive/history/rosters_and_finals_2022-26.csv'); r = r[r.season == '2025-26']
r['sk'] = np.where(r.pick == 'W', r.final_wins, 82 - r.final_wins)
fin = r.groupby('player').agg(final=('sk', 'sum'), n=('sk', 'size'))
a = a.merge(fin, left_on='player', right_index=True).dropna(subset=['weighted_average']).sort_values('date')
a['gpt'] = a.actual_skins / a.skins_pct / a.n
out = []
for p, d in a.groupby('player'):
    d = d.set_index('date')['weighted_average'].asfreq('D').ffill(limit=3)
    g = a[a.player == p].set_index('date').gpt.asfreq('D').ffill(limit=3)
    out.append(pd.DataFrame({'rev': d - d.shift(7), 'miss': fin.loc[p, 'final'] - d, 'gpt': g}).dropna())
o = pd.concat(out)
for lab, d in o.groupby(pd.cut(o.gpt, [-1, 20, 40, 70], labels=['<20', '20-40', '40-70']), observed=True):
    d = d.iloc[::7]   # roughly non-overlapping weeks
    print(f'2025-26 blend, {lab:5s} games: slope of remaining miss on last 7-day revision = {np.polyfit(d.rev, d.miss, 1)[0]:+.2f} (n={len(d)}, 6 players)')
