fit_clearance = 0.35;
overall_x = 110;
overall_y = 110;
overall_z = 135;
base_d = 96; base_h = 18; rail_w = 10; rail_h = 4;
module keyed_rail(){ cube([34,rail_w,rail_h],center=true); }
module rotating_base(){ union(){ cylinder(d=base_d,h=base_h,$fn=96); translate([0,0,base_h]) keyed_rail(); } }
rotating_base();
