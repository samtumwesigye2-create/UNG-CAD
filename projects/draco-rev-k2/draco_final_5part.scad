// UNG-DRACO FINAL 5-PART CORRECTED ARCHITECTURE
// Targets the actual problems seen in the printed prototype:
// - removes oversized spider arms
// - closes/locates the center structure
// - provides positive base/lid/chassis/front/rear attachment
// - puts PAN + TILT servos and 40 mm fan in the base
// - provides three clearly marked sensor zones with shaped seats
// - provides controlled cable pass-throughs and strain relief
// - external base ports: LAN, USB-C DATA, USB-C POWER only
//
// part_no: 0 assembly, 1 base, 2 lid, 3 chassis, 4 front, 5 rear
$fn=48;
part_no=0;
fit=0.35;
wall=3.0;

// -----------------------------
// Global envelopes (mm)
// -----------------------------
base_x=100; base_y=80; base_h=32;
lid_t=4;
head_x=92; head_y=54; head_h=58;
head_floor_z=base_h+lid_t;
corner_r=5;

// Known hardware envelopes
pi_x=65; pi_y=30;
servo_x=22.8; servo_y=12.2; servo_z=28.5;
fan=40;
cam_x=25; cam_z=24;
thermal_x=25.6; thermal_z=25.3;
radar_x=26; radar_z=30;
lidar_x=44; lidar_z=16;

// FDM helpers
boss_d=8; screw_d=3.4; screw_clear=3.6;
key_clear=0.30;
slot_w=7;

// -----------------------------
// Primitive helpers
// -----------------------------
module rounded2d(x,y,r){
  hull() for(px=[-x/2+r,x/2-r]) for(py=[-y/2+r,y/2-r]) translate([px,py]) circle(r=r);
}
module rounded_box(x,y,z,r){
  linear_extrude(z) rounded2d(x,y,r);
}
module screw_boss(h){
  difference(){ cylinder(d=boss_d,h=h); translate([0,0,-0.1]) cylinder(d=screw_d,h=h+0.2); }
}
module label_bar(txt,w=22){
  // raised identifier pad; text extrusion kept conservative for 0.20 mm layers
  translate([0,0,0.6]) linear_extrude(0.8) text(txt,size=4,halign="center",valign="center");
}

// -----------------------------
// P1 BASE — compact, no arms
// -----------------------------
module base(){
  difference(){
    union(){
      difference(){
        rounded_box(base_x,base_y,base_h,corner_r);
        translate([wall,wall,wall])
          rounded_box(base_x-2*wall,base_y-2*wall,base_h,corner_r-wall);
      }
      // four corner bosses
      for(x=[-base_x/2+9,base_x/2-9]) for(y=[-base_y/2+9,base_y/2-9])
        translate([x,y,wall]) screw_boss(base_h-wall-2);

      // PAN seat retaining rails
      for(dx=[-1,1])
        translate([dx*(servo_x/2+1.7),-8,wall+servo_z/2])
          cube([2.4,servo_y+6,servo_z+2],center=true);

      // TILT seat retaining rails
      for(dx=[-1,1])
        translate([26+dx*(servo_x/2+1.7),-8,wall+servo_z/2])
          cube([2.4,servo_y+6,servo_z+2],center=true);

      // Pi rails
      for(x=[-pi_x/2-1.5,pi_x/2+1.5])
        translate([x,18,wall+3]) cube([2.4,pi_y+4,6],center=true);

      // Fan corner posts
      for(x=[-16,16]) for(z=[-16,16])
        translate([-base_x/2+wall+3,18+x/4,base_h/2+z/4]) rotate([0,90,0])
          cylinder(d=6,h=6,center=true);
    }

    // central mechanical output + head harness pass-through
    translate([0,0,-0.1]) cylinder(d=16,h=base_h+0.2);

    // fan opening in left wall
    translate([-base_x/2,22,16]) rotate([0,90,0]) cylinder(d=36,h=wall*4,center=true);

    // USB-C POWER, USB-C DATA, LAN on front wall
    translate([-25,-base_y/2,14]) cube([11,wall*4,5.2],center=true);
    translate([0,-base_y/2,14]) cube([11,wall*4,5.2],center=true);
    translate([28,-base_y/2,14]) cube([17,wall*4,14],center=true);

    // fixed wiring trenches
    translate([-25,0,wall+2]) cube([slot_w,58,4],center=true);
    translate([0,0,wall+2]) cube([slot_w,58,4],center=true);
    translate([28,0,wall+2]) cube([slot_w,58,4],center=true);
  }

  // Labels inside base
  translate([-25,-30,wall]) label_bar("POWER");
  translate([0,-30,wall]) label_bar("DATA");
  translate([28,-30,wall]) label_bar("LAN");
  translate([0,-8,wall]) label_bar("PAN");
  translate([26,-8,wall]) label_bar("TILT");
  translate([0,18,wall]) label_bar("PI");
  translate([-39,22,wall]) rotate([0,0,90]) label_bar("FAN");
}

// -----------------------------
// P2 LID — positive attachment + keyed chassis socket
// -----------------------------
module lid(){
  difference(){
    union(){
      rounded_box(base_x,base_y,lid_t,corner_r);
      // raised locating key for chassis
      translate([0,3,lid_t]) difference(){
        rounded_box(head_x-8,head_y-10,3,4);
        translate([wall,wall,-0.1]) rounded_box(head_x-8-2*wall,head_y-10-2*wall,3.2,2);
      }
    }
    for(x=[-base_x/2+9,base_x/2-9]) for(y=[-base_y/2+9,base_y/2-9])
      translate([x,y,-0.1]) cylinder(d=screw_clear,h=lid_t+0.2);

    // central axis + controlled head-harness slot
    translate([0,0,-0.1]) cylinder(d=16,h=lid_t+3.2);
    translate([0,10,-0.1]) hull(){
      translate([-5,0]) cylinder(d=7,h=lid_t+3.2);
      translate([5,0]) cylinder(d=7,h=lid_t+3.2);
    }

    // fan exhaust grille over base fan zone
    for(y=[8:6:34]) translate([-40,y,-0.1]) cube([24,3,lid_t+0.2],center=true);
  }
}

// -----------------------------
// P3 CHASSIS — one closed structural shell
// -----------------------------
module chassis(){
  difference(){
    union(){
      // shell body
      difference(){
        translate([0,3,0]) rounded_box(head_x,head_y,head_h,6);
        translate([wall,3+wall,wall]) rounded_box(head_x-2*wall,head_y-2*wall,head_h,4);
        // front and rear open faces for dedicated plates
        translate([0,-head_y/2+3,head_h/2]) cube([head_x-8,wall*4,head_h-8],center=true);
        translate([0, head_y/2+3,head_h/2]) cube([head_x-8,wall*4,head_h-8],center=true);
      }

      // base flange, keyed to lid
      translate([0,3,0]) rounded_box(head_x-8,head_y-10,4,4);

      // three sensor-zone shelves
      for(x=[-29,0,29]) translate([x,-13,17]) cube([26,22,3],center=true);

      // rear strain-relief bridge
      translate([0,18,10]) cube([60,4,8],center=true);
    }

    // base flange central axis and harness pass-through
    translate([0,0,-0.1]) cylinder(d=16+2*key_clear,h=5);
    translate([0,10,-0.1]) cube([18,10,5],center=true);

    // front/rear M3 plate holes
    for(x=[-39,39]) for(z=[8,50]){
      translate([x,-head_y/2+3,z]) rotate([90,0,0]) cylinder(d=screw_clear,h=12,center=true);
      translate([x, head_y/2+3,z]) rotate([90,0,0]) cylinder(d=screw_clear,h=12,center=true);
    }

    // side ventilation only; no giant empty openings
    for(side=[-1,1]) for(z=[16,28,40])
      translate([side*head_x/2,8,z]) cube([wall*4,18,4],center=true);
  }

  // sensor-zone partitions
  for(x=[-14.5,14.5]) translate([x,-12,28]) cube([2,24,40],center=true);
}

// -----------------------------
// P4 FRONT — three marked sensor areas, actual shaped openings
// -----------------------------
module front(){
  difference(){
    rounded_box(head_x-4,4,head_h-4,4);

    // LEFT ZONE: THERMAL + IR
    translate([-29,0,35]) rotate([90,0,0]) cube([22,8,22],center=true);
    translate([-29,0,14]) rotate([90,0,0]) cylinder(d=12,h=8,center=true);

    // CENTER ZONE: CAMERA + LIDAR
    translate([0,0,35]) rotate([90,0,0]) cylinder(d=18,h=8,center=true);
    translate([0,0,14]) rotate([90,0,0]) cube([38,8,12],center=true);

    // RIGHT ZONE: RADAR
    translate([29,0,29]) rotate([90,0,0]) cylinder(d=22,h=8,center=true);

    // chassis attachment
    for(x=[-39,39]) for(z=[6,48])
      translate([x,0,z]) rotate([90,0,0]) cylinder(d=screw_clear,h=8,center=true);
  }

  // shallow rear retention lips around zones
  for(x=[-29,0,29]) translate([x,3,29]) difference(){
    cube([27,3,40],center=true);
    cube([23,5,36],center=true);
  }

  // printable markings
  translate([-29,-2,53]) rotate([90,0,0]) linear_extrude(.8) text("THERM/IR",size=3.2,halign="center");
  translate([0,-2,53]) rotate([90,0,0]) linear_extrude(.8) text("CAM/LIDAR",size=3.2,halign="center");
  translate([29,-2,53]) rotate([90,0,0]) linear_extrude(.8) text("RADAR",size=3.2,halign="center");
}

// -----------------------------
// P5 REAR — service cover + harness control
// -----------------------------
module rear(){
  difference(){
    rounded_box(head_x-4,4,head_h-4,4);

    // service ventilation
    for(x=[-30,-15,0,15,30]) for(z=[16,28,40])
      translate([x,0,z]) rotate([90,0,0]) cylinder(d=4,h=8,center=true);

    // controlled harness exit
    translate([0,0,8]) rotate([90,0,0]) hull(){
      translate([-6,0]) cylinder(d=7,h=8,center=true);
      translate([6,0]) cylinder(d=7,h=8,center=true);
    }

    for(x=[-39,39]) for(z=[6,48])
      translate([x,0,z]) rotate([90,0,0]) cylinder(d=screw_clear,h=8,center=true);
  }

  // internal cable comb / strain relief
  for(x=[-24,-12,0,12,24]) translate([x,-3,10]) cube([2,5,8],center=true);
}

// -----------------------------
// Assembly
// -----------------------------
module assembly(){
  base();
  translate([0,0,base_h]) lid();
  translate([0,0,head_floor_z]) chassis();
  translate([0,-head_y/2+3,head_floor_z+2]) front();
  translate([0, head_y/2+3,head_floor_z+2]) rear();
}

if(part_no==0) assembly();
if(part_no==1) base();
if(part_no==2) lid();
if(part_no==3) chassis();
if(part_no==4) front();
if(part_no==5) rear();
