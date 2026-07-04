# Geometry Conventions

Fixed conventions so every agent builds the same coordinate system and naming.
Do not deviate without recording it in the project notes.

## Units and axes

- Units: millimetres (FreeCAD default). Convert user metres to mm.
- X: longitudinal (building length). Frames repeat along X.
- Y: transverse (span). Frames cross the span in Y.
- Z: vertical (height). Floor datum at Z = 0.
- Origin: first frame at X = 0; left eave column at (0, 0, 0).

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

Always state in `notes/assumptions.md` that sections are placeholders. Replace
them with real profiles only in Gate 5 after approval.

## Separation of concerns

- Keep conceptual structural objects separate from supplier CAD blocks.
- Keep envelope and openings as their own named objects, not merged into frames.
- One re-runnable parametric script per project under `work/`.
