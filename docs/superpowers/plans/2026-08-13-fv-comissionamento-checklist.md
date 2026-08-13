# Plano de implementação — checklist de comissionamento FV

## Contexto e arquivos

O módulo novo será isolado em `framework/galpao_fw/comissionamento_fv.py` para
não aumentar a responsabilidade de `fotovoltaico.py`. Os testes específicos
ficarão em `framework/galpao_fw/tests/test_comissionamento_fv.py`. O descobridor
será alterado em `tools/loops/discovery.py` e coberto por
`tools/loops/tests/test_discovery.py`. A especificação normativa é
`docs/superpowers/specs/2026-08-13-fv-comissionamento-checklist-design.md`.

## Contrato compartilhado

```python
montar_checklist_comissionamento_fv() -> list[dict]
validar_comissionamento_fv(caso: dict) -> dict
```

O checklist terá 41 IDs estáveis, cobrindo a documentação 4.2.1/4.3.1–4.3.5,
as alíneas 5.2.2(a-m), 5.2.5(a-g), 5.2.6(a-d), os ensaios 6.1/6.2/6.4.2/6.5/
6.6/6.7.3 e as alíneas de relatório 9.1(a-f). Cada item terá `id`, `grupo`, `tipo`,
`secao`, `criterio` e `referencia`, e cada resultado terá `id`, `status`,
`observacao` e, quando aplicável, `valores`.

## Tarefa 1: contrato do checklist e estados qualitativos

**Arquivos:**

- Criar `framework/galpao_fw/tests/test_comissionamento_fv.py`.
- Criar `framework/galpao_fw/comissionamento_fv.py` somente depois do RED.

**Passos:**

1. Escrever testes para lista nova a cada chamada, IDs/ordem estáveis, grupos
   normativos e referências com `norma`, `secao` e source ID.
2. Escrever teste de caso com verificações qualitativas verdadeiras e falsas,
   verificando `APROVADO`, `REPROVADO`, `NAO_AVALIADO` e resultado geral.
3. Rodar `python -m pytest framework/galpao_fw/tests/test_comissionamento_fv.py -q`;
   esperar falha de importação/função ausente.
4. Implementar somente o catálogo imutável interno, cópia profunda do checklist,
   normalização de booleans/dicionários e agregação de estados.
5. Rodar o teste focal novamente; esperar todos os testes da tarefa passarem.

## Tarefa 2: ensaios Voc, Isc e isolamento

**Arquivos:**

- Modificar `framework/galpao_fw/tests/test_comissionamento_fv.py`.
- Modificar `framework/galpao_fw/comissionamento_fv.py`.

**Passos:**

1. Adicionar RED para Voc/Isc calcularem desvio, emitirem alerta para o valor
   típico de 5% e exigirem `confirmado=True` para aprovação; sem confirmação o
   status deve ser `REVISAO_MANUAL`, nunca reprovação automática.
2. Adicionar RED para isolamento nas três faixas, fronteiras de 120/500 V,
   tensão de ensaio errada, resistência abaixo do mínimo e campos inválidos.
3. Rodar cada teste novo isoladamente e confirmar falha por comportamento ausente.
4. Implementar validação numérica finita e a Tabela 1: `<120 -> 250/0,5`,
   `120..500 -> 500/1,0`, `>500 -> 1000/1,0`; exigir método `metodo_1` ou
   `metodo_2`, calculando `Voc STC × 1,25` a partir de `voc_stc_v` e sem calcular
   a partir de dados inválidos. Rejeitar chaves desconhecidas e campos extras
   em registros qualitativos, Voc/Isc e isolamento, inclusive chaves de tipos
   mistos, sem lançar exceção.
5. Rodar o arquivo focal e a suíte FV existente; confirmar GREEN.

## Tarefa 3: integração do descobridor

**Arquivos:**

- Modificar `tools/loops/discovery.py`.
- Modificar `tools/loops/tests/test_discovery.py`.

**Passos:**

1. Escrever RED exigindo um candidato com origem suffix
   `:fv-commissioning-checklist`, tópico `fotovoltaico`, disciplina `eletrica`,
   prioridade 65 e exatamente o caminho da NBR 16274:
   `05_ELETRICA/ELETRICA__NBR__NBR-16274-2014__documentacao-comissionamento-fv.pdf`.
2. Exigir que o candidato sugira `framework/galpao_fw/tests/test_comissionamento_fv.py`
   e fique antes da pendência ampla.
3. Rodar o teste de descoberta e confirmar RED.
4. Adicionar a constante de fonte e o candidato atômico na ramificação existente
   da pendência FV, sem alterar o candidato anterior de strings.
5. Rodar toda `tools/loops/tests/test_discovery.py` e depois toda `tools/loops/tests`.

## Tarefa 4: revisão e documentação

**Arquivos:**

- `docs/superpowers/specs/2026-08-13-fv-comissionamento-checklist-design.md`.
- `docs/superpowers/plans/2026-08-13-fv-comissionamento-checklist.md`.
- `sessions/2026-08-13.md`.
- `.superpowers/sdd/progress.md`.

**Passos:**

1. Rodar `python -m py_compile` nos módulos alterados e `git diff --check`.
2. Rodar revisão independente do diff e resolver qualquer achado crítico ou
   importante com teste de regressão antes da conclusão.
3. Reautenticar com `nlm login --check` antes da verificação final.
4. Executar o teste focal, descoberta e suíte do loop, registrando contagens
   reais; documentar separadamente qualquer timeout da suíte ampla do framework.
5. Atualizar o progresso e o log da sessão com a evidência, sem declarar a fase
   concluída enquanto qualquer item obrigatório estiver pendente.

## Critérios de saída

- checklist e validador cobertos por testes positivos, negativos e fronteiras;
- nenhum limite de 5% convertido em reprovação automática;
- candidato de descoberta usa exatamente uma fonte pronta;
- revisão e comandos finais documentados com saída observada.
