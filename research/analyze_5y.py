import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
t = pd.read_csv(__import__('sys').argv[1])
en = t[t.Type.str.startswith('Entry')].set_index('Trade number')
ex = t[t.Type.str.startswith('Exit')].groupby('Trade number').agg(exit_time=('Date and time','last'), pnl=('Net PnL USD','first'),
      signal=('Signal','last'), mfe=('Favorable excursion USD','first'), mae=('Adverse excursion USD','first'))
T = en[['Date and time','Price USD','Type']].join(ex)
T['time'] = pd.to_datetime(T['Date and time']).dt.tz_localize('Asia/Kolkata')
T['dir'] = np.where(T.Type.str.contains('long'),'BUY','SELL'); T['R'] = T.pnl/100
T['kind'] = np.where(T.signal=='time','time exit', np.where(T.pnl>0,'target','stop'))
T = T.sort_values('time')
lon = T.time.dt.tz_convert('Europe/London'); ny = T.time.dt.tz_convert('America/New_York')
lh = lon.dt.hour+lon.dt.minute/60; nh = ny.dt.hour+ny.dt.minute/60
inl=(lh>=7)&(lh<16.5); inn=(nh>=8)&(nh<17)
T['session'] = np.where(inl&inn&(lh>=8),'4 Overlap (LDN+NY)',np.where(inl,'2 London',np.where(inn,'5 NY (after LDN close)','1 Asia')))
T['ist_hour'] = T.time.dt.hour
px = T.set_index('time')['Price USD']
def past(ts,days):
    p = px[px.index<=ts-pd.Timedelta(days=days)]; return p.iloc[-1] if len(p) else np.nan
T['tr60'] = [(r['Price USD']/past(r.time,60)-1)*100 for _,r in T.iterrows()]
T['era'] = np.where(T.time<pd.Timestamp('2025-01-01',tz='Asia/Kolkata'),'2023-2024','2025-2026')
def s(g):
    if len(g)==0: return pd.Series(dict(n=0))
    r=g.R.values; eq=np.cumsum(r); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max() if len(r) else 0
    st=max((len(x) for x in "".join("L" if v<=0 else "W" for v in r).split("W")),default=0); gl=-r[r<0].sum()
    return pd.Series(dict(n=len(r),win=round((r>0).mean()*100,1),totR=round(r.sum(),1),avgR=round(r.mean(),3),
        PF=round(r[r>0].sum()/gl,2) if gl else np.inf,maxDD_R=round(dd,1),L_streak=st,time_exit=round((g.kind=='time exit').mean()*100)))
pd.set_option('display.width',230)
B=T[T.dir=='BUY']; S=T[T.dir=='SELL']
print("== BUY 5y\n",s(B).to_frame().T.to_string(), "\n== BUY 2025-26\n", s(B[B.era.str.startswith('2025')]).to_frame().T.to_string())
print("\n== Trend (gold % change over prior 60 days)")
for lab,g in (("BUY, gold rising",B[B.tr60>0]),("BUY, gold falling",B[B.tr60<=0]),("SELL, gold falling",S[S.tr60<0]),("SELL, gold rising",S[S.tr60>=0])):
    print(f"  {lab:20s}", s(g).to_dict())
print("\n== SESSION x DIRECTION (5 years)"); print(T.groupby(['dir','session']).apply(s).to_string())
print("\n== SESSION x DIRECTION x ERA"); print(T.groupby(['dir','era','session']).apply(s)[['n','win','totR','avgR','PF']].to_string())
print("\n== IST hour, BUY (5y)"); print(B.groupby('ist_hour').apply(s)[['n','win','totR','avgR']].T.to_string())
if len(S): print("\n== IST hour, SELL (5y)"); print(S.groupby('ist_hour').apply(s)[['n','win','totR','avgR']].T.to_string())
T.to_csv(__import__('sys').argv[1].replace('.csv','_parsed.csv'))
