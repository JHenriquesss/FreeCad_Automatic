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
(5) actions and site, (6) structural analysis (skill computes, engineer reviews), (7) member
sizing per element + serviceability, (8) real profiles, (9) documents and
deliverables. Each gate asks only its own questions, models that step, captures
a screenshot, and confirms before the next gate. See `references/gates.md` for
the exact questions, options, and defaults, and
`references/cbca-galpao-project-sequence.md` for the source sequence.

The skill RUNS structural calculation via the validated parametric toolkit, now a
shared package at `framework/galpao_fw/` (moved out of the project for portability;
projects import it by repo-root discovery, no absolute paths). A real run follows
the thin-framework flow **`novo_projeto -> spec -> rodar_projeto`**: `framework.novo_projeto("<slug>")`
scaffolds an isolated project; `projeto_spec.novo()` starts the single source of
truth with every field `PENDENTE`; gates fill the spec; `validar(spec)` BLOCKS until
complete; `rodar_projeto.calcular`/`montar_modelo` reset global state, then compute
and model reading ONLY from the spec (module defaults are just the 20x10 fixture).
The engineer-reviewed modules cover: wind NBR 6123, 2D frame,
2nd-order MAES NBR 8800, member check Anexos F/G, cold-formed purlin NBR 14762 +
distortional FSM, base plate + anchors AISC DG1, connections, and a sizing
driver). At Gates 5-8 it computes loads, analysis, amplified efforts, member
sizing, and serviceability, and emits the memoriais in Portuguese. The toolkit
gives the numbers; the responsible ENGINEER still reviews and signs off — never
present a memorial or a size as final/verified before that review. Every
engineering-critical input to a module is still a gate question (Ask, Do Not
Invent). See `references/calc-modules.md`.

## Model For Fabrication And Erection

Model buildable reality, not ideal geometry. Z = 0 is the top of concrete; steel
base plates sit above a grout gap. Members longer than the transport limit get
field splices. Galvanised closed sections get drain/vent holes and must avoid
water-trapping shapes. Rigid nodes get stiffeners, truss nodes get gussets.
Field connections need erection clearances so the model is assemblable, and bolt
holes keep minimum edge and wrench clearances so a tool can reach them. Rigid
(moment) nodes automatically spawn column web stiffeners (continuity plates sized
from the incoming beam flange: thickness >= flange thickness, width >= flange
width); flexible nodes get web angles with a flange gap. Base plates get oversized
anchor holes (edge >= 2 d_ca, spacing >= 4 d_ca) with thick welded plate washers,
projected anchor rods with nut/washer, and a shear key when needed. Hole arrays
also respect maximum edge/spacing for sealing, and free-edge fillet welds cap the
leg at the plate thickness (t-1.5 mm for t >= 6.35 mm). Cold-formed purlins/girts get sag rods. Galvanised holes are
diametrically opposed and at least ~50% of the section; sharp exposed plate
corners get a light fillet. Passive fire protection adds a volume that must be
checked for clashes with cladding and openings. Movable openings must not clash
with an X-braced bay; if they do, move the bracing or use a local rigid frame.
Walk/drive-through openings (gates, doors) must also be clear of ALL structure -
columns, gable posts, girts, purlins - not just bracing: frame gates between jamb
posts, put doors mid-bay clear of columns, and interrupt a crossing girt with a
lintel. Run the structure-in-opening check before calling openings done.
Maintenance access clearances are kept for painting and inspection, dissimilar
metals are checked for galvanic corrosion, and crevices are closed. Truss and bracing
skeletons are built on member centre-of-gravity axes (not bounding-box centres);
a geometry-forced eccentricity is modelled in its real position and flagged for
the engineer, not snapped to concentric. Flange braces (mao-francesa) restrain
the bottom flange under wind uplift; sag rods form a complete tension system
ending in crossed ties at the ridge. Anchor rods are modelled with 90-degree
hooks (L/J) or bottom plates. Lifting lugs sit symmetrically above the assembly's
computed centre of gravity. Objects are grouped by erection phase (shipping lot), not only by
piece type, and splices are tagged pre-assembly (ground) or aerial for the
lifting plan. Purlin continuity (simple vs lapped sleeves) and mezzanine
steel-deck rib orientation are captured to place laps and shear studs correctly.
Purlins are oriented open-face toward the eave/gutter (CBCA: better service
performance and durability); steel deck keeps its minimum bearing length on
beams; fillet welds respect the minimum leg for the base-metal
thickness; and heavy self-supporting gutters have their weight recorded in the
load memo. Tensioned end plates are flagged for
prying-action verification. Crane buildings get corbels, runway beams with
full-height transverse stiffeners (without over-restraining end rotation), and
braking bracing. Long buildings get expansion joints (doubled axes); large spans
get a camber note. Bolt holes respect minimum spacing (~2.7 db, ~3 db
preferred) and edge distance (~1.5-1.75 db against block shear); slotted/oversized
holes get continuous plate washers at least 8 mm thick; and connection plates are
kept within the punching limit (t <= db + 3 mm) where allowed to avoid costlier
drilling. Gutters and downspouts
are modelled and clash-checked against bracing and girts. Partially-encased
composite columns get web studs and a halved-stirrup note at the load-
introduction region. Mezzanine concreting is flagged shored or unshored; web
openings sit in the middle third of the web and the central span; floor vibration
is checked for occupied mezzanines; and natural-ventilation openings follow the
CBCA chimney-effect proportion. Cross bracing is modelled tension-only (light rods/angles). Mezzanines
get a composite steel-deck floor with shear studs. The environmental class (ISO
12944) is captured to drive coating and detailing, crane duty (light/heavy) sets
runway stiffness and bracing, crane runways get end stops, and erection needs
(crane lift capacity, temporary guys, lifting lugs) are provided or documented.
Bases get levelling nuts; field connections declare bearing vs friction and the
matching hole type; expansion points may use sliding slotted supports; tapered
members and web openings are modelled when chosen; and fabrication sheets carry
the erection temperature, surface-prep grade (ISO 8501-1), welding symbols,
hatched no-paint faying areas (~50 mm around field welds and HSB contact), and
machining symbols on bearing (contact) connections; fatigue splices get run-on/
run-off weld tabs.
Eave struts stabilise the columns longitudinally; purlin/rafter brace points are
marked so the unbraced length Lb is explicit for lateral-torsional buckling;
large web openings get reinforcement plates; crane runways get relieved
stiffeners (not welded to the tension flange) and a horizontal surge truss; and
unmaintained components carry a sacrificial corrosion thickness. All such thresholds are asked
with a suggested value, never hard-coded. See
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
7. Read `references/calc-modules.md` to run the structural calc toolkit at
   Gates 5-8 (which module, inputs, outputs, run order, and the orchestrator).
   Read `references/batch-defaults.md` for how secondary decisions are settled
   in one editable sheet (Gate 4b) instead of a button per choice.
8. Read `QUICKSTART.md` for the environment pre-flight (numpy<2, pycufsm, MCP
   bridge) and how a from-scratch run is conducted.
9. If working inside `projects/<project-slug>/`, read `AGENT_SCOPE.md` and obey
   its write boundary before changing files.
10. Ask for missing engineering inputs instead of inventing dimensions.
11. Prefer parametric FreeCAD scripts for repeatable frames, purlins, roof
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
- The calc toolkit computes; the responsible engineer reviews and approves. Run
  the modules and emit PT memoriais, but do not select final member sizes or
  call a memorial verified without explicit engineer approval.
- Never invent a module input; every engineering-critical value is a gate
  question or a recorded pending assumption. Do not edit a verified formula from
  memory — go to the norm PDF in `pesquisa/aço/`.
- Preserve source attribution when using downloaded CAD blocks.
- Prefer `.FCStd` for editable FreeCAD objects and `.step` for neutral import.
- Keep external downloads in `libraries/` with source/license notes.
- Do not modify sibling project folders or shared repo configuration from a
  project-scoped task.

## References

- `references/gates.md`: the 10-gate staged workflow with per-gate questions,
  options, and recommended defaults. Start here for any real project.
- `references/batch-defaults.md`: batch-defaults mode — the critical-vs-secondary
  split and the one-pass editable defaults sheet (Gate 4b).
- `references/calc-modules.md`: the structural calc toolkit (15 modules) — which
  module each gate calls, its inputs/outputs, run order, and the compute-then-
  engineer-review rule.
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
