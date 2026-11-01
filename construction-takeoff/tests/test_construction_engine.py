import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("construction_engine", Path(__file__).resolve().parents[1] / "construction_engine.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

def sample():
    return {"schema_version":"1.0","project_id":"demo","units":{"length":"m","currency":"USD"},
            "elements":[{"id":"slab","system":"concrete","quantity":10,"unit":"m3"}],
            "rates":[{"system":"concrete","unit":"m3","material_rate":100,"labor_rate":20,"equipment_rate":5,"waste_fraction":0.1}],
            "tasks":[{"id":"foundation","name":"Foundation","element_ids":["slab"],"start":"2026-11-01","finish":"2026-11-02"}]}

class ConstructionTests(unittest.TestCase):
    def test_total(self):
        r=engine.analyze(sample())
        self.assertEqual(r["costs"]["total"],1350)
        self.assertEqual(r["schedule"][0]["duration_days"],2)
    def test_missing_rate(self):
        p=sample();p["rates"]=[]
        with self.assertRaises(ValueError):engine.analyze(p)
    def test_negative_quantity(self):
        p=sample();p["elements"][0]["quantity"]=-1
        with self.assertRaises(ValueError):engine.analyze(p)
    def test_duplicate_id(self):
        p=sample();p["elements"].append(dict(p["elements"][0]))
        with self.assertRaises(ValueError):engine.analyze(p)
    def test_dependency_overlap(self):
        p=sample();p["tasks"].append({"id":"next","name":"Next","element_ids":[],"dependencies":["foundation"],"start":"2026-11-02","finish":"2026-11-03"})
        with self.assertRaises(ValueError):engine.analyze(p)

if __name__=="__main__":
    unittest.main()
