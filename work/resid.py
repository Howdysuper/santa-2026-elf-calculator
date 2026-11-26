import sys,json,math,csv; sys.path.insert(0,'src')
import numpy as np
from elf import load,best_len
P=load()
aff={r['pid']:r for r in csv.DictReader(open('work/affine_struct.csv'))}
X=[];y=[];ids=[]
for pid,pz in sorted(P.items()):
    T=pz['targets']; a=aff[pid]
    bits=[math.log2(t) for t in T]
    X.append([len(T),max(bits),min(bits),np.mean(bits),1-int(a['comps'])/len(T),int(a['edges']),max(pz['starts'])>=100,len(pz['starts']),math.log2(max(pz['starts'])),math.log2(pz['limit'])-max(bits)])
    y.append(best_len(pid)); ids.append(pid)
X=np.array(X,dtype=float); y=np.array(y,dtype=float)
try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import cross_val_predict
    m=GradientBoostingRegressor(n_estimators=300,max_depth=3,learning_rate=0.05,subsample=0.8)
    pred=cross_val_predict(m,X,y,cv=10)
except Exception as e:
    print('no sklearn',e); sys.exit()
res=y-pred
print('MAE',np.mean(np.abs(res)),'R2',1-np.var(res)/np.var(y))
o=np.argsort(-res)
print('top positive residuals (frontier worse than predicted):')
for k in o[:25]: print(ids[k],int(y[k]),round(pred[k]),round(res[k]),'nt',int(X[k,0]),'bits',round(X[k,1]),'link',round(X[k,4],2),'indep',bool(X[k,6]))
print('sum of positive residuals',res[res>0].sum())
np.save('work/resid.npy',res)
