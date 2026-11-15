# Unified regular-season game table, seasons ending 2000-2026 (82-game seasons only), keyed by the team name used
# on Basketball-Reference's preseason odds pages. Sources: 538 nbaallelo (to 2015), ESPN scoreboard (2016-19, 2022),
# repo archive/history/games_2022-26.csv (2023-26). Every team-season is checked against the bbref final record.
import pandas as pd, numpy as np, json, glob, sys, os
S, REPO = sys.argv[1], sys.argv[2]
ou = pd.read_csv(S + '/ou.csv'); ou = ou[~ou.season_end.isin([2012, 2020, 2021])]
CODE = {'ATL':'Atlanta Hawks','BOS':'Boston Celtics','BRK':'Brooklyn Nets','NJN':'New Jersey Nets','CHA':'Charlotte Bobcats','CHH':'Charlotte Hornets',
 'CHO':'Charlotte Hornets','CHI':'Chicago Bulls','CLE':'Cleveland Cavaliers','DAL':'Dallas Mavericks','DEN':'Denver Nuggets','DET':'Detroit Pistons',
 'GSW':'Golden State Warriors','HOU':'Houston Rockets','IND':'Indiana Pacers','LAC':'Los Angeles Clippers','LAL':'Los Angeles Lakers',
 'MEM':'Memphis Grizzlies','VAN':'Vancouver Grizzlies','MIA':'Miami Heat','MIL':'Milwaukee Bucks','MIN':'Minnesota Timberwolves',
 'NOH':'New Orleans Hornets','NOK':'New Orleans/Oklahoma City Hornets','NOP':'New Orleans Pelicans','NYK':'New York Knicks','OKC':'Oklahoma City Thunder',
 'SEA':'Seattle SuperSonics','ORL':'Orlando Magic','PHI':'Philadelphia 76ers','PHO':'Phoenix Suns','POR':'Portland Trail Blazers','SAC':'Sacramento Kings',
 'SAS':'San Antonio Spurs','TOR':'Toronto Raptors','UTA':'Utah Jazz','WAS':'Washington Wizards'}
rows = []
e = pd.read_csv(S + '/raw/nbaallelo.csv')
e = e[(e.lg_id == 'NBA') & (e.is_playoffs == 0) & ((e.game_location == 'H') | ((e.game_location == 'N') & (e._iscopy == 0))) & e.year_id.between(2000, 2015) & (e.year_id != 2012)]
rows.append(pd.DataFrame(dict(season_end=e.year_id, date=pd.to_datetime(e.date_game).dt.strftime('%Y-%m-%d'), home=e.team_id.map(CODE),
                              away=e.opp_id.map(CODE), margin=e.pts - e.opp_pts)))
assert rows[0].home.notna().all() and rows[0].away.notna().all()
er = []
for f in sorted(glob.glob(S + '/raw/espn/*.json')):
    ym = os.path.basename(f)[:6]; se = int(ym[:4]) + (1 if int(ym[4:]) >= 9 else 0)
    for ev in json.load(open(f))['events']:
        if ev.get('season', {}).get('type') != 2: continue
        c = ev['competitions'][0]
        if c['status']['type']['name'] != 'STATUS_FINAL': continue
        h = [x for x in c['competitors'] if x['homeAway'] == 'home'][0]; a = [x for x in c['competitors'] if x['homeAway'] == 'away'][0]
        er.append(dict(id=ev['id'], season_end=se, date=(pd.Timestamp(ev['date']).tz_convert('America/New_York')).strftime('%Y-%m-%d'),
                       home=h['team']['displayName'], away=a['team']['displayName'], margin=float(h['score']) - float(a['score'])))
er = pd.DataFrame(er).drop_duplicates('id').drop(columns='id').replace({'LA Clippers': 'Los Angeles Clippers'})
rows.append(er)
g = pd.read_csv(REPO + '/archive/history/games_2022-26.csv'); g['season_end'] = g.season.str[:4].astype(int) + 1
g = g[g.season_end >= 2023]
rows.append(pd.DataFrame(dict(season_end=g.season_end, date=g.date_et, home=g.home.map(CODE), away=g.away.map(CODE),
                              margin=np.where(g.home_win == 1, 1.0, -1.0), no_margin=True)))
G = pd.concat(rows, ignore_index=True); G['no_margin'] = G.no_margin.fillna(False).astype(bool)
valid = set(ou.team)
G = G[G.home.isin(valid) & G.away.isin(valid)]          # drops All-Star games
G['home_win'] = (G.margin > 0).astype(int)
# check against bbref final records; drop games that break it (e.g. Cup finals)
w = pd.concat([G.groupby(['season_end', 'home']).home_win.sum().rename_axis(['season_end', 'team']),
               (1 - G.home_win).groupby([G.season_end, G.away]).sum().rename_axis(['season_end', 'team'])], axis=1).fillna(0).sum(axis=1)
n = pd.concat([G.groupby(['season_end', 'home']).size().rename_axis(['season_end', 'team']),
               G.groupby(['season_end', 'away']).size().rename_axis(['season_end', 'team'])], axis=1).fillna(0).sum(axis=1)
chk = ou.set_index(['season_end', 'team']).join(w.rename('gw')).join(n.rename('gn'))
bad = chk[(chk.gw != chk.w) | (chk.gn != chk.w + chk.l)]
print('team-seasons', len(chk), 'mismatches', len(bad)); print(bad.to_string() if len(bad) else '')
G.sort_values(['season_end', 'date']).to_csv(S + '/games_all.csv', index=False)
ou.to_csv(S + '/ou_clean.csv', index=False)
print(G.groupby('season_end').size().to_string())
