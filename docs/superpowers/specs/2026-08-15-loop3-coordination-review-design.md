# Loop 3 - Revisão, resolução e emissão final

## Objetivo

Transformar a saída de coordenação do Loop 2 em um ciclo auditável de revisão.
O Loop 3 lê os conflitos estáveis `CLH-*`, classifica cada pendência como
`expected`, `real` ou `inconclusive`, aplica somente decisões explicitamente
aprovadas pelo engenheiro, cria uma nova iteração, regenera os entregáveis e
comprova se cada pendência foi resolvida, reaberta ou permanece inconclusiva.

O Loop 3 não inventa alteração geométrica, não encerra conflito por texto e não
substitui o julgamento do responsável técnico.

## Estado atual aproveitado

O Loop 2 já produz, dentro de `coordination/`:

- `clash.json`, com o conflito bruto;
- `pendencias.json`, com IDs `CLH-*`, severidade, responsáveis e ação sugerida;
- `pendencias.bcf.json`, para intercâmbio BCF-like;
- `matriz.svg` e `relatorio.txt`;
- manifesto com `parent_run_id`, `changes`, `resolutions`, hashes e status.

O Loop 3 adicionará uma camada de decisão sem alterar o significado desses
artefatos de origem.

## Contrato de decisão

O arquivo de entrada será `coordination/resolution-plan.json`:

```json
{
  "schema": "freecad-automatic/coordination-resolution-plan",
  "schema_version": 1,
  "parent_run_id": "project-...",
  "project_id": "loop15-federated-ifc",
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
      "note": "Remanejar a instalação sem alterar a estrutura."
    }
  ]
}
```

Valores permitidos:

- `classification`: `expected`, `real`, `inconclusive`;
- `approval_status`: `pending`, `approved`, `rejected`;
- `updates`: mapa de caminhos pontuados para valores JSON, igual ao contrato de
  `iterate_project`;
- `affected_disciplines`: nomes conhecidos pelo adaptador do projeto.

Uma decisão `approved` sem `approved_by` e `approved_at` é inválida. Uma
decisão com `updates` só pode ser aplicada quando `approval_status` é
`approved`. Decisões pendentes, rejeitadas ou apenas textuais nunca alteram o
spec.

## Classificação

1. Conflitos com `esperado=true` recebem classificação inicial `expected` pela
   regra já auditada de montagem intencional. Essa classificação não aplica
   alteração ao spec.
2. Conflitos não esperados começam como `inconclusive`; o sistema não pode
   promovê-los automaticamente a `real`.
3. O engenheiro pode aprovar `real`, `expected` ou `inconclusive`. `real` exige
   uma ação corretiva e, para fechar a pendência, pelo menos uma alteração
   aplicável ao spec.
4. Uma decisão aprovada de `inconclusive` permanece aberta e impede a emissão
   final, mesmo que a rodada seja reexecutada.

## Fluxo de execução

### Entrada

`review_project(previous_run, resolution_plan, out_dir=None, options=None)`
aceita um manifesto/pasta pai e o plano JSON. Antes de qualquer alteração:

- verifica os hashes do pai;
- confirma `project_id` e `parent_run_id` do plano;
- valida todos os `issue_id` contra `coordination/pendencias.json`;
- rejeita IDs duplicados, decisões duplicadas e caminhos de spec ausentes;
- calcula as disciplinas afetadas a partir de `affected_disciplines` e dos
  prefixos dos updates; geometrias comuns ou estrutura tornam a dependência
  federada explícita.

### Nova iteração

O Loop 3 chama a mesma autoridade do Loop 2 (`iterate_project`) com somente os
updates aprovados. As disciplinas declaradas afetadas são sempre incluídas na
execução. Se o entregável federado exigir coerência de todo o modelo, o
orquestrador pode reexecutar disciplinas dependentes adicionais; o manifesto
registra `affected_disciplines` e `rerun_disciplines` separadamente.

As opções de IFC, modelo 3D, desenhos, caderno, fontes e timeout são herdadas
do pai, salvo patch explícito e válido.

### Reconciliação

Após a nova coordenação, os conflitos são associados pelo `guid` estável, não
por posição na lista:

- esperado persistente: `accepted_expected`;
- real aprovado que desapareceu: `resolved`;
- real aprovado que persiste: `reopened`;
- inconclusivo persistente: `inconclusive_open`;
- conflito novo: `new_open`.

O arquivo `coordination/review-report.json` conterá a reconciliação, as
classificações, as decisões aplicadas, disciplinas reexecutadas, conflitos
resolvidos e conflitos ainda abertos. O `project-run.json` filho preservará o
plano, o vínculo pai/filho e os hashes dos novos artefatos.

### Emissão final

Uma revisão pode ser marcada `coordination.review_status=approved` somente se:

- não houver `real` aprovado ainda presente;
- não houver `inconclusive_open`, `new_open` ou `reopened`;
- IFC, modelo 3D, desenhos e caderno pedidos estiverem `generated`;
- `verify_project_run` confirmar todos os hashes;
- os gates nativos das disciplinas e as premissas humanas continuarem
  registrados, sem serem mascarados pela aprovação de coordenação.

Caso contrário, o resultado permanece `needs_review` ou `failed`, com a razão
persistida. A aprovação da coordenação nunca força `atende=true` quando uma
disciplina reprova ou quando o preflight está bloqueado.

## API e CLI

API pública:

```python
from project_loop import review_project

revision = review_project(
    "runs/loop-2",
    "runs/loop-2/coordination/resolution-plan.json",
    out_dir="runs/loop-3",
)
```

CLI:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --review-from runs/loop-2 `
  --resolution-plan runs/loop-2/coordination/resolution-plan.json `
  --out-dir runs/loop-3
```

O plano também poderá ser passado como objeto pela API, mas a CLI sempre
persistirá uma cópia no filho para auditoria.

## Falhas e segurança

- pai adulterado ou incompleto: abortar antes de criar a filha;
- plano inválido, issue inexistente ou update não aprovado: código de entrada
  inválida, sem execução parcial;
- disciplina afetada falha: preservar artefatos parciais como `partial`, marcar
  `failed` e não emitir revisão aprovada;
- conflito não encontrado após mudança: só então marcar `resolved`, com o guid
  e a evidência da nova rodada;
- nenhum arquivo do pai é sobrescrito.

## Testes de aceitação

- classificar esperados automaticamente e não esperados como inconclusivos;
- rejeitar update em decisão pendente/rejeitada;
- aceitar update somente com aprovação, responsável e data;
- recusar plano com issue inexistente ou pai adulterado;
- reexecutar disciplina afetada e preservar escopo/política do pai;
- reconciliar `resolved`, `reopened`, `inconclusive_open` e `new_open` por guid;
- exigir IFC/modelo/pranchas/caderno e hashes válidos para revisão aprovada;
- executar um smoke sintético com conflito corrigido e verificar manifesto pai,
  manifesto filho, artefatos e relatório final.

## Fora de escopo

- escolha automática de solução de engenharia;
- interface gráfica de aprovação;
- consulta normativa nova durante a classificação de um clash;
- execução de produção do SJB/ENEL enquanto o readiness estiver bloqueado.
