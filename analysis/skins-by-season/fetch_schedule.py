"""Fetch the remaining 2026-27 regular-season schedule (unplayed games) from ESPN -> schedule_2026-27.csv"""
import json, sys, datetime as dt, urllib.request, csv, os
from concurrent.futures import ThreadPoolExecutor
here=os.path.dirname(os.path.abspath(__file__))
d0=dt.date(2026,11,5); d1=dt.date(2027,4,15)
def get(day):
    url=f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day:%Y%m%d}&limit=50"
    for _ in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: return day, json.load(r)
        except Exception as e: err=e
    print("FAIL",day,err,file=sys.stderr); return day,{"events":[]}
rows=[]
with ThreadPoolExecutor(12) as ex:
    for day,js in ex.map(get,[d0+dt.timedelta(i) for i in range((d1-d0).days+1)]):
        for e in js.get("events",[]):
            if e["season"]["type"]!=2 or e["status"]["type"]["completed"]: continue
            c=e["competitions"][0]
            h=[t for t in c["competitors"] if t["homeAway"]=="home"][0]; a=[t for t in c["competitors"] if t["homeAway"]=="away"][0]
            rows.append(dict(game_id=e["id"],date=e["date"][:10],home=h["team"]["abbreviation"],away=a["team"]["abbreviation"]))
rows={r["game_id"]:r for r in rows}.values()
with open(os.path.join(here,"schedule_2026-27.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["game_id","date","home","away"]); w.writeheader(); w.writerows(sorted(rows,key=lambda r:(r["date"],r["game_id"])))
print(len(rows))
