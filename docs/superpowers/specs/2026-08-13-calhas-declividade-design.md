# Fase 21b: validação de declividade de calhas

## Objetivo

Fechar a falha de entrada em `framework/galpao_fw/calhas.py` que permite
declividade zero, abaixo de 0,5%, negativa, `NaN` ou infinita. A declividade
negativa atualmente alcança a raiz quadrada da fórmula de Manning e produz um
`TypeError` por número complexo.

## Evidência normativa

- NotebookLM: `08_ESGOTO_PLUVIAL_REUSO`
  (`8ccc440c-1e37-4089-b008-2fc667c03f2c`).
- Fonte única: ABNT NBR 10844:1989, source ID
  `6a4def7b-b788-4ee8-9441-433081a98c84`, status remoto `2`.
- Citação auditável: seção 5.5.2 exige inclinação uniforme mínima de `0,5%`
  para calhas de beiral e platibanda; a seção 5.7.1 repete o mínimo para
  condutores horizontais.

## Contrato público

Manter as assinaturas e o formato de retorno existentes. Entradas não finitas
ou fisicamente inválidas devem produzir `ValueError` determinístico antes de
qualquer operação hidráulica. Em particular:

- `secao_calha(..., i=0.005)` continua válido;
- `secao_calha(..., i < 0.005)` falha com mensagem contendo `declividade`;
- `Q_req` e `I_mm_h` não podem ser negativos ou não finitos;
- `B_base`, `n`, `H_max` e `n_condutores` devem ser finitos e positivos;
- dimensões de contribuição não podem ser negativas ou não finitas;
- resultados numéricos derivados não podem ser `NaN`/infinito.

Zero continua permitido para área/intensidade/vazão, porque representa um caso
sem contribuição e não contradiz o limite de declividade da calha.

## Implementação

Adicionar helpers internos pequenos para exigir número finito, não negativo e
positivo. Usá-los na borda das funções públicas existentes; não alterar a
equação de Manning, a escada de seções, a regra de Bellei ou o dimensionamento
do condutor.

## Testes

- preservar o caso válido do pipeline e o limite exato `i=0.005`;
- rejeitar `0`, `0.004`, `-0.01`, `NaN` e `inf` com `ValueError`;
- rejeitar entradas não finitas e negativas nas funções públicas;
- verificar que as saídas válidas continuam finitas e com veredito booleano;
- rodar a suíte hidráulica relacionada e a regressão do loop.

## Fora do escopo

- não digitalizar o ábaco da Figura 3;
- não criar a rede topológica de inspeções;
- não alterar `rodar_galpao.py`, o schema do projeto ou a geometria 3D;
- não transformar o fallback de `150 mm/h` em valor normativo universal.
