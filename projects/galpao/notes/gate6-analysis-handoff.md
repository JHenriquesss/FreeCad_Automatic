# Gate 6 - Structural Analysis Handoff

The skill does NOT calculate. This document packages what the engineer needs to
run the analysis, and the template for the results to return. Nothing here is a
computed or verified value.

## Model sent to the engineer

- Geometry: 20 m length (X) x 10 m span (Y), eave 6 m from top of concrete,
  gable roof 10% (ridge 6.5 m). 5 frames at X = 0/5/10/15/20 m.
- Typology: full-web portal frame, pinned bases assumed (confirm).
- Grid, member list, and secondary system are in `work/build_galpao.py` and the
  FCStd/STEP exports. Member schedule (placeholder sections) is in the takeoff CSV.
- Bracing: X-bracing (tension-only) in the end bays, roof plane + side walls.
- Secondary: purlins (open face to eave), girts, eave struts, gable posts, sag
  rods, flange braces. Openings: gable gate, side door, side windows.

## Loads (from Gate 5, `assumptions.md`)

- Permanent: self-weight (from model), roof cladding ~0.05 kN/m2, wall cladding,
  gutters as an eave line load ~0.6 kN/m, suspended loads ~0.10-0.15 kN/m2
  (pending real value).
- Variable: roof live ~0.25 kN/m2; wind NBR 6123 V0 = 40 m/s, terrain Cat II,
  S1 = 1.0 (flat), S2 by height ~6.5 m, S3 by use.
- No crane / mezzanine / solar. Fire TRRF 30 min (thin intumescent, no geometry).

## What the engineer must return (results template)

Fill these; they drive Gates 7-8. Until returned, sizes stay placeholders.

- [ ] Analysis type: first vs second order (P-Delta) used.
- [ ] Sway classification (deslocabilidade): small / medium / large.
- [ ] If medium-sway: member flexural + axial stiffness reduced to ~80%? (y/n)
- [ ] Geometric imperfections included: global out-of-plumb ~L/500 (or notional
      force Fn), local ~L/1000. (y/n + value)
- [ ] ULS load combinations considered (list).
- [ ] Base condition confirmed: pinned or fixed.
- [ ] Governing wind case and internal pressure coefficient (with the openings).
- [ ] Member forces/moments per member group (columns, rafters, eave struts,
      gable posts, purlins, girts, bracing, ties).
- [ ] Serviceability check: lateral drift vs H/300, roof/purlin deflection vs
      L/200 - OK? Any resize needed.
- [ ] Approved member classes and sizes per group -> feed Gate 7/8.
- [ ] Minimum connection force basis (e.g. 45 kN) and any special connections.

## Status

Handoff package ready. Analysis RESULTS: pending the responsible engineer. The
model, loads, and this template are the deliverable of Gate 6; Gates 7-8 resume
when the results above are supplied.
