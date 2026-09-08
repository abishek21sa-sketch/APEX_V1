from __future__ import annotations
from tenx.engine import run_decision
from campaign.engine import run_campaign
from empirical.backbone import run_empirical_reference

def lifecycle_report():
    d=run_decision(23); v=d['model_validation']; n=[float(x) for x in v.get('range_accel_cost',[])]; worst=max(n) if n else 0.0
    disagreements=[]
    for row in d.get('predictions',[]): disagreements.extend(float(x) for x in row.get('model_disagreement',[]) if isinstance(x,(int,float)))
    unc=max(disagreements) if disagreements else 0.0
    state='EXACT_PHYSICS_ONLY' if worst>.28 else ('SURROGATE_WATCH' if worst>.18 else 'SURROGATE_ACTIVE')
    public_data=d.get('public_data_backbone',{})
    return {'public_data_state':public_data.get('dataset_state'),'public_evidence_gate':d.get('public_evidence_gate'),'model_family':d['ml_family'],'target':d['prediction_target'],'validation':v,'worst_normalized_rmse':round(worst,6),'max_ensemble_disagreement':round(unc,6),'surrogate_state':state,'retrain_trigger':'retrain ensemble if normalized holdout RMSE >0.18, extrapolation score exceeds envelope, or ensemble disagreement spikes','monitoring':['normalized KPI RMSE','ensemble disagreement','design-space coverage','physics-vs-surrogate residual','robust shortlist stability'],'registry_state':'SURROGATE_SHADOW' if state!='SURROGATE_ACTIVE' else 'SURROGATE_CHAMPION','source_mode':run_empirical_reference().get('data_mode')}

def run_agent():
    d=run_decision(23); life=lifecycle_report(); c=run_campaign(); steps=['load vehicle requirements','screen architecture envelope','predict range/accel/cost with neural ensemble']
    state='ARCHITECTURE_REVIEW'
    public_gate=d.get('public_evidence_gate')
    if public_gate=='REFERENCE_MODE_HOLD_FOR_REAL_DATA_CLAIM':
        steps.append('flag external public-data acquisition gap; prohibit real-data performance claim')
        state='REFERENCE_MODE_HOLD'
    if life['surrogate_state']=='EXACT_PHYSICS_ONLY': steps += ['disable surrogate-led ranking','run exact physics on all candidates','rebuild training set']; state='SURROGATE_HOLD'
    else: steps += ['run common-random-number uncertainty scenarios','apply ARCH-SHIELD reliability confidence gate','challenge cheapest architecture','verify finalists with exact physics/Pareto search']
    return {'agent':'Vehicle Design Council','objective':'find a requirement-feasible architecture with defensible robustness and cost','prediction':d.get('predictions'),'decision':d['decision'],'decision_state':state,'chosen_tool_sequence':steps,'why_this_sequence':'surrogate error and disagreement determine whether AI may screen broadly or must defer immediately to exact physics','challenge':d['counterfactual'],'ml_lifecycle':life,'campaign_state':c.get('state'),'operator_actions':['inspect requirement margins','compare energy/mass/cost trade space','review ARCH-SHIELD confidence','approve/HOLD architecture release'],'human_authority':d['human_authority'],'autonomous_execution':False}
