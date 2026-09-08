from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def domain_diagnostics():
 j=json.loads((ROOT/'artifacts/portfolio_validation.json').read_text()); r=j['robust_design_selection']; scores=r['scores']; cert=[x for x in scores if x['confidence_certified']]; chosen=min(cert,key=lambda x:(x['reliability_shortfall'],x['cvar_normalized_violation'],x['manufacturing_cost_usd'])) if cert else min(scores,key=lambda x:x['reliability_shortfall'])
 cheapest=min(scores,key=lambda x:x['manufacturing_cost_usd']); premium=chosen['manufacturing_cost_usd']-cheapest['manufacturing_cost_usd']
 return {'analysis':'robust architecture confidence/cost frontier','metrics':{'scenario_samples':r['n_samples'],'candidate_designs':len(scores),'confidence_certified_designs':len(cert),'robustness_premium_vs_cheapest_usd':round(premium,2)},'selected_architecture':chosen,'cheapest_architecture':cheapest,'decision_signal':'ARCH-SHIELD may pay a manufacturing-cost premium when finite-sample reliability confidence rejects a cheaper nominal design.','evidence_boundary':j['evidence_boundary']}
