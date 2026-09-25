// UNG Simple Bicopter V2 — AD5M-oriented
// 3 unique printable designs; flat printing; no support-dependent geometry.
// Observation/tracking platform only.
$fn=40;
part=0; // 0 layout, 1 body, 2 arm, 3 guard

body_x=80; body_y=60; body_t=5;
arm_l=92; arm_w=18; arm_t=6;
motor_pad=30; motor_mount=9; motor_screw=2.2;
servo_x=23.6; servo_y=12.6; // ES09MD body + ~0.3 mm/side print clearance
servo_h=25.1; // reference envelope; arm pocket is through-cut
horn_clear_d=18; // conservative clearance envelope around servo output
link_hole=2.2; // M2 linkage clearance
guard_od=92; guard_wall=3; guard_t=4;
mount_screw=3.4; // M3 clearance
body_mount_x=30; body_mount_y=18; // matching body/arm two-screw interface
guard_mount_pitch=12; // two M3 screws prevent guard rotation

module body(){
 difference(){
  union(){
   cube([body_x,body_y,body_t],center=true);
   // raised front sensor deck gives the camera/sensor module a defined seat
   translate([0,-body_y/2+8,body_t/2+1.5])
    cube([34,14,3],center=true);
   // raised GPS deck at rear, away from the power area
   translate([0,body_y/2-9,body_t/2+1.5])
    cube([28,16,3],center=true);
  }

  // CENTER: 20x20 flight-controller mounting pattern
  for(x=[-10,10],y=[-10,10])
   translate([x,y,-body_t]) cylinder(d=3.4,h=body_t*3);

  // FRONT SENSOR/CAMERA: 24x10 mm M2 mounting pattern
  for(x=[-12,12],y=[-5,5])
   translate([x,-body_y/2+8+y,-body_t])
    cylinder(d=2.4,h=body_t*3+4);

  // REAR GPS/SENSOR: 20x10 mm M2 mounting pattern
  for(x=[-10,10],y=[-5,5])
   translate([x,body_y/2-9+y,-body_t])
    cylinder(d=2.4,h=body_t*3+4);

  // POWER/BATTERY: two strap slots kept clear of sensor decks
  for(x=[-25,25])
   translate([x-2,-10,-body_t]) cube([4,20,body_t*3]);

  // ARM INTERFACES: two M3 holes on each side
  for(side=[-1,1], y=[-body_mount_y/2,body_mount_y/2])
   translate([side*body_mount_x,y,-body_t])
    cylinder(d=mount_screw,h=body_t*3);

  // cable pass-throughs: front sensor and rear GPS/power wiring
  translate([0,-17,-body_t]) cube([10,5,body_t*3],center=true);
  translate([0,17,-body_t]) cube([10,5,body_t*3],center=true);
 }
}

module arm(){
 difference(){
  linear_extrude(height=arm_t)
   union(){
    translate([0,-arm_w/2]) square([arm_l,arm_w]);
    translate([arm_l,0]) circle(d=motor_pad);
    // widened body-end mounting lug
    translate([0,-12]) square([20,24]);
    // guard mounting ear outside propeller center
    translate([arm_l-8,-18]) square([16,12]);
   }

  // two M3 body attachment holes matching the body interface
  for(y=[-body_mount_y/2,body_mount_y/2])
   translate([10,y,-1]) cylinder(d=mount_screw,h=arm_t+2);

  // motor interface
  translate([arm_l,0,-1]) cylinder(d=4,h=arm_t+2);
  for(x=[-motor_mount/2,motor_mount/2],y=[-motor_mount/2,motor_mount/2])
   translate([arm_l+x,y,-1]) cylinder(d=motor_screw,h=arm_t+2);

  // servo pocket
  translate([arm_l-40,-servo_y/2,-1]) cube([servo_x,servo_y,arm_t+2]);
  translate([arm_l-18,0,-1]) cylinder(d=horn_clear_d,h=arm_t+2);
  translate([arm_l-7,0,-1]) cylinder(d=link_hole,h=arm_t+2);

  // two matching M3 holes for guard attachment
  for(x=[arm_l-guard_mount_pitch/2,arm_l+guard_mount_pitch/2])
   translate([x,-12,-1]) cylinder(d=mount_screw,h=arm_t+2);
 }
}

module guard(){
 difference(){
  union(){
   // C-shaped outer guard
   difference(){
    cylinder(d=guard_od,h=guard_t);
    translate([0,0,-1]) cylinder(d=guard_od-2*guard_wall,h=guard_t+2);
    translate([-guard_od,-guard_od/2-1,-1])
     cube([guard_od,guard_od+2,guard_t+2]);
   }
   // compact mounting tab at the arm side; avoids a bridge through prop sweep
   translate([-guard_mount_pitch/2-6,-guard_od/2,0])
    cube([guard_mount_pitch+12,16,guard_t]);
  }
  // two M3 guard mounting holes
  for(x=[-guard_mount_pitch/2,guard_mount_pitch/2])
   translate([x,-guard_od/2+8,-1]) cylinder(d=mount_screw,h=guard_t+2);
 }
}

if(part==1) body();
else if(part==2) arm();
else if(part==3) guard();
else {
 translate([-55,0,0]) body();
 translate([0,-35,0]) arm();
 translate([55,45,0]) guard();
}
