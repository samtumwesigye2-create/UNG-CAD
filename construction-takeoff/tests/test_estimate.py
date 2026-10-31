import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("estimate",Path(__file__).resolve().parents[1]/"estimate.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
MODEL={"schema_version":1,"model_id":"X","revision":"1","components":[{"id":"c1","system":"concrete","unit":"m3","quantity":10,"waste_fraction":0.1}]}
RATES={"concrete":{"m3":100}}
class EstimateTests(unittest.TestCase):
    def test_valid_estimate_not_gatekeeper_approved(self):
        result=mod.estimate(MODEL,RATES)
        self.assertEqual(result["status"],"ESTIMATE_ONLY")
        self.assertEqual(result["total_usd"],1100)
        self.assertFalse(result["gatekeeper_approved"])
    def test_missing_rate_blocks(self):
        self.assertEqual(mod.estimate(MODEL,{})["status"],"BLOCKED")
    def test_bad_quantity_blocks(self):
        model={**MODEL,"components":[{**MODEL["components"][0],"quantity":-1}]}
        self.assertEqual(mod.estimate(model,RATES)["status"],"BLOCKED")
    def test_duplicate_id_blocks(self):
        model={**MODEL,"components":MODEL["components"]*2}
        self.assertEqual(mod.estimate(model,RATES)["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
