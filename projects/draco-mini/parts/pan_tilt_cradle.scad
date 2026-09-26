// DRACO-Mini pan/tilt cradle — connected print-ready U-frame
servo_x=22.8;
servo_y=12.2;
servo_z=28.5;
fit_clearance=0.35;

wall=3;
inner_w=74;
arm_h=58;
arm_d=10;
bridge_w=inner_w+2*arm_d;
bridge_h=5;

// Servo pocket is kept fully inside each arm so subtraction cannot split the frame.
module servo_pocket(){
    cube([
        arm_d+2,
        servo_y+2*fit_clearance,
        servo_x+2*fit_clearance
    ],center=true);
}

module cradle(){
    difference(){
        union(){
            // Bottom bridge overlaps both side arms by bridge_h for a manifold one-piece print.
            translate([0,0,bridge_h/2])
                cube([bridge_w,arm_d,bridge_h],center=true);

            translate([-(inner_w/2+arm_d/2),0,arm_h/2])
                cube([arm_d,arm_d,arm_h],center=true);

            translate([(inner_w/2+arm_d/2),0,arm_h/2])
                cube([arm_d,arm_d,arm_h],center=true);
        }

        // Servo clearances cut inward from each arm without severing the base joint.
        translate([-(inner_w/2+arm_d/2),0,30])
            servo_pocket();
        translate([(inner_w/2+arm_d/2),0,30])
            servo_pocket();
    }
}
cradle();
