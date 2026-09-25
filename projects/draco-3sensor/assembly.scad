// DRACO 3-Sensor five-part manufacturing model
// Target envelope: 100 mm base diameter, 90 x 90 mm head, ~150 mm total height.
// IMPORTANT: sensor tray dimensions remain explicit parameters until measured hardware is verified.
// Parts: 1 base housing, 2 head rear shell, 3 front faceplate, 4 left cover, 5 right cover.

$fn=72;
fit=0.40;
wall=2.4;

module rounded_box(size=[90,60,90],r=10){
 hull() for(x=[-size[0]/2+r,size[0]/2-r]) for(y=[-size[1]/2+r,size[1]/2-r]) for(z=[r,size[2]-r])
   translate([x,y,z]) sphere(r=r);
}

module usb_c_slot(){ hull(){translate([-5,0,0]) cylinder(h=wall*4,r=2.2,center=true);translate([5,0,0]) cylinder(h=wall*4,r=2.2,center=true);} }
module ethernet_slot(){ cube([16.5,wall*4,14.5],center=true); }

module base_housing(){
 difference(){
  cylinder(h=60,d=100);
  translate([0,0,3]) cylinder(h=60,d=94);
  // rear power, data and Ethernet openings
  translate([-24,-49,25]) rotate([90,0,0]) usb_c_slot();
  translate([0,-49,25]) rotate([90,0,0]) usb_c_slot();
  translate([27,-49,25]) rotate([90,0,0]) ethernet_slot();
 }
 // simple controller/power/fan mounting rails; exact hole pattern comes from verified twins
 for(x=[-30,30]) translate([x,0,3]) cube([3,55,8]);
}

module head_rear_shell(){
 difference(){
  rounded_box([90,58,90],12);
  translate([0,-2,3]) rounded_box([84,56,86],10);
  // open front for faceplate + trays
  translate([0,-31,45]) cube([72,12,78],center=true);
 }
 // three simple tray support rails, no invented board-hole pattern
 for(z=[68,45,22]) for(x=[-28,28]) translate([x,-27,z]) cube([4,10,5],center=true);
}

module front_faceplate(){
 difference(){
  hull(){for(x=[-31,31]) for(z=[12,78]) translate([x,0,z]) rotate([90,0,0]) cylinder(h=3,r=10,center=true);}
  // openings deliberately parameterized; replace with verified hardware dimensions before release
  translate([0,0,70]) cube([24,8,22],center=true); // AMG8833 window zone
  translate([0,0,45]) rotate([90,0,0]) cylinder(h=8,d=18,center=true); // Camera Module 3 lens
  translate([0,0,20]) rotate([90,0,0]) cylinder(h=8,d=24,center=true); // C4001 sensing aperture
 }
}

module side_cover(side=1){
 difference(){
  intersection(){rounded_box([90,60,90],12);translate([side*34,0,45]) cube([22,70,100],center=true);}
  for(z=[25:8:57]) translate([side*43,0,z]) cube([12,28,3],center=true);
 }
}

module sensor_tray(width,depth,height,aperture_d=0,aperture_w=0,aperture_h=0){
 // Simple removable U-tray. Dimensions are supplied by a verified component twin.
 difference(){
  cube([width+2*fit+4,depth+2*fit+4,height+3],center=true);
  translate([0,0,2]) cube([width+2*fit,depth+2*fit,height+4],center=true);
  if(aperture_d>0) rotate([90,0,0]) cylinder(h=depth+12,d=aperture_d,center=true);
  if(aperture_w>0&&aperture_h>0) cube([aperture_w,depth+12,aperture_h],center=true);
 }
 // four corner retainers; no fabricated screw-hole coordinates
 for(x=[-width/2,width/2]) for(z=[-height/2,height/2])
   translate([x,0,z]) cube([2.2,depth+2*fit+2,2.2],center=true);
}

// Camera Module 3 NoIR tray.
// PCB envelope intentionally remains configurable until its exact owned-board dimensions are verified.
// The lens is centered on the optical axis; FFC exits rearward into the head cable channel.
camera_pcb_w=25; // provisional envelope only — UNVERIFIED
camera_pcb_h=24; // provisional envelope only — UNVERIFIED
camera_pcb_d=2;  // provisional envelope only — UNVERIFIED
camera_lens_clearance_d=18;
module camera_module3_noir_tray(){
 sensor_tray(camera_pcb_w,camera_pcb_d+4,camera_pcb_h,camera_lens_clearance_d);
 // rear FFC cable exit
 translate([0,4,-camera_pcb_h/2+4]) cube([14,8,4],center=true);
}

// AMG8833 tray profile based on Adafruit breakout envelope 25.6 x 25.3 x 6.0 mm.
// This is valid ONLY for the Adafruit-style breakout; another AMG8833 carrier must be re-verified.
amg_pcb_w=25.6; amg_pcb_h=25.3; amg_pcb_d=6.0;
module amg8833_tray(){
 sensor_tray(amg_pcb_w,amg_pcb_d+4,amg_pcb_h,0,18,18);
}

// C4001 comes in multiple carrier versions. DFRobot SEN0609 is 26 x 30 mm;
// Gravity SEN0610 is 22 x 30 mm. Select the actual owned carrier before manufacturing.
c4001_variant="UNVERIFIED"; // "SEN0609" or "SEN0610"
module c4001_tray(){
 if(c4001_variant=="SEN0609") sensor_tray(26,8,30,22);
 else if(c4001_variant=="SEN0610") sensor_tray(22,8,30,20);
 else echo("BLOCKED: select verified C4001 carrier SEN0609 or SEN0610 before manufacturing export");
}

// Locked vertical tray stations in the 90 mm head.
thermal_z=68;
camera_z=45;
radar_z=22;
tray_y=-25;

// Dedicated rear cable race: sensor leads/FFC leave each tray rearward,
// then turn into one protected vertical channel instead of crossing the boards.
module rear_cable_race(){
 translate([31,10,45]) cube([6,10,70],center=true);
 for(z=[thermal_z,camera_z,radar_z])
   translate([16,-8,z]) cube([30,6,5],center=true);
}

// Three independent removable trays. No stacked sensor PCBs.
module installed_sensor_trays(){
 translate([0,tray_y,thermal_z]) amg8833_tray();
 translate([0,tray_y,camera_z]) camera_module3_noir_tray();
 translate([0,tray_y,radar_z]) c4001_tray();
}

// Head manufacturing subassembly: shell + tray stations + cable race.
// C4001 remains fail-closed until c4001_variant matches the owned board.
module head_internal_layout(){
 head_rear_shell();
 installed_sensor_trays();
 rear_cable_race();
}

// Preview assembly. Manufacturing exports call individual modules.
module assembly(){
 color("gainsboro") base_housing();
 translate([0,0,60]) color("white") head_rear_shell();
 translate([0,-31,60]) color("white") front_faceplate();
 translate([0,0,60]) color("whitesmoke") side_cover(-1);
 translate([0,0,60]) color("whitesmoke") side_cover(1);
}

assembly();
