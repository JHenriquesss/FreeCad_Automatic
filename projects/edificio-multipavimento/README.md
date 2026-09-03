# Edifício multipavimento — caso de integração da tipologia `edificio`

Edifício residencial de 8 pavimentos-tipo + cobertura, malha 3 × 2 vãos
(14,0 m × 9,0 m), pé-direito 2,90 m, concreto C30 e aço CA-50.

**Isto não é um projeto liberado para obra.** É o caso que exercita a cadeia
de cálculo do G3 pelo Project Loop de ponta a ponta. Falta o que está
declarado como `not_available` no escopo da disciplina — veja abaixo.

## Como rodar

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/edificio-multipavimento/project-spec.json `
  --out-dir exports/edificio --no-ifc
```

## O que sai

- `project-run.json` — manifesto com o estado de **cada disciplina declarada**
  (`estrutura`, `incendio`, `hidraulica`, `eletrico`), os gates de cada uma e o
  `scope` que cada uma publica por si. O registro da redução da NBR 6120 §6.12
  sai como aviso da estrutura, porque a norma exige que ele seja registrado;
- `drawings/planta-formas-pavimento-tipo.svg` — planta de formas do
  pavimento-tipo com os 12 pilares e a descida de cargas;
- `drawings/planta-laje-pavimento-tipo.svg` — formas, armadura e quadro de
  ferros da laje;
- `bim/edificio-estrutura.ifc` e `model/` — com `--ifc` / `--3d` (G8).
- `orcamento/` — planilha 5D, curva ABC e relatório (G14);
- `cronograma/` — rede CPM, curva S (JSON + SVG) e relatório (G14);
- `documentos/caderno-encargos.md` e `documentos/pacote-legal.md` — especificações
  técnicas das disciplinas executadas e índice de pranchas/ART/PPCI/LOD/O&M com o
  memorial consolidado do prédio (G14).

Os entregáveis das instalações são o **relatório**: as três disciplinas novas
entram como cálculo e gates, não como prancha. Capacidade não declarada é
capacidade que não existe.

## O contrato de entrada

`turnkey.estrutura` é obrigatório e não tem default de engenharia. Sem ele o
Loop devolve `blocked` com `missing_structure_input` — o adaptador não arbitra
um edifício.

`turnkey.geometria` (o envelope comum que o Loop usa para coordenar) e
`turnkey.estrutura.geometria` (os vãos que a estrutura calcula) são duas
declarações do mesmo prédio. O adaptador confere as duas: `comprimento` contra
a soma de `vaos_x`, `vao` contra a soma de `vaos_y` e os dois pés-direitos,
com tolerância de 10 mm. Divergir devolve `geometry_mismatch`, não um projeto
em que o Loop coordena um envelope e a estrutura calcula outro.

## O que este caso NÃO cobre

Todos declarados como `not_available` no `scope` da disciplina, para que o
manifesto os publique em vez de omiti-los (itens abertos da seção 10 de
`framework/galpao_fw/REVISAO-G3-MULTIPAVIMENTO.md`):

| Item | Situação |
| --- | --- |
| `alvenaria_estrutural` | bloqueada por fonte — NBR 16868 ausente do acervo |
| `caso_externo_fundacao_SPT` | **bloqueado por fonte — G28**: sem laudo SPT anexo em pacote obra FNDE (ver `REVISAO-G28-FUNDACAO-FONTE-BLOQUEADA.md`, `fontes_externas/BLOQUEIO-G28-FUNDACAO-SPT.md`, `wiki/06-open-threads.md#T44`) — só `Sondagem, 3 furos × 10 m` como item de serviço (Petrópolis) |
| `momento_base_pilar` | o pórtico global dá γz e ELS, não esforço por barra |
| `viga_baldrame`, `recalque_diferencial` | fronteiras do que o G9 entrega |
| `desempenho_15575_*` (3 itens) | verificados por **ensaio**, não por conta |

`fundacao` (G9), `vibracao_piso` e `desempenho_15575` (G11) **deixaram** essa
lista. E, com o G12, `incendio`, `hidraulica` e `eletrico` também.

## A gestão do prédio (G14)

O prédio passou a ter orçamento, cronograma, caderno de encargos e pacote legal.
O mecanismo já era o do G6; o que o G14 escreveu foi a **derivação de
quantitativos de um edifício de concreto**, em `framework/galpao_fw/gestao_edificio.py`.

O orçamento desta rodada **é parcial e diz que é** — o defeito nº 3 do G7 (um
orçamento parcial se apresentando como fechado) é exatamente o que as três
guardas abaixo existem para impedir:

| Guarda | O que ela impede |
| --- | --- |
| armadura por **elemento** (`armadura_laje`, `armadura_pilar`, `armadura_fundacao`, `armadura_viga`) | as vigas do edifício são analisadas e nunca verificadas: não há `As` para elas. Num código `armadura` único, o peso sairia 30-40% abaixo com cara de completo |
| `aplicaveis` (escopo da tipologia) | um prédio de concreto não tem aço estrutural, telha nem piso industrial; declará-los "sem quantitativo" seria ruído escondendo a falta que importa. Eles saem em `nao_aplicaveis` |
| insumos **fora da tabela** de preços | revestimento, esquadria, elevador, louça, impermeabilização e o combate a incêndio não têm preço de referência: são nomeados em `a_confirmar`, e o preço de venda não passa por preço da obra |

Duas ausências que a derivação **encontrou** neste spec, e que são do spec, não
do módulo:

- não há `estrutura.parede_sobre_vigas`: o prédio foi calculado **sem alvenaria
  de fachada**, então não há área de vedação a orçar (derivar do perímetro seria
  orçar uma parede que não pesou em viga nenhuma);
- a carga das áreas comuns é declarada em VA, sem discriminação de pontos: os
  pontos elétricos das áreas comuns não estão na contagem.

Convenção de medição do concreto, declarada porque sem ela o encontro
viga-pilar é contado duas vezes ou nenhuma: **laje** cheia (área × espessura
adotada), **viga** com a alma (`h - h_laje`) medida eixo a eixo, **pilar** entre
as vigas (`pé-direito - h_viga`). O nó pertence à viga.

O cronograma é a rede do **prédio**, não a do galpão: a estrutura leva
`n_pavimentos` ciclos de forma/armadura/concretagem, e as frentes seguintes
entram em série (a rede CPM não sobrepõe vedação a pavimentos já concretados),
o que torna o prazo conservador — dito no `a_confirmar`.

O índice de pranchas do pacote legal é o escopo do **executivo**, não o conteúdo
da pasta: o manifesto publica `pranchas_emitidas_na_rodada` e avisa quando o
índice lista mais folhas do que a rodada desenhou.

## As três disciplinas de instalações (G12)

O adaptador declarava `DISCIPLINES = ("estrutura",)`: o prédio saía calculado,
desenhado e modelado — e legalmente inocupável. Cada disciplina entra por uma
fronteira própria e **só quando o spec a declara**; ausente do spec, ela é
`not_requested`, nunca um projeto inventado a partir do envelope.

| Disciplina | Fronteira | Normas |
| --- | --- | --- |
| `incendio` | `incendio_edificio` | NBR 9077:2025 + 9050 + 10898/16820/17240/13714 |
| `hidraulica` | `hidraulica_edificio` | NBR 5626:2020 + 8160 + 10844 |
| `eletrico` | `eletrica_edificio` | NBR 5410:2004 |

### A escada é uma só

É o ponto em que o projeto podia se partir em dois. A estrutura dimensiona uma
escada de concreto (`escada_concreto`, via `estrutura.escada`) e a NBR 9077
exige uma largura mínima pelo fluxo de pessoas (Tabela 10) e pela NBR 9050
6.8.3 (1,20 m em rota acessível). Se o vertical de incêndio dimensionasse a
**sua** escada, o prédio teria duas — o mesmo defeito que o G8 achou na
ancoragem viga-pilar, em que cada emissor tinha a sua.

`estrutura.escada.largura` é a **declaração única**. Era um campo morto —
documentado na entrada de `escada_concreto` e lido por ninguém, nem no
resultado aparecia. Agora ele atravessa o resultado e é o valor que o gate
`escada_largura` confere. Escada estreita **reprova**; não é alargada por conta
própria. Escada não declarada vira erro nomeado; não vira largura arbitrada.
Testado em `tests/branches/g12/test_incendio_edificio.py`.

### O que cada fronteira NÃO faz

- **incêndio**: as distâncias a percorrer e as larguras de corredor são
  *medidas* na planta de arquitetura, que o framework não tem para o edifício —
  aqui são declaradas e **verificadas**. Ventilação/pressurização da escada à
  prova de fumaça (NBR 14880), compartimentação e TRRF, área de refúgio e o
  plano de gestão do Anexo A ficam `not_available`;
- **hidráulica**: água quente, reservatório inferior + recalque, zonas de
  pressão e válvulas redutoras. O gate de 400 kPa (6.9.5) diz *quando* elas
  passam a ser necessárias; não as dimensiona. A reserva de incêndio **não** é
  somada ao volume potável — 6.5.6.2 só a soma quando armazenada junto;
- **elétrica**: os circuitos terminais dentro da unidade, o curto-circuito
  calculado (a `Icc` presumida é dado da concessionária), a subestação própria
  e o SPDA.

### Dados declarados, e por quê

| Dado | Por que não tem default |
| --- | --- |
| `incendio.velocidade_incendio` (Tab.2) | depende da carga de incêndio e dos materiais |
| `incendio.pavimentos[].atividade` (Tab.4) | classificação de responsável técnico |
| `hidraulica.consumo_per_capita_L_dia` | a NBR 5626:2020 **6.5.4 não tabela consumo** |
| `hidraulica.reservacao.superior_L` | volume é projeto de arquitetura/estrutura; aqui é *verificado* |
| `eletrico.fator_demanda_entre_unidades` | dado da concessionária (Enel CNC-NDBR-DBR-25-1580) |
| `eletrico.areas_comuns_VA` | elevador, bomba e iluminação comum não são presumidos |

Sem o fator de demanda, a elétrica **soma todas as unidades sem diversidade
nenhuma** — o teto da demanda — e publica
`fator_de_demanda_entre_unidades: not_available` com aviso. Caro é o lado certo
de errar, mas o projeto precisa saber que a redução existe e não foi aplicada.

### Achado: este prédio não é atendível em baixa tensão

Somadas as unidades sem diversidade, a carga instalada passa de **200 kW**,
contra o limite de 75 kW da conexão coletiva BT. O gate
`limite_de_baixa_tensao` **reprova** e nomeia a subestação própria em vez de
esconder o problema numa bitola maior. É resultado correto, não defeito do
caso: um prédio de nove pavimentos com essas cargas é atendido em média tensão.

### Duas populações seriam o mesmo defeito

O prédio tem **uma** população. A hidráulica lê a mesma que a NBR 9077 calculou
sobre `incendio.pavimentos` (Tabela 4: *duas pessoas por dormitório*). Declarar
`hidraulica.populacao` divergente é **erro de entrada**, não uma escolha
silenciosa entre as duas.

## Ação horizontal

`turnkey.estrutura.vento` é opcional, mas sem ele o escopo recua: `vento`,
`desaprumo`, `estabilidade_global` e `deslocamento_lateral_els` voltam a
`not_available`, e o resultado emite `acao_horizontal_nao_avaliada` dizendo que
a descida ficou apenas gravitacional. Declarado, saem calculados:

- **vento por pavimento** (NBR 6123 4.2.3, `Fa = Ca q Ae`), com `q` recalculado
  em cada cota pelo `S2`, e a faixa tributária do topo valendo meio pé-direito;
- **desaprumo** (NBR 6118 11.3.3.4.1), `θ1 = 1/(100√H)` limitado a
  `[1/300, 1/200]`, `θa = θ1·√((1+1/n)/2)`, e a regra a/b/c dos 30 % comparada
  pelos momentos na base — com `θa` **sem** `θ1mín`, como a norma manda;
- **γz** (15.5.3) por análise de pórtico plano de 1ª ordem com a rigidez de
  15.7.3 (0,8 EcIc pilares, 0,4 EcIc vigas, `Ec = 1,10 Ecs` por 15.5.1);
- **deslocamento lateral em serviço** (Tabela 13.3): `H/1700` no topo e
  `Hi/850` entre pavimentos, combinação frequente `ψ1 = 0,30`, com `Ecs` e
  seção **bruta** por 14.6.4.1 — a rigidez reduzida de 15.7.3 é exclusiva do
  ELU e usá-la aqui dobraria o deslocamento sem amparo normativo.

### `ca` é entrada, não resultado

O coeficiente de arrasto da NBR 6123 para edificação paralelepipédica está na
norma **apenas como ábaco** (Figuras 4 e 5 — confirmado no acervo; não existe
tabela de números). Digitalizar curva de imagem foi o que produziu as seis
células erradas nas tabelas de Bares, e é o mesmo motivo pelo qual o shed
multi-vão segue bloqueado. Então o projetista lê `Ca` da Figura 4 com `h/l1` e
`l1/l2` e o declara; o spec marca a proveniência como `A CONFIRMAR`. Sem `Ca`
declarado o módulo levanta `ValueError` — não arbitra.

### Hipótese de distribuição

O vento total de uma direção é dividido **igualmente** entre os pórticos planos
paralelos a ela. Vale para diafragma rígido e pórticos iguais, que é o caso da
malha ortogonal regular. Malha irregular ou núcleo rígido exige distribuição
por rigidez, e isso não é feito aqui.

O pórtico global usa **a menor** das seções adotadas no lance da base — escolha
conservadora, já que o modelo de pórtico plano tem uma seção única e menor
rigidez significa maior γz e maior deslocamento.

Nenhuma disciplina termina `passed`: aprovação para obra exige responsável
técnico e ART.

## Fontes

Referenciadas em `source_refs.estrutura`, todas verificadas no acervo:

- ABNT NBR 6118:2023 + Emenda 1:2026 — projeto de estruturas de concreto;
- ABNT NBR 6120:2019 — ações para o cálculo de estruturas de edificações;
- ABNT NBR 8681:2025 — ações e segurança nas estruturas.

## Nota sobre a seção dos pilares

O orquestrador adota a menor seção que atende, como o resto do framework. Numa
malha residencial de 9 pavimentos isso leva os pilares de canto e de
extremidade ao limite prático — seções finas e muito armadas. Para um projeto
mais folgado, passe uma lista `SECOES_PILAR` começando mais alta; a política em
si não foi alterada aqui.
