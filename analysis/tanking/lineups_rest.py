# Ideas 3 and 4: who closes close games, and who sits, by standings zone at game time.
import pandas as pd, numpy as np, os
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, 'data')
pd.set_option('display.width', 250)
ZONES = [0, 3, 6, 10, 20, 30]; ZL = ['worst 1-3', '4-6', '7-10', '11-20', 'best 10']
INJ = r'(?i)sprain|strain|surgery|fracture|knee|ankle|hamstring|foot|back|wrist|hip|calf|illness|concussion|groin|shoulder|toe|thumb|finger|hand|achilles|quad|elbow|neck|rib|eye|soreness|contusion|tendin|bruise|injury|torn|tear|plantar|abdominal|oblique|knee|leg|protocol|sick|personal|g league|two-way|suspension'
REST = r'(?i)\brest\b|load|injury management|maintenance|recovery'

res3, res4 = [], []
for season in sorted(int(s) for s in os.listdir(D) if s.isdigit()):
    sd = os.path.join(D, str(season))
    g = pd.read_csv(f'{sd}/games.csv', dtype={'event_id': str}).sort_values(['date', 'event_id'])
    if os.environ.get('TO_DAY'):   # keep only games within the first TO_DAY days of each season (same point as this season)
        _d = pd.to_datetime(g.date); g = g[_d <= _d.min() + pd.Timedelta(days=int(os.environ['TO_DAY']))]
    box = pd.read_csv(f'{sd}/box.csv', dtype={'event_id': str, 'athlete_id': str}).merge(g[['event_id', 'date']], on='event_id'); box = box[box.event_id.isin(g.event_id)]
    st = pd.read_csv(f'{sd}/stints.csv', dtype={'event_id': str, 'athlete_id': str}); st = st[st.event_id.isin(g.event_id)]
    fl = pd.read_csv(f'{sd}/flow.csv', dtype={'event_id': str}); fl = fl[fl.event_id.isin(g.event_id)]
    # Standings rank at each game (1 = worst), from records before that date
    rec, rank_at = {}, {}
    for date, x in g.groupby('date'):
        pct = pd.Series({t: (w + .5) / (n + 1) for t, (w, n) in rec.items()})
        rk = pct.rank(method='first') if len(pct) >= 28 and min(n for _, n in rec.values()) >= 5 else None
        for _, r in x.iterrows():
            for t in (r.home, r.away):
                rank_at[(r.event_id, t)] = rk.get(t, np.nan) if rk is not None else np.nan
            hw = r.home_score > r.away_score
            for t, w in ((r.home, hw), (r.away, not hw)):
                a, n = rec.get(t, (0, 0)); rec[t] = (a + w, n + 1)
    # Core players: a team's top-5 by minutes per game over the games before this one (min 3 games played)
    box = box.sort_values('date')
    box['mpg_before'] = box.groupby(['team', 'athlete_id'])['min'].transform(lambda m: m.fillna(0).shift().expanding().mean())
    box['gp_before'] = box.groupby(['team', 'athlete_id']).cumcount()
    box['core_rank'] = box[box.gp_before >= 3].groupby(['event_id', 'team']).mpg_before.rank(ascending=False, method='first')
    core5 = box[box.core_rank <= 5]
    # Idea 3: close games (|margin| <= 5 with 5:00 left in Q4) -> core-5 share of floor time over the last 5 minutes
    m43 = fl[fl.minute == 43].set_index('event_id').home_margin
    close = set(m43[m43.abs() <= 5].index)
    s = st[st.event_id.isin(close)].copy()
    s['sec'] = np.clip(np.minimum(s.t_out, 2880) - np.maximum(s.t_in, 2580), 0, None)
    s = s[s.sec > 0]
    ck = set(zip(core5.event_id, core5.athlete_id))
    s['core'] = [(e, a) in ck for e, a in zip(s.event_id, s.athlete_id)]
    for (ev, team), z in s.groupby(['event_id', 'team']):
        res3.append(dict(season=season, rank=rank_at.get((ev, team)), core_share=z.sec[z.core].sum() / z.sec.sum()))
    # Idea 4: regulars = the team's top-7 by minutes per team game over its previous 15 games. A regular missing from the box
    # score, or listed DNP, counts as sitting; the listed reason (if any) says why.
    rows4 = []
    for team, tg in box.groupby('team'):
        evs = list(dict.fromkeys(tg.sort_values('date').event_id))
        mins = tg.pivot_table(index='event_id', columns='athlete_id', values='min', aggfunc='sum').reindex(evs).fillna(0)
        info = tg.set_index(['event_id', 'athlete_id'])
        for i in range(8, len(evs)):
            ev = evs[i]
            core = mins.iloc[max(0, i - 15):i].mean().nlargest(7).index
            for a in core:
                if (ev, a) in info.index:
                    r = info.loc[(ev, a)]
                    r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
                    sat = bool(r.dnp) or not (r['min'] > 0); reason = '' if pd.isna(r.reason) else str(r.reason)
                else:
                    sat, reason = True, 'not listed'
                rows4.append(dict(event_id=ev, team=team, sat=sat, reason=reason))
    core7 = pd.DataFrame(rows4).merge(g[['event_id', 'date']], on='event_id')
    core7['why'] = np.where(~core7.sat, 'played', np.where(core7.reason.str.contains(REST), 'rest/management',
                   np.where(core7.reason.eq('not listed'), 'not listed (injured/away)',
                   np.where(core7.reason.str.contains(INJ), 'injury/other', 'coach decision / unlisted'))))
    core7['rank'] = [rank_at.get((e, t)) for e, t in zip(core7.event_id, core7.team)]
    core7['month'] = pd.to_datetime(core7.date).dt.month
    core7['season'] = season
    res4.append(core7[['season', 'rank', 'month', 'why', 'reason']])

R3 = pd.DataFrame(res3).dropna(); R3['zone'] = pd.cut(R3['rank'], ZONES, labels=ZL)
print('Idea 3. Close games (within 5 with 5:00 left): share of the last 5 minutes played by the team\'s top-5 regulars')
print(R3.groupby(['season', 'zone'], observed=True).core_share.agg(['size', 'mean']).unstack('zone').round(3).to_string())
R4 = pd.concat(res4).dropna(subset=['rank']); R4['zone'] = pd.cut(R4['rank'], ZONES, labels=ZL)
print('\nIdea 4. Top-7 regulars: % of regular-games missed, by reason and standings zone')
t = R4.groupby(['season', 'zone'], observed=True).why.value_counts(normalize=True).unstack().drop(columns='played', errors='ignore') * 100
print(t.round(1).to_string())
print('\n  after Feb 1 only:')
late = R4[R4.month.isin([2, 3, 4])]
if len(late):
    print((late.groupby(['season', 'zone'], observed=True).why.value_counts(normalize=True).unstack().drop(columns='played', errors='ignore') * 100).round(1).to_string())
print('\nmost common non-injury reasons:', R4[R4.why.isin(['rest/management', 'coach decision / unlisted'])].reason.value_counts().head(8).to_dict())
