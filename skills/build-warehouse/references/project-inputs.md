# Project Inputs

Collect these inputs before generating a warehouse model. Ask them as questions,
gate by gate (see `gates.md`); do not dump the whole list on the user at once.

## Minimum Inputs To Start (Gate 0)

Just enough to draw the grid and a conceptual skeleton. Ask these first:

- Which dimension is the transverse span (frames cross it)?
- Length and span (m).
- Clear/eave height (m). Suggested default: 6 m.
- Roof: single-slope or gable? Slope %. Suggested default: 10% gable.
- Structural typology: full-web portal frame, truss/tesoura, shed, geminated
  span, or crane bay? Recommend by span (portal <= ~12 m, truss for larger).

Everything below is collected in later gates, not at Gate 0.

## Site And Geometry

- Project name and location.
- Units.
- Overall length, width, and clear height.
- Bay spacing and frame spacing.
- Roof type and slope.
- Eaves, ridge, gutters, and overhangs.
- Floor elevation and reference datum.
- Wall and roof cladding modulation.
- Access, truck, crane, maintenance, and fire-service clearances.

## Structural Inputs

- Design code or reference standard.
- Steel grade and preferred supplier profiles.
- Column system.
- Main frame or truss system.
- Purlin/girt system.
- Bracing strategy.
- Base plate and anchor assumptions.
- Crane, mezzanine, equipment, or concentrated loads.
- Serviceability limits for roof, side sway, cladding, and crane operation.
  Lateral drift (sway) limit depends on the cladding: masonry walls are strict
  (e.g. crack width or H/300 to H/400 to avoid cracking under wind); metal-sheet
  cladding tolerates more flexibility. State which limit governs so the engineer
  can size the frame accordingly. Confirm the exact value with the engineer.
- Foundation interface assumptions and concrete strength.
- Connection philosophy: shop-welded/field-bolted, bolted moment joints,
  flexible shear joints, truss gussets, or other office standard.
- Corrosion environment and required protection system.

## Envelope And Openings

- Roof cladding type.
- Wall cladding type.
- Door, gate, and window positions.
- Ventilation and skylights.
- Fire access or operational constraints.
- Gutters, downspouts, drainage path, and water ponding risk.
- Interfaces with masonry, concrete walls, docks, canopies, or existing
  buildings.

## Engineering References To Confirm

- ABNT NBR 8800 for steel and steel-concrete building structures.
- ABNT NBR 6123 or current wind-load basis.
- ABNT NBR 14762 when cold-formed purlins/girts are used.
- ABNT NBR 14323 and ABNT NBR 14432 when fire design is required.
- Supplier catalog for selected profiles and availability.

## Deliverables

- FreeCAD model.
- DXF drawings.
- STEP exports.
- PDF sheets.
- Material takeoff.
- Assumption log.

If any engineering-critical input is missing, pause and ask for it.
