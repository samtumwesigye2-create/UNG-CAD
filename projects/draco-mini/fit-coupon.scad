// DRACO redesign fit-validation coupon
// Validates 0.35 mm mating clearance, 1.6 mm retention tabs and 7 x 5 mm harness path.
clearance=0.35; wall=2.4; rail_w=10; rail_h=4; length=35;
tab_t=1.6; tab_h=4; cable_w=7; cable_h=5;

module male_rail(){ cube([length,rail_w,rail_h]); translate([4,rail_w,0]) cube([8,2,rail_h]); }
module female_receiver(){ difference(){
 cube([length+2*wall,rail_w+2*wall+2*clearance,rail_h+2*wall]);
 translate([wall,wall,wall]) cube([length,rail_w+2*clearance,rail_h+wall]);
 translate([wall+4,wall+rail_w+2*clearance,wall]) cube([8,2+clearance,rail_h+wall]);
}}
module retention_test(){
 difference(){ cube([18,12,8]); translate([wall,wall,wall]) cube([18-2*wall,12,8]); }
 translate([9-tab_t/2,4,4]) cube([tab_t,tab_h,4],center=true);
}
module cable_test(){ difference(){ cube([14,12,9]); translate([3.5,-1,2]) cube([cable_w,14,cable_h]); } }
male_rail(); translate([0,18,0]) female_receiver();
translate([45,0,0]) retention_test();
translate([45,20,0]) cable_test();
