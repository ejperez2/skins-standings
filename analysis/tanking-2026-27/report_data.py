"""Builds report_data.json, the data behind report.html. Run from anywhere: python3 report_data.py"""
import pandas as pd, numpy as np, json, os

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
here=os.path.dirname(os.path.abspath(__file__)); R=os.path.join(here,"..","..")
rng=np.random.default_rng(7)
g=pd.read_csv(os.path.join(here,"games.csv"))
T30=sorted(set(g[g.season=="2026-27"].home)|set(g[g.season=="2026-27"].away)); TI={t:i for i,t in enumerate(T30)}
g=g[g.home.isin(T30)&g.away.isin(T30)].copy()
g["margin"]=g.hpts-g.apts
g=drop_cup_final(g)
g=g.sort_values(["season","date","game_id"]); g["idx"]=g.groupby("season").cumcount()
N=int((g.season=="2026-27").sum())
CUR="2026-27"; SEAS=sorted(g.season.unique()); PRIOR=[s for s in SEAS if s!=CUR]
DEADLINE={"2018-19":"2019-02-08","2019-20":"2020-02-07","2021-22":"2022-02-11","2022-23":"2023-02-10","2023-24":"2024-02-09","2024-25":"2025-02-07","2025-26":"2026-02-06"}
NOISE=13.0
def phases(s):
    sub=g[g.season==s]; P={"early":sub[sub.idx<N]}
    if s in DEADLINE:
        P["mid"]=sub[(sub.idx>=N)&(sub.date<DEADLINE[s])]; P["post"]=sub[sub.date>=DEADLINE[s]]
    return P
def long(d):
    q=lambda x: x.fillna("").str.split("|")
    h=pd.DataFrame(dict(team=d.home,opp=d.away,m=d.margin,tq=q(d.hq),oq=q(d.aq),idx=d.idx,date=d.date,season=d.season))
    a=pd.DataFrame(dict(team=d.away,opp=d.home,m=-d.margin,tq=q(d.aq),oq=q(d.hq),idx=d.idx,date=d.date,season=d.season))
    return pd.concat([h,a],ignore_index=True)
def team_mov(d):
    L=long(d); return L.groupby("team").m.agg(["mean","size"])
out={}
PRE=pd.read_csv(os.path.join(here,"preseason_win_totals.csv"))
def pre_bottom(season,k=10):
    x=PRE[PRE.season==season].sort_values(["win_total","team"]); return set(x.team.head(k))

# 1. per season x phase: raw/talent SD, bottom-5 raw & shrunk, 20+ blowout rate
rows=[]
for s in SEAS:
    for p,d in phases(s).items():
        t=team_mov(d); raw=t["mean"].std(ddof=0); nv=NOISE**2/t["size"]
        tv=max(raw**2-nv.mean(),0); k=tv/(tv+nv); mu=t["mean"].mean()
        shr=mu+k*(t["mean"]-mu)
        rows.append(dict(season=s,phase=p,games=len(d),gp=round(float(t["size"].mean()),1),
            raw_sd=round(float(raw),2),talent_sd=round(float(np.sqrt(tv)),2),
            bot5_raw=round(float(t["mean"].nsmallest(5).mean()),2),bot5_shrunk=round(float(shr.nsmallest(5).mean()),2),
            blow20=round(float((d.margin.abs()>=20).mean()),3)))
out["phase"]=rows

# 2. blowouts in first N games, excluding games involving that window's 6 worst teams
bl=[]
for s in SEAS:
    d=g[(g.season==s)&(g.idx<N)]; t=team_mov(d); bot=set(t["mean"].nsmallest(6).index)
    inv=d.home.isin(bot)|d.away.isin(bot)
    bl.append(dict(season=s,all=round(float((d.margin.abs()>=20).mean()),3),excl=round(float((d[~inv].margin.abs()>=20).mean()),3),n_excl=int((~inv).sum())))
out["blowouts_early"]=bl

# 3. simulation: prior seasons' full-season ratings played over 2026-27's first-N schedule
def fit(d):
    X=np.zeros((len(d),31))
    for r,(h,a) in enumerate(zip(d.home,d.away)): X[r,TI[h]]=1; X[r,TI[a]]=-1
    X[:,30]=1
    b,*_=np.linalg.lstsq(X,d.margin.values,rcond=None); return b,(d.margin.values-X@b).std()
cur=g[g.season==CUR]; H=cur.home.map(TI).values; A=cur.away.map(TI).values
def stats_from(m):
    s=np.zeros(30); c=np.zeros(30); w=np.zeros(30)
    np.add.at(s,H,m); np.add.at(s,A,-m); np.add.at(c,H,1); np.add.at(c,A,1)
    np.add.at(w,H,m>0); np.add.at(w,A,m<0)
    mov=s/c; return mov.std(), (w/c).std(), (w<=1).sum(), np.sort(mov)[:5].mean()
obs=stats_from(cur.margin.values.astype(float))
sims=[]
for s in PRIOR:
    b,sd=fit(g[g.season==s]); tal=b[:30]-b[:30].mean(); hca=b[30]
    for _ in range(2000):
        tt=tal[rng.permutation(30)]
        m=np.round(tt[H]-tt[A]+hca+rng.normal(0,sd,len(H)))
        m[m==0]=rng.choice([-1,1],(m==0).sum())
        sims.append(stats_from(m))
sims=np.array(sims)
out["sim"]=dict(obs_sd_mov=round(float(obs[0]),2),obs_sd_wp=round(float(obs[1]),3),obs_le1=int(obs[2]),obs_bot5=round(float(obs[3]),2),
    sd_mov=np.round(sims[:,0],2).tolist(),
    p_sd_mov=round(float((sims[:,0]>=obs[0]).mean()),3),p_sd_wp=round(float((sims[:,1]>=obs[1]).mean()),3),
    p_le1=round(float((sims[:,2]>=obs[2]).mean()),3),p_bot5=round(float((sims[:,3]<=obs[3]).mean()),3),reps=len(sims))
# real early-window values in prior seasons, for reference ticks
out["sim"]["prior_early_sd_mov"]={s:round(float(team_mov(g[(g.season==s)&(g.idx<N)])["mean"].std(ddof=0)),2) for s in PRIOR}

# 4. preseason line vs early results, 2026-27
NAME2={'Atlanta Hawks':'ATL','Boston Celtics':'BOS','Brooklyn Nets':'BKN','Charlotte Hornets':'CHA','Chicago Bulls':'CHI','Cleveland Cavaliers':'CLE','Dallas Mavericks':'DAL','Denver Nuggets':'DEN','Detroit Pistons':'DET','Golden State Warriors':'GS','Houston Rockets':'HOU','Indiana Pacers':'IND','Los Angeles Clippers':'LAC','Los Angeles Lakers':'LAL','Memphis Grizzlies':'MEM','Miami Heat':'MIA','Milwaukee Bucks':'MIL','Minnesota Timberwolves':'MIN','New Orleans Pelicans':'NO','New York Knicks':'NY','Oklahoma City Thunder':'OKC','Orlando Magic':'ORL','Philadelphia 76ers':'PHI','Phoenix Suns':'PHX','Portland Trail Blazers':'POR','Sacramento Kings':'SAC','San Antonio Spurs':'SA','Toronto Raptors':'TOR','Utah Jazz':'UTAH','Washington Wizards':'WSH'}
v=pd.read_csv(os.path.join(R,"team_vegas_history.csv")); v=v[v.date=="2026-10-20"]
proj=dict(zip(v.team.map(NAME2),v.vegas_proj_wins))
L=long(cur); t=L.assign(w=(L.m>0)).groupby("team").agg(mov=("m","mean"),w=("w","sum"),gp=("m","size"))
bot10=set(sorted(proj,key=proj.get)[:10])
out["calib"]=[dict(team=k,proj=round(proj[k],1),imp=round((proj[k]-41)/2.7,2),mov=round(float(t.loc[k,"mov"]),2),
                   rec=f"{int(t.loc[k,'w'])}-{int(t.loc[k,'gp']-t.loc[k,'w'])}",bot10=k in bot10) for k in T30]

# 5. Q4 fade: bottom-10 vs rest, games within 8 after Q3
q4=[]
for s in SEAS:
    Ls=long(g[g.season==s]); Ls=Ls[Ls.tq.str.len()>=4].copy()
    tq=np.array([[int(x) for x in r[:4]] for r in Ls.tq]); oq=np.array([[int(x) for x in r[:4]] for r in Ls.oq])
    Ls["q13"]=(tq[:,:3]-oq[:,:3]).sum(1); Ls["q4"]=tq[:,3]-oq[:,3]
    bottom=pre_bottom(s)
    for p,mask in [("early",Ls.idx<N)]+([("post",Ls.date>=DEADLINE[s])] if s in DEADLINE else []):
        c=Ls[mask&Ls.team.isin(bottom)&~Ls.opp.isin(bottom)&(Ls.q13.abs()<=8)]
        q4.append(dict(season=s,phase=p,q4=round(float(c.q4.mean()),2),se=round(float(c.q4.std()/np.sqrt(len(c))),2),n=len(c),winpct=round(float((c.m>0).mean()),3)))
out["q4"]=q4

# 6. last year's tanking 10
TANK=["UTAH","CHI","MIL","BKN","SAC","NO","IND","DAL","WSH","MEM"]
L25=long(g[g.season=="2025-26"]); L26=long(cur)
def rec(d): return dict(mov=round(float(d.m.mean()),2),rec=f"{int((d.m>0).sum())}-{int((d.m<0).sum())}")
tk=[]
for tm in TANK+["ALL"]:
    sel=(lambda L: L[L.team.isin(TANK)]) if tm=="ALL" else (lambda L,tm=tm: L[L.team==tm])
    a=sel(L25); b=sel(L26)
    tk.append(dict(team=tm,early25=rec(a[a.idx<N]),mid25=rec(a[(a.idx>=N)&(a.date<DEADLINE["2025-26"])]),post25=rec(a[a.date>=DEADLINE["2025-26"]]),early26=rec(b),proj26=None if tm=="ALL" else round(proj[tm],1)))
out["tank10"]=tk

# 7. bottom 10 by PRESEASON line vs everyone else, before vs after the deadline (2026-27: before, so far)
bvr=[]
for s_ in SEAS:
    Ls=long(g[g.season==s_]); bot=pre_bottom(s_)
    dl=DEADLINE.get(s_,"2099-01-01")
    pre=Ls[Ls.date<dl]; post=Ls[Ls.date>=dl]
    a=pre[pre.team.isin(bot)&~pre.opp.isin(bot)]; b=post[post.team.isin(bot)&~post.opp.isin(bot)]
    c=post[post.team.isin(bot)&post.opp.isin(bot)]
    row=dict(season=s_,teams=sorted(bot),pre=round(float(a.m.mean()),2),pre_w=round(float((a.m>0).mean()),3),pre_n=len(a))
    if len(b): row.update(post=round(float(b.m.mean()),2),post_w=round(float((b.m>0).mean()),3),post_n=len(b),bb_games=len(c)//2)
    bvr.append(row)
out["bvr"]=bvr
# 7b. same, with the bottom 10 picked on deadline day by margin before the deadline (knowable in February, not preseason)
bvr_dl=[]
for s_ in PRIOR:
    Ls=long(g[g.season==s_]); pre=Ls[Ls.date<DEADLINE[s_]]; post=Ls[Ls.date>=DEADLINE[s_]]
    bot=set(pre.groupby("team").m.mean().nsmallest(10).index)
    a=pre[pre.team.isin(bot)&~pre.opp.isin(bot)]; b=post[post.team.isin(bot)&~post.opp.isin(bot)]; c=post[post.team.isin(bot)&post.opp.isin(bot)]
    bvr_dl.append(dict(season=s_,teams=sorted(bot),pre=round(float(a.m.mean()),2),pre_w=round(float((a.m>0).mean()),3),pre_n=len(a),
                       post=round(float(b.m.mean()),2),post_w=round(float((b.m>0).mean()),3),post_n=len(b),bb_games=len(c)//2))
out["bvr_dl"]=bvr_dl

out["meta"]=dict(N=N,through="2026-11-04")
json.dump(out,open(os.path.join(here,"report_data.json"),"w"))
P=pd.DataFrame(rows); print(P.to_string()); print(pd.DataFrame(bl).to_string()); print({k:v for k,v in out["sim"].items() if k!="sd_mov"}); print(pd.DataFrame(q4).to_string())
