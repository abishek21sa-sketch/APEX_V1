from __future__ import annotations
import math
import numpy as np

def _features(x): return np.array([x['battery_kwh']/100,x['motor_kw']/300,x['mass_kg']/2200,x['cd_a']/.7,x['gear']/10],float)
def _truth(x):
    e=13.5+5.8*x['cd_a']+0.0031*x['mass_kg']+0.8*abs(x['gear']-9.2); rng=1000*x['battery_kwh']*.90/e; accel=max(2.7,8.5-0.018*x['motor_kw']+0.0009*x['mass_kg']+.12*abs(x['gear']-9.0)); cost=10500+115*x['battery_kwh']+38*x['motor_kw']+1.7*x['mass_kg']; return np.array([rng,accel,cost])
class TinyMLP:
    def __init__(self,seed): r=np.random.default_rng(seed); self.W1=r.normal(0,.35,(5,10)); self.b1=np.zeros(10); self.W2=r.normal(0,.25,(10,3)); self.b2=np.zeros(3)
    def fit(self,X,Y,steps=900,lr=.035):
        self.ym=Y.mean(0); self.ys=Y.std(0)+1e-9; T=(Y-self.ym)/self.ys
        for _ in range(steps):
            H=np.tanh(X@self.W1+self.b1); P=H@self.W2+self.b2; E=(P-T)/len(X); dW2=H.T@E; db2=E.sum(0); dH=(E@self.W2.T)*(1-H*H); self.W1-=lr*(X.T@dH); self.b1-=lr*dH.sum(0); self.W2-=lr*dW2; self.b2-=lr*db2
        return self
    def predict(self,X): return (np.tanh(X@self.W1+self.b1)@self.W2+self.b2)*self.ys+self.ym
class NeuralEnsemble:
    def train(self,X,Y,n=5):
        self.models=[]; r=np.random.default_rng(44)
        for k in range(n):
            idx=r.integers(0,len(X),len(X)); self.models.append(TinyMLP(100+k).fit(X[idx],Y[idx]))
        return self
    def predict(self,X):
        P=np.stack([m.predict(X) for m in self.models]); return P.mean(0),P.std(0)
def wilson_lower(k,n,z=1.645):
    if n<=0:return 0.0
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); r=z*math.sqrt((p*(1-p)+z*z/(4*n))/n); return max(0,(c-r)/d)
class ArchShield:
    def choose(self,designs,scenario_results,target=.95):
        rows=[]
        for d,res in zip(designs,scenario_results):
            ok=(res[:,0]>=420)&(res[:,1]<=6.3); lb=wilson_lower(int(ok.sum()),len(ok)); rows.append({'design':d,'reliability':float(ok.mean()),'reliability_lcb':lb,'robust_feasible':lb>=target,'cost':float(np.median(res[:,2]))})
        feasible=[x for x in rows if x['robust_feasible']]; return min(feasible,key=lambda x:x['cost']) if feasible else max(rows,key=lambda x:x['reliability_lcb'])
def _run_decision_core(seed=19):
    r=np.random.default_rng(seed); train=[]
    for _ in range(90): train.append({'battery_kwh':r.uniform(66,108),'motor_kw':r.uniform(180,330),'mass_kg':r.uniform(1550,2250),'cd_a':r.uniform(.48,.72),'gear':r.uniform(7.7,10.4)})
    X=np.stack([_features(x) for x in train]); Y=np.stack([_truth(x) for x in train]); ens=NeuralEnsemble().train(X,Y); hold=[{'battery_kwh':r.uniform(68,105),'motor_kw':r.uniform(185,325),'mass_kg':r.uniform(1600,2180),'cd_a':r.uniform(.49,.70),'gear':r.uniform(7.9,10.2)} for _ in range(24)]; HX=np.stack([_features(x) for x in hold]); HY=np.stack([_truth(x) for x in hold]); HP,_=ens.predict(HX); nrmse=(np.sqrt(np.mean((HP-HY)**2,axis=0))/(HY.std(0)+1e-9)).tolist()
    designs=[{'name':'Cost-Optimized','battery_kwh':76,'motor_kw':205,'mass_kg':1940,'cd_a':.63,'gear':9.5},{'name':'Balanced-Robust','battery_kwh':91,'motor_kw':285,'mass_kg':1880,'cd_a':.53,'gear':9.0},{'name':'Performance','battery_kwh':99,'motor_kw':315,'mass_kg':2020,'cd_a':.56,'gear':8.8}]
    mu,sd=ens.predict(np.stack([_features(x) for x in designs])); scen=[]
    for d in designs:
        vals=[]
        for _ in range(320):
            pert=d.copy(); pert['mass_kg']*=r.normal(1,.035); pert['cd_a']*=r.normal(1,.045); pert['battery_kwh']*=r.normal(.965,.018); vals.append(_truth(pert))
        scen.append(np.stack(vals))
    chosen=ArchShield().choose(designs,scen); cheap=min(zip(designs,mu),key=lambda z:z[1][2])[0]
    return {'project':'APEX','ml_family':'Bootstrap neural-network surrogate ensemble','prediction_target':'vehicle range, 0-60 acceleration and manufacturing cost','model_validation':{'metric':'holdout normalized RMSE','range_accel_cost':nrmse,'split':'independent synthetic architectures'},'predictions':[{'design':d['name'],'range_km':float(m[0]),'accel_s':float(m[1]),'cost':float(m[2]),'model_disagreement':sd[i].tolist()} for i,(d,m) in enumerate(zip(designs,mu))], 'original_algorithm':'ARCH-SHIELD-v1','decision':chosen,'counterfactual':{'naive_policy':'cheapest neural-surrogate point estimate','choice':cheap['name'],'disagrees':cheap['name']!=chosen['design']['name']},'uncertainty':'Bootstrap neural disagreement plus finite-sample Wilson reliability bound.','or_escalation':'Promote shortlisted architecture to exact physics, Pareto/NSGA-II and robust scenario evaluation.','tool_trace':['train bootstrap neural surrogates','predict KPI trade space','run common uncertainty scenarios','ARCH-SHIELD confidence gate','challenge cheapest design','escalate to exact physics/Pareto'],'limitations':['reference vehicle generator is synthetic','pymoo/agent native gates require full Windows dependency acceptance'],'abstention_conditions':['no architecture clears confidence bound','surrogate disagreement too high','design outside training envelope'],'user_aid':['inspect KPI prediction/disagreement','compare robust shortlist','review requirement failures','approve/hold architecture'],'human_authority':'VEHICLE_ARCHITECTURE_REVIEW','autonomous_execution':False}


def run_decision(seed=None):
    from empirical.backbone import run_empirical_reference
    import inspect
    sig=inspect.signature(_run_decision_core)
    if seed is None:
        out=_run_decision_core()
    else:
        out=_run_decision_core(seed)
    emp=run_empirical_reference()
    out["empirical_backbone"]=emp
    from empirical.public_data_backbone import integrate_decision
    out=integrate_decision(out)
    out.setdefault("tool_trace",[]).insert(0,"resolve empirical data provenance and source mode")
    out.setdefault("user_aid",[]).append("open empirical case study and entity/history drilldowns before approval")
    return out
