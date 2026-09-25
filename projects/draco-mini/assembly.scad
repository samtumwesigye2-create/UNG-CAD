// DRACO-Mini integrated three-sensor assembly
use <parts/rotating_base.scad>
use <parts/pan_tilt_cradle.scad>
use <parts/sensor_shell.scad>
use <parts/camera_insert.scad>
use <parts/electronics_cartridge.scad>

overall_x=110; overall_y=110; overall_z=135; fit_clearance=0.35;
base_z=0; cradle_z=18; shell_z=52;
shell_y=82; bay_pitch=29;
insert_front_y=-shell_y/2+3.2;
electronics_cartridge_y=28.8;

// Assembly datums shared with the redesigned shell.
sensor_x=[-bay_pitch,0,bay_pitch];
sensor_z=shell_z-20;

module sensor_insert_at(cx){
    // Insert axis points toward the protected front apertures.
    translate([cx,insert_front_y,sensor_z])
        rotate([90,0,0]) camera_insert();
}

module draco_mini_assembly(){
    translate([0,0,base_z]) rotating_base();
    translate([0,0,cradle_z]) cradle();
    translate([0,0,shell_z]) sensor_shell();

    // Three individually serviceable inserts align with the shell bays:
    // left sensor / center RGB camera / right sensor.
    for(cx=sensor_x) sensor_insert_at(cx);

    // Rear slide-out electronics cartridge receives all three harness lanes.
    translate([0,electronics_cartridge_y,shell_z-5])
        electronics_cartridge();
}
draco_mini_assembly();
