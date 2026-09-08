"""Real, currently-shipping production EVs, used as competitive benchmarks
against this platform's own generated designs -- not simulated, not tuned,
not invented. Sourced from a published 2026-model-year US EV comparison
table (coltura.org/electric-car-battery-range, fetched 2026-08-28), which
itself compiles EPA-rated range and manufacturer starting MSRP.

Two honest caveats, not glossed over:

1. `epa_range_mi` is the EPA combined-cycle test figure. This platform's own
   `range_mi` objective (apex.physics.constant_speed_range_km at 65mph) is a
   constant-speed highway simulation -- a different measurement methodology,
   not a discrepancy in either one. Comparable in spirit ("how far does this
   go"), not bit-for-bit identical.
2. `msrp_usd` is retail price to a buyer. This platform's own
   `manufacturing_cost_usd` objective is cost to build, not price to sell --
   comparing the two directly would be apples to oranges. Callers wanting a
   fair comparison should inflate manufacturing cost by the same
   msrp_markup_factor used elsewhere in this codebase (see
   apex.design.constraints.example_crossover_mission), not compare raw.

No 0-60 acceleration figure is included here: a reliable, trim-matched
0-60 time for all 98 of these specific trims was not available from a single
consistent source, and approximating one from a different vehicle's
performance-oriented trim (e.g. a "Performance" or "GT" variant's tested time
standing in for this table's base trim) would be a wrong number presented as
a real one -- worse than not having the dimension at all.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkVehicle:
    name: str
    epa_range_mi: float
    msrp_usd: float
    vehicle_type: str
    drivetrain: str


BENCHMARK_VEHICLES: list[BenchmarkVehicle] = [
    BenchmarkVehicle("Lucid Air Grand Touring XR AWD", 512, 114900, "Sedan", "AWD"),
    BenchmarkVehicle("Chevrolet Silverado EV 8WT Max Range 4WD", 493, 74200, "Pickup Truck", "4WD"),
    BenchmarkVehicle("GMC Sierra EV AT4 Max Range 4WD", 478, 92195, "Pickup Truck", "4WD"),
    BenchmarkVehicle("Cadillac Escalade IQ AWD", 465, 127405, "SUV (7 seats)", "AWD"),
    BenchmarkVehicle("Lucid Gravity Grand Touring 2-row AWD", 450, 98900, "SUV", "AWD"),
    BenchmarkVehicle("Lucid Gravity Grand Touring 3-row AWD", 437, 101800, "SUV (7 seats)", "AWD"),
    BenchmarkVehicle("BMW iX3 50 xDrive AWD", 434, 61500, "SUV", "AWD"),
    BenchmarkVehicle("Rivian R1T Dual Max 4WD", 420, 83900, "Pickup Truck", "4WD"),
    BenchmarkVehicle("GMC Sierra EV Elevation Extended Range 4WD", 410, 73195, "Pickup Truck", "4WD"),
    BenchmarkVehicle("Tesla Model S AWD", 410, 79990, "Sedan", "AWD"),
    BenchmarkVehicle("Rivian R1S Dual Max 4WD", 410, 89900, "SUV (7 seats)", "4WD"),
    BenchmarkVehicle("Audi A6 Sportback e-tron ultra RWD", 395, 66700, "Sedan", "RWD"),
    BenchmarkVehicle("Mercedes-Benz EQS 450+ Sedan RWD", 390, 104400, "Sedan", "RWD"),
    BenchmarkVehicle("BMW iX xDrive60 AWD", 364, 88500, "SUV", "AWD"),
    BenchmarkVehicle("Tesla Model 3 Premium RWD", 363, 42490, "Sedan", "RWD"),
    BenchmarkVehicle("Tesla Model Y Long Range RWD", 357, 44990, "SUV", "RWD"),
    BenchmarkVehicle("Tesla Model X AWD", 352, 79990, "SUV (7 seats)", "AWD"),
    BenchmarkVehicle("Hyundai IONIQ 6 RWD", 342, 46300, "Sedan", "RWD"),
    BenchmarkVehicle("Hyundai IONIQ 9 RWD", 335, 58955, "SUV (7 seats)", "RWD"),
    BenchmarkVehicle("Tesla Cybertruck Long Range RWD", 335, 69990, "Pickup Truck", "RWD"),
    BenchmarkVehicle("BMW i4 eDrive40 Gran Coupe RWD", 333, 57900, "Sedan", "RWD"),
    BenchmarkVehicle("BMW i5 eDrive40 Sedan RWD", 328, 67100, "Sedan", "RWD"),
    BenchmarkVehicle("Acura ZDX RWD", 327, 64500, "SUV", "RWD"),
    BenchmarkVehicle("Cadillac LYRIQ RWD", 326, 59200, "SUV", "RWD"),
    BenchmarkVehicle("Audi S6 Sportback e-tron AWD", 326, 79600, "Sedan", "AWD"),
    BenchmarkVehicle("Audi Q6 e-tron quattro AWD", 325, 64500, "SUV", "AWD"),
    BenchmarkVehicle("Audi Q6 Sportback e-tron quattro AWD", 325, 68300, "SUV", "AWD"),
    BenchmarkVehicle("Tesla Cybertruck AWD", 325, 79990, "Pickup Truck", "AWD"),
    BenchmarkVehicle("Ford Mustang Mach-E Extended Range RWD", 320, 48580, "SUV", "RWD"),
    BenchmarkVehicle("Ford F-150 Lightning Extended Range AWD", 320, 58875, "Pickup Truck", "AWD"),
    BenchmarkVehicle("Chevrolet Equinox EV FWD", 319, 34995, "SUV", "FWD"),
    BenchmarkVehicle("Kia EV6 Light Long Range RWD", 319, 41200, "SUV", "RWD"),
    BenchmarkVehicle("Hyundai IONIQ 5 RWD", 318, 41000, "SUV", "RWD"),
    BenchmarkVehicle("GMC Hummer EV Pickup 2X AWD", 318, 99895, "Pickup Truck", "AWD"),
    BenchmarkVehicle("Cadillac OPTIQ RWD", 317, 50900, "SUV", "RWD"),
    BenchmarkVehicle("Mercedes-Benz EQS 550 4MATIC SUV AWD", 317, 112450, "SUV", "AWD"),
    BenchmarkVehicle("Porsche Taycan 4S Performance Battery Plus AWD", 315, 99400, "Sedan", "AWD"),
    BenchmarkVehicle("GMC Hummer EV SUV 2X AWD", 315, 99895, "SUV", "AWD"),
    BenchmarkVehicle("Toyota bZ XLE FWD Plus", 314, 39350, "SUV", "FWD"),
    BenchmarkVehicle("BMW i7 eDrive50 Sedan RWD", 314, 105700, "Sedan", "RWD"),
    BenchmarkVehicle("Chevrolet Blazer EV FWD", 312, 44700, "SUV", "FWD"),
    BenchmarkVehicle("Polestar 3 Long Range Dual Motor AWD", 312, 73400, "SUV", "AWD"),
    BenchmarkVehicle("Polestar 4 Long Range Single Motor RWD", 310, 54900, "SUV", "RWD"),
    BenchmarkVehicle("Porsche Macan Electric RWD", 309, 78800, "SUV", "RWD"),
    BenchmarkVehicle("Subaru Uncharted FWD", 308, 34995, "SUV", "FWD"),
    BenchmarkVehicle("Honda Prologue FWD", 308, 47400, "SUV", "FWD"),
    BenchmarkVehicle("Mercedes-Benz EQE 320+ Sedan RWD", 308, 74900, "Sedan", "RWD"),
    BenchmarkVehicle("Genesis GV60 RWD", 306, 52525, "SUV", "RWD"),
    BenchmarkVehicle("Kia EV9 Long Range RWD", 305, 57900, "SUV (7 seats)", "RWD"),
    BenchmarkVehicle("Cadillac VISTIQ AWD", 305, 77395, "SUV (7 seats)", "AWD"),
    BenchmarkVehicle("Volvo EX90 Twin Motor AWD", 305, 81390, "SUV (7 seats)", "AWD"),
    BenchmarkVehicle("Nissan LEAF S+ FWD", 303, 29990, "Hatchback", "FWD"),
    BenchmarkVehicle("Cadillac CELESTIQ AWD", 303, 400000, "Sedan (4 seats)", "AWD"),
    BenchmarkVehicle("Mercedes-Benz EQE 320+ SUV RWD", 302, 77900, "SUV", "RWD"),
    BenchmarkVehicle("Lexus RZ 350e FWD", 301, 47295, "SUV", "FWD"),
    BenchmarkVehicle("Genesis Electrified G80 AWD", 300, 74375, "Sedan", "AWD"),
    BenchmarkVehicle("Audi S e-tron GT AWD", 300, 127700, "Sedan", "AWD"),
    BenchmarkVehicle("Mercedes-Maybach EQS 680 SUV AWD", 300, 179900, "SUV", "AWD"),
    BenchmarkVehicle("Volvo EC40 Single Motor Extended Range RWD", 298, 53600, "SUV (4 seats)", "RWD"),
    BenchmarkVehicle("Volvo EX40 Single Motor Extended Range RWD", 296, 56545, "SUV", "RWD"),
    BenchmarkVehicle("Jeep Wagoneer S AWD", 294, 65200, "SUV", "AWD"),
    BenchmarkVehicle("Volkswagen ID.4 Pro RWD", 291, 44875, "SUV", "RWD"),
    BenchmarkVehicle("Nissan ARIYA FWD 87 kWh", 289, 41190, "SUV", "FWD"),
    BenchmarkVehicle("Subaru Solterra AWD", 288, 38495, "SUV", "AWD"),
    BenchmarkVehicle("Audi Q4 45 e-tron RWD", 288, 50600, "SUV", "RWD"),
    BenchmarkVehicle("Toyota C-HR AWD", 287, 37000, "SUV", "AWD"),
    BenchmarkVehicle("VinFast VF 9 Plus AWD", 287, 69800, "SUV (7 seats)", "AWD"),
    BenchmarkVehicle("Audi SQ6 e-tron AWD", 285, 73200, "SUV", "AWD"),
    BenchmarkVehicle("Audi SQ6 Sportback e-tron AWD", 285, 75600, "SUV", "AWD"),
    BenchmarkVehicle("Subaru Trailseeker AWD", 281, 39995, "SUV", "AWD"),
    BenchmarkVehicle("Toyota bZ Woodland AWD", 281, 45300, "SUV", "AWD"),
    BenchmarkVehicle("Lotus Eletre AWD", 280, 229900, "SUV", "AWD"),
    BenchmarkVehicle("Audi RS e-tron GT Performance AWD", 278, 170500, "Sedan", "AWD"),
    BenchmarkVehicle("Rolls-Royce Spectre AWD", 277, 423000, "Coupe (4 seats)", "AWD"),
    BenchmarkVehicle("Chevrolet BrightDrop 600", 272, 41425, "Van", "FWD/AWD"),
    BenchmarkVehicle("Maserati Grecale Folgore AWD", 268, 121290, "SUV", "AWD"),
    BenchmarkVehicle("Genesis Electrified GV70 AWD", 263, 64380, "SUV", "AWD"),
    BenchmarkVehicle("Chevrolet Bolt FWD", 262, 27600, "Hatchback", "FWD"),
    BenchmarkVehicle("Hyundai Kona Electric FWD", 261, 36975, "SUV", "FWD"),
    BenchmarkVehicle("Volvo EX30 Single Motor Extended Range RWD", 261, 40345, "SUV", "RWD"),
    BenchmarkVehicle("VinFast VF 8 Eco AWD", 256, 46000, "SUV", "AWD"),
    BenchmarkVehicle("Kia Niro Electric FWD", 253, 39700, "SUV", "FWD"),
    BenchmarkVehicle("Mercedes-Benz EQB 250+ SUV FWD", 251, 53050, "SUV", "FWD"),
    BenchmarkVehicle("Audi Q4 Sportback 55 e-tron quattro AWD", 251, 59000, "SUV", "AWD"),
    BenchmarkVehicle("Dodge Charger Daytona Scat Pack AWD", 241, 66990, "Coupe/Sedan", "AWD"),
    BenchmarkVehicle("Mercedes-Benz G 580 with EQ Technology 4WD", 239, 161500, "SUV", "4WD"),
    BenchmarkVehicle("Volkswagen ID. Buzz RWD", 234, 59995, "Van (7 seats)", "RWD"),
    BenchmarkVehicle("Maserati GranTurismo Folgore AWD", 233, 199690, "Coupe (4 seats)", "AWD"),
    BenchmarkVehicle("Maserati GranCabrio Folgore AWD", 229, 206995, "Convertible (4 seats)", "AWD"),
    BenchmarkVehicle("Hyundai IONIQ 5 N AWD", 221, 66100, "SUV", "AWD"),
    BenchmarkVehicle("MINI Countryman SE ALL4 AWD", 216, 45200, "SUV", "AWD"),
    BenchmarkVehicle("VinFast VF 7 Plus AWD", 209, 39900, "SUV", "AWD"),
    BenchmarkVehicle("Mercedes-Benz eSprinter Cargo Van", 200, 71390, "Van", "RWD"),
    BenchmarkVehicle("VinFast VF 6 Plus FWD", 176, 35000, "SUV", "FWD"),
    BenchmarkVehicle("Rimac Nevera R 4WD", 174, 2500000, "Coupe (2 seats)", "4WD"),
    BenchmarkVehicle("Ram ProMaster EV Cargo Van", 162, 56495, "Van", "FWD"),
    BenchmarkVehicle("Ford E-Transit Cargo Van", 159, 51095, "Van", "RWD"),
    BenchmarkVehicle("Fiat 500e FWD", 149, 32500, "Hatchback (4 seats)", "FWD"),
]
