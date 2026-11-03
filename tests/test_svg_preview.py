import unittest
from professional.drafting import Drawing, Point, Line, Circle, Arc, Polyline
from professional.svg_preview import render_svg

class SvgPreviewTests(unittest.TestCase):
    def test_shapes(self):
        d = Drawing()
        d.add(Line(Point(0,0),Point(5,5),'<script>'))
        d.add(Circle(Point(5,5),2))
        d.add(Arc(Point(5,5),3,0,90))
        d.add(Polyline((Point(0,0),Point(5,0),Point(5,5)),True))
        s=render_svg(d)
        for tag in ('<svg','<line','<circle','<path','<polygon'):
            self.assertIn(tag,s)
        self.assertNotIn('<script>',s)
        self.assertIn('&lt;script&gt;',s)
    def test_empty(self):
        self.assertIn('viewBox',render_svg(Drawing()))
    def test_negative_padding(self):
        with self.assertRaises(ValueError):
            render_svg(Drawing(),-1)

if __name__ == '__main__':
    unittest.main()
