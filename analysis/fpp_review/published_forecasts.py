# FPP2 3.3-3.4: only genuine forecasts (made before the outcome, by the model of the day) measure accuracy.
# standings_history.csv keeps one row per day and was backfilled when the model changed (2026-11-08), so its
# win_prob for earlier days is a re-fit, not what the page said. This rebuilds every published run from git
# history: for each commit of standings_history.csv, the rows of its newest date are what that run published.
# The output seeds forecast_log.csv, which index.qmd appends to on every CI run and never rewrites.
# Needs full history (git fetch --unshallow if the clone is shallow).
# Usage: python3 analysis/fpp_review/published_forecasts.py [forecast_log.csv]   (run from the repo root)
import subprocess, io, sys, pandas as pd
F = 'standings_history.csv'
COLS = ['win_prob', 'win_prob_best', 'win_prob_ignore_hot', 'range_lo', 'range_hi', 'range_lo50', 'range_hi50',
        'weighted_average', 'actual_skins', 'model_version']
log = [l.split(' ', 1) for l in subprocess.run(['git', 'log', '--reverse', '--format=%H %cI', '--', F],
                                                capture_output=True, text=True).stdout.splitlines() if l]
rows = []
for sha, ts in log:
    txt = subprocess.run(['git', 'show', f'{sha}:{F}'], capture_output=True, text=True).stdout
    if not txt.strip():
        continue
    d = pd.read_csv(io.StringIO(txt))
    if 'win_prob' not in d:
        continue
    new = d[(d.date == d.date.max()) & d.win_prob.notna()]
    when = pd.Timestamp(ts).tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%SZ')
    for _, r in new.iterrows():
        rows.append(dict(published_at=when, date=r.date, player=r.player, **{c: r.get(c) for c in COLS},
                         source=f'git {sha[:7]}'))
pub = pd.DataFrame(rows)
for c in COLS:
    if c not in pub:
        pub[c] = pd.NA
pub = pub[['published_at', 'date', 'player'] + COLS + ['source']]
if len(sys.argv) > 1:
    pub.to_csv(sys.argv[1], index=False)

first = pub.groupby(['date', 'player']).first().reset_index()
now = pd.read_csv(F)[['date', 'player', 'win_prob', 'model_version']].rename(
    columns={'win_prob': 'in_file_now', 'model_version': 'model_now'})
m = first.merge(now, on=['date', 'player'])
w = m.pivot_table(index='date', columns='player', values=['win_prob', 'in_file_now'])
pd.set_option('display.width', 200)
print('First Chance to Win published each day vs. what standings_history.csv holds now (last run of the day,')
print('re-fitted with a later model where the model changed):')
print(w.round(3).to_string())
refit = m[m.model_version.fillna('') != m.model_now.fillna('')]
print(f'\n{len(pub)} published runs x players over {pub.date.nunique()} days. Days now holding a later model\'s '
      f're-fit instead of a published number: {refit.date.nunique()} ({refit.date.min()} to {refit.date.max()}).')
print(first.groupby('model_version', dropna=False).date.agg(['min', 'max', 'nunique']).sort_values('min').to_string())
