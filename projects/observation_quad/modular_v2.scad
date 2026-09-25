// UNG-CAD Modular Observation Quad V2
// Optimized for FlashForge Adventurer 5M; max printed piece <=215 mm.
// Three reusable printed part types: center plate, arm, guard.
$fn=40;
part=0; // 0 layout, 1 center plate, 2 arm, 3 guard

plate=72; plate_t=4;
arm_len=62; arm_w=14; arm_t=5;
tab_w=12; tab_len=12;
motor_pad=28;
motor_mount=9; motor_screw=2.2;
guard_od=92; guard_wall=3; guard_t=4;

module center_plate(){
 difference(){
  union(){
   cube([plate,plate,plate_t],center=true);
   // four simple arm sockets
   for(a=[0,90,180,270]) rotate([0,0,a])
    translate([plate/2+tab_len/2-1,0,0])
      cube([tab_len,tab_w+4,plate_t],center=true);
  }
  // 20x20 FC holes
  for(x=[-10,10],y=[-10,10]) translate([x,y,-5]) cylinder(d=3.4,h=10);
  // battery strap slots
  for(y=[-22,22]) translate([-14,y-2,-5]) cube([28,4,10]);
  // arm retention holes
  for(a=[0,90,180,270]) rotate([0,0,a])
    translate([plate/2+5,0,-5]) cylinder(d=3.4,h=10);
 }
}

module arm(){
 difference(){
  union(){
   translate([0,-arm_w/2,0]) cube([arm_len,arm_w,arm_t]);
   translate([arm_len,0,0]) cylinder(d=motor_pad,h=arm_t);
  }
  // center plate retention M3
  translate([5,0,-1]) cylinder(d=3.4,h=arm_t+2);
  // 1404 motor: 9x9 M2
  translate([arm_len,0,-1])
   for(x=[-motor_mount/2,motor_mount/2],y=[-motor_mount/2,motor_mount/2])
    translate([x,y,0]) cylinder(d=motor_screw,h=arm_t+2);
  translate([arm_len,0,-1]) cylinder(d=4,h=arm_t+2);
 }
}

module guard(){
 difference(){
  cylinder(d=guard_od,h=guard_t);
  translate([0,0,-1]) cylinder(d=guard_od-2*guard_wall,h=guard_t+2);
 }
 // two sacrificial mounting ears
 for(a=[0,180]) rotate([0,0,a]) translate([guard_od/2-2,0,0])
   cube([10,8,guard_t],center=true);
}

if(part==1) center_plate();
else if(part==2) arm();
else if(part==3) guard();
else {
 translate([-55,0,0]) center_plate();
 translate([10,-30,0]) arm();
 translate([65,45,0]) guard();
}
