# 01 — Arquitetura

## Princípios
- **ProjetoSpec = fonte única da verdade** (`projeto_spec.py`). `validar()` bloqueia calc/model até todos os gates respondidos. Builder lê só do spec (sem cópia hardcoded).
- **Calcula apenas; CONCEITUAL** — pendente revisão + ART do eng. responsável. Nada é executivo.
- **Ask, Do Not Invent**: σ_solo,adm, μ, coesão, fck, fyk, φ (impacto ponte), frações laterais/long — INPUT do caso; a skill pergunta. Defaults entram flagados.
- **Método extraído das normas** (`pesquisa/aço/*.pdf`), não de memória. Cada módulo cita item da NBR.

## Cadeia de cálculo (por candidato de perfil)
1. `galpao_portico` — pórtico 2D, flecha lateral no beiral (ELS).
2. `estabilidade_b1b2` — 2ª ordem **MAES** (rigidez 0,8 + forças nocionais) → Nsd/Msd/Vsd amplificados. Permite **K=1** (NBR 8800 4.9.6.2).
3. `check_nbr8800` — verificação por peça, K=1, todas as combinações → pior interação (flexo-compressão 5.5.1.2, split 0,2; FLT Anexo G).
4. `redimensionamento` — first-fit: par (coluna,viga) mais leve que passa ELU (interação≤1) **E** ELS (flecha ≤ **H/300**, Tab. C.1). Ver [[04-decisions#D5]].

## Envelope de combinações (por elemento)
`rodar_galpao._casos_base_envelope()` lê a reação do nó de base **direto do solve de 2ª ordem** (`R[3·nBaseL+{0,1,2}]` = V,N,M) por combinação ELU. Alimenta:
- **fundação** `fundacao_sapata.dimensiona_sapata_env` — menor geometria que passa TODAS as combos (bearing=N máx, tombamento=N mín+M).
- **base** `base_chumbador` — placa + chumbadores, caso "Base engastada — M=…".
Mesmo `R` para redim/fundação/base → consistência; M do engaste não é recalculado.

## Módulos
| Grupo | Módulos | Norma |
|---|---|---|
| Análise | `galpao_portico`, `estabilidade_b1b2`, `frame2d` (solver genérico) | NBR 8800 An. D |
| Verificação | `check_nbr8800`, `perfis` (tabela) | NBR 8800 |
| Ações | `vento_nbr6123` (+§8 Cpe local borda/canto), `ponte_rolante`, `sismo_nbr15421` | NBR 6123, 8800/8400, **15421** |
| Secundários | `tercas_iteracao` (+distorcional FSM), secundários, `mao_francesa`, `contraventamento`, **`telha_cobertura`** | NBR 14762, 8800 |
| Ligações/base | `ligacoes` (joelho/parafusos + furos/Tab.14/block shear/T-stub), `base_chumbador` | NBR 8800 + AISC DG1 + ACI 318 + EN 1993-1-8 |
| Fundação | `fundacao_sapata` (rasa: geotecnia+concreto), **`viga_baldrame`** (amarração), **`estaca_profunda`** (profunda) | NBR 6118, 6122 + Aoki/Décourt/Teixeira |
| Auto-sizing | `redimensionamento` | usa check |
| Orquestração | `rodar_galpao`, `rodar_projeto`, `framework`, `projeto_spec` | — |
| Geometria/saída | `build_galpao`, `dxf_vistas`, `terreno` (KML) | — |

**Sismo no envelope:** `galpao_portico`/`estabilidade_b1b2` têm caso `SISMO` (global `gp.SISMO`, `case_sismo` no beiral) + combos excepcionais C6 (1,2G±E / 1,0G±E, sem vento/Q, NBR 15421 §5.4) — entram no envelope do pórtico, base e joelho. `rodar_galpao` computa `E = H·(vão/comprimento)` e θ/P-Δ. Zona 0 (default) → E=0 → nada muda.

**Fundação profunda/baldrame:** opt-in via `params["estaca"]` / `params["baldrame"]` — **ainda não no `projeto_spec` (gates) nem no build 3D**. `estaca_profunda` = 3 métodos de capacidade (Aoki-Velloso/Décourt-Quaresma/Teixeira) + tração/grupo/atrito negativo/recalque + bloco de coroamento (bielas-tirantes+ancoragem+punção). N_pilar/N_uplift do envelope de base.

## Auditoria geométrica
`verifica_conexoes` mede as formas reais no modelo 3D (assentamento medido `_assenta`) → auto-captura defeitos de conexão/geometria. Sapata desenhada (bloco+pedestal) no take-off com densidade própria (concreto categoria separada, não soma na tonelagem de aço).

## Convenções
- `L` // eixo do momento do pórtico. Momento no plano do pórtico → dimensão L.
- γa1=1,10, γa2=1,35, γw2=1,35 (aço); γc=γn=1,40 (concreto).
- `_pt()` troca ponto decimal por vírgula nos memoriais (preserva nº de item tipo 6.118).
