# Loader for the 24-season history (2000-2026 season-end years, 82-game seasons only):
# preseason win totals (Basketball-Reference preseason odds pages) + every regular-season game.
import pandas as pd, numpy as np, os
D = os.environ.get('HIST_DIR', 'archive/history')
def load():
    ou = pd.read_csv(f'{D}/preseason_win_totals_2000-26.csv'); G = pd.read_csv(f'{D}/games_2000-26.csv')
    ou['n'] = ou.w + ou.l
    # lines are shaded toward the over (they sum to ~1,240): remove each season's average excess
    ou['ou_adj'] = ou.ou - (ou.groupby('season_end').ou.transform('mean') - 41 * ou.n / 82)
    ou['err'] = ou.w - ou.ou_adj
    return ou, G
def team_games(G):
    """Long format: one row per team-game in date order, with game number k (1..82)."""
    a = pd.DataFrame(dict(season_end=G.season_end, date=G.date, team=G.home, opp=G.away, win=G.home_win, margin=G.margin, home=1, nm=G.no_margin))
    b = pd.DataFrame(dict(season_end=G.season_end, date=G.date, team=G.away, opp=G.home, win=1 - G.home_win, margin=-G.margin, home=0, nm=G.no_margin))
    t = pd.concat([a, b]).sort_values(['season_end', 'team', 'date'], kind='stable')
    t['k'] = t.groupby(['season_end', 'team']).cumcount() + 1
    t['cw'] = t.groupby(['season_end', 'team']).win.cumsum(); t['cm'] = t.groupby(['season_end', 'team']).margin.cumsum()
    return t
