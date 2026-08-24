# Loop de generalização do framework

**Data:** 2026-08-15  
**Status:** aprovado pelo usuário em 2026-08-16  
**Escopo:** separar o núcleo universal das tipologias e validar o contrato com um segundo projeto sintético

## Decisão

O galpão de São João da Barra continuará sendo o caso de integração realista
do framework. Ele não será usado como modelo implícito para todos os projetos e
seus 419 conflitos ainda abertos não serão resolvidos nesta fase.

O próximo caso será uma `casa-residencial-sintetica`, executada por um
adaptador próprio e persistida como um `ProjectSpec` independente. O objetivo
é provar que o Loop consegue receber outra tipologia, declarar outras
capacidades e produzir estados honestos sem importar ou chamar a lógica
específica do galpão.

## Problema que esta fase resolve

O framework já possui um Loop persistente, registro de adaptadores, hooks e
manifestos auditáveis. Ainda falta demonstrar, em um projeto salvo no
repositório, que:

1. o núcleo coordena contratos sem conhecer a geometria ou as premissas do
   galpão;
2. as disciplinas e os entregáveis são capacidades declaradas pelo adaptador;
3. uma disciplina ou entrega ainda não implementada aparece como
   `not_available`, `not_requested` ou `needs_review`, nunca como resultado
   inventado;
4. a mesma jornada de preflight, execução, manifesto, verificação e revisão
   pode ser aplicada a duas tipologias.

## Princípios não negociáveis

- Nenhum dado específico do galpão ficará hardcoded no núcleo universal.
- O `ProjectSpec` é a entrada declarativa; o orquestrador não inventa
  dimensões, cargas, materiais, normas ou decisões de engenharia.
- Cada adaptador declara `project_types`, disciplinas e entregáveis que sabe
  atender.
- Calculadores permanecem isolados dos estados, artefatos e iterações do Loop.
- A ausência de um hook gera um estado explícito e auditável, não um arquivo
  que pareça válido.
- Fontes normativas entram como referências versionadas no spec ou no
  catálogo de fontes; o núcleo não consulta implicitamente um NotebookLM.
- O caso sintético testa contratos e integração. Ele não será apresentado como
  projeto residencial apto para obra.

## Decomposição proposta

### 1. Contrato de entrada: `ProjectSpec`

O envelope versionado deve preservar, no mínimo:

```json
{
  "schema": "freecad-automatic/project-spec",
  "schema_version": 1,
  "adapter": "casa-residencial-sintetica",
  "project": {
    "slug": "casa-residencial-sintetica",
    "type": "residencial"
  },
  "site": {},
  "turnkey": {},
  "source_refs": {}
}
```

O normalizador pode manter compatibilidade com os formatos legados, mas o
manifesto deve registrar o spec bruto, as derivações e as capacidades do
adaptador selecionado.

### 2. Contrato de adaptador

O registro existente será a fronteira entre o núcleo e uma tipologia:

```python
register_adapter(
    "casa-residencial-sintetica",
    runner,
    project_types=("residencial",),
    disciplines=("arquitetura", "eletrico", "hidraulica"),
    deliverables=("report",),
    hooks={...},
)
```

O `runner(normalized, run_dir)` devolve o resultado do adaptador e registros
de disciplinas. Hooks opcionais recebem o contexto do Loop e registram
artefatos pelo contrato comum. O núcleo não fará ramificações do tipo
`if galpao` para executar o adaptador residencial.

### 3. Contrato de disciplina

Cada registro de disciplina deve comunicar estado e evidência suficiente para
auditoria:

```json
{
  "status": "passed",
  "discipline": "hidraulica",
  "engine": "casa-residencial-sintetica",
  "artifacts": [],
  "warnings": [],
  "errors": [],
  "source_refs": []
}
```

Os estados válidos continuam sendo os estados do Loop (`passed`,
`needs_review`, `blocked`, `failed`, `not_requested` e `not_available`). O
adaptador não poderá marcar como `passed` uma disciplina que só possui
metadados ou placeholders sem a evidência correspondente.

### 4. Contrato de entregável

Todo entregável registrado no manifesto deve informar caminho relativo,
status, tamanho e SHA-256 quando gerado. IFC, modelo 3D, desenhos 2D e
caderno são capacidades independentes. A casa sintética poderá declarar
entregas ausentes nesta fase; o teste verificará que o estado é honesto e que
o manifesto continua verificável.

### 5. Contrato de clash e política de coordenação

Um clash é um registro versionado, com identidade estável por ocorrência,
disciplinas envolvidas, elementos, severidade, estado e decisão. A identidade
não pode depender de uma ordem acidental da lista nem colapsar duas
ocorrências iguais.

A política de coordenação será configurável por projeto. O núcleo apenas
classifica, reconcilia e registra decisões; resolver tecnicamente um conflito
exige dados e autorização do projeto específico.

## Fluxo de execução

```text
ProjectSpec
    -> normalização e preflight
    -> seleção do adaptador e das capacidades
    -> runner da tipologia
    -> registros de disciplinas
    -> hooks de entregáveis
    -> manifesto + artefatos hashados
    -> coordenação conforme política do projeto
    -> verificação e revisão auditável
```

O mesmo fluxo deve aceitar o spec do galpão e o spec da casa. As diferenças
ficam nos adaptadores, nos contratos declarados e nas políticas, não em
atalhos escondidos no orquestrador.

## Caso sintético de validação

O segundo projeto terá:

- slug `casa-residencial-sintetica`;
- tipo `residencial`;
- adaptador independente do módulo de galpão;
- geometria e parâmetros mínimos determinísticos, claramente marcados como
  dados de teste;
- disciplinas inicialmente selecionadas pelo contrato residencial;
- referências de fonte opcionais, sem alegar validação normativa de obra;
- entregáveis indisponíveis registrados como tais até que existam hooks reais.

O fixture não deverá importar `galpao_turnkey`, reutilizar o fixture turnkey do
galpão ou copiar decisões de engenharia do projeto real. Ele poderá reutilizar
somente APIs universais do Loop e utilitários explicitamente neutros.

## Fora do escopo desta fase

- dimensionamento residencial real de estrutura, elétrica, hidráulica ou
  esgoto;
- aprovação legal, licenciamento ou emissão para construção;
- obtenção automática de todas as normas e fontes do NotebookLM;
- resolução dos 419 clashes abertos do galpão;
- geração de uma biblioteca completa de tipologias;
- hardcode de regras específicas de São João da Barra ou da ENEL no núcleo.

Esses itens serão tratados como fases de domínio ou adaptadores posteriores,
com suas próprias fontes, contratos e testes.

## Critérios de aceitação

1. Existe um spec salvo para a casa residencial sintética.
2. O adaptador residencial é descoberto pelo registro e declara suas
   capacidades em JSON seguro.
3. O preflight rejeita tipo incompatível e aceita o tipo residencial declarado.
4. A execução residencial não importa nem chama `galpao_turnkey`.
5. O manifesto residencial preserva entrada, capacidades, estados, artefatos e
   verificação.
6. Entregáveis ausentes aparecem como estados explícitos, sem arquivos falsos.
7. Os testes do galpão continuam passando e sua jornada de integração não é
   reescrita para acomodar a casa.
8. Pelo menos um teste compara a mesma forma de contrato entre galpão e casa,
   sem comparar premissas de engenharia ou números específicos.
9. A documentação distingue claramente “contrato exercitado” de “projeto
   tecnicamente pronto para obra”.

## Sequência de implementação após a revisão

1. transformar este desenho em plano TDD;
2. criar o spec residencial e um teste de jornada que comece pelo preflight;
3. implementar o adaptador sintético mínimo e seus registros honestos;
4. validar a execução residencial e os artefatos;
5. rodar a regressão do Loop e do galpão;
6. registrar lacunas para as próximas fases de disciplinas e entregáveis.

## Ponto de revisão

O desenho e a sequência foram aprovados pelo usuário. Esta aprovação autoriza
a implementação do contrato de generalização e da política de coordenação
registrados nesta fase; não autoriza ainda cálculos residenciais reais,
aprovação legal ou emissão para obra.
