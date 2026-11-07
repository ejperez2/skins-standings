import pandas as pd, numpy as np
exec(open('analysis/backtest_win_prob.py').read().split('TS=8.6')[0])
nw=R.assign(w=R.pick.eq('W')).groupby(['season','player']).w.sum().rename('nW').reset_index()
D=D.merge(nw,on=['season','player'])
def model_sd(g,TS=8.6,rho_floor=.15,ramp=(10,25)):
    left=82-g.gpt.values; n=g.n.values; s=g.actual.values
    proj=np.clip(g.proj.values,s,s+left*n); p=np.clip((proj-s)/(left*n),.01,.99)
    rho=rho_floor*np.clip((g.gpt.mean()-ramp[0])/(ramp[1]-ramp[0]),0,1)
    t2=(TS*(left/82)**1.5)**2
    var=left*n*p*(1-p)+n*t2*(1+(n-1)*rho)
    return proj,var
rows=[]
for (s,t),g in D.groupby(['season','timestamp']):
    if len(g)<5: continue
    proj,var=model_sd(g)
    z=(g.final.values-proj)/np.sqrt(var)
    # pairwise differences (independence between players)
    for i in range(len(g)):
        for j in range(i+1,len(g)):
            rows.append(dict(season=s,gpt=g.gpt.mean(),kind='pair',z=((g.final.values[i]-g.final.values[j])-(proj[i]-proj[j]))/np.sqrt(var[i]+var[j])))
    for zz in z: rows.append(dict(season=s,gpt=g.gpt.mean(),kind='player',z=zz))
Z=pd.DataFrame(rows); Z['stage']=pd.cut(Z.gpt,[0,5,10,20,30,45,60,82])
print('RMS z (1.0 = spread right; >1 too narrow)')
print(Z.groupby(['kind','stage'],observed=True).z.apply(lambda v: np.sqrt((v**2).mean())).unstack(0).round(2))
print(Z[Z.gpt.between(6,14)].groupby(['kind','season']).z.apply(lambda v: np.sqrt((v**2).mean())).unstack(0).round(2))
