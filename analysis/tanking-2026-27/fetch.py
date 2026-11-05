import json, sys, datetime as dt, urllib.request, csv, os
from concurrent.futures import ThreadPoolExecutor
OUT = sys.argv[1]
# (season label, first day to scan, last day to scan)
SEASONS = {
 "2018-19": ("2018-10-16","2019-04-10"),
 "2019-20": ("2019-10-22","2020-03-11"),
 "2021-22": ("2021-10-19","2022-04-10"),
 "2022-23": ("2022-10-18","2023-04-09"),
 "2023-24": ("2023-10-24","2024-04-14"),
 "2024-25": ("2024-10-22","2025-04-13"),
 "2025-26": ("2025-10-21","2026-04-12"),
 "2026-27": ("2026-10-01","2026-11-05"),
}
def get(day):
    url=f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day:%Y%m%d}&limit=50"
    for _ in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: return day, json.load(r)
        except Exception as e: err=e
    print("FAIL", day, err, file=sys.stderr); return day, {"events":[]}
rows=[]
for s,(a,b) in SEASONS.items():
    d0=dt.date.fromisoformat(a); d1=dt.date.fromisoformat(b)
    days=[d0+dt.timedelta(i) for i in range((d1-d0).days+1)]
    with ThreadPoolExecutor(12) as ex:
        for day,js in ex.map(get, days):
            for e in js.get("events",[]):
                if e["season"]["type"]!=2: continue
                if not e["status"]["type"]["completed"]: continue
                c=e["competitions"][0]
                h=[t for t in c["competitors"] if t["homeAway"]=="home"][0]
                v=[t for t in c["competitors"] if t["homeAway"]=="away"][0]
                rows.append(dict(season=s, game_id=e["id"], date=e["date"][:10],
                    home=h["team"]["abbreviation"], away=v["team"]["abbreviation"],
                    hpts=int(h["score"]), apts=int(v["score"]),
                    hq="|".join(str(int(float(x.get("value",0)))) for x in h.get("linescores",[])),
                    aq="|".join(str(int(float(x.get("value",0)))) for x in v.get("linescores",[]))))
    print(s, sum(r["season"]==s for r in rows), file=sys.stderr)
rows={r["game_id"]:r for r in rows}.values()
with open(OUT,"w",newline="") as f:
    w=csv.DictWriter(f, fieldnames=list(next(iter(rows)).keys())); w.writeheader(); w.writerows(sorted(rows,key=lambda r:(r["season"],r["date"],r["game_id"])))
