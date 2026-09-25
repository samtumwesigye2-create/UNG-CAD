// DRACO-Mini electronics cartridge — connector-aligned revision
// USB-C cutouts are derived from the electronics mounting datum, not cosmetic shell positions.
pi_zero_x = 65;
pi_zero_y = 30;
fit_clearance = 0.35;
tray_x=72; tray_y=48; tray_z=12; wall=2.4;
pi_clear_x=pi_zero_x+2*fit_clearance; pi_clear_y=pi_zero_y+2*fit_clearance;

// Connector datums (mm), relative to cartridge center.
// Keep these parameters tied to the measured board/adapter connector centerlines.
usb_c_power_x = -22;
usb_c_data_x  =  22;
usb_c_center_z = 0;
usb_c_open_w = 10.0;
usb_c_open_h = 4.5;
usb_c_corner_r = 2.25;
connector_clearance = 0.35;
rear_wall_y = tray_y/2;

// Dedicated internal zones keep the power and data hardware directly behind their ports.
power_zone_x = -22; power_zone_y = 10; power_zone_w = 22; power_zone_d = 18;
data_zone_x  =  22; data_zone_y  = 10; data_zone_w  = 22; data_zone_d  = 18;
post_d = 3.2; post_h = 4;
// Three front sensor harness lanes line up with the redesigned shell bays.
sensor_lane_x = [-29,0,29];
sensor_lane_w = 7; sensor_lane_d = 20; sensor_lane_h = 5;
strain_post_d=3; strain_post_h=5;

module snap_tab(){ cube([8,2.2,4],center=true); }
module rounded_usb_c_cutout(w=usb_c_open_w+2*connector_clearance,h=usb_c_open_h+2*connector_clearance,depth=wall+3){
    hull(){
        for(x=[-w/2+usb_c_corner_r,w/2-usb_c_corner_r])
            for(z=[-h/2+usb_c_corner_r,h/2-usb_c_corner_r])
                translate([x,0,z]) rotate([90,0,0]) cylinder(r=usb_c_corner_r,h=depth,center=true,$fn=28);
    }
}
module zone_posts(cx,cy,w,d){
    for(x=[cx-w/2+3,cx+w/2-3]) for(y=[cy-d/2+3,cy+d/2-3])
        translate([x,y,-tray_z/2+wall+post_h/2]) cylinder(d=post_d,h=post_h,center=true,$fn=24);
}
module sensor_harness_guides(){
    // Open guide pairs route each sensor harness independently into the cartridge.
    for(cx=sensor_lane_x){
        for(dx=[-sensor_lane_w/2-1.5,sensor_lane_w/2+1.5])
            translate([cx+dx,-tray_y/2+11,-tray_z/2+wall+2.5])
                cube([1.8,sensor_lane_d,strain_post_h],center=true);
        // Strain-relief posts provide a tie point before the compute/power zones.
        translate([cx,-tray_y/2+20,-tray_z/2+wall+strain_post_h/2])
            cylinder(d=strain_post_d,h=strain_post_h,center=true,$fn=24);
    }
}
module electronics_cartridge(){
    difference(){
        cube([tray_x,tray_y,tray_z],center=true);
        // Main compute cavity.
        translate([0,-5,wall]) cube([pi_clear_x,pi_clear_y,tray_z],center=true);
        // Cable-routing corridor between electronics and connector wall.
        translate([0,19,wall]) cube([48,8,tray_z],center=true);
        // USB-C power and data openings, physically aligned to their internal zones.
        translate([usb_c_power_x,rear_wall_y,usb_c_center_z]) rounded_usb_c_cutout();
        translate([usb_c_data_x,rear_wall_y,usb_c_center_z]) rounded_usb_c_cutout();
    }
    // Mounting references for power/data interface boards.
    zone_posts(power_zone_x,power_zone_y,power_zone_w,power_zone_d);
    zone_posts(data_zone_x,data_zone_y,data_zone_w,data_zone_d);
    sensor_harness_guides();
    translate([-22,tray_y/2+1.1,2]) snap_tab();
    translate([22,tray_y/2+1.1,2]) snap_tab();
}
electronics_cartridge();
