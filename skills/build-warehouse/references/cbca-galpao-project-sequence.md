# CBCA Galpao Project Sequence (Derived)

Operational sequence derived from the CBCA/IABr manual "Galpoes para Usos
Gerais" (4a ed., NBR 8800:2008 basis). This is a paraphrased workflow map, not a
reproduction of the manual's text, tables, figures, or formulas. Use it to order
the gates and to avoid missing a step. It is not a calculation method.

## Authoritative reference chain (from the manual)

- ABNT NBR 8800:2008 - steel and steel-concrete building structures (base code).
- ABNT NBR 6123 - wind forces on buildings.
- ABNT NBR 14762 / NBR 6355 - cold-formed profiles (purlins, girts commonly).
- ABNT NBR 14323 / NBR 14432 - fire design when required.
- ABCEM Manual Tecnico de Telhas de Aco - steel roofing (slope, spans).
- CBCA Interfaces Aco-Concreto - base plates and anchors.
- CBCA Ligacoes em Estruturas Metalicas - connections.
- CBCA Projeto e Durabilidade - corrosion, coating, durability.
- AISC Design Guide 1 (base plates/anchor rods) and Design Guide 7 (industrial
  buildings) are cited as complementary references.

## Conception order (manual chapter 1.4)

1. Define use/occupancy (warehouse, factory, market, workshop, distribution).
   Use drives dimensions and loads.
2. Define volumetric configuration: height, width (span), length.
3. Define openings, fixed (e.g. louvers) and movable (doors, gates, windows).
4. Define roof slope from the roofing type. NBR 8800 (item 11.6) requires
   avoiding water ponding: slope generally not less than 5%.
5. Site analysis: topography and surrounding obstacles -> wind actions.
6. Loads: self-weight (structure, roof sheets, lighting) plus all variable
   (live/accidental) loads over the service life.
7. Treat design, fabrication, transport, and erection as one integrated problem
   for the most economical, efficient solution.

## Design and detailing order (manual chapter 2)

Project documents to produce: memorial de calculo, design drawings, fabrication
drawings, erection drawings, bill of materials.

1. Building to be designed: geometry, grid, typology.
2. Openings: roof monitor (lanternim) and side openings.
3. Gutters and downspouts.
4. Actions on the structure: permanent; variable; wind (Fwk via NBR 6123).
5. Frame structural analysis: permanent, accidental, equivalent horizontal
   (notional) force Fn, ULS combinations, analysis including second-order
   effects and sway classification (deslocabilidade).
6. Member design of the frame: column (pre-sizing + checks), rafters/beams.
7. Serviceability check: vertical and lateral displacement limits (SLS).
8. Purlins design (NBR 14762 if cold-formed).
9. Side cladding beams (girts) design.
10. Roof and side tie rods (tirantes / sag rods).
11. Base plates and anchor rods.
12. End-wall (tapamento frontal / oitao) elements, including gable posts.
13. Roof bracing elements.
14. Vertical (wall) bracing elements.

## Typology alternatives (manual 1.3)

- Gable (duas aguas) with truss/tesoura, or with rolled/welded I sections.
- Crane buildings: bracket (console) on column, trussed lower column, enlarged
  section column, or independent crane columns tied by lacing. Never infer.
- Multiple/geminated spans (four-slope, two-slope with interior column,
  transverse half-slopes), shed roofs (lighting/ventilation), arch roofs.

## Gaps this closes in the skill

- Wind and site is a first-class step, not a single question.
- Structural analysis (2nd order, sway, notional force, ULS) is an explicit,
  distinct step: the skill computes it with the calc toolkit and the engineer
  reviews/approves it (not just drafting).
- Serviceability displacement limits are a named check.
- Tie rods (tirantes) and end-wall gable framing (oitao) are required members.
- Member sizing is element-by-element in a fixed order.
- Deliverables include memorial de calculo and separate design / fabrication /
  erection drawings plus bill of materials.
