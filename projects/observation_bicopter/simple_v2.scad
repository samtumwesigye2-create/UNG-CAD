// UNG Simple Bicopter V2 — AD5M-oriented
// 3 unique printable designs; flat printing; no support-dependent geometry.
// Observation/tracking platform only.
$fn=40;
part=0; // 0 layout, 1 body, 2 arm, 3 guard

body_x=80; body_y=60; body_t=5;
arm_l=92; arm_w=18; arm_t=6;
motor_pad=30; motor_mount=9; motor_screw=2.2;
servo_x=24; servo_y=13; // intentionally generic envelope; verify selected servo
guard_od=92; guard_wall=3; guard_t=4;

module body(){
 difference(){
  cube([body_x,body_y,body_t],center=true);
  for(x=[-10,10],y=[-10,10]) translate([x,y,-5]) cylinder(d=3.4,h=10);
  for(x=[-25,25]) translate([x-2,-18,-5]) cube([4,36,10]);
  for(x=[-body_x/2+7,body_x/2-7]) translate([x,0,-5]) cylinder(d=3.4,h=10);
 }
}

module arm(){
 difference(){
  union(){
   translate([0,-arm_w/2,0]) cube([arm_l,arm_w,arm_t]);
   translate([arm_l,0,0]) cylinder(d=motor_pad,h=arm_t);
  }
  translate([7,0,-1]) cylinder(d=3.4,h=arm_t+2);
  translate([arm_l,0,-1]) cylinder(d=4,h=arm_t+2);
  translate([arm_l,0,-1])
   for(x=[-motor_mount/2,motor_mount/2],y=[-motor_mount/2,motor_mount/2])
    translate([x,y,0]) cylinder(d=motor_screw,h=arm_t+2);
  // generic servo pocket near motor end; freeze after servo selection
  translate([arm_l-32,-servo_y/2,-1]) cube([servo_x,servo_y,arm_t+2]);
 }
}

module guard(){
 difference(){
  cylinder(d=guard_od,h=guard_t);
  translate([0,0,-1]) cylinder(d=guard_od-2*guard_wall,h=guard_t+2);
  // open inner half for simple C guard
  translate([-guard_od,-guard_od/2-1,-1]) cube([guard_od,guard_od+2,guard_t+2]);
 }
 translate([0,-4,0]) cube([12,8,guard_t]);
}

if(part==1) body();
else if(part==2) arm();
else if(part==3) guard();
else {
 translate([-55,0,0]) body();
 translate([0,-35,0]) arm();
 translate([55,45,0]) guard();
}
