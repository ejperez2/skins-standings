# Clean ESPN scoreboard games (from a raw CSV made by the parse step) into regular-season games with
# Basketball-Reference team codes. Drops All-Star games and the NBA Cup final (not in the standings).
import pandas as pd, sys
ESPN2BBR = {'ATL':'ATL','BOS':'BOS','BKN':'BRK','CHA':'CHO','CHI':'CHI','CLE':'CLE','DAL':'DAL','DEN':'DEN','DET':'DET',
            'GS':'GSW','HOU':'HOU','IND':'IND','LAC':'LAC','LAL':'LAL','MEM':'MEM','MIA':'MIA','MIL':'MIL','MIN':'MIN',
            'NO':'NOP','NY':'NYK','OKC':'OKC','ORL':'ORL','PHI':'PHI','PHX':'PHO','POR':'POR','SAC':'SAC','SA':'SAS',
            'TOR':'TOR','UTAH':'UTA','WSH':'WAS'}
def clean(raw):
    g = raw[(raw.season_type == 2) & raw.home.isin(ESPN2BBR) & raw.away.isin(ESPN2BBR)].copy()
    g = g[~g.note.fillna('').str.contains('Championship') & g.status.isin(['STATUS_FINAL', 'STATUS_SCHEDULED', 'STATUS_IN_PROGRESS'])]
    g['home'] = g.home.map(ESPN2BBR); g['away'] = g.away.map(ESPN2BBR)
    fin = g.status == 'STATUS_FINAL'
    g['home_win'] = pd.NA
    g.loc[fin, 'home_win'] = (g.loc[fin, 'home_score'].astype(float) > g.loc[fin, 'away_score'].astype(float)).astype(int)
    return g[['season', 'date_et', 'home', 'away', 'home_win', 'status']].sort_values(['season', 'date_et', 'home'])
if __name__ == '__main__':
    clean(pd.read_csv(sys.argv[1])).to_csv(sys.argv[2], index=False)
