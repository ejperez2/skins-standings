# Tanking-study data logger (not used by the webpage). Run daily; safe to re-run (each source is de-duplicated).
#   1. Basketball-Reference projected lottery odds for all 30 teams  -> data/lottery_odds.csv (one snapshot per Central date)
#   2. ESPN game summaries for every finished regular-season game     -> data/<season>/games.csv, box.csv, stints.csv, flow.csv
#   2b. ESPN injury report (current only, so saved daily)  -> data/injuries.csv
#   3. ESPN player bio (birth date, draft) for every player seen      -> data/athletes.csv
# Usage: python log_daily.py                      (lottery odds + games from the last 5 days)
#        python log_daily.py 2025-10-21 2026-04-12 (backfill games for a date range; skips lottery odds)
import sys, os, io, datetime as dt, concurrent.futures as cf
import pandas as pd, requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
SB = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}'
SUM = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={}'
ATH = 'https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{}'
BR_DRAFT = 'https://www.basketball-reference.com/friv/proj_draft.html'
UA = {'User-Agent': 'Mozilla/5.0'}


def get_json(url, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


def append_csv(path, df, keys):
    """Append rows, replacing any existing rows with the same key values."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        old = pd.read_csv(path, dtype={k: str for k in keys})
        df = df.astype({k: str for k in keys})
        old = old[~old.set_index(keys).index.isin(df.set_index(keys).index)]
        df = pd.concat([old, df])
    df.sort_values(keys).to_csv(path, index=False)


# ---------- 1. Lottery odds ----------
def log_lottery_odds():
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-6))).date().isoformat()   # Central (standard) date
    html = requests.get(BR_DRAFT, headers=UA, timeout=30).text
    t = pd.read_html(io.StringIO(html))[0]
    t.columns = ['rk', 'team', 'w', 'l', 'wpct', 'ball0', 'ball1', 'ball2', 'ball3', 'bottom3'][:t.shape[1]]
    t = t[pd.to_numeric(t.rk, errors='coerce').notna()].copy()
    for c in ['ball0', 'ball1', 'ball2', 'ball3', 'bottom3']:
        t[c] = pd.to_numeric(t[c], errors='coerce').fillna(0.0)
    if len(t) != 30:
        raise RuntimeError(f'expected 30 teams, got {len(t)}')
    t.insert(0, 'date', today)
    append_csv(os.path.join(DATA, 'lottery_odds.csv'), t, ['date', 'team'])
    print(f'lottery odds: {today}, {len(t)} teams')


# ---------- 1b. Injury report (ESPN only shows the current report, so it has to be saved daily) ----------
def log_injuries():
    import re
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-6))).date().isoformat()
    j = get_json('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries')
    rows = []
    for t in j['injuries']:
        for x in t['injuries']:
            href = ' '.join(l.get('href', '') for l in x['athlete'].get('links', []))
            m = re.search(r'/id/(\d+)', href)
            d = x.get('details', {})
            rows.append(dict(date=today, team=t['displayName'], athlete_id=m.group(1) if m else '', name=x['athlete'].get('displayName'),
                             status=x.get('status'), type=d.get('type'), detail=d.get('detail'), return_date=d.get('returnDate'),
                             comment=x.get('shortComment')))
    append_csv(os.path.join(DATA, 'injuries.csv'), pd.DataFrame(rows), ['date', 'athlete_id', 'name'])
    print(f'injuries: {today}, {len(rows)} listed')


# ---------- 2. Games ----------
def secs(period, clock):
    """Game seconds elapsed at a play."""
    clock = str(clock)
    if ':' in clock:
        m, s = clock.split(':'); left = int(m) * 60 + float(s)
    else:
        left = float(clock)
    if period <= 4:
        return (period - 1) * 720 + (720 - left)
    return 2880 + (period - 5) * 300 + (300 - left)


def period_end(p):
    return p * 720 if p <= 4 else 2880 + (p - 4) * 300


def parse_game(ev_id, season, date):
    try:
        return _parse_game(ev_id, season, date)
    except Exception as e:
        print(f'  {ev_id}: {type(e).__name__}: {e}')
        return None


def _parse_game(ev_id, season, date):
    j = get_json(SUM.format(ev_id))
    if j is None or 'plays' not in j:
        return None
    comp = j['header']['competitions'][0]
    side = {c['homeAway']: c for c in comp['competitors']}
    home_id, away_id = side['home']['team']['id'], side['away']['team']['id']
    abbr = {side[k]['team']['id']: side[k]['team']['abbreviation'] for k in side}
    hs, as_ = int(side['home']['score']), int(side['away']['score'])
    game = dict(season=season, date=date, event_id=ev_id, home=abbr[home_id], away=abbr[away_id], home_score=hs, away_score=as_)

    # Box score
    box, team_of, starters = [], {}, {home_id: [], away_id: []}
    for tb in j['boxscore'].get('players', []):
        tid = tb['team']['id']
        st = tb['statistics'][0]; labels = st['labels']
        for a in st['athletes']:
            if 'id' not in a.get('athlete', {}):
                continue
            aid = a['athlete']['id']; team_of[aid] = tid
            stats = dict(zip(labels, a.get('stats') or []))
            mins = pd.to_numeric(stats.get('MIN'), errors='coerce')
            box.append(dict(event_id=ev_id, team=abbr[tid], athlete_id=aid, name=a['athlete']['displayName'],
                            starter=bool(a.get('starter')), dnp=bool(a.get('didNotPlay')), reason=a.get('reason', ''),
                            min=mins, pts=pd.to_numeric(stats.get('PTS'), errors='coerce'),
                            plus_minus=pd.to_numeric(str(stats.get('+/-', '')).replace('+', ''), errors='coerce')))
            if a.get('starter'):
                starters[tid].append(aid)

    # Plays -> score/win-probability flow and on-court stints
    wp = {w['playId']: w['homeWinPercentage'] for w in j.get('winprobability', [])}
    plays = sorted(j['plays'], key=lambda p: int(p['sequenceNumber']))
    rows = []
    for p in plays:
        per = p['period']['number']
        rows.append(dict(t=secs(per, p['clock']['displayValue']), per=per, hm=p['homeScore'] - p['awayScore'],
                         wp=wp.get(p['id']), typ=p['type']['text'],
                         parts=[x['athlete']['id'] for x in p.get('participants', []) if 'athlete' in x]))
    pl = pd.DataFrame(rows)
    pl['wp'] = pl.wp.ffill().fillna(0.5)
    flow = []
    last_min = int(pl.t.max() // 60)
    for m in range(0, last_min + 1):
        x = pl[pl.t <= m * 60]
        hm, w = (0, 0.5) if x.empty else (x.hm.iloc[-1], x.wp.iloc[-1])
        flow.append(dict(event_id=ev_id, minute=m, home_margin=hm, home_wp=round(w, 4)))

    def state_at(t):
        x = pl[pl.t <= t]
        return (0, 0.5) if x.empty else (x.hm.iloc[-1], x.wp.iloc[-1])

    stints = []
    for per in sorted(pl.per.unique()):
        pp = pl[pl.per == per]
        # Who starts the period: starters in Q1; otherwise anyone who acts (or is subbed out) before being subbed in
        on = {home_id: set(), away_id: set()}
        if per == 1:
            for tid in on: on[tid] = set(starters[tid])
        else:
            seen_in = set()
            for _, p in pp.iterrows():
                if p.typ == 'Substitution' and len(p.parts) == 2:
                    pin, pout = p.parts
                    if pout not in seen_in and pout in team_of: on[team_of[pout]].add(pout)
                    seen_in.add(pin)
                else:
                    for a in p.parts:
                        if a not in seen_in and a in team_of: on[team_of[a]].add(a)
        t0 = period_end(per - 1) if per > 1 else 0
        start = {a: t0 for tid in on for a in on[tid]}
        for _, p in pp.iterrows():
            if p.typ == 'Substitution' and len(p.parts) == 2:
                pin, pout = p.parts
                if pout in start:
                    stints.append((pout, start.pop(pout), p.t))
                start[pin] = p.t
        for a, s in start.items():
            stints.append((a, s, period_end(per)))
    st_rows = []
    for a, s, e in stints:
        if a not in team_of or e <= s:
            continue
        sign = 1 if team_of[a] == home_id else -1
        m0, w0 = state_at(s); m1, _ = state_at(e)
        st_rows.append(dict(event_id=ev_id, team=abbr[team_of[a]], athlete_id=a, t_in=round(s, 1), t_out=round(e, 1),
                            margin_in=sign * m0, margin_out=sign * m1, wp_in=round(w0 if sign == 1 else 1 - w0, 4)))
    return game, box, st_rows, flow


def log_games(d0, d1):
    days = pd.date_range(d0, d1).strftime('%Y%m%d')
    events = []
    with cf.ThreadPoolExecutor(8) as ex:
        for day, j in zip(days, ex.map(lambda d: get_json(SB.format(d)), days)):
            for e in (j or {}).get('events', []):
                c = e['competitions'][0]
                if e['season']['type'] != 2 or c['status']['type']['name'] != 'STATUS_FINAL':
                    continue
                if any('Championship' in n.get('headline', '') for n in c.get('notes', [])):
                    continue   # NBA Cup final does not count in the standings
                events.append((e['id'], e['season']['year'], f'{day[:4]}-{day[4:6]}-{day[6:]}'))
    by_season = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for ev, out in zip(events, ex.map(lambda e: parse_game(*e), events)):
            if out is None:
                print('  summary failed:', ev); continue
            by_season.setdefault(ev[1], []).append(out)
    for season, outs in by_season.items():
        sd = os.path.join(DATA, str(season))
        append_csv(os.path.join(sd, 'games.csv'), pd.DataFrame([o[0] for o in outs]), ['event_id'])
        append_csv(os.path.join(sd, 'box.csv'), pd.DataFrame([r for o in outs for r in o[1]]), ['event_id', 'athlete_id'])
        append_csv(os.path.join(sd, 'stints.csv'), pd.DataFrame([r for o in outs for r in o[2]]), ['event_id', 'athlete_id', 't_in'])
        append_csv(os.path.join(sd, 'flow.csv'), pd.DataFrame([r for o in outs for r in o[3]]), ['event_id', 'minute'])
        print(f'games: season {season}, {len(outs)} games')
    log_athletes()


# ---------- 3. Player bios ----------
def log_athletes():
    path = os.path.join(DATA, 'athletes.csv')
    seen = set(pd.read_csv(path, dtype={'athlete_id': str}).athlete_id) if os.path.exists(path) else set()
    ids = set()
    for sd in os.listdir(DATA):
        f = os.path.join(DATA, sd, 'box.csv')
        if os.path.exists(f):
            ids |= set(pd.read_csv(f, dtype={'athlete_id': str}).athlete_id)
    todo = sorted(ids - seen)
    def bio(a):
        j = get_json(ATH.format(a))
        x = (j or {}).get('athlete', {})
        return dict(athlete_id=a, name=x.get('displayName'), dob=x.get('displayDOB'), draft=x.get('displayDraft'),
                    experience=x.get('displayExperience'))
    if todo:
        with cf.ThreadPoolExecutor(8) as ex:
            append_csv(path, pd.DataFrame(list(ex.map(bio, todo))), ['athlete_id'])
    print(f'athletes: {len(todo)} new')


if __name__ == '__main__':
    if len(sys.argv) == 3:
        log_games(sys.argv[1], sys.argv[2])
    else:
        for f in (log_lottery_odds, log_injuries):
            try:
                f()
            except Exception as e:
                print(f'{f.__name__} skipped:', e)
        today = dt.date.today()
        log_games((today - dt.timedelta(days=5)).isoformat(), today.isoformat())
