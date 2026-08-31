# casa-residencial

Casa térrea de dois dormitórios executada pelo adaptador **`casa-residencial`**
(o adaptador residencial real). Diferente de
[`casa-residencial-sintetica`](../casa-residencial-sintetica/README.md), que é
uma **fixture de contrato** e não calcula nada, aqui as quatro disciplinas
declaradas são efetivamente dimensionadas.

## O que é calculado

| Disciplina | Motor | Base normativa |
|---|---|---|
| arquitetura | `arquitetura_residencial` | ABNT NBR 5410:2004 9.5.2 (previsão de carga) |
| elétrico | `residencial_eletrica` (Fases 6A/6B) | NBR 5410 + Enel BT + PRODIST Mód. 3 |
| hidráulica | `hidraulica_residencial` | NBR 5626:2020, NBR 8160:1999, NBR 10844:1989 |
| estrutura | `estrutura_casa` | NBR 6120:2019, NBR 6118:2023, NBR 8681:2025 |

O adaptador ainda acrescenta a **conferência NBR 5410 9.5.2**: cada ponto de
tomada e de luz declarado em `circuits.points` é comparado com o mínimo que a
norma exige para o ambiente correspondente do programa de arquitetura. Ponto
faltando reprova o elétrico; ponto que aponta para um ambiente inexistente no
programa também.

## A estrutura

A cadeia é a mesma do edifício multipavimento, **sem** a camada de estabilidade
horizontal:

```
carga de uso (NBR 6120 Tab.10) -> laje -> viga contínua -> pilar
                               -> viga baldrame -> fundação (sapata, pelo SPT)
```

Três coisas merecem leitura:

- **A viga é verificada, não só analisada.** `pavimento_tipo` devolve a
  envoltória de esforços de 14.6.6, mas nada ali confere se a seção resiste.
  Cada trecho passa por `viga_concreto`: flexão, cortante, flecha (Tab. 13.3) e
  fissuração. Seção que não cabe reprova com o trecho nomeado.
- **A alvenaria térrea não passa pelos pilares.** Ela nasce no baldrame e desce
  direto para a sapata. A reação do baldrame é somada ao `N_base` de cada pilar
  antes de a fundação ser dimensionada, e um *gate* de fechamento confere que a
  soma reproduz o peso lançado. Sem `estrutura.baldrame` declarado esse peso
  fica fora — e o aviso `viga_baldrame_nao_declarada` diz isso.
- **Mais de dois pavimentos é recusado.** Sem γz, desaprumo e ELS de
  deslocamento lateral, um prédio atravessaria a casa com todos os *gates*
  dizendo ATENDE. A entrada é rejeitada apontando a tipologia `edificio`.

A malha declarada (`3,5 + 3,5 + 3,4` × `4,0 + 4,0` m) cobre o mesmo envelope de
`geometry` e o mesmo pé-direito da arquitetura — o adaptador confere as duas
declarações e reprova se divergirem, inclusive geometricamente (cômodo cujo
retângulo sai da malha).

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
drawings/planta-formas.svg         malha de pilares, vigas e painéis de laje
bim/arquitetura-residencial.ifc    IfcSpace por ambiente (+ piso e paredes)
bim/estrutura-residencial.ifc      IfcColumn/IfcBeam/IfcSlab/IfcFooting
project-run.json                   manifesto com SHA-256 de cada artefato
```

Os dois IFC saem **separados** de propósito: alvenaria e pilar dividem o mesmo
plano legitimamente, e num arquivo único a varredura de interpenetração
acusaria dezenas de conflitos que são embutimento intencional. Cada modelo é
conferido contra o **seu** cálculo — contagem de peças por tipo e ausência de
interpenetração — antes de ser publicado.

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
- perfil de sondagem SPT — o spec traz um perfil **[A CONFIRMAR]**; a tensão
  admissível do solo é derivada dele (N/50), nunca arbitrada. Sem laudo real,
  esse é o dado a substituir antes de qualquer uso;
- ação horizontal na estrutura (vento, desaprumo, γz, ELS de deslocamento
  lateral) — não avaliada; a descida é apenas gravitacional;
- alvenaria **estrutural** (NBR 16868, ausente do acervo) e estrutura de
  telhado em madeira — fora do escopo;
- água quente, reservatório e recalque — não dimensionados;
- aprovação da concessionária e da prefeitura — não reivindicada.
