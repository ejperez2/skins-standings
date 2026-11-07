import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
R=pd.read_csv('archive/history/rosters_and_finals_2022-26.csv')
R['skins']=np.where(R.pick=='W',R.final_wins,82-R.final_wins)
fin=R.groupby(['season','player']).agg(final=('skins','sum'),n=('skins','size')).reset_index()
P=pd.read_csv('archive/history/player_snapshots_2022-25.csv')
P=P.rename(columns={'skins':'actual','avg':'proj'})[['season','timestamp','player','actual','games_played','proj']]
P['date']=P.timestamp.str[:10]
A=pd.read_csv('archive/2025-26/standings_history.csv').dropna(subset=['skins_pct'])
A=A[A.skins_pct>0]
A=pd.DataFrame({'season':'2025-26','timestamp':A.date,'player':A.player,'actual':A.actual_skins,
  'games_played':A.actual_skins/A.skins_pct,'proj':A.weighted_average,'date':A.date})
D=pd.concat([P,A]).merge(fin,on=['season','player'])
D['gpt']=D.games_played/D.n
TS=8.6; N=40000; rng=np.random.default_rng(1)
def probs(g):
    left=82-g.gpt.values; n=g.n.values
    s=g.actual.values; proj=np.clip(g.proj.values,s,s+left*n)
    rem=proj-s; p=np.clip(rem/(left*n),.01,.99)
    sd=np.sqrt(left*n*p*(1-p)+n*(TS*(left/82)**1.5)**2)
    f=np.clip(proj[:,None]+sd[:,None]*rng.standard_normal((len(g),N)),s[:,None],(s+left*n)[:,None])
    w=(f==f.max(0)).astype(float); w/=w.sum(0)
    return w.mean(1)
out=[]
for s,g in D.groupby('season'):
    ts=g.groupby('timestamp').gpt.mean()
    t=(ts-8.9).abs().idxmin()
    h=g[g.timestamp==t].copy()
    if len(h)<5: continue
    h['p']=probs(h); h['rank_now']=h.actual.rank(ascending=False)
    h['date_used']=t[:10]; h['gpt_used']=ts[t]
    h['winner']=h.final==h.final.max()
    h['lead']=h.actual-h.actual.sort_values().iloc[-2] if False else np.nan
    out.append(h)
O=pd.concat(out)
cols=['season','date_used','gpt_used','player','actual','proj','p','final','winner']
print(O.sort_values(['season','p'],ascending=[True,False])[cols].round(3).to_string(index=False))
O.to_pickle('analysis/O.pkl')

print("\n--- all daily snapshots, 6-14 games/team ---")
rows=[]
for (s,t),h in D.groupby(['season','timestamp']):
    if not 6<=h.gpt.mean()<=14 or len(h)<5: continue
    h=h.copy(); h['p']=probs(h); h['winner']=h.final==h.final.max(); rows.append(h)
B=pd.concat(rows)
B['bin']=pd.cut(B.p,[0,.05,.1,.2,.3,.4,.5,1])
print(B.groupby('bin',observed=True).agg(n=('p','size'),mean_p=('p','mean'),won=('winner','mean')).round(3))
print(B[B.p>=.35].groupby('season').agg(n=('p','size'),mean_p=('p','mean'),won=('winner','mean')).round(2))
