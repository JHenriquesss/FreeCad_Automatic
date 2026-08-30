# casa-residencial

Casa térrea de dois dormitórios executada pelo adaptador **`casa-residencial`**
(o adaptador residencial real). Diferente de
[`casa-residencial-sintetica`](../casa-residencial-sintetica/README.md), que é
uma **fixture de contrato** e não calcula nada, aqui as três disciplinas
declaradas são efetivamente dimensionadas.

## O que é calculado

| Disciplina | Motor | Base normativa |
|---|---|---|
| arquitetura | `arquitetura_residencial` | ABNT NBR 5410:2004 9.5.2 (previsão de carga) |
| elétrico | `residencial_eletrica` (Fases 6A/6B) | NBR 5410 + Enel BT + PRODIST Mód. 3 |
| hidráulica | `hidraulica_residencial` | NBR 5626:2020, NBR 8160:1999, NBR 10844:1989 |

O adaptador ainda acrescenta a **conferência NBR 5410 9.5.2**: cada ponto de
tomada e de luz declarado em `circuits.points` é comparado com o mínimo que a
norma exige para o ambiente correspondente do programa de arquitetura. Ponto
faltando reprova o elétrico; ponto que aponta para um ambiente inexistente no
programa também.

## O programa de ambientes

| Ambiente | Tipo | Área (m²) | Perímetro (m) | Iluminação (VA) | TUG | TUG (VA) | Critério |
|---|---|---:|---:|---:|---:|---:|---|
| Sala | sala | 20,00 | 18,00 | 280 | 4 | 400 | 9.5.2.2.1-d |
| Cozinha | cozinha | 9,00 | 12,20 | 100 | 4 | 1900 | 9.5.2.2.1-b |
| Banheiro | banheiro | 3,60 | 7,80 | 100 | 1 | 600 | 9.5.2.2.1-a |
| Área de serviço | area_servico | 6,00 | 10,00 | 100 | 3 | 1800 | 9.5.2.2.1-b |
| Circulação | circulacao | 4,00 | 10,00 | 100 | 1 | 100 | 9.5.2.2.1-e-2 |
| Dormitório 01 | dormitorio | 10,50 | 13,00 | 160 | 3 | 300 | 9.5.2.2.1-d |
| Dormitório 02 | dormitorio | 9,00 | 12,00 | 100 | 3 | 300 | 9.5.2.2.1-d |
| **Total** | | **62,10** | | **940** | **19** | **5400** | |

O conjunto de ambientes molhados tem 8 pontos (> 6), então a norma **admite** o
critério de 600 VA até dois pontos (4400 VA no total). O projeto **não adota**
essa permissão: o valor calculado continua sendo o dos três pontos. A
alternativa aparece na prancha e no JSON como campo separado.

## O que sai da execução

```
reports/preflight.json
reports/disciplinas.json
reports/adapter-result.json
drawings/quadro-ambientes.svg      previsão de carga por ambiente
drawings/conferencia-nbr5410.svg   mínimo normativo × declarado
drawings/esquema-hidraulico.svg    DN das três redes
project-run.json                   manifesto com SHA-256 de cada artefato
```

`drawings/planta-baixa.svg` **não** é emitida e o motivo fica registrado em
`deliverables.drawings.skipped`: o programa declara área e perímetro, não
posições. Desenhar cômodos em coordenadas inventadas seria uma prancha que não
corresponde ao dado.

## Como rodar

```bash
cd framework/galpao_fw
python -c "
import json, sys; sys.path.insert(0, '.')
from builtin_adapters import register_builtin_adapters
from project_loop import run_project
register_builtin_adapters()
spec = json.load(open('../../projects/casa-residencial/project-spec.json', encoding='utf-8'))
m = run_project(spec, 'out/casa-residencial', {'generate_2d': True})
print(m['status'])
"
```

## Estado honesto

Todas as disciplinas terminam em **`needs_review`**, nunca `passed`. O
adaptador não marca aprovação: emitir para obra exige responsável técnico,
ART/RRT e aprovação legal, nada disso avaliado aqui.

Dados que continuam **[A CONFIRMAR]** e o que **não** está no escopo:

- intensidade pluviométrica local (NBR 10844 Tab.5) — no spec está 150 mm/h
  declarado; trocar pelo valor da cidade antes de usar;
- pressão disponível na entrada (`agua.p_alim_kPa` = 120 kPa) é dado de sítio;
- código de obras municipal, NBR 15575 (desempenho) e NBR 9050
  (acessibilidade) — não avaliados;
- estrutura da casa (fundação, laje, alvenaria) — o adaptador declara
  `estrutura: not_available`;
- água quente, reservatório e recalque — não dimensionados;
- aprovação da concessionária e da prefeitura — não reivindicada.
