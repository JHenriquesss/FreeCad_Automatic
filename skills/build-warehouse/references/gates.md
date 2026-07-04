# Staged Gate Workflow

The warehouse workflow is split into 10 gates, aligned to the CBCA "Galpoes para
Usos Gerais" project sequence (see `cbca-galpao-project-sequence.md`). Run one
gate at a time. Each gate:

1. Ask the user ONLY the questions for that gate, as explicit questions
   (prefer a button-style question tool: one question, 2-4 options, a
   Recommended option first, and a sensible default).
2. Never invent an engineering-critical value silently. If the user defers,
   record the assumed value in `notes/assumptions.md` and mark it pending.
3. Model / update the FreeCAD geometry for that gate.
4. Capture a screenshot and show progress.
5. Update `context/decisions.md` (answers) and `context/pending.md` (open),
   then confirm before the next gate.

Hard rules:

- Every value a human should decide must reach the user as a question.
  Recommended defaults are the first option, never a silent choice.
- The skill does NOT perform structural calculation. Analysis, load
  combinations, member forces, and verified sizes come from the engineer
  (Gate 6). The skill models, documents, and organises; it never presents
  geometry or sizes as structurally verified.

Geometry conventions (axes, units, naming, placeholder sections) live in
`geometry-conventions.md`. The FreeCAD execution pattern lives in
`modeling-workflow-freecad.md`.

---

## Gate 0 - Use and volumetry

Purpose: fix occupancy and the bounding geometry.

Ask:

- Use/occupancy (warehouse, factory, market, workshop, distribution). Drives
  loads and clearances.
- Span direction: which dimension is the transverse span (frames cross it)?
- Length and span (m).
- Clear/eave height (m). Suggest 6 m.
- Structural typology: full-web portal frame, truss/tesoura, shed, geminated
  span, or crane bay? Recommend by span (portal <= ~12 m, truss for larger).
- Section variation: constant section, or welded tapered (variable-web-depth)
  columns/rafters to optimise weight (NBR 8800 Annex J)? Tapered members are
  modelled parametrically at Gate 8.
- Environmental aggressivity class (ISO 12944): C1 very low to C5-I/M very high
  industrial/marine. Drives coating and detailing; ask early.
- Overhead crane? If yes, capture rail top level, crane span/capacity, class
  (light or heavy duty), operating clearances, whether corbels (consoles) are
  needed, and note the impact/braking loads to hand to the engineer (detailed in
  Gate 2/5). Heavy-duty cranes need stricter longitudinal bracing and stiffer
  columns (variable-inertia or trussed).
- If the length is large, ask about thermal expansion joints: suggest a joint
  beyond ~120-150 m for normal buildings (reduce toward ~120 m if hot processes/
  ovens are present); ask, and the joint position -> doubled axes. See
  `constructability-detailing.md`.
- Mezzanine / elevated floor? If yes, plan a composite steel-deck floor with
  shear studs (detailed in Gate 2). See `constructability-detailing.md`.
- Partially-encased composite columns? (fire protection, forklift impact, or
  extra inertia at floor level.) If yes, at the load-introduction region (where
  beams frame in) the engineer halves the stirrup spacing and adds shear studs
  welded to the column web; model the studs and note the stirrup requirement.

Produces: grid axes, columns. Exit: user confirms use + bounding geometry.

## Gate 1 - Roof and slope

Purpose: fix roof shape before secondary members.

Ask:

- Roof form: gable (duas aguas), single-slope, multiple/geminated, shed, arch.
  For geminated (multiple naves), model the interior columns and the central
  valley gutters between naves.
- Roof slope %. Suggest 10%. Enforce NBR 8800 anti-ponding: not below 5%.
- Roofing type (drives slope and purlin spans; trapezoidal steel sheet default).
- Roof monitor (lanternim) for light/ventilation: yes/no + rough size.
- Overhangs (beirais): does the roof extend beyond the columns? By how much (m)?
  Affects purlins and wind suction.
- Parapets (platibandas): does the side/end cladding extend above the roof to
  hide it? Height (m)?
- Drainage: gutters (eave or valley for geminated bays) and downspouts. Model
  their volumes and check clashes between downspouts and vertical bracing or
  girts. (CBCA sequences gutters/downspouts early, right after openings.)

Produces: rafters, ridge, roof plane, overhangs, parapets. Exit: user confirms
roof.

## Gate 2 - Secondary layout and stability

Purpose: complete the conceptual structural system, including members often
forgotten in a first pass.

Ask:

- Frame spacing (m) -> number of bays. Suggest by span, not a fixed 5 m: span
  <= 15 m -> 3-5 m; 16-35 m -> 4-8 m; > 36 m -> 8-12 m (see
  `geometry-conventions.md` heuristics). State the resulting bay count.
- Purlin spacing / count per slope (by roofing span).
- Purlin static scheme: simply-supported or continuous with lap sleeves (luvas/
  trespasse) over the frames? Continuous laps change the copes and holes on the
  rafter top flange.
- Girt levels on walls.
- Roof bracing: which bays (suggest end bays).
- Vertical (wall) bracing: which bays and which walls.
- Sag rods (tirantes / linhas de corrente) for cold-formed purlins and girts:
  mandatory for usual spans (above ~5-6 m, ask). Ask how many lines per bay
  (mid-span or third-points) to restrain the weak axis. See
  `constructability-detailing.md` section 8.
- Eave struts (escoras de beiral): model the strut near each column-rafter node
  that stabilises columns longitudinally and carries wind force (single or
  built-up U/2U/2L). Ask; usually required.
- Flange braces (mao-francesa): knee braces from a purlin/girt to the BOTTOM
  flange of the rafter/column, giving lateral restraint to the compressed lower
  flange under wind uplift (suction). Ask; add where the bottom flange needs
  bracing.
- End-wall framing (tapamento frontal / oitao): gable posts on the end frames?
- Crane sub-flow (if crane at Gate 0): model column corbels (consoles) or
  enlarged/trussed columns, crane runway beams at the rail level, runway-beam
  web stiffeners (fatigue), longitudinal bracing to absorb crane braking
  forces, and the operating clearances. See `constructability-detailing.md`
  section 3.
- Expansion joint (if triggered at Gate 0): model doubled axes (twin
  columns/beams) at the joint position.
- Field splices: for any member longer than the agreed transport limit
  (suggest 12 m, ask), plan a split point and a splice placeholder. See
  `constructability-detailing.md` section 1.
- Shear key at bases: do high horizontal loads (wind on facades, crane braking)
  need a shear key under the base plate? Ask; engineer-decided.
- Mezzanine (if set at Gate 0): model floor beams, a composite steel-deck slab
  (e.g. MF-50/MF-75), and shear studs on the top flange of the floor beams. Ask
  the deck rib orientation (parallel or perpendicular to each beam), since it
  sets stud placement; studs are welded through the deck valley and must project
  above the rib into the concrete. See `constructability-detailing.md` section
  on composite floors.
- Web openings: are service runs (electrical, water, compressed air) passing
  through beam webs, or is height reduction wanted? If yes, model the web
  openings and coordinate the reinforcement the engineer requires.
- Crane end stops (if crane): model end stops/bumpers at both ends of each
  runway line, the horizontal surge truss along the runway top flange, and rail
  fixing by clips (see `constructability-detailing.md` section 3).
- Web-opening reinforcement (if openings at Gate 2): model welded reinforcement
  plates around large beam-web openings when the engineer requires them.

Produces: purlins, girts, eave/ridge beams, roof + vertical bracing, tie rods,
gable-end posts, crane corbels/runway, doubled joint axes, splice markers.
Exit: user confirms the full skeleton.

## Gate 3 - Envelope

Ask:

- Roof cladding type and modulation.
- Wall cladding type (steel sheet, masonry to a height, mixed).
- Gutters and downspouts: sides and drainage direction.

Produces: roof/wall surfaces, gutters, downspouts. Exit: user confirms envelope.

## Gate 4 - Openings

Ask:

- Fixed openings (louvers/venezianas) and movable openings (doors, gates,
  sliding windows): positions, sizes, which wall.
- Roof lighting/ventilation openings if not already set at Gate 1.

Clash detection (required): check every movable opening against the bays chosen
for vertical X-bracing. If a gate/door/window lands on a braced bay, alert the
user and propose either moving the bracing to another bay or using a local rigid
(moment) frame instead. Do not silently overlap an opening and an X-brace.

Produces: opening cut-outs and frames, with bracing conflicts resolved. Exit:
user confirms openings.

## Gate 5 - Actions and site

Purpose: assemble the load basis the engineer will analyse. The skill collects
and records; it does not compute wind or combinations.

Ask:

- Permanent loads: self-weight (auto), roof sheet weight, lighting, suspended
  loads, services.
- Variable loads: roof live load, and any crane/equipment/mezzanine/solar.
- Crane (if present): record dynamic impact coefficients (vertical + horizontal,
  NBR 8800), the fatigue regime for heavy-duty runways, and the rail-top drift
  limit (ask; H/400 general to H/600 steel mill). See
  `constructability-detailing.md` section 3.
- Temperature: record the local temperature variation range (e.g. +/-15 C) and
  whether erection happens under thermal restraint, into `notes/assumptions.md`,
  so the engineer can compute thermal effects when the structure cannot expand
  freely.
- Wind (NBR 6123): site location, terrain topography, surrounding obstacles,
  and building dimensions for the wind basis.
- Design code confirmation (NBR 8800; NBR 14762 if cold-formed; NBR 14323/14432
  if fire).
- Passive fire protection: is a required fire-resistance time (TRRF, NBR 14432)
  needed? If yes, ask protection type and thickness (sprayed mortar, ceramic
  blanket, concrete encasement, intumescent paint). A 30-50 mm coating changes
  the effective envelope and can clash with cladding, purlins/girts, piping,
  doors, and windows. Model it as a clash envelope or record the thickness and
  run a clearance check. See `constructability-detailing.md` section 7.
- Serviceability (SLS) lateral drift: ask "adopt the NBR 8800 default of H/300
  at the column top, or does the cladding require a stricter limit?" (masonry is
  stricter; metal sheet tolerates more). See `project-inputs.md`.

Produces: a documented action set in `notes/assumptions.md`. Exit: user/engineer
confirms the load basis.

## Gate 6 - Structural analysis (engineer handoff)

Purpose: obtain analysis results. The skill does NOT calculate. It records the
inputs sent to the engineer and waits for the returned results.

Ask / collect from engineer:

- Frame analysis results: member forces/moments for columns and rafters.
- Sway classification (deslocabilidade) and whether second-order effects govern.
- Equivalent horizontal (notional) force Fn used.
- ULS combinations considered.
- Base condition confirmed: pinned or fixed.
- Fatigue verification for crane runway beams, their supports, welds, and
  stiffeners (repetitive load cycles); confirm no stiffener is welded to the
  tension flange.

Produces: recorded analysis results, no geometry change. Exit: engineer delivers
member forces and the sizing basis.

## Gate 7 - Member sizing (per element) + serviceability

Purpose: turn analysis results into approved member sizes, element by element,
in the CBCA order. Sizes come from the engineer; the skill records and prepares
the model.

Confirm, in order:

- Columns, then rafters/beams.
- Serviceability (SLS): vertical and lateral displacement limits met.
- Purlins (NBR 14762 if cold-formed).
- Girts.
- Tie rods (tirantes).
- Base plates and anchor rods.
- End-wall (oitao) elements.
- Roof bracing, then vertical bracing.

Also confirm the detailing that follows from sizes (see
`constructability-detailing.md`):

- Base plate grout gap: raise the steel base plate above the concrete (Z=0) by
  the grout thickness (suggest 30 mm, ask). Model anchor rods.
- Web stiffeners at rigid beam-column nodes; gusset plates at truss/bracing
  nodes, where the engineer indicates they are needed.
- Prying action: flag tensioned end-plate/connection-plate thickness for
  explicit engineer verification (thin plates overload the bolts).
- Record the code minimum connection force (a common NBR 8800 value is 45 kN,
  except tie rods and purlins) as an assumption, so no connection is left
  designed for zero force.

Produces: an approved size for every member class. Exit: engineer approves the
full member list. Nothing is "verified" without the calculation behind it.

## Gate 8 - Real profiles in the model

Ask:

- Map each approved class to a concrete profile from
  `libraries/standards/freecad-bim/profiles.csv` or the supplier catalog.
- Confirm member orientation where it matters.
- Coating system: painted or hot-dip galvanised? If galvanised, model vent/drain
  holes (diametrically opposed near ends) on closed/tubular sections, and avoid
  water-trapping geometry. See `constructability-detailing.md` section 2.
- Field connection behaviour: bearing (contact) or friction (slip-critical)? Set
  the hole type (standard / oversized / slotted) and hole clearance accordingly.
- Tapered members (if chosen at Gate 0): model the variable-web-depth profiles.
- Slotted/oversized holes for erection adjustment on critical field connections?
  If yes, model hardened washers or larger shim plates over them.
- Sacrificial thickness (sobrespessura): any unmaintained/unprotected component
  needing extra corrosion allowance? Record it for the engineer.
- Re-check field splices against the real (heavier) profiles and the transport
  limit.

Produces: placeholder boxes replaced by real profile sections, with drainage and
splice detailing. Exit: user confirms the profile set.

## Gate 9 - Documents and deliverables

Ask:

- Which deliverables: memorial de calculo (from engineer), design drawings,
  fabrication drawings, erection drawings, bill of materials (takeoff), plus
  DXF / STEP / PDF as needed.
- Drawing scale and sheet set (plan, elevations, sections).
- Takeoff grouping (by member type, by profile, by axis).
- Transport/erection notes: splices and connections that affect shipping and
  assembly.
- Camber note on large-span beams/trusses (suggest span > 20 m, ask): add as a
  drawing note / object property, not a modelled deflected shape.
- Erection clearances: add assembly gaps at field connections (copes, bolt
  clearances, piece-to-piece) so the model is buildable.
- Include a recommended tolerance table (NBR 8800 appendix: plumb, alignment,
  squareness, length) on fabrication/erection PDF sheets. See
  `constructability-detailing.md` section 6.
- Add a reference erection temperature note (the temperature range assumed for
  assembly), since it changes the length of large pieces.
- Add sheet notes for the required steel surface-preparation grade before
  coating (ISO 8501-1 / SSPC, e.g. Sa 2.5 white metal, St 2 hand cleaning) and
  standard welding symbols on fabrication drawings.
- For crane runway beams, auto-add the fatigue weld notes (NBR 8800 Annex K):
  continuous longitudinal welds, no permanent backing bars on fatigue splices,
  ground weld transitions.

Produces: files in `projects/<slug>/exports/`. Exit: user accepts deliverables.

---

## Gate status tracking

Record gate progress in `context/pending.md` (open gates) and
`context/decisions.md` (closed gates with the answers given). Never skip a gate
silently; if the user wants to jump ahead, note the skipped gate's assumptions.
Gates 6 and 7 are engineer-dependent; a conceptual model may pause there with
everything before them modelled as placeholders.
