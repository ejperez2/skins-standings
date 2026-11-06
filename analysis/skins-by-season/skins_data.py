"""League-wide skins % by season -> skins_data.json (feeds skins_report.html).
Uses ../tanking-2026-27/games.csv (game results), archive rosters (2022-26), the 2026-27 draft in index.qmd,
preseason Vegas lines (team_vegas_history.csv) and schedule_2026-27.csv (unplayed games)."""
import pandas as pd, numpy as np, json, os, re

def drop_cup_final(g):
    """ESPN lists the NBA Cup final as a regular-season game, but it doesn't count in the standings.
    Drop the December game between the two teams that would otherwise have 83 games."""
    keep=[]
    for s_,d_ in g.groupby("season"):
        gp=pd.concat([d_.home,d_.away]).value_counts(); extra=set(gp[gp>82].index)
        m=d_.home.isin(extra)&d_.away.isin(extra)&d_.date.str[5:7].eq("12")
        if m.sum()>1: m&=d_.date.eq(d_[m].date.max())
        keep.append(d_[~m])
    return pd.concat(keep)
from scipy.stats import norm
here=os.path.dirname(os.path.abspath(__file__)); R=os.path.join(here,"..","..")
rng=np.random.default_rng(11)
g=pd.read_csv(os.path.join(here,"..","tanking-2026-27","games.csv"))
T30=sorted(set(g[g.season=="2026-27"].home)|set(g[g.season=="2026-27"].away)); TI={t:i for i,t in enumerate(T30)}
g=g[g.home.isin(T30)&g.away.isin(T30)].copy()
g["margin"]=g.hpts-g.apts
g=drop_cup_final(g)
g=g.sort_values(["season","date","game_id"]); g["idx"]=g.groupby("season").cumcount()
N=int((g.season=="2026-27").sum())
CUR="2026-27"
DEADLINE={"2018-19":"2019-02-08","2019-20":"2020-02-07","2021-22":"2022-02-11","2022-23":"2023-02-10","2023-24":"2024-02-09","2024-25":"2025-02-07","2025-26":"2026-02-06"}
BBR={'BRK':'BKN','CHO':'CHA','GSW':'GS','NOP':'NO','NYK':'NY','PHO':'PHX','SAS':'SA','UTA':'UTAH','WAS':'WSH'}
# rosters
ro=pd.read_csv(os.path.join(R,"archive","history","rosters_and_finals_2022-26.csv"))
PICKS={s:dict(zip(d.team_bbr.map(lambda c:BBR.get(c,c)),d.pick)) for s,d in ro.groupby("season")}
qmd=open(os.path.join(R,"index.qmd")).read()
blk=qmd[qmd.index("draft_data <- tribble("):]; blk=blk[:blk.index("\n)")]
cur_picks={}
for m in re.finditer(r'"([^"]+)",\s*"(\w+)",\s*"(\w+)",\s*"([WL])"',blk):
    cur_picks[BBR.get(m.group(3),m.group(3))]=m.group(4)
PICKS[CUR]=cur_picks
for s,p in PICKS.items(): assert set(p)==set(T30), (s,set(T30)^set(p))
DRAFTED=sorted(PICKS)

def game_skins(d,picks):
    hw=d.margin>0
    hp=d.home.map(picks); ap=d.away.map(picks)
    return ((hp=="W")&hw).astype(int)+((hp=="L")&~hw).astype(int)+((ap=="W")&~hw).astype(int)+((ap=="L")&hw).astype(int)
out={"N":N}
# 1. cumulative paths + phases + decomposition
paths={}; phase=[]; decomp=[]
for s in DRAFTED:
    d=g[g.season==s].copy(); d["sk"]=game_skins(d,PICKS[s]).values
    cum=d.sk.cumsum()/(2*np.arange(1,len(d)+1))
    paths[s]=np.round(cum.values*100,4).tolist()
    ph={"early":d[d.idx<N]}
    if s in DEADLINE: ph["mid"]=d[(d.idx>=N)&(d.date<DEADLINE[s])]; ph["post"]=d[d.date>=DEADLINE[s]]
    for p,x in ph.items(): phase.append(dict(season=s,phase=p,games=len(x),pct=round(float(x.sk.sum()/(2*len(x))*100),4)))
    for lab,x in [("early",d[d.idx<N]),("full",d)]:
        hp=x.home.map(PICKS[s]); ap=x.away.map(PICKS[s]); wl=hp!=ap
        wside_win=np.where(hp[wl]=="W",x.margin[wl]>0,x.margin[wl]<0)
        decomp.append(dict(season=s,window=lab,games=len(x),share_wl=round(float(wl.mean()*100),1),wpick_win=round(float(wside_win.mean()*100),1),pct=round(float(x.sk.sum()/(2*len(x))*100),4)))
out["paths"]=paths; out["phase"]=phase; out["decomp"]=decomp
# 2. hindsight-best skins % (each team on its better side), all seasons
def best(d):
    h=pd.DataFrame(dict(t=d.home,w=d.margin>0)); a=pd.DataFrame(dict(t=d.away,w=d.margin<0))
    t=pd.concat([h,a]).groupby("t").w.agg(["sum","size"])
    return float(np.maximum(t["sum"],t["size"]-t["sum"]).sum()/t["size"].sum()*100)
bst=[]
for s in sorted(g.season.unique()):
    d=g[g.season==s]; e=d[d.idx<N]
    row=dict(season=s,best_early=round(best(e),2),best_full=None if s==CUR else round(best(d),2))
    if s in PICKS:
        sk=game_skins(d,PICKS[s]); se=game_skins(e,PICKS[s])
        row.update(drafted_early=round(float(se.sum()/(2*len(e))*100),2),drafted_full=None if s==CUR else round(float(sk.sum()/(2*len(d))*100),2))
    bst.append(row)
out["best"]=bst
# 3. simulation for 2026-27 from preseason Vegas lines
NAME2={'Atlanta Hawks':'ATL','Boston Celtics':'BOS','Brooklyn Nets':'BKN','Charlotte Hornets':'CHA','Chicago Bulls':'CHI','Cleveland Cavaliers':'CLE','Dallas Mavericks':'DAL','Denver Nuggets':'DEN','Detroit Pistons':'DET','Golden State Warriors':'GS','Houston Rockets':'HOU','Indiana Pacers':'IND','Los Angeles Clippers':'LAC','Los Angeles Lakers':'LAL','Memphis Grizzlies':'MEM','Miami Heat':'MIA','Milwaukee Bucks':'MIL','Minnesota Timberwolves':'MIN','New Orleans Pelicans':'NO','New York Knicks':'NY','Oklahoma City Thunder':'OKC','Orlando Magic':'ORL','Philadelphia 76ers':'PHI','Phoenix Suns':'PHX','Portland Trail Blazers':'POR','Sacramento Kings':'SAC','San Antonio Spurs':'SA','Toronto Raptors':'TOR','Utah Jazz':'UTAH','Washington Wizards':'WSH'}
v=pd.read_csv(os.path.join(R,"team_vegas_history.csv")); v=v[v.date=="2026-10-20"]
imp=np.zeros(30)
for n,w in zip(v.team,v.vegas_proj_wins): imp[TI[NAME2[n]]]=(w-41)/2.7
imp-=imp.mean()
# home advantage and per-game spread from 2025-26
d25=g[g.season=="2025-26"]; X=np.zeros((len(d25),31))
for r,(h,a) in enumerate(zip(d25.home,d25.away)): X[r,TI[h]]=1; X[r,TI[a]]=-1
X[:,30]=1; b,*_=np.linalg.lstsq(X,d25.margin.values,rcond=None); HCA=float(b[30]); SIG=float((d25.margin.values-X@b).std())
TAL_SD=8.6/2.7  # preseason projection miss (README TALENT_SD 8.6 wins) in points
sch=pd.read_csv(os.path.join(here,"schedule_2026-27.csv")); sch=sch[sch.home.isin(T30)&sch.away.isin(T30)]
cur=g[g.season==CUR]
H=np.r_[cur.home.map(TI).values,sch.home.map(TI).values]; A=np.r_[cur.away.map(TI).values,sch.away.map(TI).values]
pk=np.array([1 if PICKS[CUR][t]=="W" else -1 for t in T30])  # +1 W pick, -1 L pick
def sim(reps,talent_unc=True,cond=False):
    paths=np.zeros((reps,len(H)),dtype=np.float32)
    act=game_skins(cur,PICKS[CUR]).values
    for r in range(reps):
        tal=imp+(rng.normal(0,TAL_SD,30) if talent_unc else 0)
        p=norm.cdf((tal[H]-tal[A]+HCA)/SIG); hw=rng.random(len(H))<p
        sk=(np.where(pk[H]==1,hw,~hw).astype(int)+np.where(pk[A]==1,~hw,hw).astype(int))
        if cond: sk[:N]=act
        paths[r]=np.cumsum(sk)/(2*np.arange(1,len(H)+1))*100
    return paths
P=sim(4000)
qs=[2.5,10,50,90,97.5]
band={str(q):np.round(np.percentile(P,q,axis=0),2)[::5].tolist() for q in qs}
obs=float(game_skins(cur,PICKS[CUR]).sum()/(2*N)*100)
P0=sim(4000,talent_unc=False)
C=sim(4000,cond=True)
out["sim"]=dict(hca=round(HCA,2),sigma=round(SIG,2),tal_sd=round(TAL_SD,2),games_total=len(H),band_step=5,band=band,
  at_N=np.round(P[:,N-1],2).tolist(),obs=round(obs,2),p_ge=round(float((P[:,N-1]>=obs-1e-3).mean()),3),p_ge_nounc=round(float((P0[:,N-1]>=obs-1e-3).mean()),3),p_ge_skins=int(round(obs*2*N/100)),
  median_at_N=round(float(np.median(P[:,N-1])),2),final_pre=[round(float(np.percentile(P[:,-1],q)),2) for q in qs],
  final_cond=[round(float(np.percentile(C[:,-1],q)),2) for q in qs])

# 4. W/L pick split per season and what this season's W-pick win rate would give under each split
e26=[r for r in decomp if r["season"]==CUR and r["window"]=="early"][0]
split=[]
for s_ in DRAFTED:
    nW=sum(1 for k in PICKS[s_].values() if k=="W")
    split.append(dict(season=s_,w=nW,l=30-nW,exp_share=round(nW*(30-nW)/435*100,1),
                      cf=round(50+nW*(30-nW)/435*(e26["wpick_win"]-50),2)))
out["split"]=split

# 5. draft quality: actual vs following the preseason lines vs best possible (full season; 2026-27 so far)
PRE=pd.read_csv(os.path.join(here,"..","tanking-2026-27","preseason_win_totals.csv"))
dq=[]
for s_ in DRAFTED:
    x=g[g.season==s_]
    w=pd.concat([x.home[x.margin>0],x.away[x.margin<0]]).value_counts().reindex(T30,fill_value=0)
    gp=pd.concat([x.home,x.away]).value_counts().reindex(T30)
    line=PRE[PRE.season==s_].set_index("team").win_total
    pk=pd.Series(PICKS[s_])
    tot=gp.sum()
    act=float(np.where(pk[T30]=="W",w,gp-w).sum()/tot*100)
    lines=float(np.where(line[T30]>41,w,gp-w).sum()/tot*100)
    bestv=float(np.maximum(w,gp-w).sum()/tot*100)
    dis=[dict(team=t,pick=pk[t],line=float(line[t]),pct=round(float((w[t] if pk[t]=="W" else gp[t]-w[t])/gp[t]*100),1)) for t in T30 if (pk[t]=="W")!=(line[t]>41)]
    wrong=int(sum((pk[t]=="W")!=(w[t]>gp[t]-w[t]) for t in T30 if w[t]*2!=gp[t]))
    dq.append(dict(season=s_,so_far=s_==CUR,actual=round(act,4),lines=round(lines,4),best=round(bestv,4),capture=round((act-50)/(bestv-50)*100,1),against=dis,wrong=wrong))
out["draft_quality"]=dq
json.dump(out,open(os.path.join(here,"skins_data.json"),"w"))
print("finals:",{s:paths[s][-1] for s in DRAFTED}); print("at N:",{s:paths[s][N-1] for s in DRAFTED})
print(pd.DataFrame(phase).pivot(index="season",columns="phase",values="pct"))
print(pd.DataFrame(decomp).to_string()); print(pd.DataFrame(bst).to_string())
print({k:v for k,v in out["sim"].items() if k not in("band","at_N")})
