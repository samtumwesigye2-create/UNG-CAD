import pytest
from cad_core.engineering_drawings import EngineeringDrawingGenerator
from cad_core.calibration_feedback import Measurement,CalibrationFeedbackEngine
def panel():return {"panel_id":"p","width_mm":100,"height_mm":80,"thickness_mm":3,"cutouts":[{"component_id":"usb","type":"usb_c","position":{"x_mm":20,"y_mm":15},"dimensions":{"width_mm":9,"height_mm":4},"clearance_mm":0.2}]}
def test_drawing_manifest():
 d=EngineeringDrawingGenerator().generate(panel());assert d["units"]=="mm" and len(d["dimensions"])>=7 and d["views"]==["top","front","right"]
def test_feedback_detects_bias_and_recommends_correction():
 e=CalibrationFeedbackEngine();r=e.analyze([Measurement("a",10,9.8),Measurement("b",20,19.8)],0.25)
 assert r["passed"] and r["mean_error_mm"]==pytest.approx(-0.2) and r["recommended_internal_delta_adjustment_mm"]==pytest.approx(0.2)
 assert e.update_internal_delta(0.15,r,max_step_mm=.1)==pytest.approx(.25)
def test_feedback_blocks_out_of_tolerance():
 assert not CalibrationFeedbackEngine().analyze([Measurement("a",10,10.5)],.2)["passed"]
