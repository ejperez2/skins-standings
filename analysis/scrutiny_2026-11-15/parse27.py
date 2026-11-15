import json, glob, sys, pandas as pd
rows = []
for f in sorted(glob.glob(sys.argv[1] + '/*.json')):
    for ev in json.load(open(f))['events']:
        if ev.get('season', {}).get('type') != 2: continue
        c = ev['competitions'][0]; h = [x for x in c['competitors'] if x['homeAway'] == 'home'][0]; a = [x for x in c['competitors'] if x['homeAway'] == 'away'][0]
        note = ';'.join(n.get('headline', '') for n in c.get('notes', []))
        rows.append(dict(id=ev['id'], date=pd.Timestamp(ev['date']).tz_convert('America/New_York').strftime('%Y-%m-%d'), home=h['team'].get('displayName'), away=a['team'].get('displayName'),
                         status=c['status']['type']['name'], hs=h.get('score'), as_=a.get('score'), note=note))
d = pd.DataFrame(rows).drop_duplicates('id').replace({'LA Clippers': 'Los Angeles Clippers'})
d.to_csv(sys.argv[2], index=False); print(d.status.value_counts().to_string()); print(d[d.note != ''].note.value_counts().head(8).to_string()); print(len(d))
