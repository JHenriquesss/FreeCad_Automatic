# Geometry Conventions

Fixed conventions so every agent builds the same coordinate system and naming.
Do not deviate without recording it in the project notes.

## Units and axes

- Units: millimetres (FreeCAD default). Convert user metres to mm.
- X: longitudinal (building length). Frames repeat along X.
- Y: transverse (span). Frames cross the span in Y.
- Z: vertical (height). Z = 0 at the TOP OF CONCRETE / foundation.
- Origin: first frame at X = 0; left eave column base at (0, 0, grout gap).
- Steel base plates do not sit on raw concrete: raise the steel by the grout
  gap (ask; suggest 30 mm). Column bottom at Z = `GROUT_GAP`, not Z = 0. See
  `constructability-detailing.md` section 5.

## Key levels

- Eave (pe-direito) at Z = eave height.
- Gable ridge at Y = span/2, Z = eave + slope * (span/2).
- Single-slope ridge at the high wall; Z = eave + slope * span.

## Naming

Name objects by system and axis so failures localise:

- Frames: `FRAME_01_COL_L`, `FRAME_01_COL_R`, `FRAME_01_RAFTER_L`,
  `FRAME_01_RAFTER_R` (frame number zero-padded).
- Longitudinal: `BAY_01_EAVE_L`, `BAY_01_EAVE_R`, `BAY_01_RIDGE`.
- Secondary: `PURLIN_L_01`, `PURLIN_R_01`, `GIRT_L_01`, `GIRT_R_01`.
- Bracing: `BRACE_ROOF_01_A`, `BRACE_WALL_L_01_A`.
- Tie rods: `TIEROD_ROOF_01`, `TIEROD_WALL_L_01`.
- Gable-end posts (oitao): `GABLE_FRONT_POST_01`, `GABLE_BACK_POST_01`.
- Eave struts: `EAVE_STRUT_L_01`, `EAVE_STRUT_R_01`.
- Drainage: `GUTTER_...`, `DOWNSPOUT_...`. Composite column studs: `COLSTUD_...`.
- Lifting lugs: `LIFTLUG_...`.
- Detailing: `BASEPLATE_...`, `STIFFENER_...`, `GUSSET_...`, `SPLICE_...`,
  `CRANE_CORBEL_...`, `CRANE_RUNWAY_...`, `DRAINHOLE_...`, `WASHER_...`,
  `SHEARKEY_...`, `FIREPROT_...`.
- Split segments of a spliced member: `..._SEG_A`, `..._SEG_B`.
- Envelope/openings: `ROOF_SHEET_...`, `WALL_...`, `GATE_...`, `WINDOW_...`.

L = left wall (Y = 0), R = right wall (Y = span).

## Placeholder sections

Until the engineer approves member classes and sizes, model members as
rectangular placeholder boxes (width x height, mm), centred on the member axis.
These are for visualisation only and are NOT profiles:

| System | Placeholder (w x h mm) |
| --- | --- |
| Column | 200 x 200 |
| Rafter / main beam | 200 x 150 |
| Eave / ridge beam | 150 x 100 |
| Purlin | 150 x 60 |
| Girt | 150 x 60 |
| Bracing | 80 x 80 |
| Tie rod (tirante) | 25 dia (model as 25 x 25) |
| Gable post (oitao) | 150 x 150 |
| Eave strut (escora de beiral) | 150 x 100 (or 2U/2L) |
| Base plate | 350 x 350 x 22 |
| Stiffener plate | node-fit x 10 thick |
| Gusset plate | node-fit x 10 thick |
| Splice plate (tala) | flange-fit x 10 thick |
| Crane corbel (console) | 300 x 200 |
| Crane runway beam | 400 x 200 |
| Plate washer | 100 x 100 x 16 |
| Shear key | 150 x 150 (under base) |

Detailing objects (base plates, stiffeners, gussets, splices, corbels, drain
holes) are added in Gates 7-9, not in the conceptual gates.

## Placeholder sizing heuristics (visualisation only)

These rules-of-thumb make the early placeholder model look realistic before the
engineer sizes anything. They are NOT design, NOT verified, and are replaced by
real profiles at Gates 7-8. Always present them as suggestions (ask-with-
suggestion) and record them as assumptions.

- Frame spacing by span (Bellei, economical range):
  - Span up to 15 m: spacing 3-5 m.
  - Span 16-35 m: spacing 4-8 m.
  - Span over 36 m: spacing 8-12 m.
- Column placeholder section depth: about H/20 to H/30 of the column height H.
- Main roof beam placeholder depth: about L/50 to L/70 of the span L.
- Purlin/girt placeholder depth: about L/40 to L/60 of the member span (the
  frame spacing for purlins), for the placeholder box height only; note the
  purlin deflection limit L/200 as an assumption for the engineer.
- Purlin spacing: for usual trapezoidal steel sheet (e.g. 0.55 mm), typically
  1300-1800 mm (ask; drives the purlin count per slope).
- Sag-rod lines: purlins spanning ~5-6 m need one line at mid-span; above that,
  use two lines (third-points) to control weak-axis bending and twist.

Always state in `notes/assumptions.md` that sections are placeholders. Replace
them with real profiles only in Gate 5 after approval.

## Separation of concerns

- Keep conceptual structural objects separate from supplier CAD blocks.
- Keep envelope and openings as their own named objects, not merged into frames.
- One re-runnable parametric script per project under `work/`.
