"""The vehicle design vector: every parameter the physics kernel and, later,
the optimizer are allowed to reason about.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleParams:
    name: str

    # Mass & aerodynamics
    mass_kg: float
    drag_coefficient: float
    frontal_area_m2: float
    rolling_resistance_coeff: float

    # Running gear
    wheel_radius_m: float
    tire_friction_coeff: float = 0.9

    # Powertrain, specified at the motor shaft; motor_force_limit() reflects
    # it through gear_ratio/wheel_radius into a wheel force.
    motor_power_kw: float = 0.0
    motor_peak_torque_nm: float = 0.0
    gear_ratio: float = 9.0
    drivetrain_efficiency: float = 0.90
    regen_efficiency: float = 0.70

    # Mechanical redline of the motor. With a single fixed reduction ratio (no
    # multi-speed gearbox), this is what actually caps top speed on most production
    # EVs -- not an arbitrary software governor. Default is generously high so it
    # only binds when the caller supplies a real figure.
    max_motor_rpm: float = 20000.0

    # "Mass factor" lambda: accounts for the rotational inertia of wheels,
    # gearbox, and motor rotor, which resist linear acceleration in addition
    # to the vehicle's translational mass. Typical EVs: ~1.03-1.06.
    rotational_inertia_factor: float = 1.03

    # Energy storage: usable energy (Phase 1's simple scalar, still used by
    # energy.simulate_drive_cycle()) plus the equivalent-circuit pack details
    # Phase 2's battery.py needs for SOC/voltage/current-limit modeling.
    battery_usable_kwh: float = 0.0
    battery_nominal_voltage_v: float = 350.0
    battery_internal_resistance_ohm: float = 0.05
    battery_max_c_rate_discharge: float = 3.0
    battery_max_c_rate_charge: float = 1.5
    battery_min_soc: float = 0.05
    battery_max_soc: float = 0.97

    # Capacity fade proxy: fractional capacity loss per 1000 Ah of cumulative
    # charge+discharge throughput. Order-of-magnitude only (see battery.py's
    # degrade_state_of_health docstring) -- 0 disables aging.
    battery_fade_per_1000_ah_throughput: float = 0.0003

    @property
    def battery_capacity_ah(self) -> float:
        """Nominal pack capacity implied by battery_usable_kwh and the pack's
        nominal voltage -- derived, not a separate stored figure, so the two
        energy-storage fields can't silently disagree.
        """
        return self.battery_usable_kwh * 1000.0 / self.battery_nominal_voltage_v

    def __post_init__(self) -> None:
        positive_fields = {
            "mass_kg": self.mass_kg,
            "frontal_area_m2": self.frontal_area_m2,
            "wheel_radius_m": self.wheel_radius_m,
            "drivetrain_efficiency": self.drivetrain_efficiency,
            "regen_efficiency": self.regen_efficiency,
            "rotational_inertia_factor": self.rotational_inertia_factor,
            "max_motor_rpm": self.max_motor_rpm,
            "battery_nominal_voltage_v": self.battery_nominal_voltage_v,
            "battery_max_c_rate_discharge": self.battery_max_c_rate_discharge,
            "battery_max_c_rate_charge": self.battery_max_c_rate_charge,
        }
        for field_name, value in positive_fields.items():
            if value <= 0:
                raise ValueError(f"{field_name} must be positive, got {value}")
        if self.drag_coefficient < 0:
            raise ValueError(f"drag_coefficient must be >= 0, got {self.drag_coefficient}")
        if self.rolling_resistance_coeff < 0:
            raise ValueError(f"rolling_resistance_coeff must be >= 0, got {self.rolling_resistance_coeff}")
        if not (0 < self.tire_friction_coeff <= 1.5):
            raise ValueError(f"tire_friction_coeff out of plausible range (0, 1.5], got {self.tire_friction_coeff}")
        if self.battery_internal_resistance_ohm < 0:
            raise ValueError(
                f"battery_internal_resistance_ohm must be >= 0, got {self.battery_internal_resistance_ohm}"
            )
        if not (0 <= self.battery_min_soc < self.battery_max_soc <= 1.0):
            raise ValueError(
                "battery_min_soc/battery_max_soc must satisfy 0 <= min < max <= 1, "
                f"got min={self.battery_min_soc}, max={self.battery_max_soc}"
            )
        if self.battery_fade_per_1000_ah_throughput < 0:
            raise ValueError(
                "battery_fade_per_1000_ah_throughput must be >= 0, "
                f"got {self.battery_fade_per_1000_ah_throughput}"
            )
