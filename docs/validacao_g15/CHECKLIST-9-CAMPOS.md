# Checklist G19 — 9 campos que destravam `projects/galpao-sjb` (Loop 2)

> **Fonte canônica do gate:** `projects/galpao-sjb/ENTRADAS-PENDENTES.md` e `framework/galpao_fw/project_loop.py:584` `preflight_project(..., require_source_refs=True)`.
> **Estado atual (2026-09-03):** `project-spec.json` → `blocked` 9 erros — ver `python tools/ingestao_sjb.py --check`.
> **Exemplo `ready`:** `projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json` (`ready` 0 warnings) + `proposta-36x24-exemplo-valores-referencia.json` (peso 23206 / Mcol 235.99) — `PROPOSTA NAO E OBRA REAL`, apenas demonstra preenchimento.

## Gate em 1 comando

```powershell
python tools/ingestao_sjb.py --check
python -c "import json, project_loop; s=json.load(open('projects/galpao-sjb/project-spec.json',encoding='utf-8')); import pprint; pprint.pp(project_loop.preflight_project(s, options={'require_source_refs':True})['preflight']['errors'])"
python -m validacao_sistema_g15  # 22/22 PASS (19 G15 + 2 SJB AGUARDANDO + 1 proposta 36x24 0.0%)
```

`Loop 2` só inicia com `status: ready` e `can_start_project_loop: true`. `blocked` = falta entrada; `needs_review` = tem `A CONFIRMAR` ou `source_refs` stale.

## Tabela dos 9 campos

| # | Campo do template | Path JSON | Status atual | Exemplo proposta 36×24 (hipótese, não obra) | Dado real que o engenheiro deve fornecer | Onde obter |
|---|---|---|---|---|---:|---|
| 1 | **comprimento** | `turnkey.geometria.comprimento` | `__PENDENTE__` → `invalid_common_geometry` | `36.0` m | Planta de implantação / memorial | Arquitetônico |
| 2 | **vão** | `turnkey.geometria.vao` | `__PENDENTE__` | `24.0` m | Idem | Arquitetônico |
| 3 | **pé-direito** | `turnkey.geometria.pe_direito` | `__PENDENTE__` | `7.0` m (eave) | Idem | Arquitetônico |
| 4 | **concreto e fundações** | `turnkey.concreto` (`_status: __PENDENTE__`) | `pending_discipline_input` | `fck 25 MPa, sigma_solo_adm 250 kPa, bloco 2.0×2.0×0.55, pilar 40×90` (ver `proposta-...json: structure.concreto/fundacao`) | `fck`, `fyk`, cobrimento, `sigma_solo_adm` (SPT), NA, tipo fundação (bloco/sapata/estaca) | Sondagem SPT + projeto concreto |
| 5 | **aço** | `turnkey.aco` (`_status: __PENDENTE__`) | `pending_discipline_input` | `HEB280/HEB260 + IPE450, Ue 300×85, contraventamento d20, G=0.3 Q=0.25` (ver `spec_amostra_engenheiro.json` como forma) | Perfis/regra seleção, grau aço, ligações, cargas `G/Q/self/tapamento`, `vento V0/cat/classe/s1/s3/z` | Memorial aço + NBR 8800 |
| 6 | **elétrica e SPDA** | `turnkey.eletrico` | `pending_discipline_input` | `ENEL BT 380V, 20kW iluminação + 2×75cv, alimentador 50mm² EPR, demanda 131kVA trafo 150` | Tensão/fases/frequência/padrão ENEL, lista cargas/demanda/FP, ponto entrega, protocolo ENEL, rotas/quadros | ENEL + memorial elétrico |
| 7 | **incêndio** | `turnkey.incendio` | `pending_discipline_input` | `industrial I2, risco ordinário II, 4 hidrantes 600L/min, 67 sprinklers` | Ocupação/população/carga incêndio/área/altura/compartimentação + CBMERJ protocolo | CBMERJ |
| 8 | **climatização** | `turnkey.climatizacao` | `pending_discipline_input` | `galpão, 20 pessoas, 39.4kW 11.2TR, duto 1.044×0.522` | Uso/ocupação/horários, cargas térmicas, equipamentos | HVAC |
| 9 | **hidráulica** | `turnkey.hidraulica` | `pending_discipline_input` | `DN40 água, DN100 esgoto, DN125 pluvial, calha 150, i=150mm/h` | População/consumo/aparelhos, pressão/reservação, traçado esgoto, `i` pluvial | Hidráulico |

As 14 `source_refs` já estão `status 2` (prontas) — `notebook_id`/`source_id` em `project-spec.template.json` — não são gargalo. Confirmar com `nlm login --check` antes de `Loop 2`.

## Como preencher (sem inventar)

1. **Geometria** (1-3) — 3 números `>0` em `turnkey.geometria`. Ex.: `python tools/ingestao_sjb.py --set-geometria 36 24 7`.
2. **Disciplinas** (4-9) — cada `_status: __PENDENTE__` deve virar **objeto** (não string). Use `proposta-obra-conhecida-AGENTE-36x24.json` e `project-spec-framework-teste.json` como **forma**, mas substitua cada valor pela sua obra:
   - `aco`: copie `structure` (geometria, vento, cargas, fundação) + `turnkey.aco` completo.
   - `concreto`: `fck`, `fyk`, `sigma_solo_adm` **nunca** arbitrados — vêm de sondagem.
   - `eletrico`: `tensao_V`, `cargas`, `concessionaria` com `protocolo` ENEL.
   - `incendio`/`climatizacao`/`hidraulica`: sub-specs completos (ver teste).
3. **Validar:**
   ```powershell
   python tools/ingestao_sjb.py --check  # deve ir de blocked 9 → ready
   python framework/galpao_fw/project_loop_cli.py --spec projects/galpao-sjb/project-spec.json --out-dir projects/galpao-sjb/readiness-003 --preflight-only --require-source-refs --verify-source-refs
   ```
4. **Memorial para G19:** quando `ready`, anexe `docs/validacao_g15/galpao-sjb-memorial.pdf` + `galpao-sjb-valores-referencia.json` (do `galpao-sjb-valores-referencia.json.template` com `fonte` CREA/ART + `valores_referencia` peso/Mcol/perfis) — então `python -m validacao_sistema_g15` compara número-a-número (5% V, 15% H/M, 10% peso).

## Rastreabilidade

- Template: `projects/galpao-sjb/project-spec.template.json:42` (`turnkey.geometria` 3× `__PENDENTE__` + 6× `pending_discipline_input`)
- Gate: `framework/galpao_fw/project_loop.py:637` (`_geometry_from_turnkey`) + `:673` (`pending_discipline_input`)
- Harness: `framework/galpao_fw/validacao_sistema_g15.py:530` (SJB `blocked` guard) + `:686` (proposta 36×24 `0.0%`)
- Demo: `tools/demo_g19_4o_caso.py` (usa `proposta-36x24` como proxy `ready` quando SJB ainda `blocked`)
