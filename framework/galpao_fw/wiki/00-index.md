# galpao_fw — LLM wiki

**Pitch:** Framework Python que dimensiona/verifica galpão de aço (steel warehouse) fim-a-fim: pórtico 2D → 2ª ordem (MAES) → verificação NBR 8800 por peça → secundários/terças/ligações/base/fundação → modelo 3D FreeCAD + DXF + memorial PT. Engenheiro roda a skill; sênior revisa e assina (ART). Saídas em português. Unidades SI (m, kN).

Cwd primário: `D:\dev\FreeCad_Automatic\framework\galpao_fw`. Git root: `D:\dev\FreeCad_Automatic`. Norma-fonte: PDFs em `pesquisa/aço/` (nunca de memória).

## TOC
- [[01-architecture]] — spec-driven, cadeia de módulos, envelope, MAES, calc/model split
- [[02-test-tree]] — `_selftest()` por módulo, o que cada um assere
- [[03-phases]] — fases fechadas: revisão sênior 12 módulos (r2) · features pós-homolog · análise de lacunas (gaps+FLAGs) · **projeto executivo 2D (TechDraw)** · handoff/aguarda pareceres
- [[04-decisions]] — log de decisões/fixes normativos (D0–D44)
- [[05-glossary]] — termos de domínio (pórtico, MAES, ELU/ELS, FLT, Lb, sapata rígida, estaca, biela…)
- [[06-open-threads]] — **HANDOFF (continuar em outro chat)**, T7 pareceres pendentes, PR #1, backlog

## Estado atual (2026-07-10)
Galpão completo fim-a-fim. **18 módulos matemáticos** (+`nbr8400`) + features, selftest verde. Cálculo homologado (itens 1–27). **Fases 3–5 FECHADAS (2026-07-10):** (3) fundação profunda integrada ao ProjetoSpec + 3D (estaca/bloco/baldrame desenhados; `fundacao.tipo` gate); (4) ponte estendida — rodas motoras + NBR 8400-1:2019 (φ Tab.12 / N Tab.9 do PDF) + gate do fabricante; (5) **corte seccionado hachurado** nos detalhes (blocker T6 resolvido — DrawViewSection headless FreeCAD 1.1). `smoke_executivo` **5/5**. Commits 9ac3c4f→f912e98 na branch `revisao/homologacao-12-modulos`.
**Órfãos wired (fase 6):** calha (6.a), sapata_divisa (6.a), pórtico alma variável
(6.b), pórtico tesoura (6.c — cálculo NOVO método dos nós). Restou `neve` (não
escolhido). **3 tipos de pórtico**: prismatico | alma_variavel | tesoura.
**Pareceres itens 28–33 HOMOLOGADOS (2026-07-11)** — REVISAO-INDICE.md 1–33 ✅, zero
pendente ([[04-decisions#D44]], [[06-open-threads#T8]]). 3 alegações de erro grave
refutadas com prova de bancada. **PENDENTE gate humano:** merge PR #1+#4; **push da
branch** (bloqueado p/ assistente → usuário roda `git push`). [[06-open-threads]].

last-consolidated: 2026-07-11, sessions: 7 (fases 3–6.c via /dv + homologação dos 6
pareceres sênior itens 28–33: gusset, console, fundação profunda, ponte 8400, alma
variável, tesoura)
