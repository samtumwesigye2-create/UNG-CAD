import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("pipeline",Path(__file__).resolve().parents[1]/"pipeline.py")
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)
MODEL={"schema_version":1,"model_id":"DEMO","revision":"A","components":[
    {"id":"slab","system":"concrete","unit":"m3","quantity":10,"waste_fraction":0.1,"phase":2,"source":"test-measurement"}]}
CATALOG={"currency":"USD","effective_date":"2026-10-31","location":"Demo only",
         "rates":{"concrete":{"m3":100}},"labor":{"concrete":{"m3":25}}}
class PipelineTests(unittest.TestCase):
    def test_takeoff_and_phases(self):
        r=pipeline.build(MODEL,CATALOG)
        self.assertEqual(r["status"],"ESTIMATE_ONLY")
        self.assertEqual(r["total_usd"],1350)
        self.assertFalse(r["gatekeeper_approved"])
        self.assertEqual(r["phases"][0]["components"],["slab"])
    def test_missing_price_blocks(self):
        self.assertEqual(pipeline.build(MODEL,{**CATALOG,"rates":{}})["status"],"BLOCKED")
    def test_duplicate_blocks(self):
        m={**MODEL,"components":MODEL["components"]*2}
        self.assertEqual(pipeline.build(m,CATALOG)["status"],"BLOCKED")
    def test_unverified_gatekeeper_cannot_approve(self):
        r=pipeline.build(MODEL,CATALOG,gatekeeper={"approved":True})
        self.assertEqual(r["status"],"BLOCKED")
        self.assertFalse(r["gatekeeper_approved"])
    def test_exports(self):
        with tempfile.TemporaryDirectory() as d:
            pipeline.export(pipeline.build(MODEL,CATALOG),d)
            self.assertTrue((Path(d)/"takeoff.csv").exists())
            self.assertEqual(json.loads((Path(d)/"titan-handoff.json").read_text())["mode"],"REVIEW_ONLY")
    def test_obj_preview(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"model.obj"
            f.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
            self.assertEqual(len(pipeline.obj_preview(f)["faces"]),1)
if __name__=="__main__":unittest.main()
