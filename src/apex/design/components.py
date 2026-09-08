"""Discrete component choices: named presets bundling the physical properties a
real engineering decision actually carries together (a tire choice fixes rolling
resistance, grip, *and* wheel radius as a package; a battery chemistry fixes cost
*and* mass per kWh together) -- these aren't independent continuous knobs.

Mass/cost figures are order-of-magnitude engineering estimates, web-verified
(2026-08-25) against published figures where a source exists (battery pack cost
and specific mass; motor+inverter cost floor), and reasoned extrapolations where
it doesn't (per-chemistry mass split, drive-unit vs. bare-motor mass, final
component pricing). Sources:
  - Battery pack cost: BloombergNEF 2025 survey -- BEV packs ~$99/kWh blended,
    LFP ~$81/kWh, NMC ~$128/kWh (about.bnef.com, Dec 2025 release).
  - Battery pack specific mass: ~5-7 kg/kWh at the pack level across current
    production EVs (the Tesla Model 3 LR pack: ~480kg / ~75-80kWh =~ 6-6.4 kg/kWh).
    The NMC/LFP split below is a reasoned estimate from LFP's known lower
    energy density, not independently sourced per-chemistry.
  - Motor specific power: bare traction motors run ~3-5 kW/kg (GM Volt ~4.6 kW/kg,
    BMW i3 ~3 kW/kg); this module's mass figures are for the *drive unit*
    (motor + inverter + single-speed gearbox + mounts), which is meaningfully
    heavier per kW than the bare motor alone -- ~1.2-2.0 kW/kg used below, a
    reasoned derating rather than a separately sourced drive-unit figure.
  - Motor+inverter cost: DOE technical targets cite ~$3.30/kW (motor) + ~$2.70/kW
    (inverter) =~ $6/kW at a mature-production floor; figures below sit above that
    floor to reflect nearer-term (not fully matured) production cost.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MotorArchitecture:
    name: str
    specific_power_kw_per_kg: float  # drive-unit mass (motor+inverter+gearbox), not bare motor
    cost_per_kw: float  # USD/kW, drive unit (motor+inverter)
    max_motor_rpm: float
    base_speed_rpm: float  # corner speed: full torque meets rated power -- see motor.py
    drivetrain_efficiency: float  # flat scalar for Phase 1's energy path
    regen_efficiency: float


MOTOR_ARCHITECTURES = {
    # PM synchronous: today's dominant traction-motor choice -- best efficiency and
    # power density, higher cost (rare-earth magnets), moderate redline.
    "pm_synchronous": MotorArchitecture(
        name="pm_synchronous",
        specific_power_kw_per_kg=1.8,
        cost_per_kw=11.0,
        max_motor_rpm=18000.0,
        base_speed_rpm=5500.0,
        drivetrain_efficiency=0.92,
        regen_efficiency=0.72,
    ),
    # Induction: no rare-earth magnets (cheaper, no magnet-cost exposure), slightly
    # lower peak efficiency, tolerates higher redline, common as a front/secondary
    # motor in dual-motor layouts (low drag when unpowered).
    "induction": MotorArchitecture(
        name="induction",
        specific_power_kw_per_kg=1.4,
        cost_per_kw=8.0,
        max_motor_rpm=20000.0,
        base_speed_rpm=6500.0,
        drivetrain_efficiency=0.89,
        regen_efficiency=0.68,
    ),
    # Switched reluctance: simplest/cheapest construction (no magnets, no rotor
    # windings), lowest cost and lightest, but the lowest efficiency and highest
    # torque ripple of the three -- a genuine cost/performance trade, not strictly
    # worse (matches the platform's no-free-lunch, Pareto-frontier philosophy).
    "switched_reluctance": MotorArchitecture(
        name="switched_reluctance",
        specific_power_kw_per_kg=1.9,
        cost_per_kw=6.5,
        max_motor_rpm=16000.0,
        base_speed_rpm=5000.0,
        drivetrain_efficiency=0.85,
        regen_efficiency=0.62,
    ),
}


@dataclass(frozen=True)
class BatteryChemistry:
    name: str
    specific_mass_kg_per_kwh: float
    cost_per_kwh: float
    max_c_rate_discharge: float
    max_c_rate_charge: float


BATTERY_CHEMISTRIES = {
    # NMC: higher energy density (lighter per kWh) and higher C-rate capability,
    # but pricier and more exposed to nickel/cobalt cost swings.
    "nmc": BatteryChemistry(
        name="nmc",
        specific_mass_kg_per_kwh=6.0,
        cost_per_kwh=128.0,
        max_c_rate_discharge=3.5,
        max_c_rate_charge=1.8,
    ),
    # LFP: cheaper and more thermally/cycle-life robust, but heavier per kWh and a
    # lower sustainable C-rate -- exactly the range-vs-cost-vs-power trade the
    # platform's design space is meant to expose, not resolve for the user.
    "lfp": BatteryChemistry(
        name="lfp",
        specific_mass_kg_per_kwh=7.0,
        cost_per_kwh=81.0,
        max_c_rate_discharge=2.5,
        max_c_rate_charge=1.2,
    ),
}


@dataclass(frozen=True)
class TireChoice:
    name: str
    rolling_resistance_coeff: float
    tire_friction_coeff: float
    wheel_radius_m: float
    mass_delta_kg: float  # relative to the "standard" choice, all four tires+wheels combined
    cost_delta: float  # relative to the "standard" choice, all four tires+wheels combined


TIRE_CHOICES = {
    # Low-rolling-resistance "eco" tires: measurably better range, measurably worse
    # grip -- trades acceleration/braking margin for efficiency.
    "eco_low_rolling_resistance": TireChoice(
        name="eco_low_rolling_resistance",
        rolling_resistance_coeff=0.0075,
        tire_friction_coeff=0.80,
        wheel_radius_m=0.33,
        mass_delta_kg=-5.0,
        cost_delta=-40.0,
    ),
    "standard": TireChoice(
        name="standard",
        rolling_resistance_coeff=0.0090,
        tire_friction_coeff=0.90,
        wheel_radius_m=0.335,
        mass_delta_kg=0.0,
        cost_delta=0.0,
    ),
    # Performance tires: shorter braking distance and more available traction for
    # acceleration, at a real range and cost cost.
    "performance": TireChoice(
        name="performance",
        rolling_resistance_coeff=0.0115,
        tire_friction_coeff=1.05,
        wheel_radius_m=0.34,
        mass_delta_kg=8.0,
        cost_delta=180.0,
    ),
}
