import unittest
from professional.parametric import Solid, Constraint, Component, Assembly, Room, FloorPlan, Connection, validate_connections
from professional.engineering import Net, Circuit, Beam, PrintProfile, PartEnvelope, manufacturing_preflight

class ProfessionalModulesTests(unittest.TestCase):
    def test_solids_and_bom(self):
        box=Solid("box",{"width":10,"depth":20,"height":30})
        self.assertEqual(box.volume_mm3(),6000)
        a=Assembly("test",[Component("P1",box,"PLA",2),Component("P1",box,"PLA",1)])
        self.assertEqual(a.bill_of_materials()[0]["quantity"],3)
        self.assertEqual(a.total_volume_mm3(),18000)
        self.assertEqual(validate_connections(a,[Connection("P1","P2","fixed")]),["Missing component: P1 or P2"])
    def test_constraints_rooms(self):
        self.assertTrue(Constraint("distance",10.001,10).satisfied())
        self.assertFalse(Constraint("distance",12,10).satisfied())
        plan=FloorPlan("home",[Room("Room",3000,4000,2500)])
        self.assertEqual(plan.gross_room_area_m2(),12)
        self.assertEqual(plan.room_schedule()[0]["volume_m3"],30)
    def test_electrical(self):
        c=Circuit([Net("power",("U1.VCC","J1.1")),Net("bad",("U1.VCC","J2.1"))])
        self.assertEqual(len(c.check()),1)
    def test_beam(self):
        b=Beam(100,10,10,5,200000)
        self.assertGreater(b.cantilever_tip_deflection_mm(),0)
        self.assertGreater(b.max_bending_stress_mpa(),0)
    def test_gate(self):
        p=PrintProfile(220,220,220,"PLA")
        self.assertEqual(manufacturing_preflight(PartEnvelope(120,100,100,"PLA",1.2),p)["status"],"PRELIMINARY_PASS")
        self.assertEqual(manufacturing_preflight(PartEnvelope(300,100,100,"PETG",0.3),p)["status"],"BLOCK")
    def test_invalid(self):
        with self.assertRaises(ValueError):
            Solid("box",{"width":-1,"depth":2,"height":3}).volume_mm3()

if __name__=="__main__":
    unittest.main()
