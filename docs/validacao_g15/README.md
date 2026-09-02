# Validacao G19 — Galpao SJB como 4o caso (obra real)

Este diretorio e o ponto de ingestao do memorial de obra construida para o G19.
G15 validou o sistema com 19 checks contra amostra quasi-real + CBCA + casa (19/19 PASS).
G19 estende o mesmo harness como 4o caso com o galpao SJB/ENEL sem inventar dado de obra.

## Estado atual (2026-09-02)

- `projects/galpao-sjb/project-spec.json` ainda tem 9 campos `__PENDENTE__` (3 geometria + 6 disciplinas).
- `preflight_project(..., require_source_refs=True)` = `blocked` com 9 erros — comportamento correto.
- `python -m validacao_sistema_g15` agora roda **21 checks**: 19 originais + 2 guardas SJB.
  - SJB bloqueado => 21/21 PASS com 2 SKIP (`AGUARDANDO OBRA REAL`) — prova que o framework recusa-se a rodar sem dados.
  - SJB ready + memorial anexado => 21/21 com comparacao numero-a-numero real.

Nenhum memorial externo completo foi doado ate esta data (ver `projects/galpao-sjb/ENTRADAS-PENDENTES.md`).

## O que e necessario para destravar (9 campos)

Ver `projects/galpao-sjb/ENTRADAS-PENDENTES.md`, `project-spec.template.json`, `docs/validacao_g15/CHECKLIST-9-CAMPOS.md` (tabela 9), `ESQUEMA-9-CAMPOS.json` e `FLUXO-COMPLETO.md` (passo-a-passo 9 campos → Loop 2 → sidecar → 1 comando).
Resumo do gate atual:

1. Geometria comum: `turnkey.geometria.comprimento`, `vao`, `pe_direito` (numeros >0, em metros).
2-7. Uma entrada por disciplina ainda com `__PENDENTE__`: `concreto`, `aco`, `eletrico`, `incendio`, `climatizacao`, `hidraulica`
   - Cada uma precisa deixar de ser string `__PENDENTE__` e virar objeto com os campos da disciplina.
   - `aco` aceita tanto `turnkey.aco` quanto `structure` legado (ver `spec_amostra_engenheiro.json` como exemplo quasi-real).
   - `eletrico` exige: tensao, fases, padrao ENEL, lista de cargas, ponto de entrega, protocolo ENEL, etc.
   - As outras 4 disciplinas exigem seus sub-specs completos.
8-9. As 14 fontes `source_refs` ja estao declaradas e com `status 2` (prontas). Nao e gargalo.
   - Confirmar com `nlm login --check` quando for rodar `Loop 2` com `--verify-source-refs`.

## Como preencher quando tiver a obra

1. Copie o template:
```powershell
Copy-Item projects/galpao-sjb/project-spec.template.json projects/galpao-sjb/project-spec.json -Force
# edite os 9 campos PENDENTE com dados REAIS da obra (nao estime)
```

2. Valide o gate local (sem credencial remota):
```powershell
python -c "import json, project_loop; s=json.load(open('projects/galpao-sjb/project-spec.json',encoding='utf-8')); print(project_loop.preflight_project(s, options={'require_source_refs':True})['status'])"
# deve sair: ready
```
Se ainda `blocked`, o JSON de preflight lista exatamente o que falta.

3. Valide fontes + preflight gravando relatorio em pasta nova (nao reutilize `readiness/` antigo):
```powershell
python framework/galpao_fw/project_loop_cli.py --spec projects/galpao-sjb/project-spec.json --out-dir projects/galpao-sjb/readiness-002 --preflight-only --require-source-refs --verify-source-refs
```

4. Rode o Loop 2 (turnkey) quando `status == ready`:
```powershell
python framework/galpao_fw/project_loop_cli.py --spec projects/galpao-sjb/project-spec.json --out-dir projects/galpao-sjb/run-001 --require-source-refs
```

## Memorial externo — como anexar para o harness G19 comparar

Quando o galpao SJB estiver `ready` e voce tiver o memorial da obra construida (PDF do escritorio / calculista), anexe aqui:

- `docs/validacao_g15/galpao-sjb-memorial.pdf` — o PDF original do memorial (nao gere, doe).
- `docs/validacao_g15/galpao-sjb-valores-referencia.json` — sidecar JSON preenchido a partir do template abaixo.

O sidecar JSON existe para o harness comparar numero-a-numero sem precisar fazer OCR no PDF. PDF e fonte de auditoria, JSON e fonte de maquina.

### Template do sidecar

Copie `docs/validacao_g15/galpao-sjb-valores-referencia.json.template` para `galpao-sjb-valores-referencia.json` e preencha apenas as chaves que o memorial realmente contem. Chaves ausentes sao ignoradas (SKIP), nao falsificam PASS.

```json
{
  "fonte": "Memorial Galpao SJB - Obra XYZ, Eng. Fulano CREA 123456, data 2024-03-15",
  "proveniencia": "Trecho/certidao do memorial - pagina 4, tabela de reacoes Fd1",
  "geometria": {"comprimento": 0, "vao": 0, "pe_direito": 0},
  "valores_referencia": {
    "V_kN": null,
    "H_kN": null,
    "Mcol_kNm": null,
    "peso_aco_t": null,
    "peso_aco_primario_kg": null,
    "concreto_m3": null,
    "perfis": {"coluna": null, "viga": null},
    "observacoes": "Usar valores da combinacao governante do memorial, com a mesma definicao do framework (ex: L_rafter inclinado, peso por metro de portico = kN/m2 * bay)"
  }
}
```

Guarda `d*sen45`: declare sempre se o memorial mede comprimento inclinado ou projecao horizontal.

### Comando unico apos ingestao

```powershell
python -m validacao_sistema_g15          # 22/22 PASS (19 G15 + 2 SJB AGUARDANDO + 1 proposta 36x24 0.0%)
pytest framework/galpao_fw/tests/branches/g15/test_validacao_sistema.py -v  # 37 tests
```

O harness detecta automaticamente:

- SJB `blocked` => 2 checks viram SKIP com `AGUARDANDO OBRA REAL` (22/22 PASS com proposta 36x24, prova de bloqueio).
- SJB `ready` + memorial ausente => 1 PASS ready + 1 SKIP aguardando PDF/JSON (22/22 PASS).
- SJB `ready` + memorial presente => comparacao numero-a-numero real com tolerancias G15 (5% V, 15% H/M, 10% quantitativo, 2% eletrica).

Nao ha passo extra. Detalhe completo em `docs/validacao_g15/QUARTO-CASO-1-COMANDO.md`.

### Demo sem obra real (prova que o caminho funciona)

Sem precisar de obra, o repositorio ja traz um proxy sintetico que exercita o mesmo caminho de `ready + sidecar`:

```powershell
python tools/demo_g19_4o_caso.py         # usa project-spec-framework-teste.json + exemplo-sintetico-valores-referencia.json
python tools/ingestao_sjb.py --check     # mostra status atual do SJB (blocked 9 campos)
python tools/ingestao_sjb.py --help      # ingestao guiada dos 9 campos
```

- `docs/validacao_g15/exemplo-sintetico-valores-referencia.json` — sidecar **EXEMPLO SINTETICO** (`not_real_engineering_input`) gerado do run do SPEC de teste (`romaneio_peso_primario_kg=13693.7`, `Mcol=158.87`, `HEA240/IPE330`). Nao destrava o G19, serve apenas para demonstrar que `tools/demo_g19_4o_caso.py` compara com `0.00%` erro quando o dado existe.
- O harness real continua olhando apenas para `docs/validacao_g15/galpao-sjb-valores-referencia.json` (sem prefixo `exemplo-`) + `galpao-sjb-memorial.pdf` — enquanto nao existirem, continua `AGUARDANDO OBRA REAL`.

### Ingestao guiada

```powershell
python tools/ingestao_sjb.py --check                         # so diagnostico
python tools/ingestao_sjb.py --set-geometria 40 20 6         # preenche geometria e valida
python tools/ingestao_sjb.py --from-teste                    # copia SPEC de teste como ponto de partida demo (marca como DEMO SINTETICO)
python tools/ingestao_sjb.py                                 # interativo
python tools/validar_9_campos.py --spec projects/galpao-sjb/project-spec.json --json  # valida 9 campos (esquema + gate)
python tools/gerar_sidecar.py --spec projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json --out /tmp/sidecar.json  # extrai peso/Mcol do framework
```

### Guard contra dado inventado (G19)

- `check_galpao_sjb_memorial_comparacao` (`framework/galpao_fw/validacao_sistema_g15.py:587`) agora rejeita sidecar sintético como memorial real: se `_aviso/fonte` contiver `PROPOSTA`, `EXEMPLO SINTETICO`, `NAO E OBRA REAL` ou `test_assumptions`, retorna `BLOQUEADO - sidecar sintetico` (`FAIL` no modo real). Teste: copiar `proposta-36x24-exemplo-valores-referencia.json` para `galpao-sjb-valores-referencia.json` com `project-spec.json` `ready` → `FAIL` proposital.
- Proveniência mínima para obra real: `fonte` ≥20 chars com `CREA/ART` + data + página do memorial. Sem isso → `BLOQUEADO - proveniencia insuficiente`.
- Fallback: quando `ready`, o harness lê `reports/disciplinas.json` (`aco.native.raw romaneio_peso_primario_kg`, `esf_coluna.M_kNm`) se `adapter-result.json` não existir (caso `manifest status=failed` por `A CONFIRMAR`), com tolerâncias G15 (`peso 10%`, `M 15%`, `V 5%`).

Isso garante que `22/22 PASS` (`19 G15` + `2 SJB AGUARDANDO` + `1 proposta 36×24 0.0%`) não seja confundido com validação contra concreto.

## Por que nao usar o spec de teste

`projects/galpao-sjb/project-spec-framework-teste.json` existe apenas para exercitar BIM/IFC/2D sem inventar que e obra. Ele esta marcado `test_assumptions.mode = framework_capability_test` e `not_real_engineering_input` — nao serve como memorial e nao conta para o G19.

## Rastreabilidade

- Harness: `framework/galpao_fw/validacao_sistema_g15.py:check_galpao_sjb_*` + `check_obra_conhecida_agente_36x24` (3 checks G19, total 22) — `QUARTO-CASO-1-COMANDO.md`
- Gate: `framework/galpao_fw/project_loop.py:preflight_project` (9 erros atuais) — `CHECKLIST-9-CAMPOS.md` ↔ `ESQUEMA-9-CAMPOS.json` ↔ `tools/validar_9_campos.py` + `tools/gerar_sidecar.py`
- Review: `framework/galpao_fw/REVISAO-G15-VALIDACAO-SISTEMA.md` sec. 7
