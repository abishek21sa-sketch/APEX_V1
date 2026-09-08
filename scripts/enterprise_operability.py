from __future__ import annotations
import json,time
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT/'src'):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
from apex.design import DesignCandidate
from apex.robust.design_selection import select_robust_design
from apex.robust.release_assurance import build_design_release_certificate,verify_design_release_certificate
from service.mission_registry import build_robust_mission

def cand(b,p): return DesignCandidate(b,p,9.0,.24,2.25,'pm_synchronous','nmc','1','standard')
requirements=[{'kind':'max_acceleration_time_s','threshold':6.0,'reliability_target':.95},{'kind':'min_highway_range_mi','threshold':310.0,'reliability_target':.95}]
mission=build_robust_mission('enterprise release',requirements)
short=[cand(112,280),cand(120,320)]
start=time.perf_counter()
selection=select_robust_design(short,mission,n_samples=300,seed=2026,cvar_alpha=.9,confidence=.95)
cert=build_design_release_certificate(selection,mission_requirements=requirements,shortlist=[c.as_dict() for c in short])
bad=deepcopy(cert); bad['prototype_or_production_build_authorized']=True
tamper=verify_design_release_certificate(bad)
# A deliberately weak shortlist must never receive engineering-review status.
weak=[cand(60,110),cand(70,130)]
weak_sel=select_robust_design(weak,mission,n_samples=100,seed=2026,cvar_alpha=.9,confidence=.95)
weak_cert=build_design_release_certificate(weak_sel,mission_requirements=requirements,shortlist=[c.as_dict() for c in weak])
elapsed=time.perf_counter()-start
checks={
    'selected_certificate_valid':verify_design_release_certificate(cert)['valid'] is True,
    'selected_build_authorization_blocked':cert['prototype_or_production_build_authorized'] is False,
    'tampering_detected':tamper['valid'] is False,
    'weak_shortlist_held':weak_cert['decision_state']=='HOLD',
    'reference_runtime_under_30s':elapsed<30,
}
payload={'phase':'ENTERPRISE_OPERABILITY_V1','status':'PASS' if all(checks.values()) else 'HOLD','checks':checks,'runtime_seconds':elapsed,'decision_state':cert['decision_state'],'selected_score':selection['selected_score'],'certificate_sha256':cert['certificate_sha256'],'native_pareto_gate':'PYMOO_DEPENDENCY_REQUIRED_FOR_FULL_WINDOWS_ACCEPTANCE','claim_boundary':'Model-based vehicle architecture evidence only; prototype/production build release is blocked.'}
(ROOT/'artifacts'/'enterprise_operability.json').write_text(json.dumps(payload,indent=2,sort_keys=True,default=str))
print(json.dumps({'status':payload['status'],'checks':checks,'runtime_seconds':round(elapsed,3),'decision_state':cert['decision_state']},indent=2))
if payload['status']!='PASS': raise SystemExit('APEX_ENTERPRISE_OPERABILITY=HOLD')
print('APEX_ENTERPRISE_OPERABILITY=PASS')
