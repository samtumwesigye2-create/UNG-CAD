; UNG-CAD 4D PRINTING RESEARCH DEMO — SELF-CURLING STRIP
; Material profile: PLA
; IMPORTANT: thermal response is printer/material/process dependent.
; This file records the user's experimental toolpath and activation metadata.
; Validate dimensions, extrusion mode, clearances, adhesion, and material behavior before running.
; Activation metadata: warm-water conditioning target 70 C / 158 F.
; Keep hot water handling separate from printer operation.

M140 S60
M104 S210
M109 S210
M190 S60

G28
G90
M82                  ; Explicit absolute extrusion mode for cumulative E values below
G92 E0

; LAYER 1 — Z=0.20 mm — longitudinal raster
G1 Z0.2 F1200
G1 X10 Y10 F3000
G1 X110 Y10 E3.3 F1500
G1 X110 Y15 F3000
G1 X10 Y15 E6.6 F1500
G1 X10 Y20 F3000
G1 X110 Y20 E9.9 F1500
G1 X110 Y25 F3000
G1 X10 Y25 E13.2 F1500

; LAYER 2 — Z=0.40 mm — transverse raster
G1 Z0.4 F1200
G1 X10 Y10 F3000
G1 X10 Y30 E13.8 F1200
G1 X15 Y30 F3000
G1 X15 Y10 E14.4 F1200
G1 X25 Y10 F3000
G1 X25 Y30 E15.0 F1200
G1 X35 Y30 F3000
G1 X35 Y10 E15.6 F1200
G1 X45 Y10 F3000
G1 X45 Y30 E16.2 F1200
G1 X55 Y30 F3000
G1 X55 Y10 E16.8 F1200
G1 X65 Y10 F3000
G1 X65 Y30 E17.4 F1200
G1 X75 Y30 F3000
G1 X75 Y10 E18.0 F1200
G1 X85 Y10 F3000
G1 X85 Y30 E18.6 F1200
G1 X95 Y30 F3000
G1 X95 Y10 E19.2 F1200
G1 X105 Y10 F3000
G1 X105 Y30 E19.8 F1200
G1 X110 Y30 F3000
G1 X110 Y10 E20.4 F1200

M104 S0
M140 S0
G1 X0 Y200 F3000
M84
