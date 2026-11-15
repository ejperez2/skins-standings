# How strongly do REAL drafters' teams miss together? Same-roster correlation of side-signed misses, 2022-26 real rosters,
# with a permutation test (re-deal the same teams and sides to rosters at random) and a bootstrap interval.
import numpy as np, pandas as pd, sys
sys.path.insert(0, sys.argv[1]); from hist import *
REPO, S = sys.argv[2], sys.argv[3]; ou, G = load(); tg = team_games(G).merge(ou[['season_end', 'team', 'ou_adj', 'w']], on=['season_end', 'team'])
CODE = dict(ATL='Atlanta Hawks',BOS='Boston Celtics',BRK='Brooklyn Nets',CHO='Charlotte Hornets',CHI='Chicago Bulls',CLE='Cleveland Cavaliers',DAL='Dallas Mavericks',DEN='Denver Nuggets',DET='Detroit Pistons',GSW='Golden State Warriors',HOU='Houston Rockets',IND='Indiana Pacers',LAC='Los Angeles Clippers',LAL='Los Angeles Lakers',MEM='Memphis Grizzlies',MIA='Miami Heat',MIL='Milwaukee Bucks',MIN='Minnesota Timberwolves',NOP='New Orleans Pelicans',NYK='New York Knicks',OKC='Oklahoma City Thunder',ORL='Orlando Magic',PHI='Philadelphia 76ers',PHO='Phoenix Suns',POR='Portland Trail Blazers',SAC='Sacramento Kings',SAS='San Antonio Spurs',TOR='Toronto Raptors',UTA='Utah Jazz',WAS='Washington Wizards')
ros = pd.read_csv(REPO + '/archive/history/rosters_and_finals_2022-26.csv'); ros['season_end'] = ros.season.str[:4].astype(int) + 1; ros['team'] = ros.team_bbr.map(CODE)
rng = np.random.default_rng(11)
def stat(z, pl):       # mean same-roster product of standardized side-signed misses / mean square
    num = den = 0
    for p in np.unique(pl):
        v = z[pl == p]; num += (v.sum()**2 - (v**2).sum()) / 2; den += len(v) * (len(v) - 1) / 2
    return (num / den) / (z**2).mean()
def analyse(label, data):     # data: list of (z, players) per season
    obs = [stat(z, pl) for z, pl in data]; pooled = np.mean(obs)
    perm = np.array([np.mean([stat(z, rng.permutation(pl)) for z, pl in data]) for _ in range(4000)])
    print('%s: by season %s | pooled %.3f | random re-deals: mean %.3f, sd %.3f, p(re-deal >= observed) = %.3f | rough 95%% interval %.2f to %.2f' % (
        label, np.round(obs, 2), pooled, perm.mean(), perm.std(), (perm >= pooled).mean(), pooled - 1.96 * perm.std(), pooled + 1.96 * perm.std()))
for g in [0, 13, 20, 41]:
    data = []
    for se in [2023, 2024, 2025, 2026]:
        r = ros[ros.season_end == se].set_index('team'); o = ou[ou.season_end == se].set_index('team')
        if g == 0: proj = o.ou_adj; sd = np.sqrt(82 * .25 + 7.2**2)
        else:
            t = tg[(tg.season_end == se) & (tg.k == g)].set_index('team'); tr = tg[(tg.k == g) & (tg.season_end != se)]
            b = np.linalg.lstsq(np.c_[tr.ou_adj / 82 - .5, tr.cw / g - tr.ou_adj / 82], (tr.w - tr.cw) / (82 - g) - tr.ou_adj / 82, rcond=None)[0]
            p0 = t.ou_adj / 82; proj = t.cw + (82 - g) * (p0 + b[0] * (p0 - .5) + b[1] * (t.cw / g - p0)); sd = 1.0
        e = (o.w - proj).reindex(r.index); z = (np.where(r.pick == 'W', 1, -1) * e / sd).values
        data.append((z / z.std(), r.player.values))
    analyse('real rosters, misses from %s' % ('preseason line' if g == 0 else 'game %d (formula)' % g), data)
# this season so far: opening line vs record after ~13 games
d = pd.read_csv(S + '/teams_today.csv'); z = np.where(d.pick == 'W', 1, -1) * (d.wins - d.g * d.weighted_0 / 82) / np.sqrt(d.g * .25 + (8.6 * d.g / 82)**2)
analyse('2026-27 so far (3 rosters of 10, first ~13 games)', [(z.values / z.std(), d.player.values)])
