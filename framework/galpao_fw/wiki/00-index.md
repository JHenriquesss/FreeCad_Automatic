# galpao_fw — LLM wiki

**Pitch:** Framework Python que dimensiona/verifica galpão de aço (steel warehouse) fim-a-fim: pórtico 2D → 2ª ordem (MAES) → verificação NBR 8800 por peça → secundários/terças/ligações/base/fundação → modelo 3D FreeCAD + DXF + memorial PT. Engenheiro roda a skill; sênior revisa e assina (ART). Saídas em português. Unidades SI (m, kN).

Cwd primário: `D:\dev\FreeCad_Automatic\framework\galpao_fw`. Git root: `D:\dev\FreeCad_Automatic`. Norma-fonte: PDFs em `pesquisa/aço/` (nunca de memória).

## TOC
- [[01-architecture]] — spec-driven, cadeia de módulos, envelope, MAES, calc/model split
- [[02-test-tree]] — `_selftest()` por módulo, o que cada um assere
- [[03-phases]] — fases fechadas: revisão sênior 12 módulos (r2) · features pós-homolog · análise de lacunas (gaps+FLAGs) · **projeto executivo 2D (TechDraw)** · handoff/aguarda pareceres
- [[04-decisions]] — log de decisões/fixes normativos (D0–D45)
- [[05-glossary]] — termos de domínio (pórtico, MAES, ELU/ELS, FLT, Lb, sapata rígida, estaca, biela…)
- [[06-open-threads]] — **HANDOFF (continuar em outro chat)**, T7 pareceres pendentes, PR #1, backlog
- [[07-discovered-bugs]] — relatório detalhado de inconformidades e bugs descobertos no framework
- [[08-new-discovered-bugs]] — relatório detalhado de novas inconformidades e bugs descobertos sob as diretrizes técnicas de revisão de projetos

## Estado atual (2026-07-15)
**Nova auditoria de bugs com base nas Diretrizes Técnicas concluída.** Relatório detalhado gerado em [[08-new-discovered-bugs]]. Identificados 4 novos bugs/inconformidades críticas, incluindo omissão de cisalhamento em sapata de divisa, erro normativo de combinações de vento com sobrecarga favorável em pórticos, erro mecânico na flexo-tração do helper do nbr8800, e falta de travamento transversal para estacas simples ou duplas. Todos os 9 bugs originais do ciclo anterior permanecem resolvidos e verificados ([[07-discovered-bugs]]). Código preservado intacto.

## Estado anterior (2026-07-14)
**29 módulos matemáticos.** Balde 4 (fases 6.15–6.19) FECHADO **e HOMOLOGADO** — 6 itens
residuais de refino: **6.15** `props_I_mono.py` (perfil I monossimétrico → ramo mono
real do DG25, `dg25_ltb` mono-aware); **6.16** DG25 envelope FLB/TFY/ruptura §5.4.4–7;
**6.17** `forcas_localizadas.py` (NBR 8800 §5.7 + enrijecedor de apoio §5.7.9);
**6.18** `viga_equilibrio.py` (viga de divisa sobre estacas, wiring estaca/sapata em
`rodar_galpao`); **6.19** glyph solda AWS A2.4 headless (`DrawViewSymbol`+SVG) + PE09
legível. **5 pareceres → 9 correções reais** (7 bugs contra-segurança + 2 omissões),
cada uma conferida contra PDF/estática: `rt` hc²→hw², `kc` hc→hw, teto `Mp` Sxt→Sxc
(erratum DG25), M da viga `R'·e→P·e`, +cisalhamento/peso-próprio/pele na viga, glyph
arrow/other/both. 1 rejeição minha revertida com evidência (Mp Sxc). **REVISAO-INDICE
itens 45–49 ✅.** pytest **245 passed**, `smoke_executivo` **7/7**. Ver [[03-phases]],
[[04-decisions#D48]], [[06-open-threads#T12]]. **PENDENTE gate humano:** push branch +
merge PR. Commits `12ff107`→`01e14e7`.

## Estado 2026-07-13
**26 módulos matemáticos.** Balde 3 (fases 6.13–6.14) FECHADO na implementação —
resíduos NÃO-bug (crane já era 100% homologado): **6.13** `enrijecedor_painel.py`
(NBR 8800 §5.4.3.1, `kv=5+5/(a/h)²`, requisitos §5.4.3.1.3; relaxa cap h/tw≤260 do
Anexo H) e **6.14** DG25 full (`dg25_ltb.py` estendido: Cb tapered 5.4-1/2, Rpc/Rpg,
Mn nominal 3 regiões; `cross_check_capacidade` onde Cb NÃO cancela). Ambos INFORMATIVOS
(dimensionamento segue NBR). **Itens 43 (APROVADO COM LOUVOR) + 44 (validado)
HOMOLOGADOS (2026-07-13).** Item 43: 2 refutações confirmadas (eixo I singelo = plano
médio NBR; §5.4.3.2 ≠ tension field) + `a_min→a_max`. Item 44: `γ·f_r=F_eLTB` "mais
elegante"; 5% inelástico = diferença de método; F_L monossim. já coberto (5.4-15).
**REVISAO-INDICE itens 1–44 ✅, zero pendente.** Ver [[04-decisions#D47]],
[[06-open-threads#T11]]. **PENDENTE gate humano:** push branch + merge PR #5.

## Estado anterior (2026-07-10)
Galpão completo fim-a-fim. **18 módulos matemáticos** (+`nbr8400`) + features, selftest verde. Cálculo homologado (itens 1–27). **Fases 3–5 FECHADAS (2026-07-10):** (3) fundação profunda integrada ao ProjetoSpec + 3D (estaca/bloco/baldrame desenhados; `fundacao.tipo` gate); (4) ponte estendida — rodas motoras + NBR 8400-1:2019 (φ Tab.12 / N Tab.9 do PDF) + gate do fabricante; (5) **corte seccionado hachurado** nos detalhes (blocker T6 resolvido — DrawViewSection headless FreeCAD 1.1). `smoke_executivo` **5/5**. Commits 9ac3c4f→f912e98 na branch `revisao/homologacao-12-modulos`.
**Órfãos wired (fase 6):** calha (6.a), sapata_divisa (6.a), pórtico alma variável
(6.b), pórtico tesoura (6.c — cálculo NOVO método dos nós). Restou `neve` (não
escolhido). **3 tipos de pórtico**: prismatico | alma_variavel | tesoura.
**Pareceres itens 28–33 HOMOLOGADOS (2026-07-11)** — [[04-decisions#D44]],
[[06-open-threads#T8]]. **Backlog do parecer 6.b esgotado — fases 6.4–6.8, itens 34–38
HOMOLOGADOS (2026-07-11):** coluna tapered (+compressão global J.3), zona de painel do
joelho (`zona_painel.py`, §5.7.7+doubler), FLT de mísula (`flt_misula.py`, Anexo J),
sucção vento→tesoura (bug de sinal do uplift corrigido), alma esbelta (`alma_esbelta.py`,
Anexo H) — [[04-decisions#D45]], [[06-open-threads#T9]]. **REVISAO-INDICE.md 1–38 ✅,
zero pendente.** 8 alegações de erro grave refutadas com o PDF (imagens via SendUserFile),
1 bug real acolhido. **21 módulos matemáticos.** **PENDENTE gate humano:** merge PR #1+#4;
**push da branch** (bloqueado p/ assistente → usuário roda `git push`). [[06-open-threads]].

last-consolidated: 2026-07-14, sessions: 10 (fases 3–6.c + homologação itens 28–33 +
backlog parecer 6.b fases 6.4–6.8 itens 34–38 + balde 2 fases 6.9–6.12 itens 39–42 +
balde 3 fases 6.13–6.14 itens 43–44 + **balde 4 fases 6.15–6.19 itens 45–49**: perfil
I monossimétrico, DG25 envelope §5.4.4–7, forças localizadas §5.7, viga de equilíbrio
de divisa sobre estacas, glyph solda AWS A2.4; 9 correções de parecer)
