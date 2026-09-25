// DRACO sensor shell — organized three-bay sensor architecture
// Exterior envelope preserved; internal structure now physically retains three sensor modules.
overall_x = 110;
overall_y = 110;
overall_z = 135;
fit_clearance = 0.35;
shell_x=96; shell_y=82; shell_z=78; wall=2.8;
front_y=-shell_y/2;

// Replace generic empty shell with three marked serviceable bays.
// Dimensions are deliberately parameterized so measured sensor bodies can be tuned without remodeling the shell.
bay_w=24; bay_d=22; bay_h=25; bay_gap=5;
ledge=2.4; rail=2.2; clip=1.6; cable_w=7; cable_h=5;
aperture_d=18;

module rounded_box(size=[10,10,10],r=3){
    minkowski(){ cube([size[0]-2*r,size[1]-2*r,size[2]-2*r],center=true); sphere(r=r,$fn=36); }
}
module sensor_bay(cx,label_z=0){
    // Bottom support ledge: sensor cannot fall through.
    translate([cx,-10,-shell_z/2+wall+ledge/2]) cube([bay_w+5,bay_d+5,ledge],center=true);
    // Side guide/retention rails.
    for(x=[cx-(bay_w/2+rail/2),cx+(bay_w/2+rail/2)])
        translate([x,-10,-shell_z/2+wall+bay_h/2]) cube([rail,bay_d+5,bay_h],center=true);
    // Front snap lips retain the module but remain accessible for service.
    for(x=[cx-bay_w/2+3,cx+bay_w/2-3])
        translate([x,-21,-shell_z/2+wall+bay_h-2]) cube([6,clip,4],center=true);
}
module cable_channel(cx){
    // Direct rearward cable path from each sensor pocket.
    translate([cx,7,-shell_z/2+wall+4]) cube([cable_w,30,cable_h],center=true);
}
module front_aperture(cx){
    translate([cx,front_y,0]) rotate([90,0,0]) cylinder(d=aperture_d,h=wall*4,center=true,$fn=64);
}
module sensor_shell(){
    difference(){
        rounded_box([shell_x,shell_y,shell_z],9);
        rounded_box([shell_x-2*wall,shell_y-2*wall,shell_z-2*wall],7);
        // Three protected sensor sight openings.
        for(cx=[-(bay_w+bay_gap),0,(bay_w+bay_gap)]) front_aperture(cx);
        // Rear service/electronics-cartridge interface.
        translate([0,shell_y/2,0]) cube([68,wall*4,44],center=true);
        // Cable channels remain open to the electronics cartridge.
        for(cx=[-(bay_w+bay_gap),0,(bay_w+bay_gap)]) cable_channel(cx);
        // Side ventilation, kept above the sensor support ledges.
        for(side=[-1,1]) for(z=[-12,0,12])
            translate([side*shell_x/2,8,z]) cube([wall*4,18,4],center=true);
    }
    // Dedicated retention structures: left / center / right sensor.
    for(cx=[-(bay_w+bay_gap),0,(bay_w+bay_gap)]) sensor_bay(cx);
    // Cable separators keep power/data leads out of neighboring bays.
    for(cx=[-bay_w/2-bay_gap/2,bay_w/2+bay_gap/2])
        translate([cx,6,-shell_z/2+wall+5]) cube([1.8,28,10],center=true);
}
sensor_shell();
