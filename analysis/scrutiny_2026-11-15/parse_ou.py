import pandas as pd, io, sys, re, glob, os
raw=sys.argv[1]; out=sys.argv[2]; rows=[]
for f in sorted(glob.glob(raw+'/*.html')):
    y=int(os.path.basename(f)[:4]); h=open(f,encoding='utf8',errors='replace').read().replace('<!--','').replace('-->','')
    try: ts=pd.read_html(io.StringIO(h))
    except Exception as e: print(y,'no table',e); continue
    t=[t for t in ts if 'W-L O/U' in t.columns]
    if not t: print(y,'no O/U col'); continue
    t=t[0]; t=t[t['W-L O/U'].notna()]
    for _,r in t.iterrows():
        m=re.match(r'(\d+)-(\d+)',str(r['Result']))
        rows.append(dict(season_end=y,team=r['Team'],ou=float(r['W-L O/U']),w=int(m[1]) if m else None,l=int(m[2]) if m else None))
d=pd.DataFrame(rows); d.to_csv(out,index=False)
print(d.groupby('season_end').agg(n=('team','size'),ou_sum=('ou','sum'),gp=('w',lambda s:(s+d.loc[s.index,'l']).median())).to_string())
