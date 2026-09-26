# UNG-DRACO Complete Builder Transfer — Rev C

> **Controlling mechanical build specification. Do not reproduce the failed printed base unchanged.**

## Locked architecture

- **Compute bay:** Raspberry Pi only. The Pi is the compute/controller, **not** the power subsystem. Mount it on dedicated standoffs and orient its physical Ethernet and Pi-side USB-C/data connectors toward their matching exterior openings.
- **Power bay:** Power-input, conversion, and distribution hardware only. Keep it physically distinct from the Pi compute bay.
- **Cooling:** Dedicated fan pocket, four mounting points, clear blade volume, intake/exhaust path, and fan-wire routing channel.
- **Ethernet:** RJ45 wall opening must be located from the mounted Pi connector and must clear the actual plug body, latch, molded boot, and finger access for removal.
- **USB-C data:** Dedicated opening aligned to the intended data connector; clearance is based on the actual cable plug and strain relief.
- **USB-C power:** Separate opening aligned to the power subsystem. Do not place it from nominal receptacle dimensions alone.
- **Sensors:** Each sensor/camera gets a shaped, labeled mounting area with accessible connector and protected cable route.

## Hardware measurement authority

The physical hardware is the dimensional authority. Measure in millimetres before releasing final CAD.

| Hardware | Required measurements |
|---|---|
| Raspberry Pi | Board L×W×H; mounting-hole X/Y spacing; hole diameter; Ethernet/USB-C connector offsets from board edges; connector projection |
| Power module(s) | L×W×H; mounting pattern; input/output connector locations; cable-bend space |
| Fan | Frame W×H×T; screw X/Y spacing; screw diameter; wire exit; blade/guard keep-out |
| RJ45 cable | Plug W×H; plug+boot length; maximum boot W/H; latch travel; minimum bend radius |
| USB-C data cable | Plug-body W×H×L; strain-relief W/H/L; minimum bend radius |
| USB-C power cable | Plug-body W×H×L; strain-relief W/H/L; minimum bend radius |
| Sensors/cameras | Each body L×W×H/diameter; lens projection; mounting points; connector position; cable exit |

Do **not** infer missing dimensions from the failed enclosure.

## Required build sequence

### 1. Hardware-fit coupon
Create one small coupon containing the final RJ45 opening, both USB-C openings, a representative fan pocket/corner and screw pattern, and any critical enclosure interlock. Print this before another full base. The actual hardware must insert, seat, latch where applicable, and be removable normally.

### 2. Corrected enclosure/base
Use only dimensions validated by the hardware/coupon. Move the Pi to the compute bay, reserve the power bay for power hardware, provide the fan pocket/fasteners/wire channel, align ports from mounted hardware datums, and add defined/labeled sensor mounts and cable paths.

### 3. Assembly/interference validation
The master CAD assembly must include the Pi, power hardware, fan, cable/plug envelopes, and sensors. Check wall collisions, connector insertion/removal, fan blade keep-out, cable-bend space, enclosure closure, airflow, and service access.

### 4. Final print package
Release editable source CAD, individual manifold STL/3MF parts, master assembly, exploded view/port map, and slicer-ready geometry. **No printed piece may exceed 215 mm.**

## Mechanical/printing rules

- Target printer: FlashForge Adventurer 5M.
- Nozzle: 0.4 mm.
- Nominal layer height: 0.20 mm.
- PLA is acceptable for fit/prototype work; PETG may be used where additional heat resistance is needed.
- Use practical FDM clearance on mating parts.
- Minimize screws, but every enclosure interface needs a positive attachment method.
- Preserve ventilation on both sides.
- No cable may be pinched when the enclosure closes.
- The enclosure is not required to be watertight.
- Connector openings are defined by the **actual cable plug envelope**, not just the receptacle.

## Final acceptance checklist

1. Pi is securely mounted in the compute bay and does not occupy the power bay.
2. Power hardware has its own mounting and cable route.
3. RJ45 fully inserts, latches, boot clears, and the cable can be removed by hand.
4. Both USB-C plugs fully seat without bending or enclosure contact.
5. Fan sits flat; all four mounting points align; blades remain clear; fan wire has a defined channel.
6. Airflow remains open after all electronics are installed.
7. Every sensor has a shaped/labeled location and reachable connector.
8. Every enclosure piece has a deliberate attachment method.
9. All required cables fit with the enclosure fully closed and are not pinched.
10. Fit coupon passes before committing to another full-size base print.

## Release rule

**Build from this specification and the actual hardware in hand. Measure first, validate the fit coupon, then release the corrected enclosure and final printable package from the same coordinate-controlled CAD assembly.**
