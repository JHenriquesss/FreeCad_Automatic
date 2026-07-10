# galpao_fw — LLM wiki

**Pitch:** Framework Python que dimensiona/verifica galpão de aço (steel warehouse) fim-a-fim: pórtico 2D → 2ª ordem (MAES) → verificação NBR 8800 por peça → secundários/terças/ligações/base/fundação → modelo 3D FreeCAD + DXF + memorial PT. Engenheiro roda a skill; sênior revisa e assina (ART). Saídas em português. Unidades SI (m, kN).

Cwd primário: `D:\dev\FreeCad_Automatic\framework\galpao_fw`. Git root: `D:\dev\FreeCad_Automatic`. Norma-fonte: PDFs em `pesquisa/aço/` (nunca de memória).

## TOC
- [[01-architecture]] — spec-driven, cadeia de módulos, envelope, MAES, calc/model split
- [[02-test-tree]] — `_selftest()` por módulo, o que cada um assere
- [[03-phases]] — fases fechadas: revisão sênior 12 módulos (r2) · features pós-homolog · análise de lacunas (gaps+FLAGs) · **projeto executivo 2D (TechDraw)** · handoff/aguarda pareceres
- [[04-decisions]] — log de decisões/fixes normativos (D0–D36)
- [[05-glossary]] — termos de domínio (pórtico, MAES, ELU/ELS, FLT, Lb, sapata rígida, estaca, biela…)
- [[06-open-threads]] — **HANDOFF (continuar em outro chat)**, T7 pareceres pendentes, PR #1, backlog

## Estado atual (2026-07-09)
Galpão completo fim-a-fim. **17 módulos matemáticos** + features, selftest verde. **Cálculo 100% homologado pelo sênior** (REVISAO-INDICE: itens 1–27 ✅, zero pendente, 2026-07-09). **Projeto executivo 2D FECHADO** (2026-07-09): 9 pranchas gerais + PE10–14 detalhes de ligação + memorial PDF, TechDraw headless, guard de cobertura (toda peça desenhada), `smoke_executivo` 4/4. **PR #4** aberto. Único adiado: detalhe de ligação nível fabricação (section+solda) — [[06-open-threads#T6]].

last-consolidated: 2026-07-09, sessions: 4 (bootstrap + features + lacunas/FLAGs + executivo-2D; construído do ciclo de revisão + sessão 07-09, sem sessions/*.md desta)
