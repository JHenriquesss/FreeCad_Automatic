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
- Hole size: galvanising holes should be at least ~50% of the tube diameter (or
  section diagonal), diametrically opposed. Model them accordingly.
- Round sharp corners: exposed cut plates (gussets) hold paint poorly on sharp
  edges; apply a light fillet to the corners of exposed plates.
- Maintenance access: keep minimum clearances so painting/inspection tools fit
  (ask; ~50-300 mm by depth), and where an operator must reach the surface,
  keep operator access (ask; suggest 500-600 mm). Areas that become inaccessible
  after erection need a durable special protection; flag them.
- Close crevices: seal gaps that hold electrolyte, preferably with continuous
  weld, so water/dirt cannot accumulate between faying faces.
- Galvanic corrosion (dissimilar metals): confirm material compatibility (e.g.
  do not pair galvanised bolts with unpainted weathering steel in aggressive
  environments). The less-noble component is oversized or isolated; flag for the
  engineer.
- Environmental class (ISO 12944): record the aggressivity class (C1 to C5-I/M).
  It governs the coating system and how strict the detailing must be.
- Flag any detail that conflicts with the chosen coating system (paint vs HDG)
  for the engineer.

## 3. Crane runway and dynamic equipment

- Crane buildings need modelled: column corbels (consoles) or enlarged/trussed
  columns, crane runway beams at the specified rail level, and the required
  horizontal + vertical operating clearances.
- Ask the user the rail top level, crane span/capacity, and clearances.
- Crane loads (vertical impact, longitudinal braking, lateral) affect bracing
  and columns; those are engineer analysis (Gate 6), not modelled forces.
- Runway beams need transverse web stiffeners over the full web height (fatigue)
  and must avoid crevices that retain water (fatigue + corrosion). Model
  full-height transverse stiffeners; do not model water-trapping pockets.
- Columns may be variable-inertia or trussed to carry the runway; model per the
  chosen typology.
- Rail deflection limits are strict: horizontal drift at the rail top commonly
  H/400 (general) to H/600 (steel-mill buildings). Ask and record the limit.
- Heavy-duty runways are a fatigue regime: record it so the engineer uses weld
  details without stress concentration.
- Impact coefficients: crane loads need dynamic impact factors (vertical and
  horizontal) per NBR 8800; record this for the engineer.
- Do NOT model support stiffeners that over-restrain the runway beam's natural
  end rotation; wrong restraint causes fatigue cracking.
- Rail fixing: model clips/clamps (grapas) rather than holes drilled through the
  beam flange, so the rail can be realigned and the flange is not weakened by
  fatigue-prone holes.
- Name: `CRANE_CORBEL_A_01`, `CRANE_RUNWAY_L`, `CRANE_RAIL_L`.

## 4. Expansion joints and camber

- Long buildings need thermal expansion joints: beyond an agreed length,
  interrupt the structure with doubled axes (twin columns/beams). Suggested
  trigger length: 90 m (ask). Ask the joint position; model doubled axes there.
- Large-span roof beams/trusses get a fabrication camber (contraflecha) to
  offset self-weight deflection. Suggested trigger span: 20 m (ask). Camber is a
  drawing note / object property, NOT a modelled deflected shape.

Suggested joint trigger length: 120-150 m for normal buildings; reduce toward
120 m when hot processes/ovens raise internal temperature swings (ask).

## 9. Erection provisions

- Field-splice division depends not only on transport length but on the site
  crane's tipping moment (lift capacity x radius). Ask the available lifting
  capacity when deciding splice points and piece weights.
- Temporary stability: frames are unstable during erection until the permanent
  bracing is in. Provide/indicate temporary guy wires (estais) anchored to the
  ground and lifting lugs (olhais) on liftable pieces; show them on the Gate 9
  erection drawings.
- Field splices may carry temporary erection tension before the structure is
  complete (see section 1).

## 10. Composite floors (mezzanine)

- Model floor beams, a composite steel-deck slab (formwork acting as platform
  and reinforcement, e.g. MF-50 / MF-75), and shear studs (stud bolts) welded to
  the top flange of the floor beams for steel-concrete composite action.
- Studs are typically <= 19 mm diameter and should project at least ~50 mm above
  the top of the steel deck. Confirm with the engineer.
- Name: `MEZZ_BEAM_...`, `MEZZ_DECK_...`, `STUD_...`.

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

### Rigid vs flexible connection geometry

The 3D detail must reflect the connection type the engineer specifies:

- Rigid (moment) beam-column: automatically add column web stiffeners aligned
  with the beam flanges (forces from the flanges need them).
- Flexible (shear only): model web angles or a simple plate and keep a gap
  between the beam flange and the column, so no moment is implied.

### Connection behaviour geometry

- Prying action: in bolted moment connections (high-strength bolts in tension),
  a too-thin end plate flexes and prying overloads the bolts. Flag tensioned
  connection-plate thickness for explicit engineer verification (Gate 7).
- Eccentricity: cross the system lines (member axes) at exactly the same node.
  For single-angle members (e.g. bracing), avoid gauge-line eccentricity from
  the centroid, which adds unplanned secondary bending not in the truss model.

### Fastener clearances

- Minimum edge distance: keep bolt-hole centres away from plate edges (a common
  minimum is about 1.25 x bolt diameter; the engineer confirms per NBR 8800).
- Minimum bolt spacing: centre-to-centre distance between standard holes should
  be at least 2.7 x bolt diameter (NBR 8800). Enforce this when the script lays
  out holes on gussets and end plates.
- Wrench clearance: keep bolt holes far enough from a profile web/flange so a
  tightening wrench fits. Do not place holes where a tool cannot reach.

### Anchor rods (chumbadores) detail

- Model the anchor embedment depth into the concrete and the projection above
  the base plate for nut, lock-nut, and washer.
- Combine with oversized holes + plate washers (section 5).

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
| `EXP_JOINT_LENGTH_TRIGGER` | 120000-150000 mm | Length above which to suggest a joint (lower with hot processes) |
| `BOLT_MIN_SPACING` | 2.7 x db | Min centre-to-centre standard hole spacing |
| `SLS_LATERAL_DRIFT` | H/300 | NBR 8800 default column-top drift (stricter if masonry) |
| `ERECTION_GAP` | 5-10 mm | Assembly clearance at field connections |
| `MAINT_CLEARANCE` | 50-300 mm | Access gap for painting/inspection |
| `SAG_ROD_SPAN_TRIGGER` | 5000-6000 mm | Purlin/girt span needing sag rods |
| `FIRE_PROTECTION_THK` | ask (TRRF) | Passive fire coating thickness (clash) |
