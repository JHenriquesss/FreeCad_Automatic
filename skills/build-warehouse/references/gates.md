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
- Overhead crane? If yes, capture rail top level, crane span/capacity,
  operating clearances, whether corbels (consoles) are needed, and note the
  impact/braking loads to hand to the engineer (detailed in Gate 2/5).
- If the length is large, ask about thermal expansion joints: suggest a joint
  beyond ~90 m (ask), and the joint position -> doubled axes. See
  `constructability-detailing.md`.

Produces: grid axes, columns. Exit: user confirms use + bounding geometry.

## Gate 1 - Roof and slope

Purpose: fix roof shape before secondary members.

Ask:

- Roof form: gable (duas aguas), single-slope, multiple/geminated, shed, arch.
- Roof slope %. Suggest 10%. Enforce NBR 8800 anti-ponding: not below 5%.
- Roofing type (drives slope and purlin spans; trapezoidal steel sheet default).
- Roof monitor (lanternim) for light/ventilation: yes/no + rough size.

Produces: rafters, ridge, roof plane geometry. Exit: user confirms roof.

## Gate 2 - Secondary layout and stability

Purpose: complete the conceptual structural system, including members often
forgotten in a first pass.

Ask:

- Frame spacing (m) -> number of bays. Suggest 5 m; state the resulting count.
- Purlin spacing / count per slope (by roofing span).
- Girt levels on walls.
- Roof bracing: which bays (suggest end bays).
- Vertical (wall) bracing: which bays and which walls.
- Sag rods (tirantes / linhas de corrente) for cold-formed purlins and girts:
  mandatory for usual spans (above ~5-6 m, ask). Ask how many lines per bay
  (mid-span or third-points) to restrain the weak axis. See
  `constructability-detailing.md` section 8.
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

Produces: opening cut-outs and frames. Exit: user confirms openings.

## Gate 5 - Actions and site

Purpose: assemble the load basis the engineer will analyse. The skill collects
and records; it does not compute wind or combinations.

Ask:

- Permanent loads: self-weight (auto), roof sheet weight, lighting, suspended
  loads, services.
- Variable loads: roof live load, and any crane/equipment/mezzanine/solar.
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
- Serviceability (SLS) lateral drift limits by cladding type (see
  `project-inputs.md`), so the engineer knows which limit governs member sizing.

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

Produces: files in `projects/<slug>/exports/`. Exit: user accepts deliverables.

---

## Gate status tracking

Record gate progress in `context/pending.md` (open gates) and
`context/decisions.md` (closed gates with the answers given). Never skip a gate
silently; if the user wants to jump ahead, note the skipped gate's assumptions.
Gates 6 and 7 are engineer-dependent; a conceptual model may pause there with
everything before them modelled as placeholders.
