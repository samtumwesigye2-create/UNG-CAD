import unittest
from cad_core.state import CADState, StateKind, StateStore
from cad_core.optimization import OptimizationProblem, GradientDescentOptimizer
from cad_core.simulation import SimulationRun

class CoreTests(unittest.TestCase):
    def test_state_isolation(self):
        store=StateStore(); observed=CADState("part-1",StateKind.OBSERVED,{"x":1},"measurement")
        store.append(observed); sim=SimulationRun("fit").step(observed,lambda v:{**v,"x":2})
        store.append(sim)
        self.assertEqual(store.latest_observed("part-1").values["x"],1)
        with self.assertRaises(ValueError): store.promote_to_observed(sim,approved_by="tester",source="test")

    def test_bounded_gradient_descent(self):
        p=OptimizationProblem(lambda x:(x["v"]-3)**2, lambda x:{"v":2*(x["v"]-3)}, {"v":(0,5)})
        r=GradientDescentOptimizer(.1,50).solve(p,{"v":0})
        self.assertAlmostEqual(r["parameters"]["v"],3,places=3)

if __name__=="__main__": unittest.main()
