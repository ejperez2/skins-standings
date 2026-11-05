"""Dispersion of team scoring margin by season phase -> phase_dispersion.json (feeds the chart)."""
import pandas as pd, numpy as np, json, sys, os
here=os.path.dirname(os.path.abspath(__file__))
g=pd.read_csv(os.path.join(here,"games.csv"))
T30=set(g[g.season=="2026-27"].home)|set(g[g.season=="2026-27"].away)
g=g[g.home.isin(T30)&g.away.isin(T30)].copy()
g["margin"]=g.hpts-g.apts
g=g.sort_values(["season","date","game_id"]); g["idx"]=g.groupby("season").cumcount()
N=int((g.season=="2026-27").sum())
DEADLINE={"2018-19":"2019-02-08","2019-20":"2020-02-07","2021-22":"2022-02-11","2022-23":"2023-02-10","2023-24":"2024-02-09","2024-25":"2025-02-07","2025-26":"2026-02-06"}
NOISE=13.0  # per-game margin noise SD, as in the README
out=[]
for s in sorted(g.season.unique()):
    sub=g[g.season==s]
    phases={"early":sub[sub.idx<N]}
    if s in DEADLINE:
        phases["mid"]=sub[(sub.idx>=N)&(sub.date<DEADLINE[s])]
        phases["post"]=sub[sub.date>=DEADLINE[s]]
    for p,d in phases.items():
        h=pd.DataFrame(dict(team=d.home,m=d.margin)); a=pd.DataFrame(dict(team=d.away,m=-d.margin))
        t=pd.concat([h,a]).groupby("team").m.agg(["mean","size"])
        raw=t["mean"].std(ddof=0); noise=(NOISE**2/t["size"]).mean()
        out.append(dict(season=s,phase=p,games=len(d),gp=round(float(t["size"].mean()),1),
                        raw_sd=round(float(raw),2),talent_sd=round(float(np.sqrt(max(raw**2-noise,0))),2)))
json.dump(out,open(os.path.join(here,"phase_dispersion.json"),"w"),indent=1)
print(pd.DataFrame(out).to_string())
