# Task 12 — Atualização de `01-architecture.md`: verticais multidisciplina, turnkey federado, BIM federado e executivo

- **Data:** 2026-08-11
- **Executor:** Sisyphus-Junior (todo 12 do plano de revisão da wiki)
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (branch `docs/revisao-wiki-2026-08-11`)
- **Arquivo editado (ÚNICO):** `framework\galpao_fw\wiki\01-architecture.md` (75 → 164 linhas; UTF-8 preservado — edição in place via `edit`, sem reescrita de encoding; conferido por leitura após a edição, nenhum caractere corrompido)
- **Fonte dos fatos:** task-1 (inventário 135 módulos — categorias/normas/wiring), task-7 (vereditos módulos/funções + PATCH LIST), task-3 (timeline PRs: S20 #81–#101, S21–26 #102–#106, S27–30 #107–#110, S32 #112, S36 #116, S38 #118, turnkey federado #124–#134, S39 #136–#147, S42 #162–#171) + **grep real no código** (nunca API inventada)
- **Saídas:** esta evidência (diff resumido + correções + confirmações de grep + QA) — NENHUM commit, NENHUM código alterado, NENHUM outro arquivo da wiki tocado

---

## 1. Resumo do diff (por seção)

`git diff --stat` → `01-architecture.md | 95 ++… 1 file changed, 92 insertions(+), 3 deletions(-)`

| Seção do arquivo | O que mudou |
|---|---|
| Princípios (3–7) | **INALTERADA** (task-7 não marcou nada errado) |
| Cadeia de cálculo / Envelope (9–19) | **INALTERADA** |
| Tabela de módulos (21–36) | **ESTENDIDA** com 9 grupos novos (ver §2) + 2 células corrigidas (ver §3) |
| Sismo / divisa / fundação / quadro / auditoria (47–71) | **INALTERADA** |
| Projeto executivo do aço (73–77) | **INALTERADA** |
| **NOVO** — Verticais multidisciplina (79–106) | 5 sub-blocos (concreto, elétrico, incêndio/AVCB, hidráulica, climatização): orquestrador + sub-módulos + normas + padrão stateless |
| **NOVO** — Turnkey federado (108–127) | `galpao_turnkey.rodar(spec)`, `DISCIPLINAS`, isolamento de falha, `ATENDE`, `caderno_turnkey`, apoio turnkey STATELESS |
| **NOVO** — BIM federado (129–143) | IFC federado, clash AABB, `build_federado` OCCT, coordenação, `compatibilizacao` BCF-like |
| **NOVO** — Executivo dos verticais (145–158) | `techdraw_*` (A1) + `desenho_*` (SVG puro) + `executivo_concreto` |
| Convenções (160–164) | 1 correção (item 56 do task-7: `_pt()` → `_vg`) |

**Regra da tabela respeitada:** 9 grupos novos ≤ 12 → **uma tabela estendida**, NENHUMA segunda tabela (e nunca ambas).

---

## 2. Tabela de módulos — 9 grupos novos adicionados (após "Geometria/saída")

| Grupo novo | Módulos citados (todos existem — task-1/grep) |
|---|---|
| Verticais — concreto | `galpao_concreto` (orquestrador), `pilar_concreto`, `viga_concreto`, `viga_protendida`, `perdas_protensao_nbr6118`, `premoldado_nbr9062`, `fogo_nbr15200`, `fissuracao_nbr6118`, `estabilidade_global_nbr6118`, `torcao_nbr6118`, `geotecnia_spt`, `piso_industrial` |
| Verticais — elétrico | `galpao_eletrico` (orquestrador), `cargas_eletricas`, `condutores_nbr5410`, `curto_circuito`, `protecao_nbr5410`, `fator_potencia`, `subestacao_nbr14039`, `aterramento_nbr15749`, `spda_nbr5419`, `luminotecnica_nbr8995`, `iluminacao_externa_nbr5101`, `instalacao_eletrica`, `fotovoltaico` |
| Verticais — incêndio/AVCB | `galpao_seguranca_incendio` (orquestrador), `iluminacao_emergencia_nbr10898`, `sinalizacao_nbr16820`, `deteccao_alarme_nbr17240`, `proteccao_sprinklers_nbr10897`, `hidrantes_nbr13714` |
| Verticais — hidráulica | `galpao_hidraulica` (orquestrador), `hidraulica_predial`, `esgoto_reuso` |
| Verticais — climatização | `galpao_climatizacao` (orquestrador), `climatizacao_nbr16401` |
| Turnkey | `galpao_turnkey`, `caderno_turnkey`, `caderno_encargos`, `compatibilizacao`, `pacote_legal`, `orcamento`, `cronograma`, `terraplenagem` |
| BIM federado / build 3D | `build_federado`, `build_concreto`, `build_eletrico`, `desenho_coordenacao`, `techdraw_coordenacao` |
| Executivo dos verticais | `techdraw_concreto`, `techdraw_eletrico`, `techdraw_incendio`, `techdraw_hidraulica`, `techdraw_climatizacao`, `desenho_concreto`, `desenho_eletrico`, `desenho_incendio`, `desenho_hidraulica`, `desenho_climatizacao`, `desenho_piso`, `executivo_concreto` |

**Cobertura da lista-alvo (28 "faltante-na-wiki" do task-7 §3.3): 26/28 na tabela.**
Excluídos com justificativa: `demo_engenheiro` e `tools_probe_pe13` (utilitários de dev — demo e harness de medição; não são módulos de produção de disciplina; `tools_probe_pe13` é citado no task-1 §1.3 como utilitário sem docstring). Módulos já presentes em outra linha da tabela (ex.: `calhas`, `estaca_profunda`, `viga_baldrame`, `viga_equilibrio`, `sapata_divisa`, `ifc_emit`/`ifc_map`/`modelo_neutro`, `techdraw_exec`) **não foram duplicados**.

---

## 3. Correções aplicadas (todas com origem no task-7 — PATCH LIST §6.1)

| Local | Antes | Depois | Origem |
|---|---|---|---|
| Tabela, Interoperabilidade BIM (era linha 33) | `**modelo_analitico**` como módulo | "+ analítico via `galpao_portico.modelo_analitico()` e `ifc_emit.emitir_ifc_analitico` (não é módulo próprio)" | task-7 item 43 (corrigir; sugestão: função `galpao_portico.modelo_analitico()` galpao_portico.py:305 + `ifc_emit.emitir_ifc_analitico` ifc_emit.py:533) |
| Tabela, Geometria/saída (era linha 36) | `dxf_vistas` listado | removido; linha = `build_galpao`, `terreno` (KML), `techdraw_exec` (pranchas A1) | task-7 item 45 (corrigir; `dxf_vistas` removido em D33 — 03-phases:225; sugestão: Geometria/saída = build_galpao + terreno (+techdraw_exec)) |
| Convenções (era linha 75) | `_pt()` troca ponto por vírgula | `_vg` (relatorio_calculo) troca ponto decimal por vírgula… | task-7 item 56 (corrigir; função real `relatorio_calculo._vg` relatorio_calculo.py:276-278; `_pt` existe só local em console_ponte.py:212) |

**Não aplicadas em 01-architecture (não pertencem a este arquivo):** `secundarios_lineares`/`por_marca` (00-index), `CutSurfaceDisplay="Hatch"` (03-phases/06-open-threads), `neve` órfã (00-index:232-234 e 03-phases:141-142 — 01-architecture nunca afirmou que neve é órfã; nenhuma menção a corrigir aqui). "Princípios"/pipeline: task-7 **não marcou nada errado** → intactos.

---

## 4. Confirmações de grep (entry points — grep real, worktree)

### 4.1 Padrão stateless das 5 verticais (confirmado por grep `def` em cada orquestrador)

| Orquestrador | `rodar` | `membros_bim` | `emitir_bim` | `montar_pranchas` | `_selftest` |
|---|---|---|---|---|---|
| galpao_concreto.py | :74 | :301 | :396 | :439 | :551 |
| galpao_eletrico.py | :59 | :401 | :479 | :317 | :526 |
| galpao_seguranca_incendio.py | :27 | :241 | :330 | :122 | :372 |
| galpao_hidraulica.py | :39 | :239 | :296 | :307 | :380 |
| galpao_climatizacao.py | :28 | :74 | :107 | :118 | :191 |

### 4.2 Turnkey federado (galpao_turnkey.py)

- `def rodar(spec, out_dir=None)` — **:138** ✓
- `DISCIPLINAS = ("concreto", "aco", "eletrico", "incendio", "climatizacao", "hidraulica")` — **:40** ✓ (6 disciplinas)
- Isolamento de falha: :161 `disciplinas[nome] = {"rodou": False, "ATENDE": False, "reprovados": ["ERRO"]}`; :167 `reprovados = [n for n in DISCIPLINAS if disciplinas.get(n, {}).get("ATENDE") is False]` ✓
- ATENDE global: :170 `"ATENDE": len(executadas) > 0 and len(reprovados) == 0` ✓
- `def emitir_bim(R, out_dir, spec=None, nome="GalpaoTurnkey")` — :253 ✓; `def montar_3d_federado(...)` — :313 ✓; `def checa_interferencia_federada(R, spec=None, folga=1.0, vol_min=1000.0)` — :595 ✓ (comentário :602: clash "nao entra no ATENDE do rodar") ✓; `_clash_esperado` (triagem esperado×revisar) — citado no task-7 item 4 (:524) ✓

### 4.3 caderno_turnkey.py

- `def montar_caderno(spec, out_dir, ...)` — :272 ✓; `def montar_caderno_de_pdfs(...)` (PURO, só fitz) — :173 ✓; `_selftest` :342 ✓. Cabeçalho :9: "Reusa o motor de mesclagem do dossie.py (PyMuPDF/fitz)"; fitz usado em :150/:160/:167/:181/:185/:209 ✓

### 4.4 build_federado.py / compatibilizacao.py

- `build_federado.run()` — :258 ✓; `_interferencias_cross(doc, disc_de, vol_min)` — :180 ✓; `_TIPOS_IGNORADOS = {"Covering", "Cladding"}` — :34 ✓ (fechamento/telha fora do clash)
- `compatibilizacao.gerar_pendencias(rep_clash, prefixo="CLH")` — :79 ✓; `matriz_coordenacao(rep_clash)` — :120 ✓; `bcf_topics(...)` — :133 ✓; `relatorio_pt(...)` — :157 ✓; docstring :16 "Relatorio formal de compatibilizacao: clash federado -> pendencias rastreaveis (BCF-like)" ✓

### 4.5 Executivo dos verticais (grep `def gerar_executivo_*` / `config_de_spec` / `script_bootstrap`)

| Módulo | `gerar_executivo_*` | `config_de_spec` | `script_bootstrap` |
|---|---|---|---|
| techdraw_concreto.py | :159 | :283 | :392 |
| techdraw_eletrico.py | :131 | :252 | :352 |
| techdraw_incendio.py | :80 | :184 | :282 |
| techdraw_hidraulica.py | :59 | :158 | :237 |
| techdraw_climatizacao.py | :52 | :151 | :210 |
| techdraw_coordenacao.py | :80 | :184 | :259 |

Desenhos SVG puro-Python confirmados: `desenho_concreto.planta_formas_svg` (:162)/`prancha_armacao_svg` (:94), `desenho_eletrico.diagrama_unifilar_svg` (:93)/`quadro_cargas_svg` (:182)/`planta_eletrica_svg` (:233), `desenho_incendio.planta_seguranca_svg` (:181), `desenho_hidraulica.esquema_hidraulica_svg` (:37), `desenho_climatizacao.esquema_climatizacao_svg` (:34), `desenho_coordenacao.coordenacao_svg` (:136), `desenho_piso.planta_juntas_svg` (:26), `executivo_concreto.quadro_de_aco` (:57)/`resumo_aco` (:122) ✓

### 4.6 Correções task-7 reconfirmadas por grep antes de escrever

- `galpao_portico.py:305 def modelo_analitico()` ✓; `ifc_emit.py:533 def emitir_ifc_analitico(...)` ✓ (e :632 `emitir_ifc_analitico_do_spec`)
- `relatorio_calculo.py:276 def _vg(s)` ✓
- `dxf_vistas` — NÃO existe (removido em D33; ausente do inventário task-1) ✓

---

## 5. QA interno (registro)

1. **Por vertical (aberto o orquestrador + inventário task-1):** entry point `def rodar` confirmado por grep (linhas §4.1) e ≥2 sub-módulos reais citados por vertical: concreto (`pilar_concreto`, `viga_concreto`, +10), elétrico (`cargas_eletricas`, `condutores_nbr5410`, +11), incêndio (`iluminacao_emergencia_nbr10898`, `sinalizacao_nbr16820`, +3), hidráulica (`hidraulica_predial`, `esgoto_reuso`), climatização (`climatizacao_nbr16401`). Normas por vertical extraídas da coluna "normas" do task-1 (docstrings), nunca de memória: concreto NBR 6118/9062/6122+8681; elétrico NBR 5410/14039/5419/8995/5101/15749+Mamede; incêndio NBR 10898/16820/17240/10897/13714; hidráulica NBR 5626:2020/8160/10844; climatização NBR 16401.
2. **Função citada inexistente → nenhuma encontrada.** Todos os nomes de função/módulo na versão final foram conferidos: §4.1–4.6 por grep; nomes de módulos cruzados com a tabela do task-1 (135 módulos). Zero API inventada.
3. **Encoding:** arquivo lido com Read (UTF-8) antes e depois; edição in place; nenhum caractere acentuado corrompido (conferido "pré-moldado", "incêndio", "vírgula" na leitura pós-edição).
4. **Escopo do diff:** `git diff` = 92 inserções + 3 deleções; as 3 deleções são exatamente as células corrigidas (task-7 §6.1: itens 43, 45, 56). Nenhum conteúdo do aço (linhas 1–77 originais) removido; "Princípios" e pipeline intocados (task-7 não marcou).
5. **Nenhum outro arquivo tocado:** apenas `wiki/01-architecture.md` + esta evidência em `.omo/evidence/revisao-wiki/`.

---

## 6. Garantias

- Nenhum código modificado; nenhum commit; nenhum outro arquivo da wiki (00/02/03/04/05/06) editado.
- Evidência escrita em UTF-8 explícito.
