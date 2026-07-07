# Premissas e decisoes - galpao-nf982

Run guiado real da skill build-warehouse. Lote no norte fluminense (RJ).

## Gate T - Terreno (2026-07-05)
- Fonte: `inputs/lote.kml` (Google Earth). lon ~-41,017 / lat ~-21,628.
- Area do lote: **982,0 m2** (shoelace, projecao equirretangular local).
- OBB (eixos do lote): 44,4 x 22,4 m, girado 75,8 graus do Norte.
- Parametros urbanisticos (respostas do gate; valores TIPICOS - **A CONFIRMAR na
  consulta previa / lei de uso do solo do municipio**):
  - Taxa de ocupacao (TO): **60%** -> footprint max 589,2 m2.
  - Coef. de aproveitamento (CA): **1,0** -> area construida max 982,0 m2.
  - Taxa de permeabilidade (TP): **20%** -> permeavel min 196,4 m2 ;
    impermeavel max 785,6 m2.
  - Recuos: frente 5 / lateral 1,5 / fundos 3 m.
  - Pavimentos: 1.
- **Retangulo construivel: 41,4 x 14,4 m.** Footprint governado pela TO (589 m2).
- PENDENTE: confirmar TO/CA/TP/recuos na prefeitura; a orientacao da testada
  (assumida = lado menor do OBB) e o patio/pavimentacao externa impermeavel.

## Gate 0 - Uso e volumetria (2026-07-05) - VIAVEL
- Uso: **deposito / armazenagem**.
- Geometria: **vao 10 m x comprimento 20 m**, pe-direito **6 m** (= geometria da
  referencia validada). Footprint 200-228 m2 (com beirais) << TO 589 m2.
- **Ponte rolante LEVE ~100 kN** (entra ponte_rolante + console + combos C4/C5).
- Cabe no retangulo 41,4 x 14,4 ; TO/CA/TP OK ; sobra ~557 m2 de impermeavel p/ patio.

## Gate 1 - Cobertura e inclinacao (2026-07-05)
- Duas aguas simetrica ; inclinacao 10% (5,71 graus) ; cumeeira em 6,5 m.
- Telha trapezoidal simples de aco (~0,10 kN/m2).
- Drenagem: calha de beiral + condutores.

## Gate 2 - Secundarios e estabilidade (2026-07-05)
- BAY 5 m (5 porticos, 20 m / 4 vaos).
- Contraventamento em X (so-tracao) nos vaos de extremidade + escoras de beiral.
- Base ENGASTADA (controla o drift; vao 10 m com ponte).

## Gate 5 - Vento e sitio (2026-07-05)
- V0 = **35 m/s** (litoral norte fluminense - A CONFIRMAR na isopleta pela coordenada).
- Categoria **II** (aberto/plano) ; Classe **B** (dim 20 m) ; S1 = 1,00 ; S3 = **0,95** (deposito).
- Abertura dominante: **portao no oitao** (frontal) -> Cpi +0,8 (barlavento).

## Gate 4b - Batch-defaults
- Usuario optou por MANTER todos os defaults da referencia (planilha-defaults.md).
- Ponte: exemplo 100 kN, TUDO A CONFIRMAR na ficha do fabricante.

## Gate 3 - Fechamento das paredes (2026-07-05)
- **Alvenaria (meia-parede) ate 2,5 m + telha metalica acima**, nas LATERAIS.
- Oitoes (empenas) em telha (por causa do portao/porta). Peso ~0,12 kN/m2.
- NOTA ELS: meia-parede + telha nao e parede fragil cheia -> mantido o limite de
  flecha usual (H/300..H/150), nao H/500. Confirmar com o eng. se a alvenaria for
  ligada rigido a estrutura.

## FRAMEWORK (novo) - ProjetoSpec
- O projeto agora e um ProjetoSpec (calc/projeto_spec.py) - fonte unica da verdade.
  validar() BLOQUEIA calculo/desenho com campo pendente; mappers traduzem p/ os
  modulos. Spec do projeto: work/spec_nf982.py. Modelo/calculo reconstruidos SO do
  spec (sem default hardcoded / sem copia). massa separada agora: massa_aco_kg (~13,3 t) x massa_alvenaria_kg (~26,3 t) no takeoff. Antes misturava
  aco (~13,8 t) + alvenaria (~26 t) - a categoria separa; total conflaciona (rever).

## Gate 4 - Aberturas (2026-07-05) - CORRIGIDO apos apontamento do usuario
- Portao de veiculos: **oitao FRENTE, 4,0 x 4,5 m**.
- Porta de pessoas: **oitao FUNDO** (0,9 x 2,13 m).
- Janelas: **faixa nas duas laterais** (z 4,3-5,3 m).
- SEM porta lateral (o modelo da referencia tinha uma hardcoded - removida).
- Terreno: desenhado (poligono do lote, galpao centrado no OBB).
- NOTA: no 1o build eu pulei o Gate 4 e o build_galpao desenhou as aberturas
  HARDCODED da referencia (porta lateral, janelas, portao). Corrigido: aberturas
  agora sao config (ABERTURAS) do Gate 4; default so vale p/ a fixture 20x10.

## Resultado do calculo (Gates 5-11, orquestrador) - TUDO PASSA
- Coluna 0,66 ; viga 0,75 ; ELS drift OK (engastada).
- **Mao-francesa: 0 bracos** (com V0=35 a viga passa destravada em 5,0 m -> nao
  precisa; mf_stride=3 no modelo).
- Longarina 0,76 ; escora 0,06 ; oitao 0,33 ; barras 0,51 ; verga 0,04.
- Ponte: R_vert 132,9 kN ; viga de rolamento 0,39 ; Fa long 45,2 kN.
- Base governa C3_Gfav (M=44,4) ; joelho C2_uplift (M=44,2).
- Memoriais: `exports/memoria/` (MEMORIAL-CONSOLIDADO.txt + 1 por modulo).

## Modelo (build via MCP) - 2026-07-05
- 244 elementos, 0 interferencias, 13,78 t. FCStd/STEP em `exports/`.
- mf_stride=3 (0 mao-francesa) ; 2 tirantes de parede.

## PENDENCIAS / FINDINGS do run
- **A CONFIRMAR (prefeitura)**: TO/CA/TP/recuos ; orientacao da testada.
- **A CONFIRMAR (fabricante)**: dados da ponte (Q, pesos, phi, fracoes, Hvr, classe).
- **A CONFIRMAR**: V0 na isopleta ; Ca do arrasto (Figura 4) ; props/J/Cw UPE100 e VS500.
- [OK] Geometria da ponte no modelo: viga de rolamento (VS500) + consoles nos
  pilares (PONTE_MODELO). Ref: 2 vigas + 10 consoles, aco 17,05 t.
- [OK] Vento categorias I-V na Tabela 1 (Cat II intacta; demais A CONFIRMAR vs PDF).

