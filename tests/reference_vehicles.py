"""Reference vehicles for Phase 1/2 physics-kernel validation.

Specs were web-verified (2026-08-25) against multiple public sources (evspecifications.com,
Edmunds, GM/Nissan-sourced spec aggregators, Wikipedia's Nissan EM-motor writeup, enthusiast
forums quoting drivetrain teardowns) for well-known production EVs, model years as noted.
Mass, drag coefficient, frontal area, motor power/torque, EPA range, and gear ratio matched
published figures closely (Bolt's 7.05:1 final drive and Tesla's ~9.04:1 rear-drive-unit ratio
confirmed almost exactly; the Leaf's ratio below is corrected to the 2nd-generation/2018 figure
after an initial pass mistakenly used the 1st-generation one). Frontal area for the Bolt and
Leaf, and max_motor_rpm generally, remain the least-certain figures -- no authoritative source
for either turned up, so those stay engineering estimates. battery_nominal_voltage_v is also
web-confirmed for all three (Tesla/Bolt 350V, Leaf 360V); battery_internal_resistance_ohm and
the C-rate limits are left at params.py's generic defaults -- no manufacturer publishes those,
so they're not vehicle-specific here, just a plausible pack-level order of magnitude. Treat
every value here as "plausible for this vehicle class, cross-checked where possible," not as
a verified-to-the-decimal citation.

Purpose: confirm the physics kernel's equations produce the right *ballpark* and the
right *shape* of answer (heavier/draggier -> slower and shorter range, more power ->
faster) against real vehicles, not to precisely reproduce manufacturer dyno numbers --
that requires real efficiency maps and official multi-cycle test procedures, which are
out of scope for a first-principles Phase 1 kernel.
"""

from dataclasses import dataclass

from apex.physics import VehicleParams


@dataclass(frozen=True)
class ReferenceSpec:
    params: VehicleParams
    published_0_60_s: float
    published_top_speed_mph: float
    published_epa_range_mi: float
    source_note: str


TESLA_MODEL_3_LR_AWD_2021 = ReferenceSpec(
    params=VehicleParams(
        name="Tesla Model 3 Long Range AWD (2021)",
        mass_kg=1844.0,
        drag_coefficient=0.23,
        frontal_area_m2=2.22,
        rolling_resistance_coeff=0.008,
        wheel_radius_m=0.335,
        tire_friction_coeff=0.9,
        motor_power_kw=324.0,
        motor_peak_torque_nm=550.0,
        gear_ratio=9.04,
        drivetrain_efficiency=0.90,
        regen_efficiency=0.70,
        max_motor_rpm=18447.0,
        battery_usable_kwh=75.0,
        battery_nominal_voltage_v=350.0,  # web-confirmed
    ),
    published_0_60_s=4.2,
    published_top_speed_mph=145.0,
    published_epa_range_mi=353.0,
    source_note=(
        "Dual-motor AWD, MY2021. Mass/Cd/frontal-area/0-60/top-speed/gear-ratio web-confirmed; "
        "published top speed (145 mph) sits well below both the power-limited (~215 mph) and "
        "RPM-redline-limited (~161 mph) physics ceilings computed here -- unlike the Bolt/Leaf "
        "below, Tesla's real top speed is a software cap (commonly attributed to tire speed "
        "rating), which this kernel doesn't model."
    ),
)

CHEVROLET_BOLT_EV_2020 = ReferenceSpec(
    params=VehicleParams(
        name="Chevrolet Bolt EV (2020)",
        mass_kg=1616.0,
        drag_coefficient=0.32,
        frontal_area_m2=2.36,
        rolling_resistance_coeff=0.009,
        wheel_radius_m=0.316,
        tire_friction_coeff=0.85,
        motor_power_kw=150.0,
        motor_peak_torque_nm=360.0,
        gear_ratio=7.05,
        drivetrain_efficiency=0.88,
        regen_efficiency=0.68,
        max_motor_rpm=8800.0,
        battery_usable_kwh=66.0,
        battery_nominal_voltage_v=350.0,  # web-confirmed
    ),
    published_0_60_s=6.5,
    published_top_speed_mph=91.0,
    published_epa_range_mi=259.0,
    source_note=(
        "Single front motor, MY2020. Mass/motor-power/torque/EPA-range/battery-kWh/gear-ratio "
        "(7.05:1) web-confirmed almost exactly; 0-60 sources ranged 6.2-6.9s depending on outlet, "
        "6.5s used here sits inside that range. Governed top speed (91 mph) lands close to the "
        "RPM-redline-limited physics ceiling -- consistent with the redline, not a separate "
        "software cap, being the real limiter on this car."
    ),
)

NISSAN_LEAF_40KWH_2018 = ReferenceSpec(
    params=VehicleParams(
        name="Nissan Leaf 40 kWh (2018)",
        mass_kg=1580.0,
        drag_coefficient=0.28,
        frontal_area_m2=2.30,
        rolling_resistance_coeff=0.009,
        wheel_radius_m=0.316,
        tire_friction_coeff=0.85,
        motor_power_kw=110.0,
        motor_peak_torque_nm=320.0,
        gear_ratio=8.193,
        drivetrain_efficiency=0.87,
        regen_efficiency=0.65,
        max_motor_rpm=10500.0,
        battery_usable_kwh=36.0,
        battery_nominal_voltage_v=360.0,  # web-confirmed
    ),
    published_0_60_s=7.4,
    published_top_speed_mph=89.0,
    published_epa_range_mi=151.0,
    source_note=(
        "Single front motor (EM57), 2nd-generation Leaf, MY2018. Mass/Cd/motor-power/torque/"
        "EPA-range web-confirmed almost exactly; gear ratio corrected to the 2nd-gen figure "
        "(8.193:1) after an earlier pass used the 1st-gen (2013-2017) EM57 ratio (~7.94:1) by "
        "mistake -- same motor family, different final drive. Published 0-60 is derived from a "
        "0-62mph figure (7.9s), not measured directly at 60."
    ),
)

ALL_REFERENCE_VEHICLES = [
    TESLA_MODEL_3_LR_AWD_2021,
    CHEVROLET_BOLT_EV_2020,
    NISSAN_LEAF_40KWH_2018,
]
