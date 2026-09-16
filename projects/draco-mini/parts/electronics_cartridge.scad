pi_zero_x = 65;
pi_zero_y = 30;
fit_clearance = 0.35;
tray_x=72; tray_y=48; tray_z=12; wall=2.4; pi_clear_x=pi_zero_x+2*fit_clearance; pi_clear_y=pi_zero_y+2*fit_clearance;
module snap_tab(){ cube([8,2.2,4],center=true); }
module electronics_cartridge(){ difference(){ cube([tray_x,tray_y,tray_z],center=true); translate([0,-5,wall]) cube([pi_clear_x,pi_clear_y,tray_z],center=true); translate([0,19,wall]) cube([48,8,tray_z],center=true); } translate([-22,tray_y/2+1.1,2]) snap_tab(); translate([22,tray_y/2+1.1,2]) snap_tab(); }
electronics_cartridge();
