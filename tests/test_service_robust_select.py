from fastapi.testclient import TestClient
from service.main import app


def spec(battery, power):
    return {'battery_capacity_kwh':battery,'motor_power_kw':power,'gear_ratio':9.0,'drag_coefficient':.24,'frontal_area_m2':2.25,'motor_architecture':'pm_synchronous','battery_chemistry':'nmc','num_motors':'1','tire_choice':'standard'}

def test_robust_select_endpoint_returns_governed_selection():
    r=TestClient(app).post('/robust-select',json={'candidates':[spec(92,200),spec(112,280)],'requirements':[{'kind':'max_acceleration_time_s','threshold':6.0},{'kind':'min_highway_range_mi','threshold':310.0}],'n_samples':30,'seed':9,'cvar_alpha':.9})
    assert r.status_code==200
    b=r.json(); assert b['selected_index'] in {0,1}; assert 'decision_policy' in b
