# Loop de projeto — especificação de integração e execução

**Data:** 2026-08-14  
**Status:** entrada JSON/CLI implementada e verificada; produção real ainda bloqueada por ausência de spec completo  
**Objetivo:** receber um `spec`, executar as disciplinas solicitadas, produzir entregáveis auditáveis, detectar conflitos entre modelos e permitir uma nova iteração somente com alterações explícitas.

## Contexto atual

O framework já possui os motores necessários para o primeiro vertical:

- `projeto_spec` valida o contrato estrutural e `rodar_projeto` calcula aço, memorial, IFC e, quando disponível, FreeCAD/TechDraw;
- `galpao_turnkey` despacha concreto, aço, elétrica, incêndio, climatização e hidráulica;
- `emitir_bim` e `build_federado` produzem modelos por disciplina e federados;
- `checa_interferencia_federada` e `compatibilizacao` detectam e registram pendências de coordenação;
- `caderno_turnkey` mescla as pranchas em um caderno executivo.

O problema restante não é criar um segundo calculador. É transformar esses caminhos em uma execução única, reproduzível e honesta. Hoje o `projeto_spec` estrutural e os sub-specs do turnkey são contratos diferentes; a execução pode degradar quando uma ferramenta não está disponível; e não existe um manifesto que diga, para cada disciplina e entregável, se o resultado foi gerado, bloqueado, reprovado ou apenas não solicitado.

## Objetivos

1. Expor uma entrada única `run_project(spec, out_dir, ...)`.
2. Aceitar os specs legados atuais e uma envoltória versionada sem quebrar os motores existentes.
3. Executar cada disciplina isoladamente, preservando a regra `Ask, Do Not Invent`.
4. Registrar preflight, fontes declaradas, gates, resultados, artefatos, hashes e veredito.
5. Gerar IFC por disciplina, IFC federado e relatório de compatibilização quando a dependência estiver disponível.
6. Registrar a ausência de FreeCAD/IFC como estado explícito, nunca como sucesso silencioso.
7. Expor `iterate_project(...)`, que parte de uma execução anterior, aplica somente alterações fornecidas pelo usuário e cria uma nova execução vinculada à anterior.
8. Manter uma extensão por adaptadores para que casas, edifícios e instalações futuras não precisem ser codificados dentro do adaptador do galpão.

## Não objetivos

- Resolver automaticamente conflitos de engenharia ou inventar valores de projeto.
- Substituir a pesquisa normativa do Loop de desenvolvimento ou consultar a web silenciosamente.
- Prometer projeto executivo quando uma disciplina está bloqueada, inconclusiva ou sem entregável obrigatório.
- Fazer merge, push ou apagar artefatos de execuções anteriores.
- Reescrever os calculadores existentes para caberem no novo orquestrador.

## Contrato de entrada

O novo caminho aceita uma envoltória opcional:

```json
{
  "schema": "freecad-automatic/project-spec",
  "schema_version": 1,
  "project": {"slug": "galpao-sjb", "description": "..."},
  "site": {"city": "São João da Barra", "state": "RJ", "utility": "ENEL"},
  "source_refs": {
    "eletrico": [{"notebook_id": "...", "source_id": "...", "title": "..."}]
  },
  "structure": {"terreno": {}, "geometria": {}, "fundacao": {}, "...": "spec estrutural legado"},
  "turnkey": {
    "geometria": {"comprimento": 28.5, "vao": 20.0, "pe_direito": 8.0},
    "concreto": {}, "eletrico": {}, "incendio": {},
    "hidraulica": {}, "climatizacao": {}
  }
}
```

Também são aceitos:

- o spec turnkey legado, com `geometria` e as disciplinas no topo;
- o spec estrutural legado, com `terreno`, `geometria`, `fundacao` etc. Nesse caso ele é tratado como a disciplina `aco` e a geometria comum é derivada sem alterar premissas.

O normalizador não preenche decisões ausentes. Quando uma geometria é derivada de outro bloco já decidido, a origem fica registrada no preflight; quando uma decisão de engenharia está ausente, a disciplina fica `blocked`.

`source_refs` é evidência declarada, não uma nova fonte normativa. A opção `require_source_refs=True` permite que uma execução de produção bloqueie a disciplina que não tiver ao menos uma referência auditável.

## Arquitetura

O módulo `framework/galpao_fw/project_loop.py` terá uma API independente dos calculadores:

```python
run = run_project(spec, out_dir, options=None)
next_run = iterate_project(run, updates={"turnkey.hidraulica.aparelhos_agua": {...}})
```

O módulo mantém um registro de adaptadores. A primeira implementação é `galpao`, que chama os orquestradores existentes; futuros adaptadores poderão tratar outros tipos de obra sem mudar o ledger da execução.

O registro declara tipos de obra, disciplinas, entregáveis e hooks opcionais.
O adaptador `galpao` possui os hooks nativos; adaptadores futuros podem
executar seus próprios runners e receber `not_available` para qualquer entrega
ainda não implementada. O Loop não chama `galpao_turnkey` fora do adaptador
`galpao`.

As fases são:

```text
normalizar → preflight → executar disciplinas → emitir BIM
          → federar/coordenar → emitir 2D/3D opcional
          → classificar estado → persistir manifesto
          → receber decisão/alteração → nova iteração
```

Uma falha de uma disciplina não derruba as demais. Uma falha no contrato comum (por exemplo, geometria inválida) bloqueia as disciplinas que dependem dele. O loop não chama o agente de desenvolvimento nem o NotebookLM durante a execução; os IDs de fonte recebidos no spec são apenas preservados e validados.

Quando `required_disciplines` é informado, ele define o escopo efetivo da
rodada: o input original continua preservado para auditoria, mas o adaptador
recebe um turnkey recortado às disciplinas solicitadas. O mesmo recorte deve
ser usado na coordenação e nos hooks de IFC, 3D e desenhos, evitando cálculo ou
entrega de verticais não pedidos.

## Estados e veredito

Estados de disciplina e entregável:

- `passed`: executou, gates atendem e não há alerta que exija decisão;
- `needs_review`: executou, mas há `A CONFIRMAR`, default assumido, aviso normativo ou conflito aberto;
- `blocked`: faltam dados, validação estrutural ou fonte exigida;
- `failed`: o motor lançou erro ou algum gate reprovou;
- `not_requested`: disciplina conhecida, mas não solicitada;
- `not_available`: etapa opcional depende de ferramenta ausente.

O veredito do projeto é calculado pelo ledger, não copiado de `R["ATENDE"]`:

1. `blocked` se houver disciplina obrigatória bloqueada ou preflight inválido;
2. `failed` se houver falha de cálculo/gate;
3. `needs_review` se houver pendência aberta, `A CONFIRMAR`, default ou entregável obrigatório indisponível;
4. `passed` somente quando todas as disciplinas solicitadas e todos os entregáveis obrigatórios atenderem.

`atende` só será `True` para `passed`. O retorno também preservará os vereditos nativos dos motores para auditoria, sem tratá-los como aprovação global.

## Manifesto e layout de saída

Cada execução preserva sua própria pasta:

```text
<out_dir>/
  input/spec.json
  reports/preflight.json
  reports/disciplinas.json
  reports/turnkey.txt
  bim/<disciplina>.ifc
  bim/turnkey_federado.ifc
  coordination/clash.json
  coordination/pendencias.json
  coordination/pendencias.bcf.json
  coordination/matriz.svg
  coordination/relatorio.txt
  model/                       # somente se 3D for solicitado
  drawings/                    # somente se 2D/caderno forem solicitados
  project-run.json
```

`project-run.json` contém `schema_version`, `run_id`, `project_id`, `iteration`, `parent_run_id`, hash do spec, opções, preflight, fontes, cada disciplina, coordenação, lista de artefatos (`path`, `kind`, `status`, `size`, `sha256`) e o veredito final. Caminhos no manifesto são relativos à pasta da execução.

## Compatibilização e iteração

O modelo federado gera conflitos candidatos com o algoritmo já existente. `compatibilizacao.gerar_pendencias` fornece IDs/GUIDs estáveis; conflitos esperados de montagem permanecem aprovados, e conflitos a revisar permanecem abertos.

`iterate_project`:

- carrega o spec e o manifesto da execução pai;
- aplica somente um mapa de alterações por caminho pontilhado ou um spec substituto explicitamente fornecido;
- registra `parent_run_id`, número da iteração, alterações e decisões do usuário;
- executa novamente todas as etapas determinísticas;
- considera o novo modelo como autoridade: um conflito só deixa de estar aberto se não for detectado ou se uma decisão explícita o aprovar, sempre preservando o histórico.

O loop não transforma uma decisão textual em mudança geométrica. Para corrigir um clash, o usuário/engenheiro fornece a alteração no spec; a nova execução comprova o efeito.

Cada execução deve receber uma pasta nova ou vazia. O orquestrador recusa uma
pasta que já contenha `project-run.json` ou restos de uma execução interrompida,
evitando sobrescrever o histórico ou misturar artefatos de rodadas diferentes.

Exceções inesperadas do adaptador não deixam a execução sem veredito: o Loop
persiste `status: failed`, registra o erro estruturado e inclui como artefatos
`partial` os arquivos que existirem após a interrupção, com tamanho e SHA-256.

`verify_project_run` e a opção CLI `--verify-run` conferem presença, tamanho e
SHA-256 dos artefatos declarados antes da próxima iteração. A verificação é
somente leitura e retorna falha explícita para arquivo ausente, adulterado ou
caminho que escape da pasta da execução.

## Testes de aceitação

O test tree terá:

- uma jornada real do usuário: spec de galpão → execução → manifesto → IFC/relatório de coordenação;
- ramo de preflight bloqueado por spec estrutural incompleto;
- ramo de isolamento de disciplina com erro;
- ramo de `A CONFIRMAR`/default hidráulico que não pode resultar em `passed`;
- ramo de conflito HVAC/hidráulica x estrutura com pendência aberta;
- ramo de iteração que preserva o pai, aplica alteração explícita e gera novo manifesto;
- ramo sem FreeCAD/ifcopenshell que registra `not_available` sem fingir entrega;
- teste de hashes, caminhos relativos e IDs de conflito estáveis.

O primeiro critério de saída é uma execução de cálculo/IFC/clash/manifesto reproduzível no galpão. A emissão viva de FreeCAD/TechDraw será exercitada quando solicitada e ficará claramente separada do núcleo que pode rodar em CI.

## Entrada operacional por arquivo

O primeiro incremento de produção está disponível em `project_io.py` e
`project_loop_cli.py`. O carregador aceita JSON UTF-8 versionado e, por
compatibilidade, specs legados; a CLI delega ao mesmo `run_project`. O template
SJB/ENEL é deliberadamente bloqueado por `__PENDENTE__` até receber dados reais.

Na homologação com FreeCAD disponível, o mesmo contrato gerou IFC, modelo 3D,
desenhos e caderno. O Loop normaliza os caminhos absolutos devolvidos por
ferramentas legadas antes de gravar `deliverables`; opções de execução e o
input original permanecem preservados como configuração/entrada, não como
artefatos.

## Sequência declarativa de iterações

Para execuções supervisionadas com mais de uma iteração, a API
`run_project_sequence` e a opção CLI `--iteration-plan` recebem uma lista
explícita de passos. A sequência executa a rodada inicial e aplica, em ordem,
somente os mapas `updates`, as `resolutions` e os eventuais `spec` substitutos
declarados em cada passo.

Cada rodada continua sendo uma execução independente: usa uma pasta própria,
verifica a integridade do pai antes de iterar, preserva `parent_run_id` e grava
seu `project-run.json`. A raiz da sequência grava `project-sequence.json` com
o status agregado e a lista de rodadas. Falhas de validação do plano ocorrem
antes da criação da pasta; falhas durante a execução ficam registradas e são
propagadas ao chamador.

## Gate ao vivo de fontes

`verify_project_source_refs` e a opção CLI `--verify-source-refs` conferem o
estado remoto das referências antes do preflight de produção. Para cada
notebook declarado, o gate executa `nlm list sources --full --json` e exige que
cada `source_id` exista, tenha status `2`, não esteja stale e que o notebook
permaneça dentro do limite operacional de 50 fontes. O resultado é persistido
como `source-verification.json`; uma falha de fonte deixa o gate `blocked` e
não executa nenhuma disciplina.

Quando `--verify-source-refs` é combinado com `--preflight-only`, os dois gates
compartilham a mesma pasta de readiness. A verificação é gravada em
`reports/source-verification.json`, anexada ao `project-readiness.json` e
`can_start_project_loop` só pode ser verdadeiro quando os dois resultados forem
liberáveis.

A execução inicial pela CLI pode receber `--readiness` apontando para esse
manifesto. O comando confere que o readiness está `ready`, que o `project_id` e
o input são os mesmos do spec e, quando `--require-source-refs` é usado, que a
verificação viva de fontes também está aprovada. Readiness bloqueado não cria
uma rodada parcial.

O mesmo vínculo é obrigatório para `--iteration-plan`: o manifesto é validado
antes de criar a raiz da sequência, e uma sequência bloqueada não cria sua
primeira rodada.

Quando a execução é liberada pela CLI, o resumo do readiness é persistido no
`project-run.json` e no `project-sequence.json`, incluindo o SHA-256 do arquivo
de readiness e o hash canônico do input validado. Iterações filhas preservam
essa proveniência.
