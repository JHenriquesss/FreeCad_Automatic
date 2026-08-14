# Segurança verificável da água quente — Especificação de design

**Data:** 2026-08-13  
**Status:** aprovado pela continuidade da execução do loop  
**Fase:** 30

## Objetivo

Transformar a pendência ampla de fontes de água quente em uma tarefa atômica e
implementar gates de projeto que não permitam tratar uma rede de água quente
como concluída quando faltam dados de segurança exigidos pela ABNT NBR
5626:2020.

Esta fase cobre somente a rede predial de água quente já existente no
framework. Reservatórios, bombas, fontes adicionais e seleção de equipamentos
continuam pendências posteriores.

## Evidência normativa autorizada

Consulta ao notebook `07_HIDRAULICA`, fonte `HIDRAULICA__NBR__NBR-5626-2020__agua-fria-quente.pdf`,
source ID `88bbe8c0-cab9-44e4-bfe6-8b895d8d6fc2`, retornou citações textuais
auditáveis para:

- 6.7.1.1 e 6.7.1.2: vazões consideradas e vazões máximas devem ser
  explicitadas no projeto;
- 6.9.1–6.9.6: pressão dinâmica necessária/mínima, pressão estática máxima de
  400 kPa e compatibilidade entre pressões fria e quente;
- 6.10.3–6.10.5: limite de 70 °C em ambientes sanitários com misturadores,
  prevenção automática de escaldamento a 45 °C para uso corporal e proteção de
  superfícies;
- 6.11.1–6.11.4: consideração da dilatação e mecanismos para absorver
  movimentações;
- 6.12.1–6.12.2: redução e estimativa das perdas térmicas;
- 6.13.3.2 e 6.13.3.5: limitação automática de temperatura e pressão em
  aquecedores de acumulação e reservatórios.

O texto consultado não fornece um limite numérico universal para “pressões
próximas” entre água fria e quente nem espessura universal de isolamento. O
framework deve exigir uma verificação/decisão explícita nesses pontos, sem
inventar um valor.

## Design

`hidraulica_predial.py` receberá uma função pura
`verifica_agua_quente_seguranca(config, vazao_calculada_Ls,
pressao_dinamica_ponto_kPa)`.

O bloco `config` será fornecido pelo projeto em
`hidraulica.agua_quente_seguranca`. Ele deverá declarar:

- vazão normal e máxima consideradas;
- pressão estática de projeto e confirmação da compatibilidade entre água fria
  e quente;
- temperatura máxima, existência de misturadores sanitários e uso corporal;
- limitadores automáticos aplicáveis, proteção de superfícies expostas,
  medidas/estimativa de perdas térmicas;
- consideração da dilatação e absorção das movimentações;
- se há aquecedor de acumulação e, nesse caso, os três dispositivos de
  segurança requeridos.

Dados ausentes produzem `OK=False`, `inconclusivo=True` e razões auditáveis.
Violações explícitas produzem `OK=False`, `inconclusivo=False`. Uma
configuração completa e compatível produz `OK=True`.

`galpao_hidraulica.rodar()` chamará a função quando existir água quente,
exporá o resultado em `redes.agua_quente.seguranca` e criará o gate
`gates.seguranca_agua_quente`. A rede quente sem esse bloco não será apresentada
como dimensionamento completo.

## Loop de desenvolvimento

`tools/loops/discovery.py` decomporá somente o item
“Completar fontes de água quente, reservatórios, bombas e componentes
hidráulicos” de `fontes/pendencias-atualizacao.md` em uma candidata
`agua_quente_segura`, preservando a candidata ampla para rastreabilidade. O
escopo de pesquisa será exclusivamente:

```text
07_HIDRAULICA/HIDRAULICA__NBR__NBR-5626-2020__agua-fria-quente.pdf
```

O prompt exigirá seções, condições, source ID exato, trechos textuais e
declaração explícita de lacunas sem parâmetros universais.

## Fora do escopo

- alterar ou remover fontes do NotebookLM;
- presumir edição diferente da fonte consultada;
- implementar reservatório, bomba, recirculação ou seleção de equipamento;
- criar espessuras, temperaturas ou tolerâncias que não estejam na fonte;
- alterar as redes fria, esgoto ou pluvial;
- considerar ausência de dados como aprovação silenciosa.

## Critérios de aceitação

- a candidata atômica e seus prompts são descobertos com caminho único e
  estável;
- os testes RED demonstram que a função de segurança ainda não existe e que a
  integração falha sem o bloco explícito;
- a implementação passa nos testes novos e nas regressões hidráulicas;
- o loop consulta somente o source ID autorizado, cria artefatos auditáveis e
  passa pelos gates de revisão, sem alterar fontes;
- a pendência ampla permanece aberta para reservatórios, bombas e componentes.
