# Task 6 — Checagem completa de links `[[…]]` e âncoras nos 7 arquivos da wiki

## Metadados

| item | valor |
|---|---|
| data | 2026-08-11 |
| worktree | `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` |
| wiki | `framework\galpao_fw\wiki\` (7 arquivos: 00-index, 01-architecture, 02-test-tree, 03-phases, 04-decisions, 05-glossary, 06-open-threads) |
| python | venv do repo principal por caminho absoluto (`FreeCad_Automatic\framework\galpao_fw\.venv\Scripts\python.exe`) — **usado com sucesso, sem fallback** |
| script | `%TEMP%\opencode\task6_links.py` (read-only; leitura utf-8-sig, saída utf-8) |
| padrão de extração | `re.findall(r'\[\[(.*?)\]\]')` linha a linha, com número da linha |
| âncoras | grep de `^#{1,3} ` em cada arquivo-alvo; âncora resolve por token inicial exato (ex.: `#D45` → `## D45 - …`) ou igualdade exata de título completo (ex.: 04-decisions:319) |
| arquivos wiki editados | **NENHUM** (checagem read-only) |

## Resumo

| métrica | valor |
|---|---|
| total de links `[[…]]` | 223 |
| ok | 212 |
| quebrado-ancla | 10 |
| quebrado-arquivo | 1 |
| arquivo-ausente | 0 |

## Quebrados CONHECIDOS (confirmados)

| link | origem arquivo:linha | status |
|---|---|---|
| `[[../memory]]` | 00-index.md:26 | quebrado-arquivo |
| `[[04-decisions#D74]]` | 00-index.md:69 | quebrado-ancla |
| `[[04-decisions#D75]]` | 00-index.md:70 | quebrado-ancla |
| `[[04-decisions#D76]]` | 00-index.md:71 | quebrado-ancla |
| `[[04-decisions#D77]]` | 00-index.md:72 | quebrado-ancla |
| `[[04-decisions#D78]]` | 00-index.md:73 | quebrado-ancla |
| `[[04-decisions#D79]]` | 00-index.md:74 | quebrado-ancla |

- `memory/*.md` em prosa (não `[[ ]]`): 00-index:20 e 250; 06-open-threads:4 (`memory/janela-dupla-conversao-aberta.md`) e 7 (`memory/saturacao-silenciosa-padrao.md`) — confirmados inexistentes (ver seção de caminhos externos).

## Quebrados NOVOS (encontrados além dos conhecidos)

| link | origem arquivo:linha | status | sugestão |
|---|---|---|---|
| `[[06-open-threads#T22]]` | 00-index.md:75 | quebrado-ancla | 06-open-threads.md nao tem header T22 (TOC 00-index:13 tambem o cita) — criar thread T22 (S19 IFC/BIM) ou apontar p/ thread existente da S19 |
| `[[04-decisions#D53?]]` | 06-open-threads.md:137 | quebrado-ancla | ancora com '?' residual — corrigir p/ #D53 (header '## D53 - vento correto: uplift, Cpe e Cpi por abertura (2026-07-17)' existe) |
| `[[03-phases#FECHADA — Projeto executivo 2D]]` | 06-open-threads.md:359 | quebrado-ancla | header existe por prefixo: '## FECHADA - Projeto executivo 2D (TechDraw) + memorial PDF + detalhes de ligacao - 2026-07-09' — usar titulo completo (tracinho, nao travessao) ou ancora curta; mesmo padrao OK em 04-decisions:319 |
| `[[03-phases#FECHADA — Corte seccionado 2D]]` | 06-open-threads.md:365 | quebrado-ancla | header existe por prefixo: '## FECHADA - Corte seccionado 2D (fase 5) - 2026-07-10' — usar titulo completo (tracinho, nao travessao) ou ancora curta |

## QA interno (obrigatório)

1. **12 âncoras "ok" verificadas MANUALMENTE** (abrir alvo + grep do header): T15 (06:144), T16 (06:93), T17 (06:69), T12 (06:243), T7 (06:330), T8 (06:326), D67 (04:541), D73 (04:628), D49 (04:321), D6 (04:21), D45 (04:164), D46 (04:210) — **todas OK** (header existe com token inicial exato).
2. **1 âncora de título completo** verificada manualmente: `[[03-phases#FECHADA - Balde 4 (backlog de gaps) fases 6.15-6.19 + homologação 45-49 - 2026-07-13/14]]` (04-decisions:319) → header exato em 03-phases:19 — **OK** (igualdade exata).
3. **Ciclo de correção de padrão (falso-quebrado → re-execução):** rodada 1 reportou 205 `quebrado-arquivo` porque links são escritos SEM extensão (ex.: `[[04-decisions#D67]]`); corrigido o padrão (fallback `arquivo + ".md"` quando `arquivo` não existe) → **rodada 2: 212 ok / 11 quebrados**. Confirmado que não havia falso-ok remanescente (D53?, T22 e as 2 âncoras FECHADA com travessão são quebras reais, não ruído do padrão).
4. Codepoints verificados: âncoras FECHADA de 06:359/365 contêm travessão em-dash (U+2014) e título truncado — não batem com os headers (hífen U+002D, título completo).

## Tabela completa (223 links)

| link | origem arquivo:linha | status | sugestão |
|---|---|---|---|
| `[[01-architecture]]` | 00-index.md:8 | ok | — |
| `[[02-test-tree]]` | 00-index.md:9 | ok | — |
| `[[03-phases]]` | 00-index.md:10 | ok | — |
| `[[04-decisions]]` | 00-index.md:11 | ok | — |
| `[[05-glossary]]` | 00-index.md:12 | ok | — |
| `[[06-open-threads]]` | 00-index.md:13 | ok | — |
| `[[../memory]]` | 00-index.md:26 | quebrado-arquivo | memory/ nao existe em nenhum nivel do worktree (dirs: 0, memory.md: 0) — criar dir (todo 11/16) ou remover o link |
| `[[04-decisions#D74]]` | 00-index.md:69 | quebrado-ancla | 04-decisions.md termina em D73 — criar entradas D74–D79 (todo 15) ou ajustar/remover o link |
| `[[04-decisions#D75]]` | 00-index.md:70 | quebrado-ancla | 04-decisions.md termina em D73 — criar entradas D74–D79 (todo 15) ou ajustar/remover o link |
| `[[04-decisions#D76]]` | 00-index.md:71 | quebrado-ancla | 04-decisions.md termina em D73 — criar entradas D74–D79 (todo 15) ou ajustar/remover o link |
| `[[04-decisions#D77]]` | 00-index.md:72 | quebrado-ancla | 04-decisions.md termina em D73 — criar entradas D74–D79 (todo 15) ou ajustar/remover o link |
| `[[04-decisions#D78]]` | 00-index.md:73 | quebrado-ancla | 04-decisions.md termina em D73 — criar entradas D74–D79 (todo 15) ou ajustar/remover o link |
| `[[04-decisions#D79]]` | 00-index.md:74 | quebrado-ancla | 04-decisions.md termina em D73 — criar entradas D74–D79 (todo 15) ou ajustar/remover o link |
| `[[03-phases]]` | 00-index.md:75 | ok | — |
| `[[06-open-threads#T22]]` | 00-index.md:75 | quebrado-ancla | 06-open-threads.md nao tem header T22 (TOC 00-index:13 tambem o cita) — criar thread T22 (S19 IFC/BIM) ou apontar p/ thread existente da S19 |
| `[[04-decisions#D71]]` | 00-index.md:86 | ok | — |
| `[[04-decisions#D71]]` | 00-index.md:87 | ok | — |
| `[[04-decisions#D72]]` | 00-index.md:90 | ok | — |
| `[[04-decisions#D72]]` | 00-index.md:91 | ok | — |
| `[[04-decisions#D72]]` | 00-index.md:92 | ok | — |
| `[[03-phases]]` | 00-index.md:93 | ok | — |
| `[[06-open-threads#T20]]` | 00-index.md:93 | ok | — |
| `[[04-decisions#D70]]` | 00-index.md:99 | ok | — |
| `[[04-decisions#D70]]` | 00-index.md:101 | ok | — |
| `[[04-decisions#D70]]` | 00-index.md:102 | ok | — |
| `[[04-decisions#D70]]` | 00-index.md:103 | ok | — |
| `[[04-decisions#D70]]` | 00-index.md:104 | ok | — |
| `[[04-decisions#D70]]` | 00-index.md:105 | ok | — |
| `[[04-decisions#D70]]` | 00-index.md:106 | ok | — |
| `[[03-phases]]` | 00-index.md:107 | ok | — |
| `[[06-open-threads#T19]]` | 00-index.md:107 | ok | — |
| `[[04-decisions#D68]]` | 00-index.md:114 | ok | — |
| `[[04-decisions#D68]]` | 00-index.md:115 | ok | — |
| `[[04-decisions#D68]]` | 00-index.md:116 | ok | — |
| `[[04-decisions#D68]]` | 00-index.md:117 | ok | — |
| `[[04-decisions#D68]]` | 00-index.md:118 | ok | — |
| `[[04-decisions#D68]]` | 00-index.md:119 | ok | — |
| `[[04-decisions#D69]]` | 00-index.md:121 | ok | — |
| `[[04-decisions#D69]]` | 00-index.md:122 | ok | — |
| `[[04-decisions#D69]]` | 00-index.md:123 | ok | — |
| `[[04-decisions#D69]]` | 00-index.md:124 | ok | — |
| `[[04-decisions#D69]]` | 00-index.md:125 | ok | — |
| `[[03-phases]]` | 00-index.md:126 | ok | — |
| `[[06-open-threads#T18]]` | 00-index.md:126 | ok | — |
| `[[04-decisions#D67]]` | 00-index.md:137 | ok | — |
| `[[04-decisions#D67]]` | 00-index.md:142 | ok | — |
| `[[06-open-threads#T17]]` | 00-index.md:142 | ok | — |
| `[[04-decisions#D67]]` | 00-index.md:145 | ok | — |
| `[[03-phases]]` | 00-index.md:147 | ok | — |
| `[[06-open-threads#T17]]` | 00-index.md:147 | ok | — |
| `[[04-decisions#D52]]` | 00-index.md:152 | ok | — |
| `[[04-decisions#D57]]` | 00-index.md:153 | ok | — |
| `[[06-open-threads#T15]]` | 00-index.md:153 | ok | — |
| `[[04-decisions#D52]]` | 00-index.md:156 | ok | — |
| `[[04-decisions#D53]]` | 00-index.md:158 | ok | — |
| `[[04-decisions#D54]]` | 00-index.md:160 | ok | — |
| `[[04-decisions#D55]]` | 00-index.md:162 | ok | — |
| `[[04-decisions#D56]]` | 00-index.md:165 | ok | — |
| `[[04-decisions#D57]]` | 00-index.md:168 | ok | — |
| `[[04-decisions#D50]]` | 00-index.md:187 | ok | — |
| `[[04-decisions#D51]]` | 00-index.md:187 | ok | — |
| `[[06-open-threads#T14]]` | 00-index.md:187 | ok | — |
| `[[03-phases]]` | 00-index.md:198 | ok | — |
| `[[04-decisions#D49]]` | 00-index.md:198 | ok | — |
| `[[06-open-threads#T13]]` | 00-index.md:199 | ok | — |
| `[[03-phases]]` | 00-index.md:213 | ok | — |
| `[[04-decisions#D48]]` | 00-index.md:214 | ok | — |
| `[[06-open-threads#T12]]` | 00-index.md:214 | ok | — |
| `[[04-decisions#D47]]` | 00-index.md:227 | ok | — |
| `[[06-open-threads#T11]]` | 00-index.md:228 | ok | — |
| `[[04-decisions#D44]]` | 00-index.md:235 | ok | — |
| `[[06-open-threads#T8]]` | 00-index.md:236 | ok | — |
| `[[04-decisions#D45]]` | 00-index.md:240 | ok | — |
| `[[06-open-threads#T9]]` | 00-index.md:240 | ok | — |
| `[[06-open-threads]]` | 00-index.md:243 | ok | — |
| `[[06-open-threads#T15]]` | 00-index.md:273 | ok | — |
| `[[06-open-threads#T16]]` | 00-index.md:279 | ok | — |
| `[[04-decisions#D58]]` | 00-index.md:284 | ok | — |
| `[[04-decisions#D62]]` | 00-index.md:284 | ok | — |
| `[[06-open-threads#T16]]` | 00-index.md:284 | ok | — |
| `[[06-open-threads#T14]]` | 00-index.md:287 | ok | — |
| `[[04-decisions#D5]]` | 01-architecture.md:13 | ok | — |
| `[[04-decisions#D49]]` | 01-architecture.md:51 | ok | — |
| `[[03-phases#FECHADA — Detalhe de ligação nível fabricação (A+B) — 2026-07-09]]` | 02-test-tree.md:44 | ok | — |
| `[[06-open-threads#T15]]` | 02-test-tree.md:55 | ok | — |
| `[[06-open-threads#T16]]` | 02-test-tree.md:69 | ok | — |
| `[[06-open-threads#T16]]` | 02-test-tree.md:77 | ok | — |
| `[[04-decisions#D67]]` | 02-test-tree.md:84 | ok | — |
| `[[06-open-threads#T17]]` | 02-test-tree.md:84 | ok | — |
| `[[04-decisions#D5]]` | 02-test-tree.md:129 | ok | — |
| `[[04-decisions#D49]]` | 03-phases.md:16 | ok | — |
| `[[06-open-threads#T13]]` | 03-phases.md:17 | ok | — |
| `[[04-decisions#D48]]` | 03-phases.md:23 | ok | — |
| `[[04-decisions#D48]]` | 03-phases.md:48 | ok | — |
| `[[06-open-threads#T12]]` | 03-phases.md:48 | ok | — |
| `[[04-decisions#D45]]` | 03-phases.md:55 | ok | — |
| `[[04-decisions#D44]]` | 03-phases.md:79 | ok | — |
| `[[04-decisions#D6]]` | 03-phases.md:88 | ok | — |
| `[[06-open-threads#T8]]` | 03-phases.md:90 | ok | — |
| `[[06-open-threads#T6]]` | 03-phases.md:146 | ok | — |
| `[[04-decisions]]` | 03-phases.md:201 | ok | — |
| `[[04-decisions#D6]]` | 03-phases.md:202 | ok | — |
| `[[04-decisions]]` | 03-phases.md:207 | ok | — |
| `[[04-decisions]]` | 03-phases.md:214 | ok | — |
| `[[04-decisions]]` | 03-phases.md:219 | ok | — |
| `[[06-open-threads#T6]]` | 03-phases.md:226 | ok | — |
| `[[04-decisions#D37]]` | 03-phases.md:229 | ok | — |
| `[[06-open-threads#T6]]` | 03-phases.md:232 | ok | — |
| `[[04-decisions#D46]]` | 03-phases.md:244 | ok | — |
| `[[06-open-threads#T10]]` | 03-phases.md:244 | ok | — |
| `[[06-open-threads#T7]]` | 03-phases.md:262 | ok | — |
| `[[06-open-threads#T1]]` | 03-phases.md:263 | ok | — |
| `[[06-open-threads#HANDOFF]]` | 03-phases.md:264 | ok | — |
| `[[04-decisions#D68]]` | 03-phases.md:305 | ok | — |
| `[[04-decisions#D69]]` | 03-phases.md:305 | ok | — |
| `[[04-decisions#D67]]` | 03-phases.md:315 | ok | — |
| `[[06-open-threads#T17]]` | 03-phases.md:317 | ok | — |
| `[[00-index]]` | 03-phases.md:320 | ok | — |
| `[[04-decisions#D52]]` | 03-phases.md:320 | ok | — |
| `[[04-decisions#D57]]` | 03-phases.md:320 | ok | — |
| `[[06-open-threads#T6]]` | 04-decisions.md:25 | ok | — |
| `[[04-decisions#D23]]` | 04-decisions.md:77 | ok | — |
| `[[04-decisions#D24]]` | 04-decisions.md:80 | ok | — |
| `[[04-decisions#D24]]` | 04-decisions.md:83 | ok | — |
| `[[04-decisions#D26]]` | 04-decisions.md:86 | ok | — |
| `[[04-decisions#D27]]` | 04-decisions.md:89 | ok | — |
| `[[04-decisions#D28]]` | 04-decisions.md:92 | ok | — |
| `[[04-decisions#D29]]` | 04-decisions.md:95 | ok | — |
| `[[04-decisions#D30]]` | 04-decisions.md:98 | ok | — |
| `[[04-decisions#D31]]` | 04-decisions.md:101 | ok | — |
| `[[03-phases]]` | 04-decisions.md:104 | ok | — |
| `[[06-open-threads#T6]]` | 04-decisions.md:107 | ok | — |
| `[[03-phases]]` | 04-decisions.md:110 | ok | — |
| `[[03-phases]]` | 04-decisions.md:116 | ok | — |
| `[[03-phases]]` | 04-decisions.md:119 | ok | — |
| `[[03-phases]]` | 04-decisions.md:122 | ok | — |
| `[[#D37]]` | 04-decisions.md:125 | ok | — |
| `[[06-open-threads#T6]]` | 04-decisions.md:125 | ok | — |
| `[[03-phases]]` | 04-decisions.md:133 | ok | — |
| `[[03-phases]]` | 04-decisions.md:142 | ok | — |
| `[[03-phases]]` | 04-decisions.md:152 | ok | — |
| `[[#D6]]` | 04-decisions.md:155 | ok | — |
| `[[#D37]]` | 04-decisions.md:156 | ok | — |
| `[[#D37]]` | 04-decisions.md:157 | ok | — |
| `[[#D38]]` | 04-decisions.md:158 | ok | — |
| `[[#D39]]` | 04-decisions.md:159 | ok | — |
| `[[#D42]]` | 04-decisions.md:160 | ok | — |
| `[[#D43]]` | 04-decisions.md:161 | ok | — |
| `[[03-phases]]` | 04-decisions.md:169 | ok | — |
| `[[03-phases]]` | 04-decisions.md:179 | ok | — |
| `[[03-phases]]` | 04-decisions.md:188 | ok | — |
| `[[03-phases]]` | 04-decisions.md:194 | ok | — |
| `[[03-phases]]` | 04-decisions.md:201 | ok | — |
| `[[06-open-threads#T11]]` | 04-decisions.md:283 | ok | — |
| `[[03-phases#FECHADA — Balde 4 (backlog de gaps) fases 6.15–6.19 + homologação 45–49 — 2026-07-13/14]]` | 04-decisions.md:319 | ok | — |
| `[[06-open-threads#T12]]` | 04-decisions.md:319 | ok | — |
| `[[06-open-threads#T13]]` | 04-decisions.md:369 | ok | — |
| `[[06-open-threads#T14]]` | 04-decisions.md:386 | ok | — |
| `[[06-open-threads#T14]]` | 04-decisions.md:405 | ok | — |
| `[[06-open-threads#T15]]` | 04-decisions.md:417 | ok | — |
| `[[04-decisions#D52]]` | 04-decisions.md:423 | ok | — |
| `[[06-open-threads#T14]]` | 04-decisions.md:460 | ok | — |
| `[[06-open-threads#T16]]` | 04-decisions.md:476 | ok | — |
| `[[#D58]]` | 04-decisions.md:506 | ok | — |
| `[[06-open-threads#T16]]` | 04-decisions.md:516 | ok | — |
| `[[#D59]]` | 04-decisions.md:528 | ok | — |
| `[[06-open-threads#T21]]` | 04-decisions.md:633 | ok | — |
| `[[02-test-tree]]` | 05-glossary.md:14 | ok | — |
| `[[04-decisions#D37]]` | 05-glossary.md:19 | ok | — |
| `[[04-decisions#D73]]` | 06-open-threads.md:10 | ok | — |
| `[[04-decisions#D72]]` | 06-open-threads.md:20 | ok | — |
| `[[04-decisions#D70]]` | 06-open-threads.md:33 | ok | — |
| `[[04-decisions#D68]]` | 06-open-threads.md:51 | ok | — |
| `[[04-decisions#D69]]` | 06-open-threads.md:51 | ok | — |
| `[[04-decisions#D67]]` | 06-open-threads.md:70 | ok | — |
| `[[03-phases]]` | 06-open-threads.md:80 | ok | — |
| `[[04-decisions#D58]]` | 06-open-threads.md:97 | ok | — |
| `[[04-decisions#D62]]` | 06-open-threads.md:97 | ok | — |
| `[[04-decisions#D58]]` | 06-open-threads.md:107 | ok | — |
| `[[04-decisions#D65]]` | 06-open-threads.md:119 | ok | — |
| `[[04-decisions#D63]]` | 06-open-threads.md:121 | ok | — |
| `[[04-decisions#D64]]` | 06-open-threads.md:122 | ok | — |
| `[[04-decisions#D66]]` | 06-open-threads.md:123 | ok | — |
| `[[04-decisions#D53?]]` | 06-open-threads.md:137 | quebrado-ancla | ancora com '?' residual — corrigir p/ #D53 (header '## D53 - vento correto: uplift, Cpe e Cpi por abertura (2026-07-17)' existe) |
| `[[#T16]]` | 06-open-threads.md:144 | ok | — |
| `[[03-phases#FECHADA — Revisão técnica T15 (correções+features+validação) — 2026-07-17]]` | 06-open-threads.md:148 | ok | — |
| `[[04-decisions#D52]]` | 06-open-threads.md:150 | ok | — |
| `[[04-decisions#D57]]` | 06-open-threads.md:150 | ok | — |
| `[[03-phases]]` | 06-open-threads.md:157 | ok | — |
| `[[04-decisions#D50]]` | 06-open-threads.md:177 | ok | — |
| `[[04-decisions#D51]]` | 06-open-threads.md:177 | ok | — |
| `[[03-phases]]` | 06-open-threads.md:204 | ok | — |
| `[[04-decisions#D49]]` | 06-open-threads.md:204 | ok | — |
| `[[04-decisions#D49]]` | 06-open-threads.md:241 | ok | — |
| `[[04-decisions#D48]]` | 06-open-threads.md:247 | ok | — |
| `[[#T7]]` | 06-open-threads.md:267 | ok | — |
| `[[#T1]]` | 06-open-threads.md:268 | ok | — |
| `[[#T10]]` | 06-open-threads.md:275 | ok | — |
| `[[04-decisions#D47]]` | 06-open-threads.md:275 | ok | — |
| `[[04-decisions#D46]]` | 06-open-threads.md:300 | ok | — |
| `[[#T5]]` | 06-open-threads.md:305 | ok | — |
| `[[04-decisions#D45]]` | 06-open-threads.md:312 | ok | — |
| `[[#T5]]` | 06-open-threads.md:317 | ok | — |
| `[[#T5]]` | 06-open-threads.md:327 | ok | — |
| `[[04-decisions#D44]]` | 06-open-threads.md:327 | ok | — |
| `[[#T8]]` | 06-open-threads.md:331 | ok | — |
| `[[03-phases]]` | 06-open-threads.md:343 | ok | — |
| `[[04-decisions]]` | 06-open-threads.md:343 | ok | — |
| `[[04-decisions#D14]]` | 06-open-threads.md:344 | ok | — |
| `[[04-decisions#D31]]` | 06-open-threads.md:345 | ok | — |
| `[[04-decisions#D28]]` | 06-open-threads.md:346 | ok | — |
| `[[04-decisions]]` | 06-open-threads.md:347 | ok | — |
| `[[04-decisions#D26]]` | 06-open-threads.md:349 | ok | — |
| `[[04-decisions#D8]]` | 06-open-threads.md:353 | ok | — |
| `[[03-phases#FECHADA — Projeto executivo 2D]]` | 06-open-threads.md:359 | quebrado-ancla | header existe por prefixo: '## FECHADA - Projeto executivo 2D (TechDraw) + memorial PDF + detalhes de ligacao - 2026-07-09' — usar titulo completo (tracinho, nao travessao) ou ancora curta; mesmo padrao OK em 04-decisions:319 |
| `[[04-decisions#D33]]` | 06-open-threads.md:359 | ok | — |
| `[[04-decisions#D36]]` | 06-open-threads.md:359 | ok | — |
| `[[04-decisions#D37]]` | 06-open-threads.md:360 | ok | — |
| `[[03-phases#FECHADA — Corte seccionado 2D]]` | 06-open-threads.md:365 | quebrado-ancla | header existe por prefixo: '## FECHADA - Corte seccionado 2D (fase 5) - 2026-07-10' — usar titulo completo (tracinho, nao travessao) ou ancora curta |
| `[[06-open-threads#T12]]` | 06-open-threads.md:368 | ok | — |
| `[[04-decisions#D7]]` | 06-open-threads.md:371 | ok | — |
| `[[04-decisions#D0]]` | 06-open-threads.md:381 | ok | — |
| `[[04-decisions]]` | 06-open-threads.md:385 | ok | — |

## Caminhos externos citados na wiki (findings — alimentam a varredura de cobertura do todo 19)

| referência | ocorrências (arquivo:linha) | existe? | localização verificada |
|---|---|---|---|
| `tools/run_build_suite.ps1` | 00-index:90; 03-phases:271; 04-decisions:624; 06-open-threads:24 | **SIM** | `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt\tools\run_build_suite.ps1` (raiz do worktree — base é o repo root, NÃO `framework/galpao_fw/tools` que só tem README+run_tests.py) |
| `tools/register_build_task.ps1` | 00-index:91; 03-phases:272; 04-decisions:625; 06-open-threads:25 | **SIM** | `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt\tools\register_build_task.ps1` (raiz do worktree) |
| `tools/run_tests.py` | 00-index:251 | **SIM** | `framework\galpao_fw\tools\run_tests.py` |
| `memory/` e `memory/*.md` | 00-index:20, 26 (`[[../memory]]`), 250; 06-open-threads:4, 7, 340 | **NÃO** | `Get-ChildItem -Recurse -Directory -Filter memory` → 0; `memory.md` → 0 (em todo o worktree). `[[../memory]]` é o único link `[[ ]]` com status quebrado-arquivo |
| `sessions/` | 00-index:21, 251 | **NÃO** | nenhum diretório `sessions` em todo o worktree (wiki afirma ter só 2 logs antigos) |
| `projects/` | nenhuma ocorrência na wiki | — | nenhum diretório `projects` no worktree |

### REVISAO-* (menções em prosa, não `[[ ]]`)

| referência | ocorrências | existe? | localização verificada |
|---|---|---|---|
| `REVISAO-DG25-FULL` | 06-open-threads.md:279 | **SIM** | `framework\galpao_fw\REVISAO-DG25-FULL.md` |
| `REVISAO-ENRIJECEDOR-PAINEL` | 06-open-threads.md:279 | **SIM** | `framework\galpao_fw\REVISAO-ENRIJECEDOR-PAINEL.md` |
| `REVISAO-FUNDACAO-PROFUNDA-INTEG` | 03-phases.md:193; 04-decisions.md:119 | **SIM** | `framework\galpao_fw\REVISAO-FUNDACAO-PROFUNDA-INTEG.md` |
| `REVISAO-GUSSET` | 04-decisions.md:116 | **SIM** | `framework\galpao_fw\REVISAO-GUSSET.md` |
| `REVISAO-INDICE` | 00-index.md:212; 00-index.md:227; 00-index.md:240; 03-phases.md:41; 03-phases.md:199; 03-phases.md:207; 03-phases.md:234; 03-phases.md:244; 03-phases.md:257; 03-phases.md:262; 04-decisions.md:162; 04-decisions.md:208; 04-decisions.md:251; 04-decisions.md:274; 04-decisions.md:319; 06-open-threads.md:267; 06-open-threads.md:290; 06-open-threads.md:300; 06-open-threads.md:312; 06-open-threads.md:327; 06-open-threads.md:331 | **SIM** | `framework\galpao_fw\REVISAO-INDICE.md` |

- **Achado de localização:** o README e a wiki referem `wiki/revisoes/REVISAO-*.md`, mas **o diretório `wiki\revisoes\` não existe no worktree**; os 49 REVISAO-*.md vivem em `framework\galpao_fw\`. Registrar como finding de cobertura do todo 19.

## Nota de execução

- OneDrive: nenhum erro de "arquivo em uso" ocorreu (sem re-tentativa necessária).
- Nenhum arquivo da wiki foi lido para escrita; correções de link ficam para os todos 11/15/16; esta tabela é a baseline da re-rodada do todo 19 (meta: zero quebrados).
