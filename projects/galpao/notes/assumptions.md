# Assumptions

Record assumptions, missing inputs, and engineer decisions here.

## Active Assumptions (2026-07-04, conceptual model)

Confirmed by user:
- Vao transversal (span): 10 m; comprimento: 20 m.
- Tipologia: portico rigido de alma cheia.
- Pe-direito (eave): 6 m.
- Inclinacao telhado: 10% (~5.71 deg), duas aguas, cumeeira Z = 6.5 m.

Confirmado pelo usuario (Gate 6, 2026-07-05):
- BASES ENGASTADAS (fixed). Decisao: a base rotulada REPROVA (flecha lateral
  179 mm >> H/150; interacao viga 1,75). Com engaste + os perfis atuais
  (coluna HEA200 / viga HEA180) o portico PASSA (flecha 30,8 mm <= H/150 = 40 mm;
  interacoes coluna 0,67 / viga 0,87; B2 = 1,04 -> pequena deslocabilidade).
  Contrapartida: a fundacao recebe momento (~60 kN.m) -> dimensionar
  base_chumbador + sapata (projeto de fundacao, NBR 6118).

Assumed by agent (NOT confirmed — change freely):
- Espacamento de porticos: 5.0 m -> 4 vaos, 5 porticos nos eixos X = 0/5/10/15/20 m.
- Contraventamento em X nos vaos de extremidade (telhado horizontal + paredes laterais).
- Tercas (purlins) e longarinas (girts) em posicoes de placeholder.
- Secoes dos membros sao PLACEHOLDER (caixas retangulares nominais), apenas para
  visualizacao. NAO representam perfis dimensionados:
  - Colunas: 200 x 200 mm
  - Vigas/rafters: 200 x 150 mm
  - Vigas de beiral / cumeeira: 150 x 100 mm
  - Tercas / longarinas: 150 x 60 mm
  - Contraventamento: 80 x 80 mm

## Load Memo (Gate 5, 2026-07-04) - for engineer, NOT computed here

Design codes: ABNT NBR 8800 (steel), NBR 6123 (wind), NBR 14762 (cold-formed if
purlins/girts are cold-formed), NBR 14323/14432 (fire, TRRF 30 min).

### Permanent loads (self-weight, quantified from the model takeoff)

- Steel frame: ~10.65 t total. Roof steel (rafters+purlins+sag rods+bracing)
  distributes to roughly 0.12-0.15 kN/m2 of roof plan; columns/struts/gable posts
  carry to the bases.
- Roof cladding (trapezoidal 0.65 mm): ~1026 kg -> ~0.05 kN/m2 over 200 m2.
- Wall cladding: ~1650 kg on the walls.
- Gutters (self-supporting 5 mm plate): ~1240 kg -> significant eave line load,
  ~0.6 kN/m per gutter over 20 m; hand to engineer as an eave load.
- Suspended loads (user-confirmed): lighting/ducts on the bottom chord - assume a
  provisional ~0.10-0.15 kN/m2 until the real services are defined. PENDING value.

### Variable loads

- Roof live/maintenance: ~0.25 kN/m2 (NBR 8800 minimum) - confirm.
- Wind (NBR 6123): basic speed V0 = 40 m/s; terrain Category II (open flat
  field); topography factor S1 = 1.0 assumed (flat site - confirm topography);
  S2 by Cat II + building height ~6.5 m; S3 statistical by use. Engineer to derive
  pressure coefficients (walls, roof, internal pressure with the openings modeled
  in Gate 4) and the wind load cases. High-wind site: wind likely governs.
- No crane, no mezzanine, no solar (this project).

### Serviceability (SLS)

- Cladding is metal sheet full height -> flexible frame acceptable; lateral drift
  limit ~H/300 (NBR 8800 default) is adequate (no masonry to protect). Confirm.
- Roof/purlin vertical deflection limit ~L/200. Ponding avoided (slope 10% > 5%).

### Fire (TRRF 30 min, NBR 14432/14323)

- 30 min is normally met with thin intumescent paint -> negligible added volume,
  NO geometric clash impact, so no protection envelope modeled. If the engineer
  requires sprayed mortar/board instead, model the added thickness and re-run the
  clash check against cladding and openings.

### Temperature

- Building length 20 m << expansion-joint trigger; no thermal joint needed.
  Record local temperature range for the engineer if thermal effects are checked.

## Engineer Approval Required

- Member sizes.
- Load combinations.
- Connections.
- Base plates and anchors.
- Durability/coating system.
- Fabrication and mounting details.
- Frame spacing, bracing layout, purlin/girt spacing (currently assumed).
