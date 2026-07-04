# Steel Warehouse Engineering Map

Derived from the local research folder and intended as an operational map for
the skill. Do not treat this as a calculation manual or a replacement for
current standards.

## Primary Research Inputs

- CBCA/IABr manual on galpoes para usos gerais: best source for the sequence,
  typical components, drawings, and broad workflow for single-story steel
  warehouses.
- ABNT NBR 8800: base standard for steel and steel-concrete building structures.
- CBCA/IABr manual on interfaces aco-concreto: useful for base plates,
  anchors, shear keys, embedded columns, and steel-to-concrete interfaces.
- CBCA/IABr manual on ligacoes em estruturas metalicas: useful for bolted and
  welded connection types and detailing scope.
- CBCA/IABr manual on projeto e durabilidade: useful for corrosion exposure,
  painting, galvanizing, inspection, and maintenance assumptions.
- Other books in `pesquisa/` are background material only. Do not copy text,
  tables, formulas, or figures from them into the repo.

## Galpao System Breakdown

Represent a warehouse as coordinated systems:

- Primary transverse system: rigid frame, truss/tesoura with columns, portal
  frame, shed, geminated spans, or crane-supporting frame.
- Longitudinal system: frame spacing, roof bracing, wall bracing, longitudinal
  tie members, and load path to foundations.
- Roof secondary system: purlins, ridge, eave members, roof sheets, skylights,
  lanternim, gutters, and downspouts.
- Wall secondary system: girts, cladding rails, doors, gates, windows, braced
  bays, and end-wall frames.
- Foundation interface: base plates, anchors, shear keys, grouting, concrete
  pedestal or footing assumptions.
- Connection system: shop welds, field bolts, gusset plates, end plates,
  splice plates, flexible shear joints, and moment joints.
- Durability system: steel grade, exposure category, paint or galvanizing
  system, drainage, inspection access, and maintenance plan.

## Design Sequence For Agent Work

1. Collect geometry and use: span, length, clear height, bay spacing, roof
   slope, openings, cranes/equipment, cladding, location, and exposure.
2. Select a conceptual structural typology with the engineer: truss, portal
   frame, built-up frame, shed, geminated span, or crane bay.
3. Establish load cases and load path at a descriptive level: permanent loads,
   roof/wall cladding, live roof load, wind, crane/equipment, and notional or
   stability effects when required.
4. Model only approved conceptual geometry in FreeCAD: axes, grids, frames,
   purlins, girts, bracing, openings, and envelope.
5. Attach provisional profile families from the library only after the engineer
   approves the intended member class.
6. Add connection placeholders and interface markers, not final details, unless
   the engineer supplies connection standards.
7. Produce deliverables with assumptions and unresolved engineering decisions
   visible in project notes.

## Typical Typology Decisions

- Simple storage or logistics building: portal frame or truss/tesoura with
  regular bays, purlins, girts, and braced longitudinal bays.
- Large span with lower weight target: truss/tesoura or parallel-chord truss,
  with gusset details and member orientation defined by office standard.
- Industrial bay with crane: columns may need consoles, stepped columns,
  independent crane columns, or crane runway beams; never infer this without
  explicit input.
- Multiple adjacent spans: clarify interior columns, drainage valleys, gutters,
  and bracing continuity before modeling.
- Natural lighting/ventilation: lanternim, skylights, sheds, or wall openings
  must be coordinated with bracing and purlin layout.

## Model Quality Rules

- Keep a clear grid: longitudinal axes, transverse frame axes, floor datum,
  eave line, ridge line, and base plate points.
- Name objects by system and axis, e.g. `FRAME_A_COL_1`, `PURLIN_BAY_03`,
  `BRACE_ROOF_X_02`.
- Separate conceptual objects from supplier CAD blocks.
- Store project assumptions in `projects/<project-slug>/notes/assumptions.md`.
- Do not call any member size, weld, bolt, base plate, anchor, or connection
  "verified" unless the engineer explicitly provides the calculation result.

## What The Skill Should Ask Before Modeling

- What is the intended typology: portal frame, truss, shed, geminated span, or
  crane bay?
- What are the span, length, eave height, roof slope, bay spacing, and
  cladding modulation?
- Which profile families are allowed: Gerdau W/HP, U, cantoneiras, tubes,
  welded I/H, cold-formed purlins, or another supplier?
- Which bays are braced, and are there openings that conflict with bracing?
- Is the base assumed pinned, fixed, or pending structural decision?
- Are there cranes, mezzanines, heavy equipment, solar panels, conveyors, or
  suspended loads?
- What durability environment and coating system should be assumed?
