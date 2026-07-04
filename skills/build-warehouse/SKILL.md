---
name: build-warehouse
description: Use when Codex needs to plan, model, draft, or automate a steel warehouse/galpao workflow in FreeCAD, including selecting reusable CAD blocks, using steel profile references, creating project folders, preparing FreeCAD scripts, generating deliverables, or coordinating engineering inputs for industrial buildings.
---

# Build Warehouse

Use this skill to help build a steel warehouse workflow around FreeCAD and the
local CAD block library. Treat all geometry as drafting/automation input until
an engineer approves it.

## Core Rule: Ask, Do Not Invent

Every value a human should decide must reach the user as an explicit question,
preferably button-style (one question, 2-4 options, a Recommended option first,
a sensible default). Never silently pick an engineering-critical value. When the
user defers, record the assumed value in `notes/assumptions.md` and mark it
pending. Recommended defaults are allowed as the first option, not as a silent
choice.

## Staged Gates

Do not ask for everything at once. Work in 10 gates, one at a time, aligned to
the CBCA "Galpoes para Usos Gerais" sequence: (0) use and volumetry, (1) roof
and slope, (2) secondary layout and stability, (3) envelope, (4) openings,
(5) actions and site, (6) structural analysis (engineer handoff), (7) member
sizing per element + serviceability, (8) real profiles, (9) documents and
deliverables. Each gate asks only its own questions, models that step, captures
a screenshot, and confirms before the next gate. See `references/gates.md` for
the exact questions, options, and defaults, and
`references/cbca-galpao-project-sequence.md` for the source sequence.

The skill does not perform structural calculation. Loads, analysis, member
forces, and verified sizes come from the engineer (Gates 6-7). The skill models,
documents, and organises; it never presents geometry or sizes as verified.

## Model For Fabrication And Erection

Model buildable reality, not ideal geometry. Z = 0 is the top of concrete; steel
base plates sit above a grout gap. Members longer than the transport limit get
field splices. Galvanised closed sections get drain/vent holes and must avoid
water-trapping shapes. Rigid nodes get stiffeners, truss nodes get gussets.
Field connections need erection clearances so the model is assemblable. Base
plates get oversized anchor holes with welded plate washers, and a shear key
when needed. Cold-formed purlins/girts get sag rods. Passive fire protection
adds a volume that must be checked for clashes with cladding and openings.
Maintenance access clearances are kept for painting and inspection. Crane
buildings get corbels, runway beams, and braking bracing. Long buildings get
expansion joints (doubled axes); large spans get a camber note. All such
thresholds are asked with a suggested value, never hard-coded. See
`references/constructability-detailing.md`.

## First Steps

1. Read `references/gates.md` to run the staged, question-driven workflow.
2. Read `references/geometry-conventions.md` for axes, units, naming, and
   placeholder sections.
3. Read `references/modeling-workflow-freecad.md` for the FreeCAD/MCP execution
   pattern.
4. Read `references/block-map.md` to locate available blocks and standards.
5. Read `references/steel-warehouse-engineering-map.md` to select the
   structural workflow and design gates.
6. Read `references/project-inputs.md` before starting a real project.
7. If working inside `projects/<project-slug>/`, read `AGENT_SCOPE.md` and obey
   its write boundary before changing files.
8. Ask for missing engineering inputs instead of inventing dimensions.
9. Prefer parametric FreeCAD scripts for repeatable frames, purlins, roof
   sheets, and openings; save project work under `projects/<project-slug>/`.

## Workflow

1. Create or inspect a project folder.
2. Capture the design brief: dimensions, spans, height, roof slope, load
   assumptions, materials, local code, openings, crane/industrial equipment,
   and deliverables.
3. Map reusable assets from `libraries/cad-blocks/steel-warehouse/`.
4. Use `libraries/standards/freecad-bim/profiles.csv` for profile discovery.
5. Use `references/connections-bases-durability.md` when modeling base plates,
   anchors, gusset plates, bolted/welded connections, corrosion protection, or
   fabrication/mounting notes.
6. Create FreeCAD automation only after the required inputs are clear.
7. Export deliverables into `projects/<project-slug>/exports/`.
8. Document assumptions and pending engineering decisions in the project notes.

## Rules

- Do not present generated geometry as structurally verified.
- Do not select final member sizes without explicit engineer approval.
- Preserve source attribution when using downloaded CAD blocks.
- Prefer `.FCStd` for editable FreeCAD objects and `.step` for neutral import.
- Keep external downloads in `libraries/` with source/license notes.
- Do not modify sibling project folders or shared repo configuration from a
  project-scoped task.

## References

- `references/gates.md`: the 10-gate staged workflow with per-gate questions,
  options, and recommended defaults. Start here for any real project.
- `references/cbca-galpao-project-sequence.md`: derived CBCA project sequence
  and the authoritative NBR/reference chain the gates follow.
- `references/constructability-detailing.md`: transport/field splices,
  galvanising geometry, crane runway, expansion joints, camber, stiffeners/
  gussets, base grout gap, and erection tolerances.
- `references/geometry-conventions.md`: axes, units, origin, object naming, and
  the placeholder section table.
- `references/modeling-workflow-freecad.md`: parametric script pattern, running
  via the MCP bridge, and exports/screenshots per gate.
- `references/block-map.md`: available libraries and what each folder is for.
- `references/steel-warehouse-engineering-map.md`: derived map of galpao
  systems, design sequence, and engineering gates.
- `references/connections-bases-durability.md`: connection, base-interface,
  durability, fabrication, and mounting checklists.
- `references/engineering-review-questions.md`: questions for the responsible
  engineer before turning a conceptual model into project documentation.
- `references/project-inputs.md`: minimum inputs for a warehouse project.
- `references/deliverables.md`: expected outputs and folder locations.
