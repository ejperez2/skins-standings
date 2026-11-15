# What weight did the real sources put on early results in the archived seasons (same regression as this season)?
import numpy as np, pandas as pd, sys
sys.path.insert(0, sys.argv[1]); from hist import *
REPO = sys.argv[2]; ou, G = load(); tg = team_games(G)
CODE = dict(ATL='Atlanta Hawks',BOS='Boston Celtics',BRK='Brooklyn Nets',CHO='Charlotte Hornets',CHI='Chicago Bulls',CLE='Cleveland Cavaliers',DAL='Dallas Mavericks',DEN='Denver Nuggets',DET='Detroit Pistons',GSW='Golden State Warriors',HOU='Houston Rockets',IND='Indiana Pacers',LAC='Los Angeles Clippers',LAL='Los Angeles Lakers',MEM='Memphis Grizzlies',MIA='Miami Heat',MIL='Milwaukee Bucks',MIN='Minnesota Timberwolves',NOP='New Orleans Pelicans',NYK='New York Knicks',OKC='Oklahoma City Thunder',ORL='Orlando Magic',PHI='Philadelphia 76ers',PHO='Phoenix Suns',POR='Portland Trail Blazers',SAC='Sacramento Kings',SAS='San Antonio Spurs',TOR='Toronto Raptors',UTA='Utah Jazz',WAS='Washington Wizards')
sn = pd.read_csv(REPO + '/archive/history/team_snapshots_2022-26.csv'); sn['season_end'] = sn.season.str[:4].astype(int) + 1; sn['team'] = sn.team_bbr.map(CODE)
for (se, d), s in sn.groupby(['season_end', 'date']):
    t = tg[(tg.season_end == se) & (tg.date < d)].groupby('team').agg(g=('k', 'max'), cw=('win', 'sum'))
    m = s.set_index('team').join(t).join(ou[ou.season_end == se].set_index('team')[['ou_adj', 'w']]).dropna()
    if not (8 <= m.g.mean() <= 22) or len(m) < 30: continue
    p0 = m.ou_adj / 82; left = 82 - m.g; y = (m.proj_wins - m.cw) / left - p0; X = np.c_[p0 - .5, m.cw / m.g - p0]
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    tr = tg.merge(ou[['season_end', 'team', 'ou_adj', 'w']], on=['season_end', 'team']); gg = int(round(m.g.mean())); tr = tr[(tr.k == gg) & (tr.season_end != se)]
    bo = np.linalg.lstsq(np.c_[tr.ou_adj / 82 - .5, tr.cw / gg - tr.ou_adj / 82], (tr.w - tr.cw) / (82 - gg) - tr.ou_adj / 82, rcond=None)[0]
    print(se, d, 'g %.1f' % m.g.mean(), 'source: line %+.3f record %.3f | history-optimal: line %+.3f record %.3f' % (*b, *bo))
