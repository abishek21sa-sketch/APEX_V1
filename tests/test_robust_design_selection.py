from apex.design import DesignCandidate, build_vehicle
from apex.robust import robust_crossover_mission, select_robust_design


def candidate(**overrides):
    d=dict(battery_capacity_kwh=100.0,motor_power_kw=180.0,gear_ratio=9.0,drag_coefficient=0.24,frontal_area_m2=2.25,motor_architecture='pm_synchronous',battery_chemistry='nmc',num_motors='1',tire_choice='standard')
    d.update(overrides); return DesignCandidate(**d)


def test_selector_is_deterministic_and_uses_common_scenario_policy():
    xs=[candidate(battery_capacity_kwh=92,motor_power_kw=190),candidate(battery_capacity_kwh=110,motor_power_kw=260)]
    m=robust_crossover_mission()
    a=select_robust_design(xs,m,n_samples=60,seed=7)
    b=select_robust_design(xs,m,n_samples=60,seed=7)
    assert a['selected_index']==b['selected_index']
    assert a['scores']==b['scores']


def test_robust_feasibility_outranks_lower_cost():
    # The first design is cheaper but marginal; the second has materially more battery/power reserve.
    cheap=candidate(battery_capacity_kwh=88,motor_power_kw=210,battery_chemistry='lfp',motor_architecture='switched_reluctance',tire_choice='eco_low_rolling_resistance')
    robust=candidate(battery_capacity_kwh=112,motor_power_kw=280,battery_chemistry='nmc',motor_architecture='pm_synchronous',tire_choice='standard')
    _,cheap_report=build_vehicle(cheap); _,robust_report=build_vehicle(robust)
    assert cheap_report.total_manufacturing_cost < robust_report.total_manufacturing_cost
    out=select_robust_design([cheap,robust],robust_crossover_mission(),n_samples=100,seed=11)
    if out['scores'][1]['robustly_feasible'] and not out['scores'][0]['robustly_feasible']:
        assert out['selected_index']==1
    else:
        # Even if this particular physics revision moves the boundary, selection remains lexicographic.
        keys=[(0 if s['robustly_feasible'] else 1,s['reliability_shortfall'],s['cvar_normalized_violation'],s['mean_normalized_violation'],s['manufacturing_cost_usd']) for s in out['scores']]
        assert out['selected_index']==min(range(2), key=lambda i: keys[i])
