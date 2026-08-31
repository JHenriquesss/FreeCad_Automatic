# REVISAO — G14: a gestao do edificio (orcamento, cronograma, caderno, pacote)

Fecha o item que o proprio G7 deixou aberto e nomeou: o edificio nao tinha
`orcamento`, `cronograma`, `caderno_encargos` nem `pacote_legal`. O mecanismo
era o do G6 (`entregaveis_projeto` + hooks declarados no adaptador); o que
faltava era a **derivacao de quantitativos de um predio de concreto**, que nao
e' a de um galpao metalico.

Feito **depois** do G12 de proposito: com as instalacoes ja no resultado, o
orcamento sai com os 400 pontos eletricos e os 96 pontos hidraulicos do predio.
Antes do G12 ele sairia sem eletrica nem hidraulica — que e' exatamente o
defeito n.3 do G7 (orcamento parcial se apresentando como fechado) reproduzido
de novo, na tipologia seguinte.

---

## 1. O que passou a existir

| Arquivo | Papel |
|---|---|
| `gestao_edificio.py` (novo) | derivacao de quantitativos, WBS do predio, disciplinas do caderno/pacote, memorial, e os 4 hooks |
| `entregaveis_projeto.py` | os 4 emissores viraram **nucleos** reutilizaveis (`orcamento_no_manifesto`, `cronograma_no_manifesto`, `caderno_no_manifesto`, `pacote_no_manifesto`) + os wrappers do galpao |
| `orcamento.py` | `compor_orcamento(..., aplicaveis=...)` e a saida `nao_aplicaveis` |
| `pacote_legal.py` | `gerar_pacote(..., memorial=...)` — segunda porta para quem nao passa por `galpao_turnkey` |
| `edificio_adapter.py` | declara os 4 entregaveis e liga os 4 hooks |
| `tests/branches/g14/test_gestao_edificio.py` | 25 testes, criterio = o manifesto |

A rodada do spec persistido passou de 4 para 8 entregaveis e de 4 para 15
artefatos, todos com hash no manifesto.

---

## 2. A regra que organiza tudo: o buraco tem de ter nome

Um orcamento com uma linha **parece** um orcamento. Tres guardas separadas
impedem que o preco de venda do edificio passe por preco da obra.

### 2.1 Armadura por ELEMENTO, nao um `armadura` unico

As vigas do edificio sao **analisadas** (`pavimento_tipo` devolve a envoltoria
de esforcos) e **nunca verificadas** — o gap que o G13 nomeou e que o G3 segue
tendo. Logo **nao existe `As` dimensionada para viga nenhuma** deste predio.

Com um codigo `armadura` unico, laje + pilar somariam 11,4 t com cara de
armadura completa. A armadura de viga de um predio como este pesa da ordem de
5-6 t: o numero exibido estaria 30-40% abaixo do real, e nada no manifesto
diria isso. E' o mesmo desencontro rotulo x geometria da varredura do takeoff.

Por isso os codigos sao `armadura_laje`, `armadura_pilar`, `armadura_fundacao`
e `armadura_viga` — e o ultimo sai **vazio**, com motivo:

> as vigas do edificio sao ANALISADAS (envoltoria de esforcos) e nao
> VERIFICADAS: nao ha As dimensionada para derivar peso. Declarar em
> `gestao.orcamento.quantitativos.armadura_viga` antes de usar o preco de venda

**Nao ha estimativa por taxa.** Multiplicar 53 m3 de viga por "110 kg/m3" seria
inventar engenharia na camada de entrega, que e' a linha que este framework nao
cruza.

### 2.2 `nao_aplicaveis` x `sem_quantidade`

`compor_orcamento` declarava PARCIAL contra a tabela **inteira**. Num predio de
concreto isso listaria `aco_estrutural`, `telha_cobertura` e `piso_industrial`
como faltantes — insumos que a obra **nao tem**. Ruido que esconde a falta que
importa (a armadura de viga).

`aplicaveis` e' o escopo da tipologia, e ele e' **dinamico**: com fundacao rasa
o `estaca` sai do escopo; com estacas saem `fundacao_concreto` e
`armadura_fundacao`. O que fica fora volta publicado em `nao_aplicaveis` — a
distincao aparece no manifesto, nao some.

O galpao nao mudou de comportamento: sem `aplicaveis`, o escopo continua sendo
a tabela inteira.

### 2.3 O que a tabela de precos nao tem

Revestimento, esquadria, louca, impermeabilizacao, elevador, canteiro e a
**instalacao de combate a incendio** nao existem na tabela de referencia. Nao
ha como orca-los, entao sao NOMEADOS em `a_confirmar`. Sem essa lista, o
`preco_venda` de R$ 799 mil passaria por preco de um predio de 1.134 m2 — que
ele nao e', nem perto.

---

## 3. Duas ausencias que a derivacao ENCONTROU

Nenhuma e' bug de modulo; as duas sao do spec, e sem o orcamento nenhuma delas
tinha onde aparecer.

**O predio nao tem fachada.** Nao ha `estrutura.parede_sobre_vigas` no spec:
`g_parede_kN_m` e' 0,0 e a estrutura inteira — laje, viga, pilar, fundacao —
foi calculada **sem o peso da alvenaria de vedacao**. A derivacao se recusa a
tirar area de vedacao do perimetro: seria orcar uma parede que nao pesou em
viga nenhuma (o mesmo erro, com o sinal trocado, da alvenaria terrea que sumia
entre pavimento e fundacao no G13). O codigo fica sem quantitativo e o motivo
viaja no manifesto. Declarada a parede, a area sai — coberto por teste nos dois
sentidos.

**Os pontos das areas comuns nao existem.** `areas_comuns_VA: 24000` e' uma
carga declarada em bloco (elevador, bombas, iluminacao comum), sem
discriminacao de pontos. Os 400 pontos contados sao os das 16 unidades; os das
areas comuns ficam nomeados em `nao_derivados`.

---

## 4. Convencao de medicao (a que evita contar o no duas vezes)

| Elemento | Como e' medido | Por que |
|---|---|---|
| laje | area do pavimento x espessura **adotada** x n_pav | e' a espessura que realimentou a carga, nao a declarada no spec |
| viga | `b x (h - h_laje)` x comprimento **eixo a eixo** x n_pav | a faixa dentro da laje ja foi medida na laje |
| pilar | `b x h x (pe_direito - h_viga)` por lance | o no viga-pilar pertence a viga, que foi medida eixo a eixo |
| escada | largura x comprimento **inclinado** x h, por lance | medir na projecao subestima o lance em ~13% |
| fundacao | prisma `B x L x h` da geometria aprovada | pedestal, lastro e escavacao ficam declarados de fora |

O somatorio fecha a estrutura sem sobreposicao, e ha um teste que refaz a conta
por fora: se um dia um dos lados mudar de convencao sozinho, o volume cresce
sem que gate nenhum reclame — o orcamento e' o unico lugar onde esse erro
aparece, e aparece em dinheiro.

**Aferimento por ordem de grandeza** (o predio do spec, 1.134 m2 de laje):

| Indicador | Valor | Faixa usual |
|---|---|---|
| concreto | 0,194 m3/m2 | 0,16 - 0,20 |
| forma | 1,93 m2/m2 | 1,8 - 2,2 |
| armadura de laje | 8,8 kg/m2 (74 kg/m3) | 60 - 80 kg/m3 |
| armadura de pilar | 86 kg/m3 | 80 - 130 kg/m3 |

A taxa global de aco sai **51,6 kg/m3**, abaixo dos 80-100 usuais — e a medida
exata do buraco declarado em 2.1. O numero baixo nao esta escondido: ele e' a
consequencia visivel de a armadura de viga estar publicada como ausente.

---

## 5. O cronograma e' do PREDIO

A rede do galpao tem duracao fixa. Num edificio a estrutura sao
`n_pavimentos` ciclos de forma/armadura/concretagem
(`CICLO_ESTRUTURA_DIAS_POR_PAVIMENTO = 12`, produtividade de obra, A
CONFIRMAR): 9 pavimentos = 108 dias, e a rede inteira 258 dias.

As frentes seguem em **serie** (vedacao depois da estrutura inteira, nao
defasada de dois pavimentos), porque a rede e' CPM pura e nao sobrepoe
atividades parcialmente. Isso torna o prazo **conservador**, e esta dito no
`a_confirmar` em vez de ser apresentado como planejamento de obra.

A curva S e custeada pela planilha que o orcamento acabou de gravar (a ordem
dos entregaveis e' a ordem de execucao) e satura em 100% no dia 208 de 258 —
tres das sete atividades tem custo. O aviso ja existia no modulo e continua
saindo.

---

## 6. Um achado do pacote legal: indice x pasta

O indice de pranchas do pacote lista **13 folhas** (PE-CO, PE-EL, PE-HI, PE-IN,
PE-CD) e a rodada desenha **2** SVG. Um pacote que lista treze pranchas ao lado
de uma pasta com duas passaria por completo — o orcamento parcial na forma de
prancha.

`pacote_no_manifesto` passou a confrontar os dois e publicar
`pranchas_emitidas_na_rodada`, com aviso quando o indice e' maior. Vale para as
duas tipologias, porque o nucleo e' compartilhado. O indice continua sendo o
**escopo do executivo**, que e' o que um pacote legal tem de listar; o que
mudou e' que ele nao se confunde mais com o conteudo da pasta.

---

## 7. Uma armadilha de import

`gestao_edificio` importava `entregaveis_projeto` no topo. `entregaveis_projeto`
importa `project_loop`, que **registra os adaptadores ao ser carregado** — e um
deles e' o edificio, que importa `gestao_edificio`. Importar
`edificio_adapter` primeiro (que e' o que os testes do G12 fazem) quebrava o
registro do **galpao** no meio, com
`partially initialized module 'entregaveis_projeto'`.

O import ficou preguicoso dentro dos hooks. A suite pegou isso na primeira
execucao; e' o tipo de acoplamento que so aparece quando a ordem de import muda.

---

## 8. O que este G14 NAO fez

- **nao verificou as vigas do edificio.** Seria fechar o gap do G3 (a funcao
  generica ja existe em `estrutura_casa.verifica_vigas`), mas e' trabalho de
  estrutura, nao de gestao, e mexeria nos gates e no ATENDE do predio. Fica
  nomeado aqui e no manifesto — e enquanto nao for feito, `armadura_viga`
  continua sem quantitativo;
- **nao inventou insumo fora da tabela.** Revestimento, esquadria e elevador
  continuam sem preco de referencia;
- **nao mexeu no spec do projeto.** A fachada ausente e' declaracao do
  projetista; o modulo apenas parou de fingir que ela existia.
