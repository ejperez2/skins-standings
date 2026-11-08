# 80% range coverage per player, by band, for candidates (analytic normal, no constraint)
import numpy as np, pandas as pd
exec(open('analysis/backtest_spread.py').read().split('rows=[]')[0])
for EXP,RHO in [(1.5,.15),(1.5,.25),(1.0,.25),(1.0,.35)]:
    out=[]
    for (se,t),g in D.groupby(['season','timestamp']):
        if len(g)<5 or g.gpt.mean()>=75: continue
        left=82-g.gpt.values; n=g.n.values; s=g.actual.values
        proj=np.clip(g.proj.values,s,s+left*n); p=np.clip((proj-s)/np.maximum(left*n,1e-9),.01,.99)
        v=left*p*(1-p)+(8.6*(left/82)**EXP)**2; var=n*v*(1+(n-1)*RHO)
        z=(g.final.values-proj)/np.sqrt(var)
        for zz in z: out.append(dict(season=se,band=pd.cut([g.gpt.mean()],[0,15,30,50,75])[0],inside=abs(zz)<1.2816))
    O=pd.DataFrame(out)
    print(f'EXP {EXP} RHO {RHO}: 80% range held', O.groupby('band',observed=True).inside.mean().round(2).to_dict(),
          '| by season', O.groupby('season').inside.mean().round(2).to_dict())
