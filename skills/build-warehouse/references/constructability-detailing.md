# Constructability and Detailing

Rules so the FreeCAD model reflects fabrication, transport, galvanising, and
erection reality, not idealised geometry. Derived from NBR 8800:2008, the CBCA
manuals (Galpoes, Interfaces Aco-Concreto, Ligacoes, Projeto e Durabilidade),
and industrial-building practice. Paraphrased guidance, not reproduced text or
tables.

All numeric thresholds below are SUGGESTIONS. Always ask the user and present the
suggested value; never hard-code a silent default (see the core rule in
`SKILL.md`).

## 1. Transport limits and field splices

- Fabricated members (columns, portal beams, truss chords) are usually limited
  by road transport length. Suggested max piece length: 12 m (ask; special
  transport allows more).
- When a member exceeds the agreed `L_TRANSPORT_MAX`, split it and insert a
  field-splice placeholder (bolted with splice plates / talas, or welded).
- Name split segments `..._SEG_A`, `..._SEG_B`; name the splice
  `..._SPLICE_01`. Record splice type as pending engineer detail.

## 2. Durability geometry (corrosion, galvanising)

- Avoid geometry that traps water or dirt ("trays"): open sections should shed
  water; do not model upward-facing channels that pond.
- Avoid tight crevices (e.g. double angles without proper spacer/packing).
- Hot-dip galvanised closed/tubular sections REQUIRE vent and drain holes,
  placed diametrically opposed near each end. Model them as boolean cuts.
  Sealed pockets can explode in the zinc bath; venting is a safety requirement,
  not just drainage.
- Maintenance access: keep minimum clearances between parallel members and to
  walls so painting/inspection tools fit (ask; suggested 50-300 mm by depth).
  Flag any gap below the chosen clearance as a clash.
- Flag any detail that conflicts with the chosen coating system (paint vs HDG)
  for the engineer.

## 3. Crane runway and dynamic equipment

- Crane buildings need modelled: column corbels (consoles) or enlarged/trussed
  columns, crane runway beams at the specified rail level, and the required
  horizontal + vertical operating clearances.
- Ask the user the rail top level, crane span/capacity, and clearances.
- Crane loads (vertical impact, longitudinal braking, lateral) affect bracing
  and columns; those are engineer analysis (Gate 6), not modelled forces.
- Name: `CRANE_CORBEL_A_01`, `CRANE_RUNWAY_L`, `CRANE_RAIL_L`.

## 4. Expansion joints and camber

- Long buildings need thermal expansion joints: beyond an agreed length,
  interrupt the structure with doubled axes (twin columns/beams). Suggested
  trigger length: 90 m (ask). Ask the joint position; model doubled axes there.
- Large-span roof beams/trusses get a fabrication camber (contraflecha) to
  offset self-weight deflection. Suggested trigger span: 20 m (ask). Camber is a
  drawing note / object property, NOT a modelled deflected shape.

## 5. Connections: stiffeners, gussets, base grout gap

- Rigid beam-to-column (moment) nodes often need web stiffeners in the column
  aligned with the beam flanges. Model stiffener plates when the node is rigid.
- Truss/bracing nodes converge on gusset plates; model gusset placeholders.
- Base plates never sit on raw concrete: leave a grout gap. Set Z = 0 at the top
  of concrete and raise the steel base plate by the grout thickness. Suggested
  grout gap: 30 mm (ask; typically 25-50 mm). Model anchor rods into the
  concrete.
- Oversized anchor holes + special washers: base-plate holes are larger than the
  rods (foundation tolerance); model the enlarged hole and a thick plate washer
  (`WASHER_...`) welded over each rod after levelling.
- Shear key (barra de cisalhamento): optional profile/plate welded under the
  base plate and embedded in concrete when horizontal forces exceed anchor/
  friction capacity. Model `SHEARKEY_...` below the plate; engineer-decided.
- Necessity of stiffeners/gussets/shear keys depends on forces (engineer, Gate
  6/7); the skill models them once indicated.

## 6. Fabrication and erection tolerances

- Real assemblies need erection clearances; a perfectly-tight CAD model cannot
  be assembled. Add small assembly gaps at field connections (beam copes, bolt
  clearances, piece-to-piece gaps).
- Include a recommended tolerance table (NBR 8800 appendix: plumb, alignment,
  squareness, length) as a note on fabrication/erection PDF drawings.

## 7. Passive fire protection (TRRF)

- If a required fire-resistance time (TRRF, NBR 14432) applies, columns and beams
  may receive thick protection: sprayed mortar, ceramic blanket, concrete
  encasement, or intumescent paint (NBR 14323).
- Ask the required TRRF and the protection type/thickness. A 30-50 mm coating
  around columns changes the effective envelope and can CLASH with side
  cladding, purlins/girts, piping, doors, and windows.
- Model the protection as an added volume (clash envelope) around the member so
  interferences are caught early, or at least record the thickness as a property
  and run a clearance check against cladding and openings.

## 8. Sag rods / tie rods for cold-formed secondary members

- Cold-formed purlins/girts (lipped U, Z) twist and buckle about the weak axis.
  For usual spans (above ~5-6 m, ask), model sag rods (round threaded tie rods)
  at mid-span or third-points to restrain the minor axis and align the members.
- Ask how many sag-rod lines per purlin/girt bay. Name `TIEROD_ROOF_...`,
  `TIEROD_WALL_...`.

## Parameters (all ask-with-suggestion)

| Parameter | Suggested | Meaning |
| --- | --- | --- |
| `L_TRANSPORT_MAX` | 12000 mm | Max piece length before a field splice |
| `GROUT_GAP` | 30 mm | Steel base plate rise above concrete (Z=0) |
| `CAMBER_SPAN_TRIGGER` | 20000 mm | Span above which a camber note is added |
| `EXP_JOINT_LENGTH_TRIGGER` | 90000 mm | Length above which to suggest a joint |
| `ERECTION_GAP` | 5-10 mm | Assembly clearance at field connections |
| `MAINT_CLEARANCE` | 50-300 mm | Access gap for painting/inspection |
| `SAG_ROD_SPAN_TRIGGER` | 5000-6000 mm | Purlin/girt span needing sag rods |
| `FIRE_PROTECTION_THK` | ask (TRRF) | Passive fire coating thickness (clash) |
