// UNG-DRACO hardware fit coupon — Rev C
// PRINT THIS BEFORE ANOTHER FULL ENCLOSURE.
// Replace the placeholder plug/fan dimensions below with physical measurements
// recorded in BUILD_HANDOFF.md. Do not release the full base until this coupon passes.
$fn=36;
wall=2.8;
clearance=0.50;

// ACTUAL-PLUG ENVELOPE PARAMETERS (placeholders until measured)
rj45_plug_w=14.0; rj45_plug_h=10.0;      // includes insertion body; enlarge for boot as measured
usb_data_w=12.0; usb_data_h=7.0;          // plug body/strain-relief envelope
usb_power_w=12.0; usb_power_h=7.0;
fan_screw_pitch=32.0;                     // placeholder; measure actual fan
fan_screw_d=3.4;
fan_frame=40.0;
coupon_h=16;

module rounded_rect_cutout(w,h,d,r=2){
    hull() for(x=[-w/2+r,w/2-r]) for(z=[-h/2+r,h/2-r])
        translate([x,0,z]) rotate([90,0,0]) cylinder(r=r,h=d,center=true);
}

module port_block(label_w=24){
    cube([label_w,wall,coupon_h],center=true);
}

module rj45_test(){
    difference(){
        port_block(26);
        translate([0,0,0]) cube([rj45_plug_w+2*clearance,wall+4,rj45_plug_h+2*clearance],center=true);
        // latch/finger relief above plug
        translate([0,0,(rj45_plug_h+2*clearance)/2+2.5])
            cube([10,wall+4,5],center=true);
    }
}

module usb_test(w,h){
    difference(){
        port_block(22);
        rounded_rect_cutout(w+2*clearance,h+2*clearance,wall+4,min((h+2*clearance)/2,2.5));
    }
}

module fan_corner_test(){
    // Two-hole representative fan rail verifies frame edge + screw pitch.
    difference(){
        cube([fan_frame+8,12,8],center=true);
        for(x=[-fan_screw_pitch/2,fan_screw_pitch/2])
            translate([x,0,0]) cylinder(d=fan_screw_d,h=12,center=true);
    }
    // Pocket datum lip: actual fan frame must sit flat against this edge.
    translate([0,-8,-2]) cube([fan_frame+2*clearance,4,4],center=true);
}

module interlock_test(){
    rail_w=10; rail_h=4; len=30;
    cube([len,rail_w,rail_h]);
    translate([0,rail_w+6,0])
    difference(){
        cube([len,rail_w+2*wall+2*clearance,rail_h+2*wall]);
        translate([0,wall,wall]) cube([len+1,rail_w+2*clearance,rail_h+wall]);
    }
}

// Four required validations on one small print.
translate([-42,0,0]) rj45_test();
translate([-14,0,0]) usb_test(usb_data_w,usb_data_h);
translate([14,0,0]) usb_test(usb_power_w,usb_power_h);
translate([52,0,0]) fan_corner_test();
translate([-15,24,-4]) interlock_test();
