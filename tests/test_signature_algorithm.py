import unittest
import importlib.util
import sys
from pathlib import Path


def _load_signature_module():
    path = Path(__file__).parents[1] / "src" / "apex" / "robust" / "signature_algorithm.py"
    spec = importlib.util.spec_from_file_location("apex_signature_algorithm", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_signature = _load_signature_module()
Architecture = _signature.Architecture
ablation = _signature.ablation
select_architecture = _signature.select_architecture
sensitivity = _signature.sensitivity


class SignatureAlgorithmTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            Architecture("cheap", 40_000, 420, 7.5, 0.82),
            Architecture("shielded", 44_000, 410, 7.7, 0.96),
            Architecture("long", 48_000, 520, 8.4, 0.94),
        ]
        self.kwargs = dict(min_range_km=400, max_zero_to_sixty_s=8.0, max_cost_usd=46_000)

    def test_reliability_gate_selects_shielded_design(self):
        self.assertEqual(select_architecture(self.candidates, **self.kwargs).name, "shielded")

    def test_infeasible_requirements_hold(self):
        self.assertIsNone(select_architecture(self.candidates, min_range_km=600, **{k: v for k, v in self.kwargs.items() if k != "min_range_km"}))

    def test_ablation_can_select_nominally_cheapest(self):
        self.assertEqual(ablation(self.candidates, **self.kwargs).name, "cheap")

    def test_cost_sensitivity_can_hold(self):
        self.assertIsNone(sensitivity(self.candidates, 0.9, **self.kwargs))


if __name__ == "__main__":
    unittest.main()
