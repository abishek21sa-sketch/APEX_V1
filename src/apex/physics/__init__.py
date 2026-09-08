"""Vehicle physics kernel: longitudinal dynamics, performance, energy, motor, and
battery models.

Phase 1 (longitudinal.py, performance.py, energy.py's flat-efficiency functions)
and Phase 2 (motor.py, battery.py, energy.py's simulate_drive_cycle_with_battery)
of the APEX platform. Everything here is first-principles vehicle engineering math
operating on a plain `VehicleParams` design vector. Later phases wrap this kernel
in optimization (MDO / MINLP / Pareto search) and surrogate models — nothing in
here should assume how it will be called.
"""

from .params import VehicleParams
from .longitudinal import (
    aero_drag_force,
    rolling_resistance_force,
    grade_force,
    road_load_force,
    wheel_power_required,
    max_traction_force,
    max_motor_speed_mps,
    motor_force_limit,
    available_wheel_force,
)
from .performance import (
    simulate_acceleration,
    zero_to_sixty_s,
    top_speed_mps,
    max_gradeability,
    braking_distance_m,
)
from .energy import (
    simulate_drive_cycle,
    range_from_cycle,
    constant_speed_range_km,
    simulate_drive_cycle_with_battery,
)
from .motor import (
    motor_peak_speed_rad_s,
    motor_base_speed_rad_s,
    motor_shaft_torque_nm,
    motor_shaft_speed_rad_s,
    motor_efficiency,
)
from .battery import (
    BatteryState,
    open_circuit_voltage,
    terminal_voltage,
    max_discharge_current_a,
    max_charge_current_a,
    degrade_state_of_health,
    step_soc,
)

__all__ = [
    "VehicleParams",
    "aero_drag_force",
    "rolling_resistance_force",
    "grade_force",
    "road_load_force",
    "wheel_power_required",
    "max_traction_force",
    "max_motor_speed_mps",
    "motor_force_limit",
    "available_wheel_force",
    "simulate_acceleration",
    "zero_to_sixty_s",
    "top_speed_mps",
    "max_gradeability",
    "braking_distance_m",
    "simulate_drive_cycle",
    "range_from_cycle",
    "constant_speed_range_km",
    "simulate_drive_cycle_with_battery",
    "motor_peak_speed_rad_s",
    "motor_base_speed_rad_s",
    "motor_shaft_torque_nm",
    "motor_shaft_speed_rad_s",
    "motor_efficiency",
    "BatteryState",
    "open_circuit_voltage",
    "terminal_voltage",
    "max_discharge_current_a",
    "max_charge_current_a",
    "degrade_state_of_health",
    "step_soc",
]
