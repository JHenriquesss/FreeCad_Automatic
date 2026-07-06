# Calc Modules — the structural calculation toolkit

The skill now RUNS structural calculation via a validated, parametric toolkit in
`projects/galpao/calc/` (17 modules, each with a self-test, Portuguese outputs,
and formulas extracted from the norm PDFs). Every module was reviewed by the
responsible engineer. The skill computes and produces the PT memoriais; the
responsible engineer still REVIEWS them and signs off — the toolkit gives the
numbers, the engineer gives the approval. Never present a memorial as final
before that review.

## Golden rules

- **Ask, Do Not Invent** still holds. Each module needs inputs; every
  engineering-critical input is a gate question to the user (with a justified
  recommended default). Never hard-code a value the user should decide.
- **Outputs in Portuguese** — the memoriais are read by a PT-only team. Code and
  comments stay English; printed reports/memoriais are PT.
- **Zero method errors** — the formulas are already verified against the norm
  PDFs. Do not "improve" a formula from memory; if a method question arises, go
  to the norm PDF in `pesquisa/aço/`.
- Run each module, save its stdout as the memorial under
  `projects/<slug>/exports/memoria/`, and keep the code+result markdown pattern
  (see `projects/galpao/notes/scripts-md/`).
- **numpy < 2** is required only for `distorcional_fsm` (pycufsm). Pinned to
  1.26.4; the other modules are numpy-agnostic. See `calc/REQUISITOS.txt`.

## Module map (what to call, and when)

| Gate | Module | Computes | Key inputs (gate questions) |
|------|--------|----------|------------------------------|
| ALL | `projeto_spec` | FRAMEWORK: single source of truth for the project; `validar()` BLOCKS calc/model while a required field is unasked; `to_rodar_params`/`to_build_kwargs` map spec → modules (no hardcoded copy) | every gate answer fills the spec |
| T terreno | `terreno` | land feasibility (FIRST): lot area from KML/coords, buildable rectangle, TO/CA/TP caps, fit check | KML/coordenadas, taxa de ocupação, taxa de permeabilidade, coef. aproveitamento, recuos, nº pavimentos |
| 5 actions | `vento_nbr6123` | NBR 6123 wind: S2, Vk, q, Cpe (Tab.4/5, α=90), Cpi (portão dominante); LONGITUDINAL α=0 (`compute_longitudinal`): Cpe empena Tab.4 + arrasto Fa=Ca·q·Ae (Ca da Fig.4, A CONFIRMAR) | V0, categoria, classe, S1, S3, z, θ telhado, dims a/b/h, abertura dominante, Ca arrasto |
| 6 analysis | `galpao_portico` (+ `frame2d`) | portal efforts M/N/V, drift, ELS ladder | geometria (vão, pé-direito, cumeeira, BAY), G/Q, base rotulada/engastada, perfis placeholder |
| 6 analysis | `estabilidade_b1b2` | 2nd order MAES: B1/B2, deslocabilidade, 80% stiffness, força nocional, amplified efforts | (reuses portico) |
| 7 sizing | `check_nbr8800` | member check (Anexos F/G), K=1, interação, worst combo | perfis coluna/viga, fy, Lb travamento |
| 7 sizing | `mao_francesa` | flange-brace spacing: inverts the 5.5.1.2 interaction for max Lb, derives braces/frame (feeds the viga Lb) | perfil viga, fy, Nsd/Msd/Vsd do combo governante, vão, inclinação, nº terças/água |
| 7 sizing | `redimensionamento` (+ `perfis`) | iterate profile + base until ELU≤1 and drift≤H/150; lightest | escada de perfis candidatos, limite de flecha (fechamento) |
| 7 sizing | `tercas_nbr14762` | cold-formed Ue purlin: MSE local, Anexo F suction, distortional, shear, biaxial, deflection | perfil Ue (catálogo), fy, vão, linha de corrente, trib, contínua?, cargas G/Q/W |
| 7 sizing | `distorcional_fsm` | Mdist (elastic distortional, FSM/pycufsm) when Table 14 does not dispense | Ue dims, fy → feeds `tercas` cfg["Mdist"] |
| 7 sizing | `base_chumbador` | base plate + anchors: bearing (6.6.5), N+M eccentricity (DG1), anchor tension/shear, plate t both sides | N/V/M from portico base, fck, placa BxL, chumbadores, dims pilar |
| 7 sizing | `secundarios_nbr8800` | secondary members: wall girt (U) biaxial bending (Anexo G + 5.5.1), eave strut/ridge (I) + gable post (I) beam-column | perfis U/I, trib, peso tapamento, nº tirantes de parede, pressão de vento, Nsd (do arrasto) |
| 7 sizing | `contraventamento` | tension rods (5.2): bracing diagonals, sag rods, flange-brace rod — yield/rupture + slenderness; diagonal force from Fa; 2% brace force | d das barras, fy/fu, Fa/lado (do vento long.), Msd viga, Nsd tirante (A CONFIRMAR) |
| 5/6 crane | `ponte_rolante` | crane action (NBR 8800/8400): wheel loads (impact φ), surge (transversal), braking (longitudinal); runway beam (moving-load moment + lateral + ELS L/600…L/1000 + fatigue flag); packages the console reaction for the portico | Q, pesos ponte/trole, vão ponte, aproximação mín, nº rodas, φ/frações (fabricante/8400, A CONFIRMAR), perfil da viga de rolamento |
| 7 sizing | `ligacoes` | bolts (6.3), fillet welds (6.2.5), 45 kN min (6.1.5.2) | efforts per node, bolt/weld data, exception flag |

## Orchestrator (one call runs the whole chain)

`calc/rodar_galpao.py` is the canonical runner: give it a project params dict
(geometry, base condition, chosen sections, loads, terça/base/knee data) and it
configures every module, runs Gates 5-9 in order, extracts the base and knee
efforts FROM the portico (not hardcoded), and writes one memorial per module +
`MEMORIAL-CONSOLIDADO.txt`. `PARAMS_REF` is the validated 20x10 reference and
reproduces it exactly (column 0.67, rafter 0.93 with the flange-brace-derived Lb;
2 flange braces/frame). The geometry is PARAMETRIC:
`gp.configurar(span, eave, ridge, bay, base_fixed, sections, loads)`,
`ti.configurar(...)`, and `build_galpao.configurar(length, span, eave_h, slope,
bay, export_dir, doc_name)` set any dimension; `estabilidade` re-syncs from the
portico automatically. Use the orchestrator instead of calling modules ad hoc.

## Run order for a full galpão

1. Gate 5 → `vento_nbr6123.compute(...)` with the site/geometry answers → net
   pressures. Feed into the portico wind case.
2. Gate 6 → set `galpao_portico` geometry/loads/`BASE_FIXED`; run
   `estabilidade_b1b2.analyse()` → amplified envelope + deslocabilidade + drift.
3. Gate 7 → `mao_francesa` on the rafter's governing combo to fix the flange-brace
   spacing (= the viga's Lb), then `check_nbr8800` (K=1) on the chosen profiles
   with that Lb and the amplified envelope. If it fails, `redimensionamento` to
   find the lightest passing profile+base. Then `tercas_nbr14762` (calling
   `distorcional_fsm` for Mdist if not dispensed), `base_chumbador`, `ligacoes`.
4. Gate 8 → swap placeholder sections for real ones from `perfis` / the
   supplier catalog (properties A CONFIRMAR).
5. Gate 9 → assemble the memoriais (one per module) into the deliverables.

## Known delegated gaps (state them, do not hide)

- Concrete anchor breakout / pull-out cone (NBR 6118 / ACI 318) is the
  foundation designer's scope — `base_chumbador` flags it, does not compute it.
- Block shear / plate limit states beyond bearing are not in `ligacoes`.
- Rigorous Ief / Wef,y for the purlin come from catalog/software; the module
  uses a conservative fallback and flags it.
- `secundarios_nbr8800`: the eave-strut axial now comes from the LONGITUDINAL
  wind drag (`vento.compute_longitudinal`, Fa/side). The drag Ca is read from
  NBR 6123 Figura 4 (a graph) → flagged A CONFIRMAR. The U-profile J/Cw for the
  girt FLT are catalog inputs (method is Anexo G). Still pending: consume Fa in
  the gable posts and the longitudinal bracing rods.

## Inputs the skill must have collected before running

Each cfg/case dict maps to gate answers. Do not run a module with invented
numbers — if an input is missing, ask (Gate question) or record it pending in
`notes/assumptions.md`. The example dicts at the bottom of each module
(`*_EXEMPLO`, `CASO_EXEMPLO_*`) show the exact keys each module expects.
