# galpao_fw — LLM wiki

**Pitch:** Framework Python que dimensiona/verifica galpão de aço (steel warehouse) fim-a-fim: pórtico 2D → 2ª ordem (MAES) → verificação NBR 8800 por peça → secundários/terças/ligações/base/fundação → modelo 3D FreeCAD + DXF + memorial PT. Engenheiro roda a skill; sênior revisa e assina (ART). Saídas em português. Unidades SI (m, kN).

Cwd primário: `D:\dev\FreeCad_Automatic\framework\galpao_fw`. Git root: `D:\dev\FreeCad_Automatic`. Norma-fonte: PDFs em `pesquisa/aço/` (nunca de memória).

## TOC
- [[01-architecture]] — spec-driven, cadeia de módulos, envelope, MAES, calc/model split
- [[02-test-tree]] — `_selftest()` por módulo, o que cada um assere
- [[03-phases]] — fases fechadas: revisão sênior 12 módulos (r2) · features pós-homolog · **análise de lacunas completa (gaps+FLAGs)** · ATUAL: handoff/aguarda pareceres
- [[04-decisions]] — log de decisões/fixes normativos (D0–D32)
- [[05-glossary]] — termos de domínio (pórtico, MAES, ELU/ELS, FLT, Lb, sapata rígida, estaca, biela…)
- [[06-open-threads]] — **HANDOFF (continuar em outro chat)**, T7 pareceres pendentes, PR #1, backlog

## Estado atual (2026-07-08)
Galpão completo fim-a-fim. **17 módulos matemáticos** + features, todos selftest verde. Análise de lacunas ENCERRADA (3 pequenas + 2 médias + 1 grande) + todos os FLAGs corrigíveis fechados. **Sem pendência de implementação**; aguarda 6 pareceres sênior. Ver [[06-open-threads#HANDOFF]].

last-consolidated: 2026-07-08, sessions: 3 (bootstrap + features + lacunas/FLAGs; construído do ciclo de revisão, sem sessions/*.md)
