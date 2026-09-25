// UNG-CAD compact observation quad — optional prop guard
// Print four. Fits within 215 mm rule. Generic geometry pending exact prop/motor selection.
$fn=64;
outer_d=78;
inner_d=70;
ring_h=4;
mount_d=3.4;
difference(){
 union(){
  difference(){
   cylinder(d=outer_d,h=ring_h);
   translate([0,0,-1]) cylinder(d=inner_d,h=ring_h+2);
  }
  translate([-outer_d/2, -5,0]) cube([18,10,ring_h]);
 }
 translate([-outer_d/2+8,0,-1]) cylinder(d=mount_d,h=ring_h+2);
}
