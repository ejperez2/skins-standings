# Summarise analysis/synthetic_results_*.csv (from synthetic_leagues.py). Seasons weigh equally.
import pandas as pd, numpy as np, glob
import sys
PATTERN = sys.argv[1] if len(sys.argv) > 1 else 'analysis/synthetic_results_*.csv'
R = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(PATTERN))])
R['stage'] = pd.cut(R.games, [-1, 15, 30, 50, 82], labels=['<15', '15-30', '30-50', '50+'])
models = ['M1', 'M2c', 'M2c+S', 'M2c+P']
def sm(df, col): return df.groupby(['model', 'season'])[col].mean().groupby('model').mean().reindex(models)
print('League-seasons scored:', R[R.model == 'M2c'].groupby('season').league.nunique().to_dict(),
      '| forecasts per model:', len(R[R.model == 'M2c']))
print('Equal-odds log loss = %.3f, Brier = %.3f' % (np.log(3), 2 / 3))
T = pd.DataFrame({'log loss': sm(R, 'll'), 'Brier': sm(R, 'brier'), 'fav prob': sm(R, 'p_fav'),
                  'fav won': sm(R, 'fav_won'), '80% held': sm(R, 'in80')})
print('\n== Overall =='); print(T.round(4).to_string())
for col, name in [('ll', 'log loss'), ('brier', 'Brier'), ('in80', '80% range held')]:
    print(f'\n== {name} by stage =='); print(R.groupby(['stage', 'model', 'season'], observed=True)[col].mean().groupby(['stage', 'model'], observed=True).mean().unstack().reindex(columns=models).round(4).to_string())
print('\n== log loss by season =='); print(R.groupby(['season', 'model']).ll.mean().unstack().reindex(columns=models).round(4).to_string())
print('\n== Favourite: average stated chance vs how often it won, by stage ==')
f = R.groupby(['stage', 'model'], observed=True).agg(stated=('p_fav', 'mean'), won=('fav_won', 'mean')).round(3)
print(f.unstack().to_string())
# calibration: pool every player-forecast
P = pd.concat([R[['model', 'stage', f'p{i}', f'w{i}']].rename(columns={f'p{i}': 'p', f'w{i}': 'w'}) for i in range(3)])
P['bin'] = pd.cut(P.p, [0, .1, .2, .35, .5, .65, .8, .9, 1.0])
print('\n== Calibration (all player forecasts; predicted vs actual win rate) ==')
C = P.groupby(['model', 'bin'], observed=True).agg(n=('p', 'size'), predicted=('p', 'mean'), actual=('w', 'mean'))
print(C.unstack(0).round(3).to_string())
# paired comparison by season: share of league-snapshots where each model beats M2c
print('\n== Paired vs M2c: mean log-loss difference (negative = better than M2c), per season ==')
Pv = R.pivot_table(index=['season', 'date', 'league'], columns='model', values='ll')
for m in ['M1', 'M2c+S', 'M2c+P']:
    dif = (Pv[m] - Pv['M2c']).groupby('season').mean()
    print(m, dif.round(4).to_dict())
