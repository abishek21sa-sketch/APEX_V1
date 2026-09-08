from copy import deepcopy
from apex.robust.release_assurance import build_design_release_certificate, verify_design_release_certificate


def selection(certified=True):
    return {
        'selected_index':0,'selected_candidate':{'battery_capacity_kwh':120},'n_samples':300,'seed':1,'cvar_alpha':.9,'reliability_confidence':.95,
        'selected_score':{
            'robustly_feasible':certified,'confidence_certified':certified,'manufacturing_cost_usd':40000,
            'requirement_reliability_lower_bound':{'accel':.97,'range':.98} if certified else {'accel':.92,'range':.98},
            'requirement_targets':{'accel':.95,'range':.95},'reliability_shortfall':0 if certified else .03,
            'mean_normalized_violation':0,'cvar_normalized_violation':0,'worst_normalized_violation':0,
        }
    }


def test_release_certificate_requires_confidence_certification_and_physical_review():
    c=build_design_release_certificate(selection(True),mission_requirements=[{'kind':'x'}],shortlist=[{'x':1}])
    assert c['decision_state']=='ENGINEERING_DESIGN_REVIEW'
    assert c['prototype_or_production_build_authorized'] is False
    assert verify_design_release_certificate(c)['valid'] is True
    bad=deepcopy(c); bad['selected_score']['manufacturing_cost_usd']=1
    assert verify_design_release_certificate(bad)['valid'] is False


def test_uncertified_shortlist_is_held():
    c=build_design_release_certificate(selection(False),mission_requirements=[{'kind':'x'}],shortlist=[{'x':1}])
    assert c['decision_state']=='HOLD'
