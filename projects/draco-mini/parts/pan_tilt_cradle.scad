servo_x = 22.8;
servo_y = 12.2;
servo_z = 28.5;
fit_clearance = 0.35;
wall=3; inner_w=74; arm_h=58; arm_d=10;
module servo_pocket(){ cube([servo_y+2*fit_clearance,servo_x+2*fit_clearance,servo_z+2*fit_clearance],center=true); }
module cradle(){ difference(){ union(){ cube([inner_w+2*arm_d,arm_d,wall],center=true); translate([-(inner_w/2+arm_d/2),0,arm_h/2]) cube([arm_d,arm_d,arm_h],center=true); translate([(inner_w/2+arm_d/2),0,arm_h/2]) cube([arm_d,arm_d,arm_h],center=true); } translate([-(inner_w/2+arm_d/2),0,28]) rotate([90,0,0]) servo_pocket(); translate([(inner_w/2+arm_d/2),0,28]) rotate([90,0,0]) servo_pocket(); } }
cradle();
