# Contrato de capacidades dos adaptadores

**Data:** 2026-08-14  
**Status:** aprovado para implementação  
**Escopo:** tornar a extensão por tipo de obra executável e honesta

## Problema

O registro atual aceita um runner customizado, mas o restante do Loop chama
`galpao_turnkey` diretamente para relatório, coordenação, IFC, 3D e desenhos.
Assim, registrar um adaptador de casa ou edifício não é uma extensão real: ele
pode falhar em caminhos específicos do galpão ou parecer suportado sem gerar
entregáveis.

## Decisão

Estender `register_adapter` sem quebrar a assinatura antiga:

```python
register_adapter(
    name,
    runner,
    project_types=(...),
    disciplines=(...),
    deliverables=(...),
    hooks={
        "report": callable,
        "coordination": callable,
        "ifc": callable,
        "model_3d": callable,
        "drawings": callable,
    },
)
```

O runner continua recebendo `(normalized, run_dir)` e devolvendo
`(adapter_result, discipline_records)`. Cada hook opcional recebe
`(manifest, run_dir, normalized, options, adapter_result)` e pode registrar
seus artefatos usando as funções do Loop.

O adaptador nativo `galpao` declara os seis verticais e todos os hooks atuais.
Um adaptador externo pode declarar, por exemplo, `arquitetura`, executar seu
próprio cálculo e deixar IFC/coordenação/3D/desenhos como `not_available` até
fornecer os hooks correspondentes. O Loop nunca chama `galpao_turnkey` para
esse adaptador.

## Registro e manifesto

`describe_adapters()` retorna apenas metadados JSON-safe, sem expor callables.
O preflight inclui `adapter_capabilities`; adaptador desconhecido lista os
nomes registrados. O manifesto também preserva essas capacidades.

Disciplinas declaradas por um adaptador são aceitas no preflight mesmo que não
façam parte da lista nativa do galpão. Disciplinas não declaradas continuam
`unsupported_discipline`.

Quando o spec declarar `project.type`, `project.project_type` ou `project.tipo`,
o preflight compara esse valor com `project_types` do adaptador, sem diferenciar
maiúsculas/minúsculas. Um tipo explicitamente incompatível retorna
`unsupported_project_type` e bloqueia a execução; a ausência do campo mantém a
compatibilidade com specs legados.

## Estados

- Hook presente: o entregável usa o hook e mantém o status produzido por ele.
- Hook ausente e opção não solicitada: `not_requested`.
- Hook ausente e opção solicitada: `not_available`, e o projeto no mínimo fica
  `needs_review`.
- Coordenação sem hook: `not_available`; o Loop não fabrica clashes.
- Resultado/relatório genérico: salvo como `reports/adapter-result.json` para
  preservar auditoria sem usar o relatório textual do galpão.

## Aceitação

1. O adaptador `galpao` mantém a mesma jornada e os mesmos entregáveis.
2. Um adaptador de teste com disciplina `arquitetura` executa sem importar ou
   chamar `galpao_turnkey`.
3. O manifesto registra capacidades, disciplina e estados honestos de hooks
   ausentes.
4. Adaptador desconhecido permanece bloqueado e lista adaptadores suportados.
5. A regressão do Loop e dos motores turnkey permanece verde.

## Estado de implementação

O registry e o dispatch por hooks foram integrados ao `project_loop`. O
adaptador `galpao` declara seus seis verticais e entregáveis; um adaptador
externo de teste com `arquitetura` executa sem importar o orquestrador de
galpão e registra coordenação/IFC ausentes como estados explícitos.
