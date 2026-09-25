// UNG-CAD Compact Bicopter V1
// Observation/tracking platform. Two tilting motor pods + center body.
// Optimized for AD5M; every printed part <215 mm.
$fn=48;
part=0; // 0 layout, 1 body, 2 boom, 3 tilt_pod, 4 guard

body_x=92; body_y=54; body_t=5;
boom_l=58; boom_w=16; boom_t=6;
pod_d=30; pod_t=6;
pivot_d=3.4; motor_mount=9; motor_screw=2.2;
guard_od=92; guard_wall=3; guard_t=4;

module body(){
 difference(){
  cube([body_x,body_y,body_t],center=true);
  // 20x20 FC
  for(x=[-10,10],y=[-10,10]) translate([x,y,-5]) cylinder(d=3.4,h=10);
  // battery straps
  for(x=[-24,24]) translate([x-2,-16,-5]) cube([4,32,10]);
  // left/right boom fasteners
  for(x=[-body_x/2+7,body_x/2-7]) translate([x,0,-5]) cylinder(d=3.4,h=10);
 }
}

module boom(){
 difference(){
  translate([0,-boom_w/2,0]) cube([boom_l,boom_w,boom_t]);
  translate([7,0,-1]) cylinder(d=3.4,h=boom_t+2);
  // pivot at motor end
  translate([boom_l-6,0,-1]) cylinder(d=pivot_d,h=boom_t+2);
 }
}

module tilt_pod(){
 difference(){
  cylinder(d=pod_d,h=pod_t);
  cylinder(d=4,h=pod_t+2);
  for(x=[-motor_mount/2,motor_mount/2],y=[-motor_mount/2,motor_mount/2])
    translate([x,y,-1]) cylinder(d=motor_screw,h=pod_t+2);
  translate([pod_d/2-5,0,-1]) cylinder(d=pivot_d,h=pod_t+2);
 }
 // servo/linkage ear
 translate([pod_d/2-2,-4,0]) cube([10,8,pod_t]);
}

module guard(){
 difference(){
  cylinder(d=guard_od,h=guard_t);
  translate([0,0,-1]) cylinder(d=guard_od-2*guard_wall,h=guard_t+2);
 }
}

if(part==1) body();
else if(part==2) boom();
else if(part==3) tilt_pod();
else if(part==4) guard();
else {
 translate([-70,0,0]) body();
 translate([5,-25,0]) boom();
 translate([65,-25,0]) tilt_pod();
 translate([45,50,0]) guard();
}
