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

## Estado atual (2026-07-13)
**25 módulos matemáticos.** Balde 2 do parecer 6.b FECHADO — fases 6.9–6.12, itens
39–42 HOMOLOGADOS (2026-07-13): M-V no joelho (`tensao_ponto.py`, §5.5.2.3), cortante
de mesas inclinadas (`cortante_tapered.py`, equilíbrio), vento por zona 90°+0°
(`tesoura`/`vento_nbr6123`, Tabela 5), cross-check AISC DG25 (`dg25_ltb.py`, validação
informativa). **REVISAO-INDICE itens 1–42 ✅, zero pendente.** 2 bugs reais acolhidos
(braço `h_0`; vento 0° longitudinal), 1 refutação com prova (Cpi). Ver
[[04-decisions#D46]], [[06-open-threads#T10]]. **PENDENTE gate humano:** push da branch
`revisao/homologacao-12-modulos` (bloqueado p/ assistente) + merge PR.

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

last-consolidated: 2026-07-13, sessions: 9 (fases 3–6.c + homologação itens 28–33 +
backlog parecer 6.b fases 6.4–6.8 itens 34–38 + balde 2 fases 6.9–6.12 itens 39–42:
M-V §5.5.2.3, cortante mesas inclinadas, vento por zona 90°+0°, cross-check DG25)
