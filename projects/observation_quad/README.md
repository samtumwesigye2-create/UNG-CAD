# UNG Compact Observation Quad

Safe, low-cost UNG-CAD concept for visual observation, tracking experiments, and basic autonomous flight. It is not designed to collide with, capture, disable, or carry a payload against another aircraft.

## Baseline
- 180 mm motor-span compact quad layout
- one-piece printable main frame, under the 215 mm per-part limit
- 20x20 mm flight-controller mounting pattern
- battery strap slots
- four generic motor pads
- optional center bumper ring
- intended for prop guards and low-energy testing

## CAD
Open `observation_quad.scad`. Set `part=1` for the frame or `part=2` for the optional bumper.

Motor mounting holes are intentionally not finalized beyond a generic center clearance. Match them to the selected motor's verified mounting pattern before fabrication.

## Intended flight features
Position hold, return-to-home, geofencing, telemetry, camera observation, visual tracking, and separation-aware following. No physical interception behavior.
