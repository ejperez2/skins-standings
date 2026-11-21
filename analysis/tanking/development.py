# Does development time get pushed into decided games, inflating bad teams' losses?
# Uses ESPN stints (who was on the floor when) and the per-minute score / win-probability flow logged by log_daily.py.
# Team class = preseason Vegas win total (bottom 8 / middle 14 / top 8). Young = 23 or younger on game day.
import pandas as pd, numpy as np, os, sys
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..'); D = os.path.join(H, 'data')
ABBR = {'BOS': 'Boston Celtics', 'TOR': 'Toronto Raptors', 'BKN': 'Brooklyn Nets', 'WSH': 'Washington Wizards', 'CHI': 'Chicago Bulls',
        'PHX': 'Phoenix Suns', 'MIL': 'Milwaukee Bucks', 'MEM': 'Memphis Grizzlies', 'CLE': 'Cleveland Cavaliers', 'IND': 'Indiana Pacers',
        'MIN': 'Minnesota Timberwolves', 'CHA': 'Charlotte Hornets', 'NO': 'New Orleans Pelicans', 'ORL': 'Orlando Magic',
        'OKC': 'Oklahoma City Thunder', 'UTAH': 'Utah Jazz', 'DAL': 'Dallas Mavericks', 'LAL': 'Los Angeles Lakers', 'SAC': 'Sacramento Kings',
        'LAC': 'Los Angeles Clippers', 'GS': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'DET': 'Detroit Pistons', 'ATL': 'Atlanta Hawks',
        'PHI': 'Philadelphia 76ers', 'MIA': 'Miami Heat', 'SA': 'San Antonio Spurs', 'DEN': 'Denver Nuggets', 'POR': 'Portland Trail Blazers',
        'NY': 'New York Knicks'}
ou = pd.read_csv(f'{R}/archive/history/preseason_win_totals_2000-26.csv')
vh = pd.read_csv(f'{R}/team_vegas_history.csv').sort_values('date').groupby('team').first().vegas_proj_wins
ou = pd.concat([ou[['season_end', 'team', 'ou']], pd.DataFrame({'season_end': 2027, 'team': vh.index, 'ou': vh.values})])
ath = pd.read_csv(f'{D}/athletes.csv', dtype={'athlete_id': str})
ath['dob'] = pd.to_datetime(ath.dob, format='%d/%m/%Y', errors='coerce')
dob = ath.set_index('athlete_id').dob

def team_class(season):
    r = ou[ou.season_end == season].set_index('team').ou.rank()
    return {a: ('bottom8' if r[n] <= 8 else 'top8' if r[n] > 22 else 'middle') for a, n in ABBR.items() if n in r}

def state(wp):
    return np.select([wp < 0.05, wp < 0.20, wp <= 0.80, wp <= 0.95], ['lost (<5%)', 'trailing (5-20%)', 'competitive', 'leading (80-95%)'], 'won (>95%)')

out = {}
for season in sorted(int(s) for s in os.listdir(D) if s.isdigit()):
    sd = os.path.join(D, str(season))
    g = pd.read_csv(f'{sd}/games.csv', dtype={'event_id': str}); g['date'] = pd.to_datetime(g.date)
    st = pd.read_csv(f'{sd}/stints.csv', dtype={'event_id': str, 'athlete_id': str})
    fl = pd.read_csv(f'{sd}/flow.csv', dtype={'event_id': str})
    box = pd.read_csv(f'{sd}/box.csv', dtype={'event_id': str, 'athlete_id': str})
    cls = team_class(season)
    # Per minute, per team: win prob at the start of the minute, points margin change during it, and who was on the floor
    fl = fl.sort_values(['event_id', 'minute'])
    fl['d_home'] = fl.groupby('event_id').home_margin.shift(-1) - fl.home_margin
    fl = fl.dropna(subset=['d_home']).merge(g[['event_id', 'home', 'away', 'date']], on='event_id')
    tm = pd.concat([pd.DataFrame({'event_id': fl.event_id, 'minute': fl.minute, 'team': fl.home, 'opp': fl.away, 'wp': fl.home_wp, 'd': fl.d_home, 'date': fl.date}),
                    pd.DataFrame({'event_id': fl.event_id, 'minute': fl.minute, 'team': fl.away, 'opp': fl.home, 'wp': 1 - fl.home_wp, 'd': -fl.d_home, 'date': fl.date})])
    # Stints -> seconds on the floor per (player, minute)
    st = st.merge(g[['event_id', 'date']], on='event_id')
    st['young'] = (st.date - st.athlete_id.map(dob)).dt.days / 365.25 <= 23.99
    starters = set(zip(box.event_id[box.starter], box.athlete_id[box.starter]))
    st['starter'] = [(e, a) in starters for e, a in zip(st.event_id, st.athlete_id)]
    rows = []
    for m0 in range(0, 53):
        a = np.clip(np.minimum(st.t_out, (m0 + 1) * 60) - np.maximum(st.t_in, m0 * 60), 0, None)
        k = a > 0
        if k.any():
            x = st[k].assign(sec=a[k], minute=m0)
            rows.append(x.groupby(['event_id', 'team', 'minute']).apply(
                lambda z: pd.Series({'young_sec': z.sec[z.young].sum(), 'starter_sec': z.sec[z.starter].sum(), 'sec': z.sec.sum()}), include_groups=False))
    on = pd.concat(rows).reset_index()
    tm = tm.merge(on, on=['event_id', 'team', 'minute'], how='left')
    tm['cls'] = tm.team.map(cls); tm['opp_cls'] = tm.opp.map(cls); tm['state'] = state(tm.wp)
    tm['season'] = season
    out[season] = tm

T = pd.concat(out.values())
T = T[T.sec > 0]
# Opponent's floor composition in the same minute
O = T[['event_id', 'team', 'minute', 'young_sec', 'starter_sec', 'sec']].rename(columns={'team': 'opp', 'young_sec': 'o_young_sec', 'starter_sec': 'o_starter_sec', 'sec': 'o_sec'})
T = T.merge(O, on=['event_id', 'opp', 'minute'], how='left')
for p in ['', 'o_']:
    T[p + 'young'] = T[p + 'young_sec'] / T[p + 'sec']; T[p + 'starter'] = T[p + 'starter_sec'] / T[p + 'sec']
summ = lambda z: pd.Series({'team_minutes': len(z), 'young_share_%': z.young_sec.sum() / z.sec.sum() * 100,
                            'starter_share_%': z.starter_sec.sum() / z.sec.sum() * 100, 'net_per_48': z.d.mean() * 48})
order = ['lost (<5%)', 'trailing (5-20%)', 'competitive', 'leading (80-95%)', 'won (>95%)']
pd.set_option('display.width', 250)
for season, z in T.groupby('season'):
    print(f'\n===== season ending {season} =====')
    t = z.groupby(['cls', 'state']).apply(summ, include_groups=False).unstack('cls')
    print(t.reindex(order).round(1).to_string())

# Losses: how much of the final margin is added after the game is decided (team win prob first drops below 5% for good)
print('\n===== losses: margin when decided vs final =====')
res = []
for season, z in T.groupby('season'):
    z = z.sort_values(['event_id', 'team', 'minute'])
    for (ev, team), x in z.groupby(['event_id', 'team']):
        fin = x.d.sum()
        if fin >= 0: continue
        alive = x.wp >= 0.05
        last_alive = x.minute[alive].max() if alive.any() else -1
        post = x[x.minute > last_alive]
        if len(post) == 0:
            res.append(dict(season=season, cls=x.cls.iloc[0], final=fin, decided_min=np.nan, post_min=0, post_d=0, post_young=np.nan)); continue
        res.append(dict(season=season, cls=x.cls.iloc[0], opp_cls=x.opp_cls.iloc[0], final=fin, decided_min=post.minute.iloc[0], post_min=len(post),
                        post_d=post.d.sum(), post_young=post.young_sec.sum() / post.sec.sum(), pre_d=fin - post.d.sum(),
                        opp_post_young=np.nan))
L = pd.DataFrame(res)
print(L.groupby(['season', 'cls']).apply(lambda z: pd.Series({
    'losses': len(z), 'final_margin': z.final.mean(), 'decided_early_%': (z.post_min > 0).mean() * 100,
    'minutes_after_decided': z.post_min[z.post_min > 0].mean(), 'pts_lost_after': -z.post_d[z.post_min > 0].mean(),
    'pts_lost_per_min_after': -z.post_d[z.post_min > 0].sum() / z.post_min[z.post_min > 0].sum(),
    'young_share_after_%': z.post_young.mean() * 100}), include_groups=False).round(2).to_string())

# Where do young players' minutes go? Share of each class's young-player minutes that came in decided games, vs share of all minutes
print('\n===== young-player minutes spent in decided states (win prob <5% or >95%) =====')
T['decided'] = (T.wp < 0.05) | (T.wp > 0.95)
print(T.groupby(['season', 'cls']).apply(lambda z: pd.Series({
    'all_min_decided_%': z.sec[z.decided].sum() / z.sec.sum() * 100,
    'young_min_decided_%': z.young_sec[z.decided].sum() / z.young_sec.sum() * 100,
    'young_share_competitive_%': z.young_sec[z.state == 'competitive'].sum() / z.sec[z.state == 'competitive'].sum() * 100,
    'young_share_lost_%': z.young_sec[z.state == 'lost (<5%)'].sum() / z.sec[z.state == 'lost (<5%)'].sum() * 100}), include_groups=False).round(1).to_string())

# Regression: points per minute in decided-loss minutes, controlling for both teams' floor composition and class
print('\n===== decided-loss minutes: net points per 48 explained (OLS) =====')
Z = T[(T.state == 'lost (<5%)')].dropna(subset=['young', 'o_young', 'starter', 'o_starter'])
for season, z in list(Z.groupby('season')) + [('all', Z)]:
    X = pd.DataFrame({'const': 1.0, 'own_young': z.young, 'opp_young': z.o_young, 'own_starter': z.starter, 'opp_starter': z.o_starter,
                      'own_bottom8': (z.cls == 'bottom8') * 1.0, 'own_top8': (z.cls == 'top8') * 1.0,
                      'opp_bottom8': (z.opp_cls == 'bottom8') * 1.0, 'opp_top8': (z.opp_cls == 'top8') * 1.0})
    y = z.d.values * 48
    b, *_ = np.linalg.lstsq(X.values, y, rcond=None)
    resid = y - X.values @ b; XtX = np.linalg.inv(X.values.T @ X.values)
    # cluster-robust by game
    meat = sum(np.outer(X.values[i].T @ resid[i], X.values[i].T @ resid[i]) for i in [np.where(z.event_id.values == e)[0] for e in z.event_id.unique()])
    se = np.sqrt(np.diag(XtX @ meat @ XtX))
    print(f'season {season}, {len(z)} team-minutes: ' + ', '.join(f'{c} {bb:+.1f} ({s:.1f})' for c, bb, s in zip(X.columns, b, se)))
L.to_csv(os.environ.get('DEV_OUT', os.devnull), index=False)
T.to_csv(os.environ.get('DEV_MIN_OUT', os.devnull), index=False)
