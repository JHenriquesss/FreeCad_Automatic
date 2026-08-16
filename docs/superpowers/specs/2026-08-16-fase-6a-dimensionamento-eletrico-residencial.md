# Fase 6A — Dimensionamento elétrico residencial auditável

**Status:** aprovado pelo usuário em 2026-08-16
**Base normativa consultada:** NotebookLM `78cd2efd-0652-484e-b312-c5c5a7648962`, fonte `d213019d-6e5c-4f18-8151-bf5a74c11b5d` (ABNT NBR 5410:2004), consulta validada em 2026-08-16.

## 1. Contexto e objetivo

O adaptador `casa-residencial-eletrica` já valida demanda, entrada BT da Enel e pontos de carga, mas ainda não dimensiona os circuitos. Esta fase adiciona o primeiro cálculo elétrico auditável do framework: corrente de projeto, seção do condutor, proteção contra sobrecarga, indicação de DR/DPS e rastreabilidade normativa. Ela não promete pranchas, modelos BIM, aprovação de concessionária ou liberação para obra.

O projeto residencial sintético continua sendo apenas fixture de integração. O núcleo não receberá regras específicas de galpão, São João da Barra ou de uma única casa.

## 2. Evidência normativa registrada

A consulta curta ao NotebookLM confirmou os seguintes pontos da NBR 5410:2004:

- capacidade de condução: subseção 6.2.5, tabelas 36 a 39 e fatores de correção das tabelas 42 a 45;
- seção mínima: subseção 6.2.6.1.1, tabela 47 e, quando aplicável, tabela 58 para condutor de proteção;
- queda de tensão: subseção 6.2.7, incluindo 6.2.7.2 e o limite de circuito terminal informado pela fonte;
- sobrecarga: subseção 5.3.4, especialmente 5.3.4.1, com `IB <= In <= Iz` e `I2 <= 1,45 Iz`;
- curto-circuito: subseção 5.3.5, 5.3.5.5.2, tabela 30 e subseções 6.3.4.3.1/6.3.4.3.2, com `I²t <= k²S²`.

Os números de tabelas e seções são rastreabilidade da fonte. O calculador reutilizará as tabelas já transcritas em `condutores_nbr5410.py` e `protecao_nbr5410.py`; não será criada uma segunda tabela normativa no adaptador.

## 3. Escopo desta fase

### Entregas

1. Contrato explícito `turnkey.eletrico.circuits.designs` para circuitos residenciais.
2. Calculador isolado em `dimensionamento_eletrico_residencial.py`.
3. Integração do calculador no adaptador residencial existente.
4. Fixture sintético atualizado, testes de unidade/contrato e uma asserção no golden journey.
5. Resultado JSON com cálculo, falhas, avisos, escopo implementado e rastreabilidade.

### Fora do escopo

- IFC, FCStd, DXF, SVG, PDF, diagrama unifilar ou prancha 2D;
- aprovação da Enel, ART, responsabilidade técnica ou prontidão para obra;
- cálculo de curto-circuito presumido a partir de um valor inventado;
- geração automática de circuitos a partir de cômodos, heurísticas ou cargas ausentes;
- alteração das tabelas genéricas sem um teste que demonstre a necessidade.

## 4. Contrato de entrada

`circuits.points` continua descrevendo as cargas declaradas. `circuits.designs` passa a declarar como cada grupo de pontos será projetado. Cada ponto deve pertencer a no máximo um design.

Exemplo mínimo válido:

```json
{
  "circuits": {
    "points": [
      {"id": "TUE-01", "room": "banheiro", "kind": "tue", "power_va": 6000, "voltage_v": 220}
    ],
    "routes": [],
    "designs": [
      {
        "id": "C-TUE-01",
        "point_ids": ["TUE-01"],
        "length_m": 18.0,
        "system": "monofasico",
        "conductors_loaded": 2,
        "insulation": "PVC",
        "reference_method": "B1",
        "ambient_temperature_C": 30.0,
        "grouping_count": 3,
        "power_factor": 1.0,
        "voltage_drop_limit_pct": 4.0,
        "use": "forca",
        "protection": {"location": "banheiro", "exposure": "quadro"}
      }
    ]
  }
}
```

Campos obrigatórios por design:

| Campo | Regra |
|---|---|
| `id` | string não vazia e única |
| `point_ids` | lista não vazia de IDs existentes; sem repetição entre designs |
| `length_m` | número finito maior que zero |
| `system` | `monofasico` ou `trifasico` |
| `conductors_loaded` | inteiro 2 ou 3 |
| `insulation` | `PVC`, `EPR` ou `XLPE` |
| `reference_method` | `B1` ou `F` |
| `ambient_temperature_C` | finito e dentro da faixa tabelada de 10 a 60 °C |
| `grouping_count` | inteiro em `1`, `2`, `3`, `4`, `6` ou `9` |
| `power_factor` | exatamente `0.8`, `0.95` ou `1.0`; para `1.0`, a queda usa a coluna `0.95` |
| `voltage_drop_limit_pct` | finito, maior que zero e no máximo 4% para circuito terminal |
| `use` | `iluminacao` ou `forca` |
| `protection.location` | `seco`, `molhado`, `banheiro`, `cozinha`, `externo` ou `area_externa` |
| `protection.exposure` | `direta`, `rede_aerea`, `indireta`, `quadro` ou `equipamento_sensivel` |

O bloco opcional `short_circuit` só é aceito completo:

```json
{"short_circuit": {"Icc_A": 5000.0, "t_s": 0.1, "Icu_A": 6000.0}}
```

Se o bloco não existir, o cálculo de interrupção/curto será explicitamente `not_evaluated`, com aviso e status geral `needs_review`. Se existir parcialmente ou tiver valor inválido, a disciplina será `blocked`; nenhum valor de curto será presumido.

## 5. Semântica do cálculo

Para cada design:

1. `S_total = sum(point.power_va)`.
2. Todos os pontos referenciados devem ter a mesma tensão.
3. Para `monofasico`, `IB = S_total / V`.
4. Para `trifasico`, `IB = S_total / (sqrt(3) * V)`; neste contrato `V` é a tensão linha-linha dos pontos referenciados.
   Como `power_va` já é potência aparente, `fp` não divide novamente a corrente; ele permanece disponível para a interpretação de potência ativa e para a coluna de queda de tensão suportada.
5. O calculador chama `dimensiona_condutor` com todos os dados explícitos, convertendo `length_m` para `L_km` e os nomes do contrato para a API genérica.
6. O calculador chama `dimensiona_protecao` com `IB`, `IZ`, uso, local e exposição.
7. Quando há disjuntor candidato, o condutor é recalculado com `I_protecao = In`; a proteção é conferida novamente contra o `IZ` final.
8. O design só é calculado como válido se a coordenação `IB <= In <= IZ` e as verificações de queda/seção retornarem verdadeiras.

Os dados de curto, quando completos, são enviados como `Icc`, `t_curto_s` e `Icu`. Sem eles, o resultado distingue claramente “não avaliado” de “aprovado”.

`short_circuit_evaluation` só é `implemented` quando todos os designs
publicados possuem dados completos e foram avaliados. Se houver designs
mistos, o escopo permanece `not_evaluated` e o resultado inclui o aviso
`short_circuit_not_evaluated`.

Nota de decisão da revisão coordenada: para o caso de 6000 VA/220 V com
PVC/B1 e agrupamento 3, a primeira passagem pode indicar 6 mm²; após
selecionar o disjuntor de 32 A e reaplicar a coordenação com `I_protecao`, a
saída pública coordenada é 10 mm². O resultado preserva
`base_conductor`/`base_protection` para auditoria e publica
`conductor`/`protection` da segunda passagem.

## 6. Interface do calculador

O módulo novo terá uma entrada pública:

```python
def calculate_residential_circuit_designs(
    circuits: dict,
    source_refs: list[dict],
) -> dict:
    """Valida e dimensiona designs explícitos sem efeitos externos."""
```

O retorno conterá `ok`, `errors`, `warnings`, `points`, `routes`, `designs` e `scope`. Cada design terá pelo menos:

```json
{
  "id": "C-TUE-01",
  "point_ids": ["TUE-01"],
  "load": {"power_va": 6000.0, "voltage_v": 220.0, "current_a": 27.2727},
  "base_conductor": {"secao_mm2": 6, "OK": true},
  "base_protection": {"disjuntor": {"IN": 32, "OK": true}, "OK": true},
  "conductor": {"secao_mm2": 10, "Iz": 41, "OK": true},
  "protection": {"disjuntor": {"IN": 32, "OK": true}, "OK": true},
  "short_circuit": {"status": "not_evaluated"},
  "traceability": {
    "source_ids": ["d213019d-6e5c-4f18-8151-bf5a74c11b5d"],
    "normative_references": ["5.3.4.1", "5.3.5", "6.2.5", "6.2.6.1.1", "6.2.7"]
  }
}
```

O campo `scope` do adaptador passará a declarar:

```json
{
  "conductor_sizing": "implemented",
  "protection_sizing": "implemented",
  "short_circuit_evaluation": "not_evaluated",
  "executive_deliverables": "not_implemented",
  "enel_approval": "not_claimed",
  "construction_readiness": "not_claimed"
}
```

## 7. Falhas e ausência de inferência

As validações devem bloquear sem exceção não controlada nos seguintes casos:

- `circuits.designs` ausente, vazio ou não-lista: `missing_circuit_designs`;
- campo obrigatório ausente/inválido: `missing_design_field` ou `invalid_design_field`;
- ID de design repetido: `duplicate_design_id`;
- ponto inexistente: `unknown_design_point`;
- ponto associado a mais de um design: `duplicate_design_point`;
- tensão inconsistente no mesmo design: `inconsistent_design_voltage`;
- short-circuit incompleto/inválido: `invalid_short_circuit`;
- nenhuma proteção comercial que satisfaça a coordenação: `no_protection_candidate`.

Não haverá `default` para comprimento, método de instalação, isolação, temperatura, agrupamento, fator de potência, limite de queda, uso, local, exposição, `Icc`, tempo ou `Icu`.

## 8. Integração no Loop

`residencial_eletrica.py` continua sendo o adaptador, não o lugar das tabelas. Ele deve:

1. validar fontes e demanda como hoje;
2. chamar o novo calculador com `payload["circuits"]` e as referências elétricas;
3. incorporar os erros/avisos e os designs no registro `disciplines.eletrico` e no `adapter-result.json`;
4. manter `needs_review` em entradas válidas sem curto ou sem entregáveis executivos;
5. manter `blocked` em entrada inválida ou cálculo que não possa ser coordenado.

O golden journey deve executar o fixture persistido e conferir que o manifesto continua íntegro, que os designs são persistidos como JSON e que o status não é falsamente promovido a `passed`.

## 9. Critério de encerramento

A fase estará encerrada quando os testes cobrirem contrato, happy path do
chuveiro 6000 VA/220 V com base 6 mm² / final coordenado 10 mm² e disjuntor
32 A, queda governante, coordenação, falta de curto, todos os bloqueios
listados e o percurso universal persistido. IFC e desenhos ficam
explicitamente como semente da Fase 6B.
