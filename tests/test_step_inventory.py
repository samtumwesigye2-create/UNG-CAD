import tempfile
import unittest
from pathlib import Path
from cad_core.step_inventory import inventory_step

class StepInventoryTests(unittest.TestCase):
    def test_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.step"
            p.write_text("ISO-10303-21;\nHEADER;ENDSEC;\nDATA;\n#1=ADVANCED_FACE('a',(),.T.);\n#2=CLOSED_SHELL('b',());\nENDSEC;\nEND-ISO-10303-21;")
            r=inventory_step(p)
            self.assertEqual(r["advanced_face_count"],1)
            self.assertEqual(r["status"],"inventory_only")
    def test_duplicate_entity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.stp"
            p.write_text("ISO-10303-21;\n#1=ADVANCED_FACE();\n#1=CLOSED_SHELL();\nEND-ISO-10303-21;")
            with self.assertRaises(ValueError):inventory_step(p)
if __name__=="__main__":
    unittest.main()
