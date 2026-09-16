overall_x = 110;
overall_y = 110;
overall_z = 135;
fit_clearance = 0.35;
shell_x=96; shell_y=82; shell_z=78; wall=2.8; aperture_d=18;
module rounded_box(size=[10,10,10],r=3){ minkowski(){ cube([size[0]-2*r,size[1]-2*r,size[2]-2*r],center=true); sphere(r=r,$fn=36); } }
module sensor_shell(){ difference(){ rounded_box([shell_x,shell_y,shell_z],9); rounded_box([shell_x-2*wall,shell_y-2*wall,shell_z-2*wall],7); translate([0,-shell_y/2,4]) rotate([90,0,0]) cylinder(d=aperture_d,h=wall*4,center=true,$fn=64); translate([0,shell_y/2,0]) cube([68,wall*4,44],center=true); } }
sensor_shell();
