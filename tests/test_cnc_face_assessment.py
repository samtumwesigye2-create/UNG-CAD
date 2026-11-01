import unittest
from cad_core.cnc_face_assessment import Face, assess_faces

class CNCFaceAssessmentTests(unittest.TestCase):
    def test_hole_candidate_requires_review(self):
        result=assess_faces([Face("hole1","cylindrical",diameter_mm=8,depth_mm=3)],4,10)
        self.assertEqual(result[0]["operation"],"hole_candidate")
        self.assertEqual(result[0]["status"],"review_required")
    def test_small_hole_blocked(self):
        result=assess_faces([Face("hole1","cylindrical",diameter_mm=2,depth_mm=3)],4,10)
        self.assertEqual(result[0]["status"],"blocked")
    def test_stock_depth_blocked(self):
        result=assess_faces([Face("p1","planar_pocket",width_mm=20,height_mm=15,depth_mm=12)],4,10)
        self.assertEqual(result[0]["status"],"blocked")
    def test_duplicate_faces_rejected(self):
        with self.assertRaises(ValueError):
            assess_faces([Face("a","unknown"),Face("a","unknown")],4,10)
if __name__=="__main__":
    unittest.main()
