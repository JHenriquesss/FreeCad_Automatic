# Entradas pendentes do galpão SJB/ENEL

Este arquivo é a checklist do Loop 1.5. As fontes do NotebookLM já estão
vinculadas ao template por `notebook_id` e `source_id`; ainda não há dados
dimensionais ou de engenharia suficientes para iniciar o Loop 2.

Última reconciliação das fontes: `nlm login --check` válido em 2026-08-15;
15 notebooks da coleção FreeCAD Automatic, 188 fontes remotas e 14 referências
do template conferidas com status remoto `2`. O bloqueio atual é de entrada do
empreendimento, não de autenticação ou de referência normativa.

Preencha o arquivo `project-spec.json` a partir de
`project-spec.template.json`, sem substituir dados desconhecidos por valores
estimados.

Verificação adicional em 2026-08-14 22:05: `nlm login --check` válido; gate ao
vivo `ready`, 14 referências consultadas e 0 erros. O preflight combinado
permaneceu `blocked` somente pelos 9 erros listados abaixo. O tipo de obra
`galpao` já está declarado no template e é compatível com o adaptador nativo.

## Dados comuns

- comprimento, vão e pé-direito;
- inclinação e tipo de cobertura;
- implantação, orientação, cotas e níveis;
- uso do galpão, áreas, ambientes e quantidade de pavimentos;
- coordenadas/endereço do terreno e restrições de implantação.

## Concreto e fundações

- sistema estrutural e elementos de concreto previstos;
- fck, aço, cobrimentos e vida útil;
- ações permanentes, variáveis, vento e combinações adotadas;
- sondagem, tensão/parametrização do solo e nível d'água;
- tipo de fundação, apoios e parâmetros de execução.

## Aço

- perfis e seções ou regra de seleção;
- grau do aço, contraventamentos e estabilidade global;
- ligações, parafusos, soldas e condições de montagem;
- cargas, vãos, espaçamentos e combinações compartilhadas com concreto;
- proteção contra corrosão e, quando aplicável, proteção contra incêndio.

## Elétrica e SPDA

- tensão, fases, frequência e padrão de entrada;
- lista de cargas, demanda, fator de potência e simultaneidade;
- ponto de entrega, modalidade de fornecimento e dados/protocolo da ENEL;
- comprimentos/rotas, quadros, circuitos e equipamentos;
- aterramento, equipotencialização, SPDA e classificação de risco.

## Incêndio

- ocupação, população, carga de incêndio e classificação de risco;
- área, altura, compartimentação e rotas de fuga;
- extintores, hidrantes, alarme, iluminação e sinalização previstos;
- exigências aplicáveis do Corpo de Bombeiros e protocolo do processo.

## Climatização

- uso, ocupação, horários e condições internas desejadas;
- cargas térmicas, renovação de ar e exaustão;
- equipamentos, capacidades, posições e caminhos de manutenção;
- requisitos de ruído, energia e drenagem de condensado.

## Hidráulica, esgoto, pluvial e reúso

- população, consumo, aparelhos e simultaneidade;
- fonte, pressão, reservação, cotas e pontos de abastecimento;
- traçado e ponto de ligação do esgoto;
- áreas de cobertura, chuva de projeto, drenagem e lançamento;
- reúso, separação de redes e requisitos de operação/manutenção.

## Critério de liberação

1. Confirme as fontes declaradas em uma pasta nova:

```powershell
nlm login --check
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/galpao-sjb/project-spec.json `
  --verify-source-refs `
  --out-dir projects/galpao-sjb/source-gate-001
```

2. Depois execute o preflight do projeto:

Execute:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/galpao-sjb/project-spec.json `
  --out-dir projects/galpao-sjb/readiness `
  --preflight-only `
  --require-source-refs
```

Também é possível combinar as duas etapas acrescentando
`--verify-source-refs` ao comando de preflight. Nesse formato, o relatório de
fontes é gravado em `readiness/reports/source-verification.json` e uma fonte
inválida mantém o readiness bloqueado.

O Loop 2 só pode começar quando o resultado for `ready`. `blocked` significa
que ainda faltam entradas; `needs_review` significa que há uma decisão ou
fonte que exige revisão humana.

Na fotografia atual do template, o preflight produz 9 erros: três de geometria
comum (`comprimento`, `vao` e `pe_direito`) e um `pending_discipline_input` para
cada uma das seis disciplinas. Depois do preenchimento, execute o comando acima
em uma pasta nova; não reutilize os diretórios de readiness anteriores.

## Estado confirmado após a criação do spec de trabalho

Em 2026-08-14, a autenticação foi renovada com `nlm login` e confirmada por
`nlm login --check`; o gate remoto das referências do arquivo foi `ready`. O
arquivo canônico de preenchimento é agora `project-spec.json`, criado sem
alterar o template e sem inventar valores de engenharia. O readiness local
mais recente está em
`.loop-runtime/project-loop/readiness-sjb-project-spec-20260815/` e permanece
`blocked` pelos mesmos 9 campos: geometria comum e os seis sub-specs.
