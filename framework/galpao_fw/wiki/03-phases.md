# 03 — Fases

## FECHADA — Revisão sênior módulo-a-módulo (r2) — 2026-07-07
**Escopo:** conferência matemática/normativa dos 12 módulos de cálculo por engenheiro sênior (parecer colado pelo usuário) + auditoria independente. Regra: verificar CADA finding contra o PDF da norma (não de memória) e contra o código-fonte real (não o snippet do doc). Fixar defeitos reais; rejeitar findings inválidos com citação exata.

**Resultado:** 12/12 homologados. Docs `REVISAO-*.md` sincronizadas com código verbatim + respostas; `REVISAO-INDICE.md` rastreia status.

**Fixes de código (4):** ver [[04-decisions]] D2–D5.
**Pareceres rejeitados (3):** ligações esmagamento, contravento "Anexo L", mão-francesa "bugs de snippet". Ver [[04-decisions#D6]].

**Entregáveis:** commits `d668daf` (base…fundação), `d0638b8` (redim). Branch `revisao/homologacao-12-modulos` → PR #1.

## FECHADA — Features pós-homologação (punção, recalque, ancoragem, cone, cortante, fadiga, junta, sismo) — 2026-07-07/08
7 features novas homologadas pelo sênior (ciclo parecer→resposta). Ver [[04-decisions]] D8–D22 e `REVISAO-INDICE.md` (tabela de features). Base 100% nos modos do concreto (§9-§13: ancoragem, cone ACI, cortante-tríade, edge breakout, interação T-V).

## FECHADA — Análise de lacunas do galpão COMPLETO — 2026-07-08
**Escopo:** fechar TODOS os gaps de um projeto de galpão completo, na ordem pequenos→médios→grande. Depois, TODOS os FLAGs residuais. Regra zero-erro mantida (todo valor verificado no PDF via texto OU render de imagem; nunca de memória; Décourt/Aoki/Teixeira/Tab.14 lidas por imagem quando o OCR falhou).

**Gaps (6):** pequenos — furos ligações (6.3.9/10/11+Tab.14), Cpe local borda/canto (6123 Tab.4/5), telha vão×carga (14762 → `telha_cobertura.py`); médios — sismo→envelope (15421 §5.4 combinação excepcional no pórtico/base/joelho), viga de baldrame/amarração (`viga_baldrame.py`); grande — fundação profunda (`estaca_profunda.py`).

**FLAGs (16, todos fechados):** ver [[04-decisions]] D23–D32. Destaques: 3 métodos de estaca (Aoki-Velloso, Décourt-Quaresma, Teixeira 1996 — cross-check), tração/uplift, grupo (Converse-Labarre), atrito negativo, recalque de grupo, bloco de coroamento (biela 22.3.2 + ancoragem 9.3.2 + punção pilar/estaca), sismo θ/P-Δ (9.6) + 100/30, block shear (6.5.6), T-stub/prying (EN 1993-1-8).

**Entregáveis:** commits `c8d10de`→`7009b61` (~20). Todos: `_selftest()` PASSED, doc REVISAO-*.md, não-regressivos (ref 20×10 inalterada). Novos módulos: `telha_cobertura`, `viga_baldrame`, `estaca_profunda`.

## FECHADA — Projeto executivo 2D (TechDraw) + memorial PDF + detalhes de ligação — 2026-07-09
**Escopo:** 2D completo e genérico para qualquer projeto. Substituiu scripts de vistas à mão por TechDraw headless (`freecad.exe`). Ver [[04-decisions]] D33–D36.
- **Pranchas gerais (9):** cobertura, fundações, elevações, pórtico, contraventamento, det. base, det. joelho, fechamento, quadros. A1 ISO5457, PDF+SVG+DXF+PNG + `executivo.FCStd`.
- **Detalhes de ligação (PE10–14):** cumeeira, gusset cob/parede, clipe girt, console (só ponte) — auto-gerados, eixo curado por tipo. Total dinâmico: 13 (sem ponte) / 14 (ponte).
- **Guard de cobertura:** toda peça do modelo desenhada (`PREFIXOS_SEM_DESENHO`=VAO); guard anti-silhueta `_n_edges`≥15.
- **Memorial PDF:** `relatorio_calculo.py`, método+cálculo, no `build_final.py`.
- **Regressão:** `smoke_executivo.py` — 4 geometrias headless (padrão, vão>comp, baixo-largo, ponte) calc+3D(freecadcmd)+pranchas(freecad.exe)+PDF, sem MCP. Pré-flight sem freecad: carimbo (anti-`__PENDENTE__`) + cobertura. **4/4 OK.**
- **Entregáveis:** commits e696b84→b0c2e89. Branch → **PR #4**. Scripts antigos (`vistas_fc`,`dxf_vistas`,`techdraw_vistas`) removidos.
- **Fora de escopo (adiado):** detalhe de ligação nível fabricação (section+hachura+símbolo solda) — hoje elevação+arranjo, sizing no memorial. [[06-open-threads#T6]].

## FECHADA — Detalhe de ligação nível fabricação (A+B) — 2026-07-09
**Escopo:** callouts de fabricação nos detalhes de ligação, todo número rastreável ao CÁLCULO (fonte única). Decisão A+B; C (enriquecer 3D) rejeitado. Ver [[04-decisions#D37]].
- **Cálculo novo (compõe primitivos homologados, sem fórmula nova):** `gusset_ligacao.verifica_gusset` (tração/compressão Whitmore 30° AISC, block shear, solda — reusa `ligacoes`+`check_nbr8800`); `console_ponte.verifica_console` (grupo de solda elástico, dimensiona perna, cortante da chapa). Ambos `_selftest` PASSED. Wiring: `rodar_galpao` gate7-gusset/console + `res[*_adotado]`; `rodar_projeto.calcular` copia p/ `spec['estrutura']`.
- **Callouts (B):** `techdraw_exec.config_de_spec` passa joelho/gusset/console ao cfg; `_callout_fab` desenha leader+texto (joelho/cumeeira "N×db, chapa t"; gusset/console "chapa t, solda perna"). Sem número inventado (guard `mne-1`).
- **Corte seccionado (A):** `DrawViewSection` **falha headless** (`failed to create section CS`, mesmo em box trivial) → **fallback elevação** (já boa). Dado de fabricação entregue via callout. Símbolo AWS de solda ausente headless → texto. [[06-open-threads#T6]].
- **Regressão:** `smoke_executivo.py` 4/4 — callouts (cfg tem joelho/gusset sempre; console só ponte) + cobertura + edges≥15 + memorial PDF. Ref 20×10 inalterada (`mne-3` limpo).
- **PENDENTE sênior:** REVISAO-INDICE itens 28 (gusset) + 29 (console). Módulos entram no memorial PDF automático (`relatorio_calculo` lê consolidado).

## ATUAL — Handoff / aguardando pareceres — 2026-07-08
- **NADA pendente de implementação do lado do assistente.** Todos os gaps + FLAGs corrigíveis fechados.
- ~~6 pareceres sênior pendentes~~ → **TODOS HOMOLOGADOS 2026-07-09** (calhas, divisa, telha, vento §8, sismo §6; demais já eram). REVISAO-INDICE zero pendente. [[06-open-threads#T7]]
- PR #1 ainda aberto, aguarda merge do usuário. [[06-open-threads#T1]]
- Continuação em outro chat: ver [[06-open-threads#HANDOFF]].

## Status — 17 módulos matemáticos + features (todos com selftest verde)
12 r2 (Pórtico·Perfil·Vento·Terças·Secundários·Base·Ligações·Ponte·Mão-francesa·Contravento·Fundação·Redim) + Junta + Sismo + **Telha** + **Baldrame** + **Estaca profunda**.
