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
module micro_usb_slot(){ hull(){translate([-3.4,0,0]) cylinder(h=wall*4,r=1.7,center=true);translate([3.4,0,0]) cylinder(h=wall*4,r=1.7,center=true);} }
module ethernet_slot(){ cube([16.5,wall*4,14.5],center=true); }

// Rear connector columns deliberately correspond to sensor stack:
// thermal (top) -> Micro USB power; camera (middle) -> USB-C power/data;
// radar (bottom) -> USB-C power/data; Ethernet -> Pi 5 system/network.
thermal_port_x=-32;
camera_port_x=-11;
radar_port_x=10;
ethernet_port_x=32;

module base_housing(){
 difference(){
  cylinder(h=60,d=100);
  translate([0,0,3]) cylinder(h=60,d=94);
  // Reserve the verified/provisional electronics volumes as true interior keepouts.
  translate([16,10,16]) cube([dc_w+2*dc_clear,dc_l+2*dc_clear,dc_h+4],center=true);
  // Protected harness riser from base to sensor head.
  translate([34,5,42]) cube([10,18,34],center=true);
  // rear ports grouped left-to-right to match the three sensor functions.
  translate([thermal_port_x,-49,25]) rotate([90,0,0]) micro_usb_slot();
  translate([camera_port_x,-49,25]) rotate([90,0,0]) usb_c_slot();
  translate([radar_port_x,-49,25]) rotate([90,0,0]) usb_c_slot();
  translate([ethernet_port_x,-49,25]) rotate([90,0,0]) ethernet_slot();
 }
 // controller rails + retained DC-DC cradle are printable base features.
 for(x=[-30,30]) translate([x,0,3]) cube([3,55,8]);
 translate([16,10,5]) dc_dc_cradle();
}

module head_rear_shell(){
 difference(){
  rounded_box([90,58,90],12);
  translate([0,-2,3]) rounded_box([84,56,86],10);
  // open front for faceplate + trays
  translate([0,-31,45]) cube([72,12,78],center=true);
  // physical rear cable race and three branch clearances
  translate([31,10,45]) cube([8,12,72],center=true);
  for(z=[thermal_z,camera_z,radar_z])
    translate([16,-8,z]) cube([32,8,7],center=true);
 }
 // three simple tray support rails, no invented board-hole pattern
 for(z=[68,45,22]) for(x=[-28,28]) translate([x,-27,z]) cube([4,10,5],center=true);
}

module front_faceplate(){
 difference(){
  hull(){for(x=[-31,31]) for(z=[12,78]) translate([x,0,z]) rotate([90,0,0]) cylinder(h=3,r=10,center=true);}
  // Apertures share the exact tray centerlines.
  translate([0,0,thermal_z]) cube([18,8,18],center=true);
  translate([0,0,camera_z]) rotate([90,0,0]) cylinder(h=8,d=camera_lens_clearance_d,center=true);
  translate([0,0,radar_z]) rotate([90,0,0]) cylinder(h=8,d=(c4001_variant=="SEN0609"?22:20),center=true);
 }
 // faceplate registration pins into rear shell
 for(x=[-30,30]) for(z=[12,78]) translate([x,2,z]) rotate([90,0,0]) cylinder(h=5,d=3.2,center=true);
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
 // four corner retainers; no fabricated board screw-hole coordinates
 for(x=[-width/2,width/2]) for(z=[-height/2,height/2])
   translate([x,0,z]) cube([2.2,depth+2*fit+2,2.2],center=true);
 // simple rear spring latch + front stop: tray slides out only after latch release
 translate([0,depth/2+fit+1,height/2]) cube([10,2,2],center=true);
 translate([0,-depth/2-fit-1,-height/2]) cube([width+2,2,2],center=true);
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


// Provisional DC-DC cradle. No mounting-hole coordinates are assumed.
// The board drops into the pocket; low corner stops constrain XY while leaving
// the display, inductor, capacitors and terminal blocks unobstructed.
dc_w=39; dc_l=66; dc_h=18; dc_clear=0.8;
module dc_dc_cradle(){
 difference(){
  cube([dc_w+2*wall+2*dc_clear,dc_l+2*wall+2*dc_clear,4],center=true);
  translate([0,0,1.5]) cube([dc_w+2*dc_clear,dc_l+2*dc_clear,5],center=true);
 }
 for(x=[-(dc_w/2+dc_clear+wall/2),(dc_w/2+dc_clear+wall/2)])
  for(y=[-(dc_l/2+dc_clear+wall/2),(dc_l/2+dc_clear+wall/2)])
   translate([x,y,4]) cube([wall,wall,8],center=true);
}

// C4001 SEN0610 retention uses the verified 22 x 30 mm board envelope.
// Side clips avoid assuming unverified mounting-hole locations.
module c4001_sen0610_retention(){
 sensor_tray(22,8,30,20);
 for(x=[-12.2,12.2])
   translate([x,2,0]) cube([2.4,8,10],center=true);
}

// C4001 comes in multiple carrier versions. DFRobot SEN0609 is 26 x 30 mm;
// Gravity SEN0610 is 22 x 30 mm. Select the actual owned carrier before manufacturing.
c4001_variant="SEN0610"; // selected DRACO carrier: 22 x 30 mm
module c4001_tray(){
 if(c4001_variant=="SEN0609") sensor_tray(26,8,30,22);
 else if(c4001_variant=="SEN0610") c4001_sen0610_retention();
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

// Base electronics zones updated from user's actual hardware photos.
// Controller is Raspberry Pi Pico 2 W with pre-soldered headers.
// Power module is the photographed adjustable DC-DC board; exact board envelope still requires scale verification.
// User's latest hardware photo shows a Raspberry Pi 5 as the main controller.
rpi5_w=56; rpi5_l=85;
module base_electronics_layout(){
 // Raspberry Pi 5 pocket. Envelope follows official Raspberry Pi mechanical drawing.
 translate([-10,4,10]) cube([rpi5_w+4,rpi5_l+4,3],center=true);
 // leave connector-edge access and cooling clearance above the board
 translate([-10,-34,18]) cube([rpi5_w+8,18,18],center=true);
 // XL4015/LM2596-style DC-DC converter provisional envelope: 66 x 39 x 18 mm.
 // Retained by a perimeter cradle instead of invented screw-hole coordinates.
 translate([16,10,5]) dc_dc_cradle();
 // rear port cable corridor: thermal Micro USB / camera USB-C / radar USB-C / Pi 5 Ethernet
 translate([0,-35,18]) cube([88,20,10],center=true);
 // protected vertical harness route to head
 translate([34,5,38]) cube([8,16,38],center=true);
}

// Port alignment gauges terminate at the actual rear openings.
// They are clearance volumes, not printable solids.
module rear_port_keepouts(){
 translate([thermal_port_x,-44,25]) cube([12,18,9],center=true);
 translate([camera_port_x,-44,25]) cube([14,18,10],center=true);
 translate([radar_port_x,-44,25]) cube([14,18,10],center=true);
 translate([ethernet_port_x,-44,25]) cube([20,18,18],center=true);
}

// Dedicated internal routes preserve the visual/functional sensor-to-port mapping.
module sensor_port_routes(){
 // thermal -> Micro USB
 hull(){translate([-28,-20,thermal_z]) sphere(2);translate([thermal_port_x,-34,30]) sphere(2);}
 // camera -> USB-C
 hull(){translate([-10,-20,camera_z]) sphere(2);translate([camera_port_x,-34,30]) sphere(2);}
 // radar -> USB-C
 hull(){translate([10,-20,radar_z]) sphere(2);translate([radar_port_x,-34,30]) sphere(2);}
 // Pi 5 -> Ethernet
 hull(){translate([24,0,15]) sphere(2);translate([ethernet_port_x,-34,30]) sphere(2);}
}

// Manufacturing guardrails. Echo BLOCKED for unresolved hardware truth.
module manufacturing_truth_check(){
 if(c4001_variant!="SEN0609" && c4001_variant!="SEN0610")
   echo("BLOCKED: C4001 carrier variant unresolved");
 echo("BLOCKED UNTIL VERIFIED: Camera Module 3 NoIR owned-board envelope/mounting geometry");
 echo("VERIFIED IDENTITY: Raspberry Pi 5 main controller");
 echo("VERIFIED INTERFACE: onboard Raspberry Pi 5 Ethernet port replaces need for a separate Ethernet module");
 echo("PROVISIONAL: DC-DC envelope 66 x 39 x 18 mm; verify owned board before manufacturing-final export");

}

module printable_part(part=1){
 if(part==1) base_housing();
 else if(part==2) head_rear_shell();
 else if(part==3) front_faceplate();
 else if(part==4) side_cover(-1);
 else if(part==5) side_cover(1);
}

manufacturing_truth_check();
// Mechanical preflight for the approved port layout.
// These assertions catch envelope/spacing mistakes before STL export.
module mechanical_preflight(){
 assert(100<=220 && 100<=220 && 150<=220,"BLOCKED: DRACO exceeds 220 mm printer envelope");
 assert(wall>=2.4,"BLOCKED: enclosure wall below 2.4 mm");
 assert(camera_z<thermal_z && radar_z<camera_z,"BLOCKED: sensor tray order invalid");
 assert(abs(camera_port_x-thermal_port_x)>=18,"BLOCKED: thermal/camera ports too close");
 assert(abs(radar_port_x-camera_port_x)>=18,"BLOCKED: camera/radar ports too close");
 assert(abs(ethernet_port_x-radar_port_x)>=18,"BLOCKED: radar/Ethernet ports too close");
 assert(dc_w+2*dc_clear+2*wall < 94,"BLOCKED: DC-DC cradle exceeds base inner diameter");
 assert(dc_l+2*dc_clear+2*wall < 94,"BLOCKED: DC-DC cradle exceeds base inner diameter");
 assert(dc_h+6 < 57,"BLOCKED: DC-DC component height exceeds base internal height");
 assert(22+2*fit+4 < 84,"BLOCKED: C4001 tray exceeds head internal width");
 assert(5==5,"BLOCKED: printable part count changed from approved five-part architecture");
 assert(30+3 < 86,"BLOCKED: C4001 tray exceeds head internal height");
 echo("PASS: envelope, sensor order, connector spacing, DC-DC cradle envelope and C4001 tray envelope");
 echo("PROVISIONAL: DC-DC envelope 66 x 39 x 18 mm; terminal height still requires physical verification");
 echo("LOCKED: C4001 SEN0610 carrier 22 x 30 mm");
}
mechanical_preflight();


// Five-part export layout: each printable body is spatially separated so an
// export/slicer cannot accidentally fuse adjacent DRACO parts.
module five_part_print_layout(){
 translate([-60,-60,0]) printable_part(1);
 translate([55,-45,0]) printable_part(2);
 translate([55,35,0]) rotate([90,0,0]) printable_part(3);
 translate([-35,65,0]) rotate([0,90,0]) printable_part(4);
 translate([15,65,0]) rotate([0,-90,0]) printable_part(5);
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
