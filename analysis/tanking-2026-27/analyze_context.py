import pandas as pd, numpy as np, sys
from scipy import stats
import os
R=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..")+os.sep
g=pd.read_csv(sys.argv[1])
T30=set(g[g.season=='2026-27'].home)|set(g[g.season=='2026-27'].away)
g=g[g.home.isin(T30)&g.away.isin(T30)].copy()
g["margin"]=g.hpts-g.apts
g=g.sort_values(["season","date","game_id"]); g["idx"]=g.groupby("season").cumcount()
N=(g.season=="2026-27").sum()
DEADLINE={"2018-19":"2019-02-08","2019-20":"2020-02-07","2021-22":"2022-02-11","2022-23":"2023-02-10","2023-24":"2024-02-09","2024-25":"2025-02-07","2025-26":"2026-02-06"}
BBR2ESPN={'BRK':'BKN','CHO':'CHA','GSW':'GS','NOP':'NO','NYK':'NY','PHO':'PHX','SAS':'SA','UTA':'UTAH','WAS':'WSH'}
names=pd.read_csv(R+"team_projection_history.csv").team.unique()
# full-name -> ESPN abbr via nickname match on espn ids
NAME2={'Atlanta Hawks':'ATL','Boston Celtics':'BOS','Brooklyn Nets':'BKN','Charlotte Hornets':'CHA','Chicago Bulls':'CHI','Cleveland Cavaliers':'CLE','Dallas Mavericks':'DAL','Denver Nuggets':'DEN','Detroit Pistons':'DET','Golden State Warriors':'GS','Houston Rockets':'HOU','Indiana Pacers':'IND','Los Angeles Clippers':'LAC','Los Angeles Lakers':'LAL','Memphis Grizzlies':'MEM','Miami Heat':'MIA','Milwaukee Bucks':'MIL','Minnesota Timberwolves':'MIN','New Orleans Pelicans':'NO','New York Knicks':'NY','Oklahoma City Thunder':'OKC','Orlando Magic':'ORL','Philadelphia 76ers':'PHI','Phoenix Suns':'PHX','Portland Trail Blazers':'POR','Sacramento Kings':'SAC','San Antonio Spurs':'SA','Toronto Raptors':'TOR','Utah Jazz':'UTAH','Washington Wizards':'WSH'}
assert set(NAME2.values())==T30, set(NAME2.values())^T30

def long(d):
    q=lambda s: s.fillna("").str.split("|")
    h=pd.DataFrame(dict(season=d.season,idx=d.idx,date=d.date,team=d.home,opp=d.away,m=d.margin,hq=q(d.hq),aq=q(d.aq)))
    a=pd.DataFrame(dict(season=d.season,idx=d.idx,date=d.date,team=d.away,opp=d.home,m=-d.margin,hq=q(d.aq),aq=q(d.hq)))
    L=pd.concat([h,a],ignore_index=True)
    ok=L.hq.str.len()>=4
    L=L[ok].copy()
    tq=np.array([[int(x) for x in v[:4]] for v in L.hq]); oq=np.array([[int(x) for x in v[:4]] for v in L.aq])
    L["q13"]=(tq[:,:3]-oq[:,:3]).sum(1); L["q4"]=tq[:,3]-oq[:,3]; L["win"]=(L.m>0).astype(int)
    return L.drop(columns=["hq","aq"])
L=long(g)

# ---------- A. Preseason market expectation vs early results ----------
print("=== A. Preseason win-total dispersion and early-results calibration ===")
pres={}
t=pd.read_csv(R+"archive/history/team_snapshots_2022-26.csv")
for s in ["2023-24","2024-25","2025-26"]:
    x=t[t.season==s]; x=x[x.date==x.date.min()]
    pres[s]=(x.date.iloc[0], dict(zip(x.team_bbr.map(lambda c:BBR2ESPN.get(c,c)),x.proj_wins)), x.approx_games_played.iloc[0])
v=pd.read_csv(R+"team_vegas_history.csv"); v=v[v.date=="2026-10-20"]
pres["2026-27"]=("2026-10-20",dict(zip(v.team.map(NAME2),v.vegas_proj_wins)),0.0)
cal=[]
for s,(dt,proj,gp) in pres.items():
    e=L[(L.season==s)&(L.idx<N)].groupby("team").agg(mov=("m","mean"),w=("win","sum"),gp=("m","size"))
    e["proj"]=pd.Series(proj); e["imp"]=(e.proj-41)/2.7
    sl=stats.linregress(e.imp,e.mov)
    bot=e.nsmallest(10,"proj"); top=e.nlargest(10,"proj")
    print(f"{s}: line date {dt} (~{gp} GP)  preseason SD wins={np.std(list(proj.values())):.2f}  slope(early MOV ~ implied MOV)={sl.slope:.2f}±{sl.stderr:.2f}  r={sl.rvalue:.2f}  "
          f"bottom-10-projected: proj {bot.proj.mean():.1f}W, early MOV {bot.mov.mean():+.1f} vs implied {bot.imp.mean():+.1f} (resid {(bot.mov-bot.imp).mean():+.1f}) | top-10 resid {(top.mov-top.imp).mean():+.1f}")
    cal.append(e.assign(season=s))
C=pd.concat(cal)
cur=C[C.season=="2026-27"].sort_values("mov")
print("\n2026-27 teams sorted by early MOV, with preseason line:")
print(cur[["w","gp","mov","proj","imp"]].assign(resid=cur.mov-cur.imp).round(1).head(12).to_string())

# ---------- B. Within-season timing: where did tanking show up historically? ----------
print("\n=== B. Dispersion & bottom tail by phase of season (team MOV) ===")
print("phase: first-N | N..deadline | post-deadline.  sd_mov, noise-adjusted talent SD, bottom-5 MOV, 20+pt blowout rate")
for s in sorted(L.season.unique()):
    rows=[]
    sub=L[L.season==s]
    phases={"early":sub[sub.idx<N]}
    if s in DEADLINE:
        phases["mid"]=sub[(sub.idx>=N)&(sub.date<DEADLINE[s])]
        phases["post"]=sub[sub.date>=DEADLINE[s]]
    out=[]
    for p,d in phases.items():
        tt=d.groupby("team").agg(mov=("m","mean"),gp=("m","size"))
        noise=(13.0**2/tt.gp).mean()
        out.append(f"{p}: sd {tt.mov.std(ddof=0):4.1f} talent {np.sqrt(max(tt.mov.var(ddof=0)-noise,0)):4.1f} bot5 {tt.mov.nsmallest(5).mean():+5.1f} bl20 {(d.m.abs()>=20).mean()/1:.3f}")
    print(s," | ".join(out))

# ---------- C. Late-game (4th quarter) fade in close games: the classic tank signature ----------
print("\n=== C. 4th-quarter net points in games within 8 after 3 quarters ===")
print("bottom10 = 10 worst teams by full-season MOV (prior seasons) / by preseason line (2026-27). Diff = bottom10 minus rest.")
def q4(d):
    c=d[d.q13.abs()<=8]; return c.q4.mean(), c.q4.std()/np.sqrt(len(c)), len(c), c.win.mean()
for s in sorted(L.season.unique()):
    sub=L[L.season==s]
    if s=="2026-27":
        proj=pres[s][1]; bottom=set(sorted(proj,key=proj.get)[:10])
    else:
        bottom=set(sub.groupby("team").m.mean().nsmallest(10).index)
    res=[]
    phases=[("early",sub.idx<N)]+([("post",sub.date>=DEADLINE[s])] if s in DEADLINE else [])
    for p,mask in phases:
        d=sub[mask]; b=q4(d[d.team.isin(bottom)]); r=q4(d[~d.team.isin(bottom)&~d.opp.isin(bottom)])
        bvr=d[d.team.isin(bottom)&~d.opp.isin(bottom)]  # bottom vs rest only
        x=q4(bvr)
        res.append(f"{p}: bottom10 vs rest Q4 {x[0]:+.2f}±{x[1]:.2f} (n={x[2]}, close-game W% {x[3]:.2f})")
    print(s," | ".join(res))

# ---------- D. The article's 'tanking 10' across phases ----------
print("\n=== D. Last year's 'tanking 10': MOV and record by phase ===")
TANK=["UTAH","CHI","MIL","BKN","SAC","NO","IND","DAL","WSH","MEM"]
p25=L[L.season=="2025-26"]; p26=L[L.season=="2026-27"]
def rec(d): return f"{d.win.sum()}-{len(d)-d.win.sum()} ({d.m.mean():+.1f})"
print(f"{'team':5s} {'2025-26 first N':>16s} {'25-26 N..deadline':>18s} {'25-26 post-deadl.':>18s} {'2026-27 first N':>16s} {'26-27 line':>10s}")
agg=[]
for tm in TANK:
    a=p25[(p25.team==tm)&(p25.idx<N)]; b=p25[(p25.team==tm)&(p25.idx>=N)&(p25.date<DEADLINE["2025-26"])]; c=p25[(p25.team==tm)&(p25.date>=DEADLINE["2025-26"])]; d=p26[p26.team==tm]
    print(f"{tm:5s} {rec(a):>16s} {rec(b):>18s} {rec(c):>18s} {rec(d):>16s} {pres['2026-27'][1][tm]:10.1f}")
    agg.append((a.m.mean(),b.m.mean(),c.m.mean(),d.m.mean()))
agg=np.array(agg); print("mean MOV:", np.round(agg.mean(0),1))
allT=lambda d: d[d.team.isin(TANK)]
print("pooled:", rec(allT(p25[p25.idx<N])), rec(allT(p25[(p25.idx>=N)&(p25.date<DEADLINE['2025-26'])])), rec(allT(p25[p25.date>=DEADLINE['2025-26']])), rec(allT(p26)))

# ---------- E. Article's 'more blowouts' claim restricted to games NOT involving bottom teams ----------
print("\n=== E. Who is in the blowouts? (first N games) ===")
for s in sorted(g.season.unique()):
    d=g[(g.season==s)&(g.idx<N)]
    mov=L[(L.season==s)&(L.idx<N)].groupby("team").m.mean(); bot=set(mov.nsmallest(6).index)
    inv=d.home.isin(bot)|d.away.isin(bot)
    print(s, f"20+ blowouts: {(d.margin.abs()>=20).sum()}  of which involve current bottom-6: {((d.margin.abs()>=20)&inv).sum()}  | blowout rate w/o bottom-6 games: {(d[~inv].margin.abs()>=20).mean():.3f}")
