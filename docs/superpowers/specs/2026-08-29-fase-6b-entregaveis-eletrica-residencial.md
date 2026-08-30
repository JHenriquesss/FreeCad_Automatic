# Fase 6B — Entregáveis da elétrica residencial (desenho + BIM)

**Estado anterior:** `residencial_eletrica.py` + `dimensionamento_eletrico_residencial.py`
calculavam circuitos, condutores, proteção, queda de tensão e coordenação. O
adaptador declarava `deliverables=("report",)`: só relatório, sem desenho e sem BIM.

**Entregue:** a partir do MESMO JSON já validado, o adaptador emite unifilar,
quadro de cargas, planta 2D e IFC4. Geração gráfica e cálculo continuam
separados — nenhum módulo novo calcula seção, proteção ou demanda.

## Decisão de reuso

`desenho_eletrico.py` tinha `diagrama_unifilar_svg(r)` / `quadro_cargas_svg(r)`,
mas moldados para o shape industrial (`r["gates"]`, `subestacao`,
`cargas.por_grupo`, `instalacao`). O shape residencial é outro
(`circuits.designs`, `service_entry`, `calculation.demand`).

Adaptar o resultado residencial ao shape industrial exigiria fabricar campos que
o projeto residencial não tem (subestação, grupos de carga). Generalizar as
funções compostas as encheria de ramos por tipologia.

**Escolha: generalizar as PRIMITIVAS, não as composições.** Nasceu
`desenho_svg_base.py` com escape XML, texto, linha e a simbologia ABNT
(NBR 5444/IEC); `desenho_eletrico.py` passou a importá-las com aliases privados
para preservar seus nomes históricos, e `desenho_eletrico_residencial.py` monta
suas próprias pranchas sobre as mesmas primitivas.

O ponto decisivo: existe **uma** implementação de `esc()`. Duplicá-la seria
recriar a superfície do bug S41 (o `<` cru de `R <= 10 ohm` invalidando o SVG
inteiro) num dos dois lados.

## Mapa de arquivos

| Arquivo | Papel |
| --- | --- |
| `desenho_svg_base.py` | primitivas SVG compartilhadas (novo) |
| `desenho_eletrico.py` | passa a importar as primitivas (modificado) |
| `layout_eletrico_residencial.py` | contrato de `circuits.layout` (novo) |
| `desenho_eletrico_residencial.py` | unifilar, quadro de cargas, planta (novo) |
| `bim_eletrico_residencial.py` | membros neutros + IFC + checagem de comprimento (novo) |
| `residencial_eletrica.py` | valida layout, registra hooks `drawings`/`ifc` (modificado) |
| `dimensionamento_eletrico_residencial.py` | ecoa `declared_length_m` (modificado) |
| `projects/casa-residencial-eletrica-sintetica/project-spec.json` | ganha `layout` (modificado) |

## Contrato novo: `circuits.layout` (opcional, sem default)

O dimensionamento não conhece coordenadas — calcula sobre comprimentos
declarados. Planta e IFC precisam de posição. `circuits.layout` traz
`units` (`"m"`), `board`, `rooms` e `points`, um ponto por ponto de circuito.

- **Ausente** → `executive_deliverables: schematic_only`. Saem unifilar e quadro
  de cargas; a planta é omitida com motivo `layout_not_declared` e o IFC fica
  `not_available`. Nenhuma posição é inventada.
- **Presente e incoerente** → disciplina `blocked`. Códigos:
  `missing_layout_point`, `unknown_layout_point`, `point_outside_declared_room`,
  `duplicate_layout_room`, `overlapping_layout_rooms`,
  `board_outside_declared_rooms`, `missing_layout_field`, `invalid_layout_value`.

`point_outside_declared_room` é rótulo × geometria no próprio contrato: o ponto
diz em que cômodo está e a posição precisa cair dentro daquele retângulo.

## As três técnicas de caça

**Renderizar-e-olhar** — os três SVG foram convertidos em PNG e abertos. A barra
verde não pegou nada disso:

1. o nome do cômodo, centrado, colidia com o quadro e com os pontos (a etiqueta
   "Área de serviço" saía cortada por cima do QD-01) → rótulo foi para o canto
   superior esquerdo;
2. o ramo do DPS caía em cima do barramento do QD;
3. faltavam os trechos de linha entre o disjuntor e o DR, e entre o disjuntor
   geral e o barramento;
4. a tracejada ponto→quadro parecia traçado de eletroduto → a legenda agora diz,
   em vermelho, que a ligação é esquemática.

**Rótulo × geometria** — duas checagens viraram código de produção, não só teste:
o diâmetro do cilindro IFC do condutor tem a área da seção dimensionada; e
`verificar_comprimentos` compara o comprimento declarado do circuito (o que
alimenta a queda de tensão) com a distância reta quadro→ponto do layout. Se o
declarado for menor que esse mínimo físico, o manifesto recebe
`declared_length_shorter_than_layout_distance`.

**Saturação silenciosa** — o contrato residencial já limita
`ambient_temperature_C` a 10–60 °C (faixa exata da Tab.40) e `grouping_count` aos
valores tabelados da Tab.42, então não há saturação a montante; a suíte fixa isso
com testes que provam recusa, não saturação. Mas a caça achou o **irmão do
padrão**: um circuito que falha o dimensionamento não entra em `designs` e
**sumia do desenho em silêncio** — a prancha parecia completa faltando circuito,
igual ao quadro de materiais que desapareceu sem aviso. Unifilar e quadro de
cargas agora abrem faixa vermelha listando os circuitos rejeitados e o código do
motivo, e o STATUS por linha escreve `REPROVA` quando `OK` é falso.

## Teste

`framework/galpao_fw/tests/branches/phase6b/test_residential_electrical_deliverables.py`
(34 testes). Regra da suíte: **SVG é XML**. Todo desenho é parseado com
`ElementTree` e as asserções olham nós e atributos — nunca substring, que foi
exatamente o que deixou o unifilar malformado passar em S41. O trunk
(`test_project_loop_golden_journey.py`) executa a fixture com `generate_2d` e
`generate_ifc`, confere `sha256` e tamanho de cada artefato no manifesto e
re-parseia os SVG lidos do disco.

## Fora de escopo

FCStd, DXF, PDF, prancha formatada em folha A1, e qualquer alegação de aprovação
Enel, ART ou liberação para obra.
