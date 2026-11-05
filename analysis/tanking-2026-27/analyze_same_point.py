import pandas as pd, numpy as np, sys
from scipy import stats
rng=np.random.default_rng(7)
g=pd.read_csv(sys.argv[1])
T30=set(g[g.season=='2026-27'].home)|set(g[g.season=='2026-27'].away)
g=g[g.home.isin(T30)&g.away.isin(T30)].copy()
g["margin"]=g.hpts-g.apts
g=g.sort_values(["season","date","game_id"])
g["idx"]=g.groupby("season").cumcount()
N=(g.season=="2026-27").sum()
print("games this season:",N,"avg GP:",round(2*N/30,2))
SEAS=sorted(g.season.unique())

def team_table(d):
    h=pd.DataFrame(dict(team=d.home,w=(d.margin>0).astype(int),m=d.margin))
    a=pd.DataFrame(dict(team=d.away,w=(d.margin<0).astype(int),m=-d.margin))
    t=pd.concat([h,a]).groupby("team").agg(gp=("w","size"),w=("w","sum"),mov=("m","mean"))
    t["wp"]=t.w/t.gp; return t

def summarize(d):
    t=team_table(d)
    resid_sd=12.0  # per-game margin noise SD (estimated below)
    var_noise_wp=(0.25/t.gp).mean()
    var_noise_mov=(resid_sd**2/t.gp).mean()
    am=d.margin.abs()
    return dict(
      games=len(d), avg_gp=t.gp.mean(),
      sd_wp=t.wp.std(ddof=0), talent_sd_wp=np.sqrt(max(t.wp.var(ddof=0)-var_noise_wp,0)),
      sd_mov=t.mov.std(ddof=0), talent_sd_mov=np.sqrt(max(t.mov.var(ddof=0)-var_noise_mov,0)),
      le1win=(t.w<=1).sum(), ge7win=(t.w>=7).sum() if False else None,
      mov_le_m10=(t.mov<=-10).sum(), mov_ge_p10=(t.mov>=10).sum(),
      worst_mov=t.mov.min(), best_mov=t.mov.max(),
      bot5_mov=t.mov.nsmallest(5).mean(), top5_mov=t.mov.nlargest(5).mean(),
      mean_abs_margin=am.mean(), pct15=(am>=15).mean(), pct20=(am>=20).mean(), pct_close5=(am<=5).mean())

# per-game noise estimate: residual of margin after fitting team ratings (full seasons)
def fit_resid(d):
    teams=sorted(T30); ix={t:i for i,t in enumerate(teams)}
    X=np.zeros((len(d),31)); 
    for r,(h,a) in enumerate(zip(d.home,d.away)): X[r,ix[h]]=1; X[r,ix[a]]=-1
    X[:,30]=1
    b,*_=np.linalg.lstsq(X,d.margin.values,rcond=None)
    res=d.margin.values-X@b; return res.std(), b
for s in SEAS[:-1]:
    full=g[g.season==s]
    print(s,"per-game margin resid SD (full season):",round(fit_resid(full)[0],2))

# 1) same-point comparison: first N games of each season
print("\n=== Same point in season: first",N,"games ===")
rows=[]
for s in SEAS:
    d=g[(g.season==s)&(g.idx<N)]
    r=summarize(d); r["season"]=s; r["thru"]=d.date.max(); rows.append(r)
S=pd.DataFrame(rows).set_index("season").drop(columns=["ge7win"])
pd.set_option("display.width",250); pd.set_option("display.max_columns",30)
print(S.round(3).T)

# 2) wins distribution table like article (date-aligned: through Nov 4 games ET ~ first N games)
print("\n=== Win-count distribution after first",N,"games ===")
for s in ["2024-25","2025-26","2026-27"]:
    t=team_table(g[(g.season==s)&(g.idx<N)])
    print(s, t.w.value_counts().sort_index().to_dict())

# 3) how unusual is 2026-27 vs the prior-season distribution (z-scores, empirical rank)
print("\n=== 2026-27 vs 7 prior seasons (mean, sd, z, rank of 8) ===")
prior=S.drop("2026-27")
for c in ["sd_wp","talent_sd_wp","sd_mov","talent_sd_mov","le1win","mov_le_m10","bot5_mov","top5_mov","mean_abs_margin","pct15","pct20","pct_close5"]:
    v=S.loc["2026-27",c]; mu=prior[c].mean(); sd=prior[c].std()
    rank=int((S[c]>=v).sum())
    print(f"{c:16s} this={v:7.3f} prior_mean={mu:7.3f} prior_sd={sd:6.3f} z={(v-mu)/sd:5.2f} rank(high=1)={rank}/8")

# 4) blowout rate significance: 2026-27 first N vs pooled prior first N
cur=g[(g.season=="2026-27")]; pr=g[(g.season!="2026-27")&(g.idx<N)]
for thr in [15,20]:
    a=(cur.margin.abs()>=thr).sum(); b=(pr.margin.abs()>=thr).sum()
    tab=[[a,len(cur)-a],[b,len(pr)-b]]
    print(f"blowouts >= {thr}: this {a}/{len(cur)}={a/len(cur):.3f}  prior {b}/{len(pr)}={b/len(pr):.3f}  Fisher p={stats.fisher_exact(tab)[1]:.3f}")
print("abs margin Mann-Whitney p:",round(stats.mannwhitneyu(cur.margin.abs(),pr.margin.abs()).pvalue,3))

# 5) bootstrap CI for talent SD of MOV this season (resample teams' games? -> parametric)
# Simulate: if true talent dispersion equaled each prior season's FULL-season ratings, what would
# 2026-27's first-N schedule produce? Distribution of sd_wp, # teams <=1 win, # teams MOV<=-10, worst MOV
sched=cur[["home","away"]].values
def sim(talent, hca, sigma=12.0, reps=4000):
    out=[]
    teams=sorted(T30)
    for _ in range(reps):
        perm=rng.permutation(30)  # random assignment of talent to this season's schedule slots
        tal={t:talent[perm[i]] for i,t in enumerate(teams)}
        mu=np.array([tal[h]-tal[a]+hca for h,a in sched])
        m=np.round(mu+rng.normal(0,sigma,len(mu)))
        m[m==0]=rng.choice([-1,1],(m==0).sum())
        d=pd.DataFrame(dict(home=sched[:,0],away=sched[:,1],margin=m))
        t=team_table(d)
        out.append((t.wp.std(ddof=0),(t.w<=1).sum(),(t.mov<=-10).sum(),t.mov.min(),(np.abs(m)>=20).mean(),t.mov.std(ddof=0)))
    return np.array(out)
obs=S.loc["2026-27"]
print("\n=== Simulated first-N windows on 2026-27 schedule, talent = each prior season's full-season ratings ===")
print("columns: P(sd_wp>=obs), P(#<=1win>=obs), P(#MOV<=-10 >=obs), P(worstMOV<=obs), P(blowout20>=obs), P(sd_mov>=obs), mean #<=1win")
allsims=[]
for s in SEAS[:-1]:
    sd,b=fit_resid(g[g.season==s]); tal=b[:30]-b[:30].mean(); hca=b[30]
    r=sim(tal,hca,sigma=sd,reps=2000); allsims.append(r)
    print(s, "talent SD %.2f"%tal.std(), np.round([(r[:,0]>=obs.sd_wp).mean(),(r[:,1]>=obs.le1win).mean(),(r[:,2]>=obs.mov_le_m10).mean(),(r[:,3]<=obs.worst_mov).mean(),(r[:,4]>=obs.pct20).mean(),(r[:,5]>=obs.sd_mov).mean(),r[:,1].mean()],3))
A=np.vstack(allsims)
print("POOLED", np.round([(A[:,0]>=obs.sd_wp).mean(),(A[:,1]>=obs.le1win).mean(),(A[:,2]>=obs.mov_le_m10).mean(),(A[:,3]<=obs.worst_mov).mean(),(A[:,4]>=obs.pct20).mean(),(A[:,5]>=obs.sd_mov).mean(),A[:,1].mean()],3))

# 6) how predictive is an N-game window of the full season? (prior seasons)
print("\n=== Predictiveness of first-N stats (prior seasons) ===")
for s in SEAS[:-1]:
    e=team_table(g[(g.season==s)&(g.idx<N)]); f=team_table(g[g.season==s])
    j=e.join(f,rsuffix="_f")
    print(s,"r(early wp, final wp)=%.2f  r(early MOV, final MOV)=%.2f  early SD MOV %.2f -> full SD MOV %.2f; teams <=1 win early: %d, their final W%% avg %.3f"%(
        np.corrcoef(j.wp,j.wp_f)[0,1],np.corrcoef(j.mov,j.mov_f)[0,1],e.mov.std(ddof=0),f.mov.std(ddof=0),(j.w<=1).sum(),j.loc[j.w<=1,"wp_f"].mean() if (j.w<=1).any() else np.nan))
# correlation across seasons between early dispersion and full-season dispersion
E=[team_table(g[(g.season==s)&(g.idx<N)]).mov.std(ddof=0) for s in SEAS[:-1]]
F=[team_table(g[g.season==s]).mov.std(ddof=0) for s in SEAS[:-1]]
print("across-season r(early SD MOV, full SD MOV) = %.2f"%np.corrcoef(E,F)[0,1])

S.to_csv(sys.argv[2])
