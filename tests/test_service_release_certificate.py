from fastapi.testclient import TestClient
from service.main import app


def spec(battery,power):
    return {'battery_capacity_kwh':battery,'motor_power_kw':power,'gear_ratio':9.0,'drag_coefficient':.24,'frontal_area_m2':2.25,'motor_architecture':'pm_synchronous','battery_chemistry':'nmc','num_motors':'1','tire_choice':'standard'}


def test_release_certificate_endpoint_never_authorizes_build():
    r=TestClient(app).post('/robust-select/certificate',json={'candidates':[spec(112,280),spec(128,330)],'requirements':[{'kind':'max_acceleration_time_s','threshold':6.0},{'kind':'min_highway_range_mi','threshold':310.0}],'n_samples':100,'seed':17,'cvar_alpha':.9})
    assert r.status_code==200
    assert r.headers['X-Request-ID'].startswith('apex-')
    assert float(r.headers['X-Response-Time-Ms']) >= 0
    b=r.json()
    assert b['verification']['valid'] is True
    assert b['certificate']['prototype_or_production_build_authorized'] is False
    assert b['certificate']['decision_state'] in {'ENGINEERING_DESIGN_REVIEW','HOLD'}
