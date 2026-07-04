# Skill Audit - Galpao 20x10 End-to-End Run (2026-07-04)

First real execution of the build-warehouse skill after 17 refinement rounds.
Model rebuilt as `work/build_galpao.py` v2, run via the FreeCAD MCP bridge.
Result: 180 objects (was 52), FCStd + STEP + PNG exported.

## What the skill translated to geometry cleanly

- Core geometry: 10 m span x 20 m length, eave 6 m, 10% gable, 5 frames.
- New Gate-2 structural elements all modelled: eave struts, gable-end posts
  (oitao), sag rods (tirantes) with ridge ties, tension-only cross bracing as
  thin rods, base plates + L-hook anchor rods + plate washers, grout gap (steel
  raised to Z=30).
- Naming convention from geometry-conventions.md applied cleanly.
- The rule set materially enriched the model (52 -> 180 objects).

## What broke or was awkward (execution-only findings)

1. Placeholder boxes cannot express most detail rules. Purlin open-face-to-eave,
   U/C shape, tension-only behaviour, weld legs, hole spacing, welded washers,
   punching limit, drain holes, corner rounding - none are representable as
   bounding boxes. Of ~150 constructability rules, a conceptual box model can
   show ~15 (member layout); the rest need real profiles (Gate 8) + fabrication
   modelling.
2. Flange braces (mao-francesa) as boxes are crude stubs; the inboard-direction
   heuristic (+/-150 mm) is a guess, not engineering.
3. Gate timing is unclear. ~80% of constructability rules only become geometry at
   Gate 7-8 (real profiles/detailing), but the conceptual model is pre-Gate-6.
   The skill does not tag each rule with WHEN it becomes geometry vs a note.
4. No clash detection actually runs. The skill promises clash checks (openings vs
   bracing, downspout vs bracing, fire-protection envelope) and CG/Lb export, but
   the script implements none of them. Rules assume capabilities that do not
   exist yet.
5. Ask-don't-invent vs running. A full run needed ~15 auto-assumed secondary
   decisions (bay 5 m, 1 sag line, section placeholders, gable-post count, no
   openings/gutters). Asking all of them as buttons is impractical; the skill
   needs a conceptual "batch defaults" mode.

## Datum inconsistency found

Grout-gap rule raises columns to Z0=30, but eave height is still 6000 absolute,
so column length becomes 5970 and the datum for "eave height" (top of concrete
vs top of base plate) is undefined. The skill introduced Z0 without resolving
what heights measure from.

## Verdict

The skill's high-level flow and member layout execute well. The mass of
fabrication detail (rounds 3-19) is real and correct but largely NOT expressible
in a pre-Gate-6 conceptual box model - it belongs to later gates and needs
capabilities (profiles, clash, CG, weld/hole detailing) the current FreeCAD
script does not have. Next real improvement is implementing a few of those
capabilities, not adding more rules.
