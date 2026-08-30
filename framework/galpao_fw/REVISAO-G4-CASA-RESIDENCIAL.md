# G4 - ADAPTADOR DE CASA RESIDENCIAL REAL: o que entrou, como foi aferido, o que ficou

Fecha o gap deixado explicito no proprio desenho de generalizacao
(`docs/superpowers/specs/2026-08-15-generalizacao-framework-design.md`):
`casa_residencial_sintetica.py` declarava `("arquitetura", "eletrico",
"hidraulica")` e **nao calculava nenhuma delas** - devolvia `needs_review` com o
gate `synthetic_fixture: True`. Era, deliberadamente, uma fixture de contrato:
"nao sera apresentado como projeto residencial apto para obra".

A vertical eletrica residencial (Fases 6A/6B) ja era real, mas cobria **uma**
disciplina e dependia de o usuario declarar ponto a ponto - sem nunca saber
dizer se o que ele declarou atende ao **minimo normativo** daquela planta.

---

## 1. Modulos

| Arquivo | Conteudo |
|---|---|
| `arquitetura_residencial.py` | Programa de ambientes (area, perimetro, area util) + PREVISAO DE CARGA da NBR 5410:2004 9.5.2: carga de iluminacao (9.5.2.1.2), numero minimo de pontos de tomada por alinea (9.5.2.2.1 a-e) e potencia minima atribuivel (9.5.2.2.2 a-b). Stateless, `_selftest` |
| `hidraulica_residencial.py` | Agua fria (NBR 5626:2020), esgoto + ventilacao (NBR 8160) e pluvial (NBR 10844) de uma casa. NAO contem tabela propria: reusa as primitivas ja aferidas de `hidraulica_predial` |
| `casa_residencial.py` | ADAPTADOR do Project Loop: despacha as tres disciplinas e faz a CONFERENCIA ponto declarado x minimo normativo + a conferencia geometrica planta x layout |
| `desenho_casa_residencial.py` | Tres pranchas SVG (quadro de ambientes, conferencia NBR 5410, esquema hidraulico), sem FreeCAD |
| `projects/casa-residencial/` | Spec real persistido: casa terrea de 2 dormitorios, 7 ambientes, 27 pontos, 6 circuitos, rede hidraulica completa |

Reuso por PRIMITIVA (licao da Fase 6B): a vertical eletrica inteira vem de
`residencial_eletrica`; toda tabela hidraulica vem de `hidraulica_predial`; o
SVG vem de `desenho_svg_base`. Nenhuma dessas contas foi reescrita.

A fixture sintetica **continua registrada e testada**: sao dois adaptadores para
o mesmo `project_type` (`casa-residencial-sintetica` exerce o contrato do nucleo,
`casa-residencial` exerce as disciplinas). Criterios 7 e 8 do desenho de
generalizacao preservados.

---

## 2. Proveniencia dos numeros

Transcricao literal da ABNT NBR 5410:2004 pelo NotebookLM (notebook eletrico
`78cd2efd-0652-484e-b312-c5c5a7648962`, fonte `d213019d-6e5c-4f18-8151-bf5a74c11b5d`),
com `cited_text` conferido - nunca de memoria (regra AR300):

| Item | Conteudo transcrito |
|---|---|
| 9.5.2.1.1 | "pelo menos um ponto de luz fixo no teto, comandado por interruptor" |
| 9.5.2.1.2 | area <= 6 m2 -> 100 VA; area > 6 m2 -> 100 VA + 60 VA por "cada aumento de 4 m2 INTEIROS" |
| 9.5.2.2.1-a | banheiros: >= 1 ponto proximo ao lavatorio (restricoes de 9.1) |
| 9.5.2.2.1-b | cozinhas/copas/areas de servico/lavanderias: 1 ponto por 3,5 m ou fracao de perimetro; >= 2 tomadas acima da bancada |
| 9.5.2.2.1-c | varandas: >= 1 ponto |
| 9.5.2.2.1-d | salas e dormitorios: 1 ponto por 5 m ou fracao de perimetro |
| 9.5.2.2.1-e | demais: 1 se area <= 2,25 m2; 1 se 2,25 < area <= 6 m2; 1 por 5 m ou fracao se area > 6 m2 |
| 9.5.2.2.2-a | molhados: 600 VA ate TRES pontos + 100 VA nos excedentes, cada ambiente separadamente; se o CONJUNTO passa de seis pontos, ADMITE-SE 600 VA ate DOIS |
| 9.5.2.2.2-b | demais comodos: 100 VA por ponto |
| 9.5.3.1 / 9.5.3.2 | ponto > 10 A em circuito independente; TUG de cozinha/area de servico em circuito exclusivo |

A alternativa dos dois pontos e' uma **permissao**, nao o criterio padrao: o
modulo calcula o de tres pontos e expoe o alternativo em campo separado, com
aviso. Rebaixar a carga em silencio seria a saturacao silenciosa de novo, so
que com o sinal trocado.

Hidraulica: nenhuma tabela nova. Tudo vem de `hidraulica_predial`, ja aferido
contra os PDFs (NBR 5626:2020 Tab.B.4 e pesos de 1998; NBR 8160 Tab.3, 5, 6, 7,
8 e D.1; NBR 10844 Tab.3, 4 e 5).

---

## 3. Achados (as tres tecnicas de caca)

### 3.1 Saturacao silenciosa - quatro funcoes da NBR 8160

`hidraulica_predial` ja tinha `_menor_dn_sat`, que devolve `(dn, saturado)`.
Quatro funcoes publicas **descartavam a flag**:

| Funcao | Teto da tabela | Consequencia |
|---|---|---|
| `diametro_ramal_esgoto` | Tab.5, 160 UHC em DN100 | DN100 saia igual para 160 e para 1600 UHC |
| `diametro_tubo_queda` | Tab.6 | idem |
| `diametro_coletor` | Tab.7 | idem |
| `diametro_ramal_ventilacao` | Tab.8, DN75 acima de 60 UHC (com bacias) | **o mais alcancavel**: DN75 saia igual para 60 e para 600 UHC, com `OK=True` |

Criadas as versoes `*_sat` que devolvem `{DN_mm, saturado, uhc, tabela}`; as
funcoes antigas delegam (o galpao nao muda de assinatura). `galpao_hidraulica`
ganhou o gate EFETIVO `esgoto_saturacao` e a marca `[SATURADO]` na string de
dimensionamento; `hidraulica_residencial` nasce com o gate.

### 3.2 Rotulo x geometria - dois niveis

**Dentro da arquitetura**: um comodo de area A tem perimetro minimo `4*raiz(A)`
(o quadrado - desigualdade isoperimetrica). Perimetro declarado abaixo disso e'
geometricamente impossivel e REPROVA. Sem isso o numero de tomadas sairia de uma
planta que nao existe. Tambem se confere area/perimetro declarados contra
`largura x comprimento`.

**Entre disciplinas**: o programa de arquitetura declara `largura_m x
comprimento_m`; o layout eletrico declara `width_m x depth_m` do MESMO ambiente,
de forma independente. `conferir_geometria_layout` compara as duas areas -
se divergirem, o numero de tomadas foi tirado de uma planta e conferido contra
outra (`area_do_layout_diverge_do_programa`).

### 3.3 Renderizar-e-olhar - a dupla escapa do SVG

A primeira versao de `desenho_casa_residencial` chamava `esc()` **antes** de
`texto()`, que ja escapa. Um ambiente chamado `Sala <estar & jantar>` sairia com
`&amp;lt;` no arquivo e imprimiria `&lt;` literal na prancha. O teste que
procura substring nao pega (a substring escapada esta la); so o teste que
**parseia** o SVG e le `no.text` pega. Irmao do bug do SVG XML-malformado (#154):
a barra verde nao cobre o artefato final.

As tres pranchas foram rasterizadas (svglib + reportlab) e olhadas, inclusive no
pior caso (nome com `<` e `&`, ambiente deficitario, ponto orfao).

### 3.4 Filtro de nome morto - prevenido

A conferencia casa `points[].room` com o nome do ambiente. Se o `room` nao casa
com nada, a contagem daria zero **em silencio**. Duas defesas: chave normalizada
(acento, caixa, espaco - `Area de servico` == `ÁREA DE SERVIÇO`) e o erro
`ambiente_desconhecido_no_circuito` para todo ponto orfao.

### 3.5 `i_default` por coincidencia de valor

`diametro_pluvial` marca a intensidade de chuva como "assumida" sempre que ela
iguala 150 mm/h, mesmo quando o projeto a confirmou. O modulo residencial deriva
a flag de o spec ter **declarado** ou nao o valor - um projeto que confirmou
150 mm/h nao merece o `[A CONFIRMAR]`.

---

## 4. A costura que faltava

A vertical eletrica exige `circuits.points` declarados um a um e nunca soube
dizer se aquilo atende a norma para aquela planta. Agora:

- tomada faltando -> `tomadas_abaixo_do_minimo_nbr5410`, disciplina **blocked**;
- comodo sem ponto de luz -> `ponto_de_luz_ausente_nbr5410`;
- numero certo mas potencia abaixo -> `carga_de_tomadas_abaixo_do_minimo_nbr5410`
  (cozinha com 4 TUG de 100 VA nao atende: 9.5.2.2.2 exige 3x600 + 100);
- ponto em ambiente inexistente -> `ambiente_desconhecido_no_circuito`;
- TUE **nao** conta como TUG (9.5.3.1 e' circuito dedicado, nao substitui).

O gate `previsao_nbr5410_atendida` entra no registro da disciplina eletrica.

---

## 5. Estado

Nenhuma disciplina e' marcada `passed`. Todas terminam em `needs_review`:
aprovacao para obra exige responsavel tecnico, ART/RRT e aprovacao legal, nada
disso avaliado. O adaptador declara apenas `report` e `drawings` (sem IFC, sem
3D) - capacidade nao declarada e' capacidade que nao existe.

**Fora do escopo, registrado:** estrutura da casa (alvenaria segue bloqueada por
falta da NBR 16868 no acervo), codigo de obras municipal, NBR 15575, NBR 9050,
agua quente/reservatorio/recalque, IFC e 3D da casa.

**Dados de sitio [A CONFIRMAR] no spec persistido:** intensidade pluviometrica
local (NBR 10844 Tab.5) e pressao disponivel na entrada.

Testes: 99 novos em `tests/branches/g4/`.
