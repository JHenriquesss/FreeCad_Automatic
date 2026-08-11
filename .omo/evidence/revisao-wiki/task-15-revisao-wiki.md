# Task 15 — Reconstrução das decisões D74–D79 (S19) em 04-decisions.md + correções task-9

- **Data da evidência:** 2026-08-11 (todo 15 do plano de revisão da wiki)
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (HEAD `6358157` = main, merge PR #171)
- **Arquivo editado (ÚNICO):** `framework/galpao_fw/wiki/04-decisions.md` — apêndice `## D74`–`## D79` entre D73 e D0 (política), **append-only puro: `git diff --numstat` = +18 inserções, 0 deleções** (639 → 657 linhas)
- **Formato:** UTF-8 sem BOM (verificado byte a byte: arquivo NÃO inicia com `EF BB BF`)
- **NENHUM outro arquivo da wiki editado; NENHUM commit; NENHUM código modificado**

---

## 1. Fonte de reconstrução (verificada)

- **Bloco S19** (00-index:66-75, linhas 69–74): descrição primária dos PRs #55–#61.
- **task-3** (arqueologia git): datas/PRs — merges `#55/#56/#57/#58` em 2026-07-22 (21:58–22:10Z) e `#59/#60/#61` em 2026-07-23 (00:15Z); #57 mergeado em branch intermediária, conteúdo na main via #59.
- **task-9** (cross-check): veredito de reconstrução por D# (3 plenas, 2 correção de nome, 1 fallback) — **autoridade sobre o texto escrito**.
- **task-6**: links `[[04-decisions#D74]]`–`[[04-decisions#D79]]` de 00-index quebrados por ausência de âncoras.
- **Código no worktree** (grep/read, todos os itens citados nas D7x CONFIRMADOS existentes — §4).

## 2. Decisões apendadas (resumo do texto — 6 entradas)

| D# | PR(s) | Data | Modo | Resumo (decisão) |
|---|---|---|---|---|
| D74 | #55 | 2026-07-22 | **plena** | Cherry-pick Gaps A3/C5 + wiki S18 para a main (merge `83570c9`); conteúdo presente: `console_ponte.mrd_flt_chapa` (console_ponte.py:38) + `escada._dimensiona_multi` (escada.py:22) — mesmo conteúdo de D73; alternativa rejeitada: reencadear merges empilhados |
| D75 | #56 | 2026-07-22 | **plena** | Exportador IFC4 (BIM) no `build_galpao.export()` via `ifc_map.py:20 ifc_tipo(nome)` (módulo puro, asserts C00→Column…CHUMBADOR→MechanicalFastener; 1,67 MB / 789 elementos no modelo real); alternativa rejeitada: export nativo do FreeCAD (GUI) |
| D76 | #57→#59 | 2026-07-22/23 | **correção de caminho** | `montar_modelo(headless=None)` auto-fallback bridge→freecadcmd (rodar_projeto.py:210-218); **corrige o caminho: conteúdo de #57 chegou à main via PR #59 (`5863532`)**; alternativa rejeitada: exigir bridge sempre |
| D77 | #58 | 2026-07-22 | **plena** | `modelo_neutro.py` + `ifc_emit.py` (ifcopenshell): IFC4 puro-Python direto do cálculo, sem FreeCAD (`emitir_ifc_do_spec` ifc_emit.py:523; wire rodar_projeto.py:528-540, degrada sem ifcopenshell); alternativa rejeitada: estender export do build_galpao |
| D78 | #60 | 2026-07-23 | **correção de nome** | **`secundarios_lineares` NÃO existe** (grep vazio em *.py); funções reais em `modelo_neutro.py`: `tercas()` :116, `girts()` :163, `tirantes_parede()` :198, `contrav_cobertura()` :222, `frame_completo()` :920 + `ifc_emit._perfil_ifc` :204 (perfil/marca reais como IfcMember); alternativa rejeitada: secundários fora do IFC puro |
| D79 | #61 | 2026-07-23 | **FALLBACK (c)** | Módulo `modelo_analitico.py` NÃO existe (ver §5); implementação real documentada: `galpao_portico.modelo_analitico()` (galpao_portico.py:305) + `ifc_emit.emitir_ifc_analitico` (ifc_emit.py:533: IfcStructuralAnalysisModel :548, IfcStructuralPointConnection :559, IfcBoundaryNodeCondition :569, IfcStructuralCurveMember :579) + `emitir_ifc_analitico_do_spec` (:632); `rodar_projeto.py:533-535` grava `{slug}.ifc` + `{slug}_analitico.ifc` em `EXPORT_DIR/ifc/` |

Formato das entradas idêntico às demais (D67–D73): `## Dn — PR #NN: título (data)` + corpo; data do git (task-3). Âncoras `## D74`…`## D79` criadas (cada header inicia com `## D74`/`D75`/… → os wikilinks `[[04-decisions#D7x]]` de 00-index passam a resolver por prefixo, mesmo padrão dos links D23/D24 etc. já funcionais).

## 3. Correções do task-9 aplicadas em D1–D73

- **Veredito do task-9 para 04-decisions.md:** as 10 decisões spot-checkadas (D52, D63, D64, D67, D40, D54, D69, D70, D71, D73) = **todas `ok`** — NENHUMA correção pendente em D1–D73 dentro deste arquivo (a inconsistência "Hatch"×"SvgHatch" atinge 03-phases:151 e 06-open-threads:364, fora do escopo deste todo — arquivos NÃO editados).
- **As 2 únicas marcações "corrigir" do task-9 neste arquivo** são D78 e D79 — correções de nome embutidas na própria reconstrução (§2): D78 cita as 5 funções reais (não `secundarios_lineares`); D79 documenta função+emissores (não o módulo inexistente).
- **Resultado:** zero alterações fora do apêndice — comprovado por `git diff --numstat` (+18/-0).

## 4. QA interno — cada D7x com função/arquivo citado EXISTENTE (verificado no worktree)

| D# | Verificação | Resultado |
|---|---|---|
| D74 | `console_ponte.py` → `def mrd_flt_chapa` :38; `escada.py` → `def _dimensiona_multi` :22 | ✅ |
| D75 | `ifc_map.py` → `def ifc_tipo(nome)` :20; docstring/asserts com as 8 categorias (IfcColumn/Beam/Member/Plate/Footing/Pile/Covering/MechanicalFastener) | ✅ |
| D76 | `rodar_projeto.py:210-218` → `montar_modelo(..., headless=None)` docstring "None (default) tenta o BRIDGE … cai automaticamente para o FREECADCMD HEADLESS"; `freecadcmd` candidatos :175-179 | ✅ |
| D77 | `ifc_emit.py` → `def emitir_ifc_do_spec` :523; `rodar_projeto.py:528-540` (import ifc_emit + `if EM.disponivel()`) | ✅ |
| D78 | `modelo_neutro.py` → `tercas` :116, `girts` :163, `tirantes_parede` :198, `contrav_cobertura` :222, `frame_completo` :920; `ifc_emit._perfil_ifc` :204; **`secundarios_lineares`: grep vazio (nome inexistente — correção aplicada)** | ✅ |
| D79 | `galpao_portico.py` → `def modelo_analitico()` :305; `ifc_emit.py` → `emitir_ifc_analitico` :533 (IfcStructuralAnalysisModel :548, IfcStructuralPointConnection :559, IfcBoundaryNodeCondition :569, IfcStructuralCurveMember :579), `emitir_ifc_analitico_do_spec` :632; `rodar_projeto.py:533-535` (`{slug}.ifc` / `{slug}_analitico.ifc` em `<out_dir>/ifc/`) | ✅ |

**Âncoras confirmadas** (grep `^## D7[4-9] `): D74:635, D75:638, D76:641, D77:644, D78:647, D79:650; **D0 preservado por último (653)** — 04-decisions.md agora com 657 linhas.

## 5. JUSTIFICATIVA do fallback da D79 (caminho (c) do plano — passos que falharam)

1. **Verificação no disco:** `glob framework/galpao_fw/modelo_analitico.py` no worktree → **nenhum arquivo** (o módulo citado em 00-index:74 e 05-glossary:46 não existe).
2. **Verificação no git/main:** `git ls-tree main -- framework/galpao_fw/modelo_analitico.py` → **vazio** (task-9 §5, não refeito — conferido na evidência do task-9 e confirmado pela ausência do arquivo no disco, que é espelho do main).
3. **Diff do PR #61** (`ea48acf`): o PR adicionou `tests/test_modelo_analitico.py` (+88) e tocou `ifc_emit.py` (+82) / `galpao_portico.py` (+52) / `modelo_neutro.py` (+38) / `rodar_projeto.py` (+18) — ou seja, a implementação analítica NUNCA foi um módulo próprio; é função + emissores.
4. **Fallback aplicado:** a D79 documenta a implementação REAL (função `galpao_portico.modelo_analitico()` + `ifc_emit.emitir_ifc_analitico*` com IfcStructuralAnalysisModel/PointConnection/BoundaryNodeCondition/CurveMember + gravação `{slug}_analitico.ifc` em `EXPORT_DIR/ifc/`), com a alternativa rejeitada explícita ("citar o módulo inexistente"). **Nada foi fabricado**: só o que está no código foi escrito.
5. **Nota para o todo 11:** 00-index:74 ("modelo_analitico (módulo)") e 05-glossary:46 continuam citando o módulo inexistente — correção de texto desses arquivos pertence ao todo 11 (fora do escopo: não editar outros arquivos da wiki).

## 6. Correções do task-9 NÃO aplicadas aqui (registro — fora de escopo)

| Item | Onde corrigir | Por que não aqui |
|---|---|---|
| "Hatch"→"SvgHatch" | 03-phases:151, 06-open-threads:364 | Outros arquivos da wiki (MUST NOT DO) |
| Placeholders `<6a>/<6b>/<6c>` | 03-phases:106/123/140 | Idem |
| Bloco "ATUAL" obsoleto / PR #1 | 03-phases:260-263, 06-open-threads:333-337 | Idem |
| 00-index:150 "sem commit" falso | 00-index | Idem |
| 00-index:74/73 nomes D79/D78 | 00-index | Todo 11 (00-index) — ver nota §5.5 |
| S19/S20–S42 faltantes em 03-phases | 03-phases | Todo 14 |
| Threads T# obsoletos | 06-open-threads | Todo 13 |

## 7. Resumo executivo

- **6 decisões apendadas** (D74–D79): **3 plenas** (D74 via #55, D75 via #56, D77 via #58), **2 com correção de nome** (D76: caminho #57→#59; D78: funções reais `tercas/girts/tirantes_parede/contrav_cobertura/frame_completo`, NÃO `secundarios_lineares`), **1 com FALLBACK** (D79: sem módulo `modelo_analitico.py` — documentada a implementação real).
- **Correções D1–D73 aplicadas:** nenhuma pendente verificada (10/10 spot-check `ok` no task-9); as 2 "corrigir" do task-9 (D78/D79) foram embutidas na reconstrução.
- **Âncoras:** `## D74`–`## D79` criadas → links `[[04-decisions#D7x]]` de 00-index passam a resolver.
- **Formato:** append-only puro (+18/-0 no diff), UTF-8 sem BOM, D0 (política) preservado por último.
- **Evidência em:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt\.omo\evidence\revisao-wiki\task-15-revisao-wiki.md` (UTF-8)
