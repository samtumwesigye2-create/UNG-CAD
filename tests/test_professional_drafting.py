import unittest
from professional.drafting import Point, Line, Circle, Polyline, Drawing, length, offset_line, dxf

class DraftingTests(unittest.TestCase):
    def test_line_and_offset(self):
        line=Line(Point(0,0),Point(3,4))
        self.assertEqual(length(line),5)
        shifted=offset_line(Line(Point(0,0),Point(10,0)),2)
        self.assertEqual(shifted.start,Point(0,2))
    def test_dxf(self):
        drawing=Drawing()
        drawing.add(Line(Point(0,0),Point(10,10),"WALLS"))
        drawing.add(Circle(Point(5,5),2))
        drawing.add(Polyline((Point(0,0),Point(10,0),Point(10,10)),True))
        data=dxf(drawing)
        self.assertIn("WALLS",data)
        self.assertIn("CIRCLE",data)
        self.assertIn("EOF",data)
        self.assertEqual(drawing.bounds(),(0,0,10,10))
    def test_reject_invalid(self):
        with self.assertRaises(ValueError):
            Drawing().add(Circle(Point(0,0),-1))
        with self.assertRaises(ValueError):
            offset_line(Line(Point(0,0),Point(0,0)),2)

if __name__=="__main__":
    unittest.main()
