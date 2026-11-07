import pandas as pd, numpy as np
exec(open('analysis/backtest_spread.py').read().split('rows=[]')[0])
rng=np.random.default_rng(5); N=20000
def wp(g,constrain):
    left=82-g.gpt.values; n=g.n.values.astype(int); s=g.actual.values
    proj=np.clip(g.proj.values,s,s+left*n); p=np.clip((proj-s)/(left*n),.01,.99)
    rho=.15*np.clip((g.gpt.mean()-10)/15,0,1)
    v=left*p*(1-p)+(8.6*(left/82)**1.5)**2  # per team var (equal within roster)
    nW=g.nW.values.astype(int)
    E=[];Ssum=0;cov_parts=[];var_S=0
    for i in range(len(g)):
        side=np.r_[np.ones(nW[i]),-np.ones(n[i]-nW[i])]
        u=rng.standard_normal(N); zt=rng.standard_normal((n[i],N))
        e=np.sqrt(v[i])*(np.sqrt(1-rho)*zt+np.sqrt(rho)*u)   # skins misses, roster-correlated
        E.append(e.sum(0)); Ssum=Ssum+(side[:,None]*e).sum(0)
        k=side.sum(); cov_parts.append(v[i]*(k+rho*(k*n[i]-k)))   # cov(E_p, S)
        var_S+=v[i]*(n[i]+rho*(k*k-n[i]))
    E=np.array(E)
    if constrain: E=E-np.array(cov_parts)[:,None]/var_S*Ssum[None,:]
    f=np.clip(proj[:,None]+E,s[:,None],(s+left*n)[:,None])
    w=(f==f.max(0)); w=w/w.sum(0); return w.mean(1)
res=[];tab=[]
for (s,t),g in D.groupby(['season','timestamp']):
    gm=g.gpt.mean()
    if len(g)<5 or gm>41: continue
    win=(g.final==g.final.max()).values
    for c in [0,1]:
        p=wp(g,c); res.append(dict(season=s,stage=pd.cut([gm],[0,10,20,41])[0],c=c,ll=-np.log(max((p*win).sum(),1e-3))))
X=pd.DataFrame(res)
print(X.groupby(['season','c']).ll.mean().unstack().round(3))
print(X.groupby(['stage','season','c'],observed=True).ll.mean().groupby(['stage','c'],observed=True).mean().unstack().round(3))
