"""Engineering release assurance for APEX robust design selection."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json
from typing import Any


def _canonical(x: Any) -> bytes:
    return json.dumps(x,sort_keys=True,separators=(',',':'),default=str).encode('utf-8')


def build_design_release_certificate(selection: dict[str,Any], *, mission_requirements: list[dict[str,Any]], shortlist: list[dict[str,Any]]) -> dict[str,Any]:
    score=dict(selection.get('selected_score') or {})
    lbs=score.get('requirement_reliability_lower_bound',{})
    targets=score.get('requirement_targets',{})
    confidence_checks={name:float(lbs.get(name,0.0)) >= float(target) for name,target in targets.items()}
    checks={
        'selected_design_confidence_certified':score.get('confidence_certified') is True,
        'selected_design_point_estimate_feasible':score.get('robustly_feasible') is True,
        'all_reliability_lower_bounds_meet_targets':bool(confidence_checks) and all(confidence_checks.values()),
        'finite_sample_count_sufficient':int(selection.get('n_samples',0)) >= 100,
        'production_release_blocked':True,
    }
    state='ENGINEERING_DESIGN_REVIEW' if all(checks.values()) else 'HOLD'
    core={
        'certificate_type':'APEX_RDS_RELEASE_ASSURANCE_V1',
        'decision_state':state,
        'selected_index':selection.get('selected_index'),
        'selected_candidate':selection.get('selected_candidate'),
        'selected_score':score,
        'reliability_confidence':selection.get('reliability_confidence'),
        'n_samples':selection.get('n_samples'),
        'seed':selection.get('seed'),
        'cvar_alpha':selection.get('cvar_alpha'),
        'requirement_confidence_checks':confidence_checks,
        'mission_requirements':mission_requirements,
        'shortlist_sha256':hashlib.sha256(_canonical(shortlist)).hexdigest(),
        'checks':checks,
        'approval_authority':'VEHICLE_SYSTEMS_ENGINEER',
        'required_physical_validation':['DYNAMOMETER','THERMAL_DERATING','RANGE_CYCLE','ACCELERATION_TEST','PACKAGING_REVIEW'],
        'prototype_or_production_build_authorized':False,
        'claim_boundary':'Model-based architecture selection only; no homologation, safety certification, durability certification, or production release claim.',
    }
    return {**core,'certificate_sha256':hashlib.sha256(_canonical(core)).hexdigest(),'generated_at_utc':datetime.now(timezone.utc).isoformat()}


def verify_design_release_certificate(certificate: dict[str,Any])->dict[str,Any]:
    stored=certificate.get('certificate_sha256')
    core={k:v for k,v in certificate.items() if k not in {'certificate_sha256','generated_at_utc'}}
    expected=hashlib.sha256(_canonical(core)).hexdigest()
    return {'valid':bool(stored and stored==expected),'stored_sha256':stored,'expected_sha256':expected,'decision_state':certificate.get('decision_state')}
