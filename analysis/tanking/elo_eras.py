# Ideas 2 and 5: late-season results of teams near the bottom of the standings, vs an Elo expectation, by lottery era.
import pandas as pd, numpy as np, glob, os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
h = pd.read_csv(f'{R}/archive/history/games_2000-26.csv'); h = h[h.season_end < 2023][['season_end', 'date', 'home', 'away', 'margin', 'home_win']]
s = pd.read_csv(f'{R}/archive/history/scores_2023-26.csv')[['season_end', 'date', 'home', 'away', 'margin', 'home_win']]
cur = pd.read_csv(f'{R}/analysis/tanking/data/2027/games.csv') if os.path.exists(f'{R}/analysis/tanking/data/2027/games.csv') else None
G = pd.concat([h, s])
if cur is not None:   # this season, ESPN abbreviations -> full names
    from development_names import ABBR
    G = pd.concat([G, pd.DataFrame({'season_end': 2027, 'date': cur.date, 'home': cur.home.map(ABBR), 'away': cur.away.map(ABBR),
                                    'margin': cur.home_score - cur.away_score, 'home_win': (cur.home_score > cur.away_score).astype(int)})])
G['date'] = pd.to_datetime(G.date); G = G.sort_values(['date', 'home']).reset_index(drop=True)
G['elo_h'] = 0.0; G['elo_a'] = 0.0
# Bobcats/Hornets, Sonics/Thunder, Nets, Pelicans renames: Elo is carried by franchise name as given; first game of a new name starts at 1500
HCA, K = 70, 20
elo, last_season = {}, None
pre = np.zeros(len(G))
for i, r in G.iterrows():
    if r.season_end != last_season:
        elo = {t: 0.75 * v + 0.25 * 1505 for t, v in elo.items()}; last_season = r.season_end
    eh, ea = elo.get(r.home, 1500), elo.get(r.away, 1500)
    G.at[i, 'elo_h'] = eh; G.at[i, 'elo_a'] = ea
    p = 1 / (1 + 10 ** (-(eh + HCA - ea) / 400)); pre[i] = p
    mov = abs(r.margin) if r.margin == r.margin else 1
    w = r.home_win; d = eh + HCA - ea if w else ea - eh - HCA
    mult = ((mov + 3) ** 0.8) / (7.5 + 0.006 * d)
    elo[r.home] = eh + K * mult * (w - p); elo[r.away] = ea - K * mult * (w - p)
G['p_home'] = pre
# Standings rank at game time (1 = worst win%), games remaining
rows = []
for sea, g in G.groupby('season_end'):
    rec = {}
    n_games = g.groupby('home').size().add(g.groupby('away').size(), fill_value=0).max()
    for _, r in g.iterrows():
        pct = {t: (w + 0.5) / (n + 1) for t, (w, n) in rec.items()}
        rk = pd.Series(pct).rank(method='first') if len(pct) >= 28 else None
        for team, opp, won, p in [(r.home, r.away, r.home_win, r.p_home), (r.away, r.home, 1 - r.home_win, 1 - r.p_home)]:
            gp = rec.get(team, (0, 0))[1]
            rows.append(dict(season=sea, date=r.date, team=team, opp=opp, won=won, p=p, elo=r.elo_h if team == r.home else r.elo_a, opp_elo=r.elo_a if team == r.home else r.elo_h, home=team == r.home, margin=r.margin if team == r.home else -r.margin,
                             rank=rk.get(team) if rk is not None else np.nan, opp_rank=rk.get(opp) if rk is not None else np.nan,
                             left=n_games - gp))
        for team, won in [(r.home, r.home_win), (r.away, 1 - r.home_win)]:
            w, n = rec.get(team, (0, 0)); rec[team] = (w + won, n + 1)
L = pd.DataFrame(rows)
era = lambda s: 'A 2000-04 (steep odds)' if s <= 2004 else ('B 2005-18 (worst 25%)' if s <= 2018 else 'C 2019-26 (bottom 3 flat 14%)')
L['era'] = L.season.map(era)
# Freeze each team's Elo at 25 games left, so the expectation does not learn from the slump we are trying to measure
fz = L[L.left <= 25].sort_values('date').groupby(['season', 'team']).elo.first()
L['elo_fz'] = [fz.get((a, b), np.nan) for a, b in zip(L.season, L.team)]
L['opp_fz'] = [fz.get((a, b), np.nan) for a, b in zip(L.season, L.opp)]
L['p_fz'] = 1 / (1 + 10 ** (-(L.elo_fz - L.opp_fz + np.where(L.home, HCA, -HCA)) / 400))
late = L[(L.left <= 25) & L['rank'].notna()].copy()
late['p'] = late.p_fz
late['zone'] = pd.cut(late['rank'], [0, 3, 6, 10, 15, 30], labels=['1-3 worst', '4-6', '7-10', '11-15', '16-30'])
# ---- Same point of the season: first TO_DAY days, ranks once every team has 5+ games ----
TD = int(os.environ.get('TO_DAY', 32))
L['day'] = (L.date - L.groupby('season').date.transform('min')).dt.days
early = L[(L.day <= TD) & L['rank'].notna()].copy()
early['zone'] = pd.cut(early['rank'], [0, 3, 6, 10, 20, 30], labels=['1-3 worst', '4-6', '7-10', '11-20', 'best 10'])
print(f'To date (first {TD} days): win% minus live Elo expectation (pts), by standings rank at game time')
e = early.groupby(['season', 'zone'], observed=True).apply(lambda z: (z.won - z.p).mean() * 100).unstack()
print(e.loc[2015:].round(1).to_string())
print('past-season mean / sd:', e.loc[:2026].mean().round(1).to_dict(), e.loc[:2026].std().round(1).to_dict())
eh = early[(early['rank'] <= 6) & (early.opp_rank <= 6) & (early.team < early.opp)]
print('bottom-6 vs bottom-6 to date:', eh.groupby('season').apply(lambda z: f"{len(z)} g, close {(z.margin.abs()<=5).mean()*100:.0f}%, abs {z.margin.abs().mean():.1f}", include_groups=False).loc[2019:].to_dict())
print()
print('Idea 2. Last 25 games of each season: win% minus Elo expectation (pts), by standings rank at game time')
t = late.groupby(['era', 'zone'], observed=True).apply(lambda z: pd.Series({'n': len(z), 'resid': (z.won - z.p).mean() * 100,
                                                                              'se': np.sqrt((z.p * (1 - z.p)).sum()) / len(z) * 100}))
print(t.round(1).unstack('zone').to_string())
print('\nby season, worst 3 vs 4-6 residual:')
bys = late.groupby(['season', 'zone'], observed=True).apply(lambda z: (z.won - z.p).mean() * 100).unstack()[['1-3 worst', '4-6']]
print(bys.round(1).T.to_string())
# Idea 5: head-to-head of two bottom-6 teams, last 25 games
hh = late[(late['rank'] <= 6) & (late.opp_rank <= 6) & (late.team < late.opp)]
print('\nIdea 5. Bottom-6 vs bottom-6, last 25 games: closeness')
print(hh.groupby('era').apply(lambda z: pd.Series({'games': len(z), 'avg_abs_margin': z.margin.abs().mean(),
      'close<=5_%': (z.margin.abs() <= 5).mean() * 100, 'blowout20_%': (z.margin.abs() >= 20).mean() * 100}), include_groups=False).round(1))
oth = late[(late['rank'] > 6) & (late.opp_rank > 6) & (late.team < late.opp)]
print('reference, all other late games:', oth.groupby('era').apply(lambda z: f"abs {z.margin.abs().mean():.1f}, close {(z.margin.abs()<=5).mean()*100:.1f}%", include_groups=False).to_dict())
L.to_csv(os.environ.get('ELO_OUT', os.devnull), index=False)
