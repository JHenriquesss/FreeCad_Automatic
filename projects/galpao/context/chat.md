# Project Chat Context

Use this file to keep a compact, project-specific summary of the conversation.
Do not paste full transcripts. Record only durable context needed to resume work.

## Current Summary

- Galpao 20x10 m, portico rigido de alma cheia. Conceptual model built in FreeCAD
  via the Robust MCP Bridge (execute over XML-RPC 9875) on 2026-07-04.
- Confirmed geometry: span 10 m (Y), length 20 m (X), eave 6 m, roof 10% duas
  aguas, ridge 6.5 m. Frame spacing 5 m (assumed) -> 5 frames.
- Model = 52 placeholder members (frames, eave/ridge beams, purlins, girts,
  end-bay bracing). Section sizes are placeholders only.

## Last Agent State

- Parametric script: work/build_galpao.py v3 (real profiles, datum fixed, clash
  check, material takeoff). Re-runnable; closes+rebuilds doc.
- Model: 180 objects, real I/U/rod sections, clash_count = 0.
- Gate 1 finished: gutters both eaves + downspouts (drainage clash-verified);
  no overhang / lanternim / parapet.
- Deliverables: FCStd, STEP, PNG, and takeoff CSV
  (exports/takeoff/galpao_takeoff.csv). Total steel ~10.9 t (incl. ~1.24 t
  gutters), ~54 kg/m2 - placeholder sections run heavy, not verified sizing.
- Gate 3 finished: trapezoidal roof sheet + full-height steel wall cladding
  (thin 0.65 mm skin, area-based mass ~5 kg/m2). Roof clad ~1.0 t, walls ~1.85 t.
- Total incl. envelope ~13.8 t (steel frame ~10.9 t + cladding ~2.9 t);
  placeholder sections, not verified.
- Gate 4 finished: front-gable gate (framed BETWEEN jamb posts, clear opening
  3080-6920), one side personnel door (mid-bay, clear of columns, lower girt
  interrupted with a lintel), high window strip on both side walls (central
  non-braced bays; columns act as mullions).
- Fixed a real bug the user caught: structure was inside the openings. Added a
  structure-in-opening check (gate/door must be clear of ALL structure, not just
  bracing). Now: clash 0, opening-vs-bracing 0, structure-in-openings 0.
- Gates done: 0, 1, 2, 3, 4; capability 8 (real profiles, placeholder sizes); 9
  partial (3D + takeoff, no DXF/PDF/memorial). Gates 5-7 pending (6-7 need
  engineer).
