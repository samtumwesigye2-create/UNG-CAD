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
