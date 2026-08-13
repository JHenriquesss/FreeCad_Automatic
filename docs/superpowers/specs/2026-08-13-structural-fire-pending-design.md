# Decomposição das fontes de incêndio estrutural — Especificação de Design

**Data:** 2026-08-13
**Status:** aprovado para implementação nesta sessão
**Escopo:** Fase 28 do loop de desenvolvimento

## Objetivo

Corrigir a duplicação introduzida pelo documento espelho de pendências e
transformar a lacuna ampla de incêndio estrutural em três tarefas de pesquisa
independentes, cada uma com fonte local, notebook e prompt auditáveis.

## Evidência atual

`fontes/fontes-faltantes.md:P1` já é a origem canônica da decomposição de NBR
12693/NBR 13434. A linha equivalente em
`fontes/pendencias-atualizacao.md:Incêndio, geotecnia e segurança do trabalho`
é um espelho operacional e atualmente gera uma candidata genérica duplicada.

A mesma seção de `pendencias-atualizacao.md` contém a lacuna ampla:

```text
Obter ABNT NBR 15200, NBR 14432 e NBR 14323 para estruturas em situação de incêndio.
```

Nenhum dos três PDFs foi localizado em `fontes/09_INCENDIO` e não há entrada
catalogada disponível para eles.

## Decisões

### Deduplicação estreita

Ignorar somente o item que começa com “Obter ABNT NBR 12693 e NBR 13434 para
proteção contra incêndio” quando ele vier do heading
`fontes/pendencias-atualizacao.md:Incêndio, geotecnia e segurança do trabalho`.
Não ignorar a seção inteira nem outras pendências do mesmo arquivo.

### Tarefas atômicas

O item estrutural será expandido, mantendo a candidata ampla original para
rastreabilidade, em:

1. **NBR 15200 — concreto em situação de incêndio**, tópico `fogo_concreto`.
2. **NBR 14432 — exigências de resistência ao fogo**, tópico `resistencia_fogo`.
3. **NBR 14323 — estruturas de aço e mistas em situação de incêndio**, tópico
   `fogo_aco`.

Todas usarão disciplina `seguranca` e ficarão no notebook da pasta
`09_INCENDIO`, evitando misturar a consulta com fontes gerais de aço ou
concreto. As edições não serão presumidas.

## Caminhos canônicos

```text
09_INCENDIO/INCENDIO__NBR__NBR-15200__estruturas-concreto-incendio.pdf
09_INCENDIO/INCENDIO__NBR__NBR-14432__exigencias-resistencia-fogo.pdf
09_INCENDIO/INCENDIO__NBR__NBR-14323__estruturas-aco-incendio.pdf
```

Os nomes neutros permitem confirmar a edição quando os arquivos forem
fornecidos. O loop não deve substituir uma fonte existente por semelhança de
título, consultar outra norma como substituta ou inferir a edição.

## Prompts e testes sugeridos

Cada tópico terá prompt normal e retry próprios, exigindo somente requisitos
verificáveis do PDF declarado, seção/tabela, source ID exato, trechos textuais
no retry e declaração explícita de ausência quando a norma não cobrir o ponto.

Os testes sugeridos serão escolhidos dos testes de incêndio existentes; a tarefa
NBR 15200 também apontará para `test_fogo_nbr15200.py`.

## Fora do escopo

- baixar normas ou alterar notebooks remotos;
- implementar ou alterar fórmulas de fogo, concreto ou aço;
- decidir a edição vigente das três normas;
- transformar a linha espelho em nova fonte de verdade;
- desbloquear NBR 12693, NBR 13434 ou NBR 6122 sem os arquivos corrigidos.

## Critério de aceitação

Os testes devem provar que o espelho não cria candidata, que a lacuna
estrutural cria exatamente três atomics com caminhos distintos e estáveis, e
que cada prompt usa somente sua norma. A suíte completa deve permanecer verde.
Um dry-run autenticado deve estacionar a primeira tarefa estrutural por fonte
ausente antes de `nlm notebook query`, gerando pedido manual específico.
