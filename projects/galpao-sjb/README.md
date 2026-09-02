# Galpao SJB / ENEL — projeto galpao real (G19)

Este projeto e o 4o caso do harness G15/G19: validacao contra obra real.
Estado: **bloqueado com 9 campos pendentes** — comportamento correto, o framework recusa-se a rodar sem obra real.

## O que falta (9 erros atuais)

```
invalid_common_geometry: comprimento, vao, pe_direito (3)
pending_discipline_input: concreto, aco, eletrico, incendio, climatizacao, hidraulica (6)
```

Detalhe completo em `ENTRADAS-PENDENTES.md`, `docs/validacao_g15/CHECKLIST-9-CAMPOS.md` (tabela dos 9 campos com exemplo 36×24) e no gate:

```powershell
python -c "import json, project_loop; s=json.load(open('projects/galpao-sjb/project-spec.json',encoding='utf-8')); import pprint; pprint.pp(project_loop.preflight_project(s, options={'require_source_refs':True})['preflight']['errors'])"
```

As 14 `source_refs` ja estao OK (`status 2`). Gargalo e entrada do empreendimento, nao norma.

## Template

`project-spec.template.json` e o ponto de partida. Nunca inventar valores — deixar `__PENDENTE__` se nao souber.

`project-spec.json` atual e copia do template ainda bloqueada (canonico). `project-spec-framework-teste.json` e copia sintetica com dados de teste (marcada `not_real_engineering_input`) — serve para exercitar BIM/IFC, nao para validar contra obra.

## Como preencher quando tiver a obra

### Minimo para destravar o preflight

```json
{
  "turnkey": {
    "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
    "aco": { /* spec estrutural completo — ver spec_amostra_engenheiro.json */ },
    "concreto": { /* ... */ },
    "eletrico": { /* cargas, tensao, ENEL */ },
    "incendio": { /* ocupacao, risco, CBMERJ */ },
    "climatizacao": { /* ... */ },
    "hidraulica": { /* ... */ }
  }
}
```

Exemplo quasi-real completo: `framework/galpao_fw/spec_amostra_engenheiro.json` (galpao 20x28.5, V0=45).
Para casa residencial: `projects/casa-residencial/project-spec.json`.

### Passos

1. Preencha `project-spec.json` a partir do template com dados REAIS (geometria, sondagem `sigma_solo_adm`, cargas `G/Q`, vento `V0/cat/classe`, dados ENEL, CBMERJ...).

2. Gate local:

```powershell
python -c "import json, project_loop; s=json.load(open('projects/galpao-sjb/project-spec.json',encoding='utf-8')); print(project_loop.preflight_project(s, options={'require_source_refs':True})['status'])"
```

3. Gate com fontes remotas (requer `nlm login --check` valido):

```powershell
python framework/galpao_fw/project_loop_cli.py --spec projects/galpao-sjb/project-spec.json --out-dir projects/galpao-sjb/readiness-002 --preflight-only --require-source-refs --verify-source-refs
```

4. Loop 2 quando `ready`:

```powershell
python framework/galpao_fw/project_loop_cli.py --spec projects/galpao-sjb/project-spec.json --out-dir projects/galpao-sjb/run-001 --require-source-refs
```

## Memorial e validacao G19

Quando o galpao estiver `ready`, anexe o memorial da obra construida em `docs/validacao_g15/galpao-sjb-memorial.pdf` + sidecar JSON (`docs/validacao_g15/galpao-sjb-valores-referencia.json` a partir do template). Entao:

```powershell
python -m validacao_sistema_g15          # 21/21 PASS — inclui comparacao SJB real
pytest framework/galpao_fw/tests/branches/g15/test_validacao_sistema.py -v
```

Enquanto nao houver obra real, o mesmo comando roda 21/21 PASS com 2 SKIP (`AGUARDANDO OBRA REAL`) — prova que o bloqueio funciona.

Ver `docs/validacao_g15/README.md` para formato do sidecar.

## Atalhos G19

```powershell
python tools/ingestao_sjb.py --check                 # diagnostico dos 9 campos
python tools/ingestao_sjb.py --set-geometria 40 20 6 # preenche geometria rapido
python tools/demo_g19_4o_caso.py                     # demo ponta-a-ponta com SPEC de teste (sintetico, nao e obra)
```

`docs/validacao_g15/exemplo-sintetico-valores-referencia.json` e o sidecar de demonstracao (peso 13693.7 kg, Mcol 158.87 kNm) — nao destrava G19, apenas prova o caminho de comparacao.

## Por que nao usar valores de teste como obra

`project-spec-framework-teste.json` esta explicitamente marcado como `framework_capability_test` e `agent_assumed_values`. Ele prova que o pipeline gera IF C/BIM/2D, nao que a engenharia esta certa contra concreto.
