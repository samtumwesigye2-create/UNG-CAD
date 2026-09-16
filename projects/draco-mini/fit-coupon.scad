// DRACO-Mini Gen-1 fit-validation coupon
// Tests the locked 0.35 mm nominal mating clearance before full enclosure printing.

clearance = 0.35;
wall = 2.4;
rail_w = 10;
rail_h = 4;
length = 35;

// Male keyed rail
module male_rail() {
    cube([length, rail_w, rail_h]);
    translate([4, rail_w, 0]) cube([8, 2, rail_h]);
}

// Female receiver coupon. Opening is expanded by the nominal fit clearance.
module female_receiver() {
    difference() {
        cube([length + 2*wall, rail_w + 2*wall + 2*clearance, rail_h + 2*wall]);
        translate([wall, wall, wall])
            cube([length, rail_w + 2*clearance, rail_h + wall]);
        translate([wall + 4, wall + rail_w + 2*clearance, wall])
            cube([8, 2 + clearance, rail_h + wall]);
    }
}

male_rail();
translate([0, 18, 0]) female_receiver();
