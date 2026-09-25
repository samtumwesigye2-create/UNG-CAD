// DRACO serviceable sensor insert — positive retention revision
// Sized from the existing verified camera envelope; reusable as the center RGB bay insert.
camera_x = 25;
camera_y = 24;
camera_z = 11.5;
fit_clearance = 0.35;
frame=3;
insert_x=camera_x+2*frame+2*fit_clearance;
insert_y=camera_y+2*frame+2*fit_clearance;
insert_z=camera_z+frame;
lens_d=18;
lip=1.4;
tab_w=5;
tab_t=1.6;
tab_h=4;
cable_w=7;
cable_h=5;

module retention_tabs(){
    // Flexible side tabs prevent the module from backing out of the insert.
    for(s=[-1,1])
        translate([s*(camera_x/2+fit_clearance+tab_t/2),2,0])
            cube([tab_t,tab_h,tab_w],center=true);
}
module camera_insert(){
    difference(){
        cube([insert_x,insert_z,insert_y],center=true);
        // Sensor body pocket.
        cube([camera_x+2*fit_clearance,camera_z+fit_clearance,camera_y+2*fit_clearance],center=true);
        // Protected optical opening.
        translate([0,-insert_z/2,0]) rotate([90,0,0])
            cylinder(d=lens_d,h=frame*4,center=true,$fn=64);
        // Rear cable exit aligned to the shell/cartridge harness lane.
        translate([0,insert_z/2,0])
            cube([cable_w,frame*4,cable_h],center=true);
    }
    // Front stop lip keeps the board from moving toward the aperture.
    translate([0,-insert_z/2+lip/2,insert_y/2-frame/2])
        cube([camera_x+2,lip,frame],center=true);
    retention_tabs();
}
camera_insert();
