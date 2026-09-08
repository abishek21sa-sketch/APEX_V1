from __future__ import annotations
import hashlib
import json
from pathlib import Path
from apex.design import DesignCandidate
from apex.robust import robust_crossover_mission, select_robust_design

shortlist = [
    # Cheaper nominal candidates that intentionally stress the robust gate.
    DesignCandidate(88, 210, 8.6, 0.29, 2.25, 'switched_reluctance', 'lfp', '1', 'eco_low_rolling_resistance'),
    DesignCandidate(110, 360, 10.0, 0.20, 2.00, 'pm_synchronous', 'nmc', '2', 'eco_low_rolling_resistance'),
    # Robust-feasible candidates. The selector must choose on reliability/tail risk before cost.
    DesignCandidate(115, 380, 10.5, 0.21, 2.05, 'pm_synchronous', 'nmc', '2', 'eco_low_rolling_resistance'),
    DesignCandidate(120, 350, 10.0, 0.20, 2.00, 'pm_synchronous', 'nmc', '2', 'eco_low_rolling_resistance'),
]
result = select_robust_design(shortlist, robust_crossover_mission(), n_samples=300, seed=2026, cvar_alpha=.90, confidence=.95)
selected = result['selected_score']
status = 'PASS' if bool(selected['confidence_certified']) else 'HOLD'
payload = {
    'release': 'APEX_PORTFOLIO_RC1',
    'status': status,
    'robust_design_selection': result,
    'release_gate': {
        'selected_design_robustly_feasible': bool(selected['robustly_feasible']),
        'selected_design_confidence_certified': bool(selected['confidence_certified']),
        'all_reliability_lower_bounds_meet_targets': all(
            selected['requirement_reliability_lower_bound'][k] >= v for k, v in selected['requirement_targets'].items()
        ),
        'human_design_review_required': True,
        'autonomous_release_allowed': False,
    },
    'production_claim': False,
    'evidence_boundary': 'Physics/simulation benchmark only; not vehicle certification.',
}
core = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
payload['evidence_sha256'] = hashlib.sha256(core).hexdigest()
root = Path(__file__).resolve().parents[1]
(root / 'artifacts').mkdir(exist_ok=True)
(root / 'artifacts' / 'portfolio_validation.json').write_text(json.dumps(payload, indent=2, sort_keys=True))
print(json.dumps({'release': payload['release'], 'status': status, 'selected_index': result['selected_index'], 'selected_score': selected}, indent=2))
if status != 'PASS':
    raise SystemExit('APEX_PORTFOLIO_VALIDATION=HOLD: no selected design satisfies the finite-sample confidence release gate')
print('APEX_PORTFOLIO_VALIDATION=PASS')
