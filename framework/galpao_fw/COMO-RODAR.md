# Como rodar o framework de galpão (guia de execução)

CONCEITUAL — o framework **calcula, dimensiona e desenha**; o **engenheiro
responsável revisa e assina (ART)**. Nada aqui é projeto executivo.

## 1. Preparar um PC novo (uma vez)

Na raiz do repositório, duplo-clique em **`install.bat`** (ou
`powershell -ExecutionPolicy Bypass -File install.ps1`). Ele monta:

- o servidor MCP do FreeCAD (uv tool) + o workbench `RobustMCPBridge`;
- o **ambiente Python do cálculo** em `framework/galpao_fw/.venv`
  (Python 3.12, `numpy<2`, `pycufsm`, `ezdxf`) — é onde o cálculo e o DXF rodam.

Pré-requisitos: FreeCAD instalado; `uv` no PATH (ou rode com `-InstallUvIfMissing`).

O `.venv` NÃO vai no git — cada PC monta o seu pelo instalador.

## 2. Rodar um projeto

O projeto é dirigido por um **spec** (fonte única da verdade). Fluxo:

```
spec  ->  validar (trava se faltar decisão)
      ->  calcular       (dimensiona perfil, base, joelho, terça, longarina...)
      ->  montar_modelo  (modelo 3D no FreeCAD, com conexões + auditor)
      ->  rodar_executivo (pranchas 2D + DXF)
```

Código (rodar com o python do venv de cálculo):

```python
import sys; sys.path.insert(0, "framework/galpao_fw")
import projeto_spec as PS, rodar_projeto as RP

s = PS.novo()                       # spec com tudo PENDENTE (bloqueia)
# ... preencher os gates (terreno, geometria, cobertura, fechamento,
#     aberturas, vento, ponte, cargas) - pasta de projeto criada por framework.novo_projeto
RP.calcular(s, "projeto/exports/memoria")          # dimensiona + memoriais
RP.montar_modelo(s, "projeto/exports", "meu_galpao")  # FreeCAD aberto (MCP)
RP.rodar_executivo(s, "projeto/exports", "projeto/exports/freecad/meu_galpao.FCStd")  # pranchas 2D + DXF
```

`calcular` roda no venv puro (não precisa do FreeCAD). `montar_modelo` usa o
FreeCAD pela ponte MCP (porta 9875). Não existe `gerar_dxf`: o DXF sai junto
com as pranchas 2D do `rodar_executivo` (freecad.exe headless, TechDraw).

Para criar uma pasta de projeto isolada nova: `framework.novo_projeto("slug")`.

## 3. O que sai (exports/)

- `memoria/` — memoriais PT por etapa + **MEMORIAL-CONSOLIDADO** (abre com um
  QUADRO DE VERIFICAÇÕES e grita `!!! NÃO ATENDEM !!!` se algo passar de 1,0);
- `freecad/*.FCStd` + `step/*.step` — modelo 3D;
- `takeoff/*.csv` — levantamento de material (aço);
- `dxf/*.dxf` — pórtico, elevação, planta, corte (terças/telha), detalhes do
  joelho e da base, eixos numerados, níveis, quadro de verificações e de
  materiais. Camadas com cor fixa (visível em fundo branco e preto).

## 4. O que o framework FAZ

Portal de 1 vão, 2 águas, base engastada/rotulada, com ou sem ponte rolante:

- vento NBR 6123 (transversal + longitudinal, Cat I–V);
- pórtico 1ª + 2ª ordem (MAES) e **redimensiona** coluna/viga (HEA→HEB300/IPE550);
- **dimensiona** base (placa/chumbadores/espessura), joelho (chapa/parafusos),
  terça (Ue), longarina (UPE + tirantes), escora/montante (HEA);
- **dimensiona** a sapata isolada (NBR 6118): tensão no solo + FS tombamento/
  deslizamento (Parte A) e concreto — rigidez 22.6.1, armadura de flexão
  (22.6.3+17.2.2), compressão diagonal 19.5.3.1 (Parte B, sapata rígida);
- terças NBR 14762 (+ distorcional FSM), mão-francesa, contraventamento;
- modelo 3D com conexões detalhadas + **auditor geométrico** (mede a forma real
  e pega erro de conexão no build);
- DXF com quadros de verificação e materiais.

Referência validada: galpão 20×10 m com ponte rolante 100 kN — roda ponta a
ponta com todos os elementos ATENDENDO (a pasta `projects/<slug>/` é criada em
runtime por `framework.novo_projeto`; não fica no repositório).

## 5. O que ainda NÃO faz (fora de escopo / próximos)

> **Já implementado posteriormente** (saiu desta lista): bloco sobre estacas e
> punção (fase 3 + D8, 2026-07-07/10), armadura executiva (item 24 do índice),
> treliça e alma variável (fases 6.c/6.b, 2026-07-10), multi-vão (D51,
> 2026-07-16, PR #12), sismo (D18, 2026-07-08), fadiga (D10/D16, 2026-07-08),
> fabricação — piece marks 3D + lista de corte + tolerâncias (PR #46,
> 2026-07-22; D37, 2026-07-09) e plano de montagem (PR #47, 2026-07-22).

- **Fundação**: sapata isolada JÁ dimensionada (rígida, NBR 6118), com envelope
  de combinações por elemento (bearing pega N máx gravitacional; tombamento pega
  N mín + M) — ver `REVISAO-FUNDACAO.md`; ainda falta **tubulão** (bloco sobre
  estacas, punção e armadura executiva já implementados — ver nota);
- mezanino e formado a frio como principal (treliça, multi-vão e alma variável
  já implementados — ver nota);
- fachadas/cortes longitudinais detalhados das paredes;
- cargas especiais: ponte múltipla e carga térmica plena (sísmica e fadiga já
  implementadas — ver nota; `junta_dilatacao` cobre só o movimento térmico).

## 6. Regras do sistema (para o revisor)

- **Ask, Do Not Invent**: toda decisão de engenharia é campo do spec; `validar()`
  bloqueia enquanto houver PENDENTE.
- **Utilização** = solicitação/resistência; `<= 1,0` atende. O memorial e o
  quadro do DXF marcam `NÃO ATENDE` em vermelho quando passa de 1.
- Propriedades de perfil (incl. UPE J/Cw) e alguns dados estão marcados
  **A CONFIRMAR** no catálogo do fornecedor — confirmar antes do executivo.
- Métodos extraídos das normas — lidos verbatim do PDF, não de memória (ex.:
  `estaca_profunda.py` registra "LIDO do PDF").

## 7. Loop de projeto: execução, coordenação e iteração

O orquestrador `project_loop.py` recebe o spec e preserva cada execução em uma
pasta própria. Ele aceita o spec turnkey legado, o spec estrutural legado ou a
envoltória versionada `freecad-automatic/project-spec`.

```python
import sys
sys.path.insert(0, "framework/galpao_fw")
import project_loop

spec = {
    "schema": "freecad-automatic/project-spec",
    "schema_version": 1,
    "project": {"slug": "galpao-sjb"},
    "site": {"city": "São João da Barra", "state": "RJ", "utility": "ENEL"},
    "source_refs": {"eletrico": [{"notebook_id": "...", "source_id": "..."}]},
    "turnkey": {
        "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
        "eletrico": {"tensao_V": 380,
                     "cargas": {"iluminacao_kW": 20, "ilum_fp": 0.92,
                                "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F",
                                     "isolacao": "EPR"}},
    },
}

run = project_loop.run_project(
    spec, "projects/galpao-sjb/iterations/001",
    options={"generate_ifc": True, "generate_3d": False},
)
```

O resultado é `project-run.json`, com o hash do input, preflight, fontes,
estado de cada disciplina, artefatos, IFC, conflitos e veredito. Os estados
`passed`, `needs_review`, `blocked`, `failed` e `not_available` não devem ser
confundidos: default ou `A CONFIRMAR` hidráulico, conflito aberto e FreeCAD
ausente exigem revisão e não resultam em `atende=True`.

Se um adaptador ou uma etapa de entrega lançar uma exceção inesperada, o Loop
fecha a execução com `status: failed`, grava `reports/execution-error.json` e
registra como `partial` qualquer arquivo que já tenha sido produzido. Assim a
pasta continua auditável e não precisa ser reutilizada ou apagada para
diagnosticar a falha.

Quando `generate_2d` ou `generate_caderno` estiver habilitado, `timeout_seconds`
e um prazo global com rateio ponderado por custo: o aco recebe uma reserva
maior porque seu dispatch monta o modelo 3D e o executivo no mesmo estagio.
Para o lote completo das seis disciplinas, use pelo menos `timeout_seconds: 1800`
e confirme o resultado com `--verify-run`; o valor deve ser ajustado conforme
o hardware e nunca substitui a verificacao de `missing_disciplines`.
tempo reservado para a etapa e para as etapas restantes; disciplinas que não
couberem no prazo ficam registradas como `timeout`, e um PDF parcial nunca é
classificado como `generated`. O manifesto preserva `missing_disciplines` e
`failed_disciplines`, e o veredito do projeto fica `failed`, permitindo retomar
em uma pasta nova sem confundir entrega incompleta com revisão humana.

Para uma rodada parcial, use `required_disciplines`. O Loop preserva o spec
original em `input/spec.json`, mas envia ao runner, à coordenação, ao IFC, ao
modelo 3D e aos desenhos somente as disciplinas solicitadas. Isso permite
validar um vertical isoladamente sem executar os demais por acidente.

Os entregáveis agregados só recebem `generated` quando todas as disciplinas
solicitadas aparecem no resultado correspondente. IFC, modelo 3D ou caderno
parcial carregam `missing_disciplines` e deixam o projeto em `failed`, mesmo
que existam arquivos de algumas disciplinas.

No executivo de aço, as vistas gerais de cobertura e elevações usam uma fonte
de contexto reduzida (perfis, fechamentos e drenagem principal). Isso evita
que o HLR do TechDraw projete centenas de peças de fabricação de uma só vez.
O modelo 3D, IFC, take-off e detalhes de ligação continuam usando o conjunto
completo. A execução só deve ser aceita quando `cobertura.nao_cobertos` estiver
vazio; peças como bocais e condutores permanecem incluídas no contexto para
que a auditoria não aprove desenho incompleto.

Cada execução deve usar uma pasta nova ou vazia. O Loop recusa diretórios que
já contenham `project-run.json` ou restos de uma execução interrompida, para
não misturar artefatos nem sobrescrever o histórico; use uma nova iteração.

Antes de continuar uma cadeia de iterações, verifique o manifesto e os hashes:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --verify-run projects/galpao-sjb/iterations/001
```

O verificador retorna código `0` quando todos os artefatos estão íntegros,
`3` quando há arquivo ausente/adulterado e `4` quando o manifesto é inválido.

Uma nova rodada nunca altera a anterior:

```python
run2 = project_loop.iterate_project(
    run,
    updates={"turnkey.hidraulica.aparelhos_esgoto": {"bacia": 2}},
    resolutions=[{"issue_id": "CLH-001", "status": "reviewed"}],
)
```

O loop aplica apenas alterações explícitas no spec. A decisão textual não
fecha um clash por si só; a nova execução do modelo é a autoridade.

Ao iterar, um dicionário passado em `options` funciona como alteração parcial
da política da rodada pai. Assim, mudar apenas `generate_ifc` não apaga
`required_disciplines`, `timeout_seconds` ou `require_source_refs` herdados.

Também é possível executar a iteração pelo terminal, carregando o manifesto
da rodada anterior e registrando cada alteração como JSON:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --iterate-from projects/galpao-sjb/iterations/001 `
  --out-dir projects/galpao-sjb/iterations/002 `
  --update 'turnkey.hidraulica.aparelhos_esgoto={\"bacia\":2}' `
  --resolution '{\"issue_id\":\"CLH-001\",\"status\":\"reviewed\",\"note\":\"revisado pelo engenheiro\"}'
```

`--update` usa o formato `CAMINHO=JSON` e pode ser repetido. `--resolution`
recebe um objeto JSON e também pode ser repetido. A CLI não cria a nova rodada
quando o JSON é inválido ou quando o caminho de alteração não existe.
Para uma alteração ampla, informe também `--spec caminho-do-novo-spec.json`; o
manifesto pai continuará sendo preservado e a nova entrada será usada como
base da iteração.

### 8. Entrada por arquivo e gate de prontidão

Para executar sem escrever um script Python, copie e preencha
`projects/galpao-sjb/project-spec.template.json`. O template contém somente o
local São João da Barra/RJ e a concessionária ENEL; todo dado de engenharia
começa como `__PENDENTE__` e o resultado correto, enquanto não for preenchido,
é `blocked`.

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/galpao-sjb/project-spec.json `
  --out-dir projects/galpao-sjb/iterations/001 `
  --require-source-refs
```

O comando grava `project-run.json`, relatórios, entregáveis e coordenação na
pasta indicada. O código de saída é `0` para `passed` ou `needs_review`, `2`
para `blocked`, `3` para falha de cálculo e `4` para arquivo/JSON inválido.
Nenhum campo é preenchido automaticamente e a execução não consulta o
NotebookLM; os `source_refs` devem ser declarados no próprio spec.

### 9. Extensão por tipo de obra

O Loop não considera um nome de adaptador como suporte automático. Um novo
adaptador deve declarar suas capacidades e fornecer um runner; hooks de IFC,
coordenação, 3D e desenhos são opcionais e ausências ficam registradas como
`not_available`.

```python
import project_loop

project_loop.register_adapter(
    "residencial",
    runner_residencial,
    project_types=("casa", "residencial"),
    disciplines=("arquitetura", "estrutura"),
    deliverables=("ifc", "drawings"),
    hooks={"ifc": emitir_ifc_residencial},
)
print(project_loop.describe_adapters())
```

O registro não inventa o calculador da nova obra. Até os hooks e disciplinas
serem implementados, o manifesto permanece auditável e o veredito não vira
`passed` silenciosamente.

### 9.1 Fixture residencial sintética

Para exercitar a entrada por arquivo e o adaptador residencial sintético:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/casa-residencial-sintetica/project-spec.json `
  --out-dir .loop-runtime/project-loop/casa-residencial-sintetica `
  --no-ifc

python framework/galpao_fw/project_loop_cli.py `
  --verify-run .loop-runtime/project-loop/casa-residencial-sintetica
```

Para esta fixture, `needs_review` é o resultado esperado. A saída `ok: true`
do segundo comando significa somente integridade dos artefatos persistidos e
dos hashes; não representa cálculo, validação normativa, aprovação técnica ou
projeto para obra. A fixture não gera IFC, modelo 3D, desenhos nem caderno.

### 9.2 Política de coordenação por projeto

A política de coordenação pertence ao `ProjectSpec`, não ao código do
adaptador. Quando omitida, o Loop usa os defaults de `ProjectLoopOptions`;
quando declarada, `folga_mm` e `vol_min_mm3` do projeto prevalecem. A política
efetiva é persistida no preflight, no manifesto e no registro de coordenação:

```json
{
  "coordination_policy": {
    "enabled": true,
    "folga_mm": 1.0,
    "vol_min_mm3": 1000.0,
    "resolution_mode": "manual_approval"
  }
}
```

`resolution_mode` permanece `manual_approval`: o framework registra,
classifica e reconcilia conflitos, mas não inventa correções técnicas. Com
`enabled: false`, a execução registra `coordination.status = "disabled"`, não
cria artefatos de clash e permanece em `needs_review`.

## 10. Loop 1.5: gate de prontidão

Primeiro confirme ao vivo as fontes do spec. Essa etapa não executa disciplinas
nem gera entregáveis:

```powershell
nlm login --check
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/galpao-sjb/project-spec.json `
  --verify-source-refs `
  --out-dir projects/galpao-sjb/source-gate-001
```

O comando consulta cada `notebook_id` com `nlm list sources --json --full`,
confirma cada `source_id`, exige status remoto `2`, rejeita fontes `stale` e
verifica o limite de 50 fontes por notebook. O relatório persistido é
`source-verification.json`; o código de saída é `0` para `ready`, `2` para
`blocked` e `4` para entrada inválida. A pasta deve ser nova ou vazia.

Para executar o gate de fontes e o preflight juntos, acrescente
`--preflight-only` ao mesmo comando. Nesse modo, a verificação fica em
`reports/source-verification.json`, é incorporada ao
`project-readiness.json` e qualquer falha de fonte mantém
`can_start_project_loop=false`.

Antes de iniciar uma iteração de projeto, homologue o spec sem executar
calculadores, FreeCAD ou coordenação:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/galpao-sjb/project-spec.json `
  --out-dir projects/galpao-sjb/readiness `
  --preflight-only `
  --require-source-refs
```

Esse comando grava `project-readiness.json` e `reports/preflight.json`, mas
nunca grava `project-run.json`. O manifesto retorna `ready` somente quando não
há erros nem avisos; `needs_review` exige revisão humana e `blocked` exige
preenchimento/correção antes do Loop 2. Os códigos de saída são `0`, `1` e `2`,
respectivamente; `4` continua reservado para entrada inválida.

Para que `--require-source-refs` aceite uma fonte, cada referência precisa de
`source_id` (ou `id`) e de uma origem auditável (`notebook_id`, `catalog_id`,
`path`, `uri` ou `url`). Payloads de disciplina também precisam ser objetos
JSON; entradas semanticamente inválidas retornam código `4`. A pasta de
readiness deve ser nova e não pode conter `project-run.json` de uma execução
anterior.

Na execução inicial de produção, vincule o Loop 2 ao readiness aprovado:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/galpao-sjb/project-spec.json `
  --readiness projects/galpao-sjb/readiness `
  --out-dir projects/galpao-sjb/iterations/001 `
  --require-source-refs
```

`--readiness` confere schema, status `ready`, `can_start_project_loop`,
`project_id`, igualdade do spec e, com `--require-source-refs`, a presença de
uma verificação viva de fontes aprovada. Um readiness bloqueado não cria uma
pasta de execução.

## 11. Executar um plano explícito de iterações

Quando houver uma lista conhecida de ajustes, use um plano JSON. O orquestrador
sempre executa a rodada inicial e depois uma rodada para cada item de `steps`;
não há decisão automática de engenharia nem alteração implícita entre as
rodadas.

```json
{
  "steps": [
    {
      "updates": {
        "turnkey.hidraulica.aparelhos_esgoto": {"bacia": 2}
      },
      "resolutions": [
        {"issue_id": "CLH-001", "status": "reviewed"}
      ]
    }
  ]
}
```

Execute-o pela CLI:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/galpao-sjb/project-spec.json `
  --iteration-plan projects/galpao-sjb/iteration-plan.json `
  --readiness projects/galpao-sjb/readiness `
  --out-dir projects/galpao-sjb/sequence-001 `
  --require-source-refs `
  --no-ifc
```

Uma sequência também é uma execução inicial de produção: `--readiness` é
validado antes de criar a primeira rodada e deve corresponder exatamente ao
spec. Se o manifesto estiver bloqueado, nenhuma rodada da sequência é criada.

Cada rodada fica em `iteration-NNN/project-run.json`, com integridade dos
artefatos e `parent_run_id`. A pasta raiz recebe `project-sequence.json`, com
status agregado, passos solicitados, rodadas concluídas e eventuais erros.
Antes de criar a filha, o manifesto pai é verificado; uma pasta de sequência
deve ser nova ou vazia. O código de saída é `0` para `passed` ou
`needs_review`, `2` para `blocked` e `3` para `failed`.

## 12. Loop 3: revisar conflitos e emitir uma nova revisao

Depois que o Loop 2 gerar `coordination/pendencias.json`, crie um plano de
decisoes. O plano referencia o manifesto pai e nunca deve conter uma alteracao
que nao tenha sido aprovada pelo responsavel tecnico:

```json
{
  "schema": "freecad-automatic/coordination-resolution-plan",
  "schema_version": 1,
  "parent_run_id": "project-...",
  "project_id": "galpao-sjb",
  "decisions": [
    {
      "issue_id": "CLH-001",
      "classification": "real",
      "approval_status": "approved",
      "approved_by": "engenheiro-responsavel",
      "approved_at": "2026-08-15T12:00:00Z",
      "affected_disciplines": ["eletrico", "aco"],
      "updates": {
        "turnkey.eletrico.cargas.iluminacao_kW": 21.0
      },
      "note": "solucao registrada pelo responsavel tecnico"
    }
  ]
}
```

Execute a revisao em uma pasta nova:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --review-from projects/galpao-sjb/iterations/001 `
  --resolution-plan projects/galpao-sjb/iterations/001/coordination/resolution-plan.json `
  --out-dir projects/galpao-sjb/iterations/002 `
  --require-source-refs
```

O comando verifica o pai, aplica somente `updates` de decisoes `approved`,
reexecuta o escopo herdado, grava `coordination/resolution-plan.json` e
`coordination/review-report.json` no filho e recalcula os hashes. Pendencias
nao esperadas iniciam como `inconclusive`; elas nao sao promovidas
automaticamente a `real`. Os estados da reconciliacao sao
`accepted_expected`, `resolved`, `reopened`, `inconclusive_open` e `new_open`.

`coordination.review_status=approved` exige que nao haja conflito real
persistente, pendencia inconclusiva/nova/reaberta, entregavel solicitado
ausente, disciplina bloqueada/reprovada ou hash invalido. O `status` nativo do
projeto continua preservando os gates de cada disciplina. O pai nunca e
sobrescrito; um plano invalido falha antes de criar o filho.

Para o projeto real de Sao Joao da Barra/ENEL, primeiro preencha e homologue o
readiness. Enquanto houver `__PENDENTE__` no spec, o Loop 3 de producao nao
deve ser emitido; use apenas smoke/testes ou uma rodada bloqueada auditavel.
