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

module sensor_tray(width,depth,height,label_offset=0){
 // U-shaped tray: board rests on floor and is laterally retained; exact dimensions must come from verified twin.
 difference(){cube([width+2*fit+4,depth+2*fit+4,height+3],center=true);translate([0,0,2]) cube([width+2*fit,depth+2*fit,height+4],center=true);}
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
