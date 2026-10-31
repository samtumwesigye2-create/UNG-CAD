# UNG-CAD Construction Takeoff — consolidated pipeline

This module contains an illustrative browser-based 3D sequencing visualization plus a local, measured-component takeoff engine.

## Usage

```sh
python3 construction-takeoff/pipeline.py construction-takeoff/examples/model.json construction-takeoff/examples/catalog.json --out construction-output
python3 -m unittest discover -s construction-takeoff/tests
```

For IFC: install `ifcopenshell` separately, then pass an IFC file as the first argument. Only supported IFC BaseQuantities are read; missing quantities block estimation. Non-base SI and non-SI length/area/volume units are rejected. OBJ is available as a geometry-preview parser only, not quantity estimation.

The output includes `estimate.json`, `takeoff.csv`, and review-only handoff manifests for TITAN, APOLLO, and MERCURY. No external services are called, no procurement orders are placed, and no existing UNG APIs are assumed. The stage animation remains a schematic demo and does not render imported IFC geometry.

## Gatekeeper release rule

The pipeline **never** marks a result as Gatekeeper-approved. Incomplete measurements, missing price rates, invalid identifiers, and unsupported units block takeoff. Actual approval requires verified integration with the existing Gatekeeper and review of geometry, structural design, building codes, tolerances, safety, and procurement assumptions.

## Remaining production dependencies

Production deployment still needs authenticated UNG integrations, project-specific BIM rendering, verified unit conversion and IFC coverage, signed Gatekeeper approval, real regional material/labor rates, full integration tests, and a security review. Demo rates are not suitable for bids or purchasing.
