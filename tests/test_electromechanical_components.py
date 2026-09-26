from cad_core.electromechanical import Connection
from cad_core.electromechanical_components import *

def test_machine_requires_real_component_roles():
    m=MachineAssembly("M1",ComponentKind.MOTOR)
    assert m.validate()["issues"]==["missing stator","missing rotor","missing winding"]
    m.add(ElectromechanicalComponent("part-1",ComponentKind.STATOR,"Stator"))
    m.add(ElectromechanicalComponent("part-2",ComponentKind.ROTOR,"Rotor"))
    m.add(WindingComponent("part-3",ComponentKind.WINDING,"Winding",connection=Connection.DELTA,turns=120,resistance_ohm=1.1))
    assert m.validate()["valid"]
    assert m.by_kind("winding")[0].topology()[-1]==("L3","W3","L1")

def test_generator_mode_supported():
    assert MachineAssembly("G1",ComponentKind.GENERATOR).mode is ComponentKind.GENERATOR
