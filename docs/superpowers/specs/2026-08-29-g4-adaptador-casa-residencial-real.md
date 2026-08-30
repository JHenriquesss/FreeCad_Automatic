# G4 — Adaptador de casa residencial real

**Data:** 2026-08-29
**Status:** em implementação
**Escopo:** substituir a fixture de contrato por um adaptador residencial que
calcula de verdade as três disciplinas declaradas (arquitetura, elétrico,
hidráulica).

## Estado anterior

`casa_residencial_sintetica.py` declara `("arquitetura", "eletrico",
"hidraulica")` e **não calcula nenhuma delas**: devolve `needs_review` com o
gate `synthetic_fixture: True`. O desenho de generalização
(`2026-08-15-generalizacao-framework-design.md`) foi explícito: "o caso
sintético testa contratos e integração. Ele não será apresentado como projeto
residencial apto para obra".

Em paralelo, a vertical elétrica residencial (`residencial_eletrica.py`,
Fases 6A/6B) já é real: demanda Enel, padrão de entrada, condutores/proteções
NBR 5410, desenhos e IFC. Ela cobre **uma** disciplina e depende de o usuário
declarar ponto a ponto (`circuits.points`) — nunca confere se os pontos
declarados atendem ao **mínimo normativo**.

## O que este loop entrega

Um segundo adaptador residencial, `casa-residencial`, **real**, que compõe:

1. **arquitetura** — novo `arquitetura_residencial.py`: programa de ambientes
   com geometria conferida e **previsão de carga da NBR 5410:2004 9.5.2**
   (o vão que faltava entre "casa" e "instalação").
2. **eletrico** — delega à vertical existente e acrescenta a **conferência
   ponto declarado × mínimo normativo** por ambiente.
3. **hidraulica** — novo `hidraulica_residencial.py`: água fria, esgoto,
   ventilação e pluvial da casa, reusando as primitivas já aferidas de
   `hidraulica_predial.py` (NBR 5626:2020 / 8160 / 10844).

A fixture sintética **permanece** registrada e testada: ela é o caso de
contrato do núcleo (critério 7 e 8 do desenho de generalização). O adaptador
real é um segundo adaptador para o mesmo `project_type`.

## Base normativa transcrita (AR300)

Consultada no notebook elétrico `78cd2efd-0652-484e-b312-c5c5a7648962`,
fonte `d213019d-6e5c-4f18-8151-bf5a74c11b5d` (ABNT NBR 5410:2004), com
`cited_text` literal:

- **9.5.2.1.1** — "Em cada cômodo ou dependência deve ser previsto pelo menos
  um ponto de luz fixo no teto, comandado por interruptor."
- **9.5.2.1.2** — "a) em cômodos ou dependências com área igual ou inferior a
  6 m², deve ser prevista uma carga mínima de 100 VA; b) em cômodo ou
  dependências com área superior a 6 m², deve ser prevista uma carga mínima de
  100 VA para os primeiros 6 m², acrescida de 60 VA para cada aumento de 4 m²
  inteiros."
- **9.5.2.2.1 a)** — banheiros: "pelo menos um ponto de tomada, próximo ao
  lavatório, atendidas as restrições de 9.1".
- **9.5.2.2.1 b)** — cozinhas, copas, copas-cozinhas, áreas de serviço,
  cozinha-área de serviço, lavanderias e locais análogos: "no mínimo um ponto
  de tomada para cada 3,5 m, ou fração, de perímetro, sendo que acima da
  bancada da pia devem ser previstas no mínimo duas tomadas de corrente".
- **9.5.2.2.1 c)** — varandas: "pelo menos um ponto de tomada".
- **9.5.2.2.1 d)** — salas e dormitórios: "pelo menos um ponto de tomada para
  cada 5 m, ou fração, de perímetro".
- **9.5.2.2.1 e)** — demais cômodos: 1 ponto se área ≤ 2,25 m²; 1 ponto se
  2,25 m² < área ≤ 6 m²; 1 ponto para cada 5 m ou fração de perímetro se área
  > 6 m².
- **9.5.2.2.2 a)** — banheiros, cozinhas, copas, copas-cozinhas, áreas de
  serviço, lavanderias e locais análogos: "no mínimo 600 VA por ponto de
  tomada, até três pontos, e 100 VA por ponto para os excedentes,
  considerando-se cada um desses ambientes separadamente. Quando o total de
  tomadas no conjunto desses ambientes for superior a seis pontos, admite-se
  que o critério (…) seja de no mínimo 600 VA por ponto de tomada, até dois
  pontos".
- **9.5.2.2.2 b)** — demais cômodos: "no mínimo 100 VA por ponto de tomada".
- **9.5.3.1** — ponto de utilização com corrente nominal superior a 10 A deve
  constituir circuito independente.
- **9.5.3.2** — pontos de tomada de cozinhas, copas, copas-cozinhas, áreas de
  serviço, lavanderias e locais análogos "devem ser atendidos por circuitos
  exclusivamente destinados à alimentação de tomadas desses locais".

A alternativa de 600 VA "até dois pontos" é uma **permissão**, não o padrão:
o módulo calcula o critério dos três pontos e expõe o alternativo como campo
separado, nunca escolhendo em silêncio o menor.

## Técnicas de caça aplicadas

- **Rótulo × geometria** — todo ambiente declara tipo, área e perímetro. Um
  retângulo com área A tem perímetro mínimo `4·√A` (o quadrado). Perímetro
  declarado abaixo disso é geometricamente impossível → erro, nunca um número
  de tomadas calculado sobre uma planta que não existe.
- **Saturação silenciosa** — as tabelas de esgoto da NBR 8160 têm teto
  (Tab.5 ramal 160 UHC em DN100; Tab.7 coletor; Tab.8 ventilação satura em
  DN75 acima de 60 UHC). `hidraulica_predial` já expunha `_menor_dn_sat`, mas
  `diametro_ramal_esgoto`, `diametro_tubo_queda`, `diametro_coletor` e
  `diametro_ramal_ventilacao` **descartavam a flag**. O loop expõe a flag e o
  gate reprova.
- **Renderizar-e-olhar** — o adaptador emite planta de ambientes e quadro de
  previsão de carga; os desenhos são parseados como XML e inspecionados.

## Contrato do adaptador

```python
register_adapter(
    "casa-residencial",
    run_casa_residencial,
    project_types=("residencial",),
    disciplines=("arquitetura", "eletrico", "hidraulica"),
    deliverables=("report", "drawings", "ifc"),
    hooks={"drawings": ..., "ifc": ...},
)
```

Cada disciplina devolve estado honesto: `needs_review` quando calculou sem
aprovação humana, `blocked` quando falta entrada obrigatória,
`not_requested` quando o spec não a declarou. Nenhuma disciplina é marcada
`passed` por este adaptador — aprovação para obra continua sendo decisão de
responsável técnico.

## Fora do escopo

- aprovação legal, código de obras municipal e NBR 15575 (desempenho);
- estrutura da casa (fundação, laje, alvenaria) — segue bloqueada por fonte;
- água quente residencial, reservatório e recalque;
- substituir ou apagar a fixture sintética de contrato.
