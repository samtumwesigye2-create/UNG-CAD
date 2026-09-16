camera_x = 25;
camera_y = 24;
camera_z = 11.5;
fit_clearance = 0.35;
frame=3; insert_x=camera_x+2*frame+2*fit_clearance; insert_y=camera_y+2*frame+2*fit_clearance; insert_z=camera_z+frame; lens_d=18;
module camera_insert(){ difference(){ cube([insert_x,insert_z,insert_y],center=true); cube([camera_x+2*fit_clearance,camera_z+fit_clearance,camera_y+2*fit_clearance],center=true); translate([0,-insert_z/2,0]) rotate([90,0,0]) cylinder(d=lens_d,h=frame*4,center=true,$fn=64); } }
camera_insert();
