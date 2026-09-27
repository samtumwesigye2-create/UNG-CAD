# DRACO Rev-K.2.1 — Locked CAD Correction Specification

## Do not redesign the frozen architecture
Preserve the current Rev-K.2.1 base, lid, Pi tray, yoke, sensor carrier/head, baffle/bezel, pan/tilt arrangement and overall 160 x 124 x 178.8 mm envelope.

## External base ports
The base has exactly:
- LAN / Ethernet
- USB-C DATA
- USB-C POWER

There is NO circular 12 V power jack.

## Power path
USB-C POWER -> small USB-C PD/power-trigger board -> its screw-terminal DC output -> Inland DC-DC regulator input -> regulator output -> DRACO power rail.

The PD trigger must be mounted directly behind the POWER USB-C opening. The opening centerline, PD-board USB-C socket centerline and mounting standoffs must align so an external USB-C plug can pass through the assembled wall and seat completely in the board. DATA USB-C is separate.

## Dedicated component seats and permanent printed markings
No generic empty electronics cavities. Every component gets a designed seat plus an embossed/debossed printable identifier beside it.

Required labeled areas:
- POWER/PD — USB-C PD/power-trigger board, directly behind POWER port
- REGULATOR — single Inland DC-DC regulator
- PI — Raspberry Pi Zero 2 W
- CAMERA — Raspberry Pi Camera Module 3 NoIR
- THERMAL — AMG8833
- RADAR — DFRobot C4001 / SEN0609
- LIDAR — ToFFuture XT-S1
- IR — purchased IR illuminator
- FAN — 40 mm fan
- PAN — MG90S pan servo
- TILT — MG90S tilt servo
- DATA — USB-C data interface
- LAN — Ethernet interface

Use component-specific posts, retaining walls, pockets, clips, screw patterns or other appropriate retainers. Markings must remain readable after normal 0.20 mm-layer PETG printing.

## Established component envelopes
- Pi Zero 2 W: 65 x 30 mm
- Pi Camera Module 3 NoIR: 25 x 24 x 11.5 mm
- AMG8833: 25.6 x 25.3 x 6.0 mm
- C4001/SEN0609: 26 x 30 mm
- MG90S: 22.8 x 12.2 x 28.5 mm
- Fan: nominal 40 x 40 mm
- XT-S1 LiDAR safe CAD envelope: 44 x 16 x 27 mm
- HUSB238 STEMMA reference envelope, when applicable: 29.1 x 20.3 x 10.1 mm

Do not substitute a different IR board or regulator merely because its dimensions are known.

## Fit-test gate
The previous P0 coupon failed because openings were substantially oversized. Do not propagate it.

Before production:
1. Make a representative P0 fit assembly, not a board full of component-body holes.
2. Test LAN, DATA USB-C and POWER USB-C interfaces.
3. Test the real POWER-port wall + PD-trigger mount/standoffs and verify an actual USB-C plug fully seats.
4. Test the relevant sensor retaining-seat/post/clip interfaces.
5. Use actual hardware dimensions and normal PETG fit clearance; do not use oversized placeholders.
6. Only after physical P0 passes should corrections be propagated to production parts.

## Manufacturing constraints
- FlashForge Adventurer 5M
- OrcaSlicer target
- 0.20 mm nominal layer workflow
- Maximum individual printed piece: 215 mm
- Keep LAN geometry unchanged unless the user explicitly reopens it.
- Latest one-regulator configuration supersedes older two-regulator geometry.


## Rev-K.2.1 v3 build-viewer corrections — locked
- Final baffle material: **black PLA**. Preserve build step 9 wording accordingly.
- Preserve the shown P0-v3 -> base/port plates -> regulator -> Pi tray -> lid/fan/pan -> yoke/tilt -> sensor carrier -> head shell -> baffle/bezel assembly progression.
- Treat wiring currently shown in the build viewer as illustrative only until routed harness geometry is validated.
- Fixed-base harnesses must be routed through dedicated wall/deck clips or channels with minimal free movement and no contact with the fan, pan servo, lid screws, port-plate grooves, ribs, or connector insertion paths.
- Required base routes: POWER/PD -> REGULATOR -> PWR DIST; PWR DIST -> PI/FAN/servos/required electronics; PI USB/OTG -> USB HUB -> DATA and LAN ADAPTER -> LAN.
- The moving HEAD HARNESS must use a controlled flex zone with stationary-side and moving-side strain relief. Validate through pan +/-90 degrees and tilt +/-25 degrees.
- Harnesses must not become taut, snag, rub sharp edges, enter servo/horn/fan sweep, pull connectors, or leave an uncontrolled loose coil at any motion limit.
- Final wire cut lengths are derived from validated routed path lengths plus only required connector/service/motion allowance; do not invent fixed lengths before physical routing is locked.
- P0-v3 remains the production gate: no remaining production part is approved to print until real interfaces, component retention, connector seating, representative harness routing, and full-motion cable behavior pass.


## Rev-K.2.1 servo relocation — superseding yoke-mounted tilt servo
Both MG90S servos are required inside the base. This supersedes the earlier yoke-arm TILT-servo location.

### Base servo seats
- Add separate retained, labeled `PAN` and `TILT` MG90S seats inside the base.
- Use the established 22.8 x 12.2 x 28.5 mm MG90S envelope plus physically validated print clearance.
- Both servo bodies/connectors must clear REGULATOR, PI, USB HUB, LAN ADAPTER, PWR DIST, fan, port hardware, lid screws and ribs.
- PAN drives the yoke/head through the central pan axis.
- TILT drives the head from the base through a mechanical transmission to the head tilt axis; remove the exposed yoke-arm servo body.
- The tilt transmission must remain independent through pan motion and must not bind, back-drive, collide or alter commanded tilt.
- Preserve pan +/-90 degrees and tilt +/-25 degrees.

### Servo power and control
Never power servo motor current through Raspberry Pi GPIO.
- `PWR DIST -> PAN PWR -> PAN MG90S`
- `PWR DIST -> TILT PWR -> TILT MG90S`
- `PI/PWM CONTROLLER -> PAN PWM -> PAN MG90S`
- `PI/PWM CONTROLLER -> TILT PWM -> TILT MG90S`
- Servo power ground and controller signal ground share the required common reference.
- Add labeled connection points `PAN PWR`, `TILT PWR`, `PAN PWM`, `TILT PWM`.
- Size the servo-power branch for simultaneous real servo demand using verified hardware voltage/current limits; do not invent electrical ratings.
- Keep both servo power/PWM harnesses fixed and clipped inside the base. Neither servo harness crosses the moving joint.
- Only the sensor/head harness crosses the pan/tilt assembly through the controlled flex zone.

### Servo relocation validation gate
With real MG90S hardware installed, test simultaneous powered motion at pan -90/0/+90 degrees and tilt -25/0/+25 degrees. Fail for collision, binding, transmission slip, excessive backlash, cable contact, connector pull, servo stall, or interference with electronics/fan.
