// UNG-CAD Compact Observation Quad — printable frame concept
// Safety-oriented platform: observation/tracking only; no interception payload.
// Overall motor span: 180 mm. Individual printed frame <215 mm.
$fn=48;
span=180;
plate_d=72;
plate_t=4;
arm_w=12;
motor_pad_d=28;
motor_hole=9; // generic center clearance; adapt to selected motor before printing

module arm(a=45){
 rotate([0,0,a]) hull(){
  translate([0,-arm_w/2,0]) cube([plate_d/2,arm_w,plate_t]);
  translate([span/2-14,0,0]) cylinder(d=motor_pad_d,h=plate_t);
 }
}
module motor_cut(a=45){
 rotate([0,0,a]) translate([span/2-14,0,-1]) cylinder(d=motor_hole,h=plate_t+2);
}
module frame(){
 difference(){
  union(){
   cylinder(d=plate_d,h=plate_t);
   for(a=[45,135,225,315]) arm(a);
  }
  for(a=[45,135,225,315]) motor_cut(a);
  // flight-controller pattern: 20x20 mm, M3 clearance
  for(x=[-10,10],y=[-10,10]) translate([x,y,-1]) cylinder(d=3.4,h=plate_t+2);
  // strap slots
  for(y=[-20,20]) translate([-13,y-2,-1]) cube([26,4,plate_t+2]);
 }
}
module guard(){
 difference(){
  cylinder(d=plate_d,h=3);
  translate([0,0,-1]) cylinder(d=plate_d-6,h=5);
 }
}
part=1; // 1 frame, 2 optional center bumper ring
if(part==1) frame();
if(part==2) guard();
