// DRACO-Mini Gen-1 assembly-fit model
// Benign compact camera/sensor enclosure assembly.

use <parts/rotating_base.scad>
use <parts/pan_tilt_cradle.scad>
use <parts/sensor_shell.scad>
use <parts/camera_insert.scad>
use <parts/electronics_cartridge.scad>

overall_x = 110;
overall_y = 110;
overall_z = 135;
fit_clearance = 0.35;

// Locked assembly reference positions (mm).
base_z = 0;
cradle_z = 18;
shell_z = 52;
camera_insert_y = -41;
electronics_cartridge_y = 29;

module draco_mini_assembly() {
    // Pan base.
    translate([0, 0, base_z]) rotating_base();

    // Tilt cradle seated on the keyed base rail.
    translate([0, 0, cradle_z]) cradle();

    // Rounded windowless sensor shell centered between cradle arms.
    translate([0, 0, shell_z]) sensor_shell();

    // Removable camera carrier aligned with the recessed front aperture.
    translate([0, camera_insert_y, shell_z + 4])
        rotate([90, 0, 0]) camera_insert();

    // Rear slide-out electronics cartridge.
    translate([0, electronics_cartridge_y, shell_z - 5])
        electronics_cartridge();
}

draco_mini_assembly();
