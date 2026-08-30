# G3 - EDIFICACAO MULTIPAVIMENTO: o que entrou, como foi aferido, o que ficou

Fecha o gap da secao 4 de `REVISAO-GAPS-G2-LAJE-ALVENARIA-MULTIPAV.md`. Antes disto
a vertical de concreto era moldada para o PORTICO PRE-MOLDADO do galpao: um lance de
pilar em balanco, viga biapoiada de um vao, `n_andares=1` fixo. Nao havia conceito de
pavimento-tipo nem de descida de cargas por pavimento.

---

## 1. Modulos

| Arquivo | Conteudo |
|---|---|
| `cargas_nbr6120.py` | ACOES da NBR 6120:2019: Tab.1 (pesos especificos), Tab.2 (alvenarias, kN/m2 DE PAREDE, estrutural x vedacao, revestimento 0/1/2 cm por face), Tab.3 (divisorias/caixilhos), Tab.10 (cargas de uso por ambiente, com a marca REDUTIVEL/NAO REDUTIVEL de cada linha), Tab.11 (paredes sem posicao definida), Tab.12 (guarda-corpos, 1,1 m acima do piso) + `Fd = 15 kN` de balancim, Tab.13 cat.I (garagem <= 30 kN), Tab.19 / item 6.12 (multiplicador `alpha_n`) |
| `viga_continua.py` | Viga continua de varios tramos: solver proprio por deslocamentos (slope-deflection), as tres correcoes obrigatorias de 14.6.6.1 (a/b/c), engastamento parcial nos apoios extremos com devolucao dos momentos aos tramos do pilar, e alternancia de cargas de 14.6.6.3 |
| `pilar_continuo.py` | Pilar de varios lances: `le = min(l0 + h ; l)` de 15.6 POR DIRECAO, descida da forca normal com peso proprio, mudanca de secao entre lances e gates de continuidade |
| `pavimento_tipo.py` | Malha de pilares/vigas/lajes; vinculacao de cada painel DEDUZIDA da malha; reacoes das lajes por 14.7.6.1; cada linha vira uma viga continua; reacoes de apoio = carga do pilar. Reacoes separadas em `g` e `q` |
| `descida_cargas.py` | Empilha os pavimentos, aplica `alpha_n` de 6.12 SO sobre a parcela variavel, monta os lances de cada pilar e emite o registro exigido pela norma |
| `escada_concreto.py` | Escada de concreto como laje armada em uma direcao (a `escada.py` existente e METALICA): Blondel, carga da laje inclinada e dos degraus, flexao, cortante de laje, ELS |
| `desenho_pavimento.py` | Planta de formas do pavimento-tipo: malha em escala, paineis com o caso de vinculacao, bordas continuas, cotas e quadro de cargas por pilar |
| `edificio_multipavimento.py` | ORQUESTRADOR: um `rodar(spec)` encadeia a cadeia inteira e consolida os gates num ATENDE global, no padrao stateless de `galpao_concreto.rodar`. Adota automaticamente a MENOR secao de pilar que atende em cada lance, sem nunca deixar a secao encolher ao descer |

Reuso por PRIMITIVA (licao da Fase 6B): a flexo-compressao, esbeltez, 2a ordem e
armaduras minimas vem de `pilar_concreto`; a flexao de laje, os minimos da Tab.19.1,
o detalhamento de 20.1, o cortante de 19.4.1 e as reacoes de 14.7.6.1 vem de
`laje_concreto`; a flecha de Branson vem de `viga_baldrame`; o SVG vem de
`desenho_svg_base`. Nenhuma dessas contas foi reescrita.

---

## 2. Proveniencia dos numeros

Todas as tabelas foram transcritas do texto das normas via NotebookLM, com as
CITACOES DO TEXTO BRUTO conferidas - nao de memoria (regra do projeto depois do
episodio do "AR300" inventado, que ainda criou teste cristalizando o erro).

Itens conferidos literalmente e com citacao:

- NBR 6120:2019 - Tab.2 (com a nota de composicao), Tab.3, Tab.10, Tab.11 + o texto
  de 6.2, Tab.12 + notas a/b + o Fd de 15 kN de 6.3, Tab.13 cat.I, e o item 6.12
  INTEGRAL com a Tab.19 e a lista de usos nao redutiveis.
- NBR 6118:2014 - 14.6.6.1 alineas a/b/c (com a expressao dos coeficientes e a
  Figura 14.8), 14.6.6.3, 15.6 (`le = min(l0+h ; l)`), 15.8.1 (`lambda <= 200`,
  ressalva de `N < 0,10 fcd Ac`, `gamma_n1`), 15.8.3.2 (`metodo geral obrigatorio
  para lambda > 140`), 15.8.3.3.2 (`lambda <= 90`) e 15.8.4 (fluencia obrigatoria
  acima de 90).

### Duas divergencias de fonte, resolvidas a favor da norma

1. **Coeficientes de 14.6.6.1-c.** Uma apostila didatica do acervo escreve
   `3r/(4r_vig + 3r_inf + 3r_sup)`; o TEXTO da NBR 6118 nao tem os fatores 3 e 4.
   Implementado como esta na norma. A variante fica em
   `coef_engastamento_parcial(variante='apostila')` apenas para comparacao, nunca
   como default, e um teste garante que as duas dao resultados diferentes.
2. **Tabela 2 da NBR 6120, bloco ceramico de furo horizontal.** A nota da tabela
   declara revestimento a 19 kN/m3, logo 1 cm por face soma 0,38 kN/m2. Todas as
   linhas fecham nisso EXCETO as espessuras de 9 e 19 cm, cujo salto da coluna de
   1 cm para a de 2 cm e 0,5. Reconferido no texto bruto: os digitos impressos na
   norma sao mesmo 1,6 e 2,3 - e arredondamento da propria ABNT, nao erro de
   leitura. Transcritos como estao, com a divergencia declarada e travada em
   `DIVERGENCIAS_TAB2_CONHECIDAS`.

### O que NAO foi implementado, e por que

- **Alvenaria ESTRUTURAL: continua bloqueada por FONTE.** A NBR 16868 segue ausente
  do acervo (reconfirmado em `REVISAO-GAPS-G2-...`, secao 3). A alvenaria entra
  neste G3 apenas como ACAO, e agora com fonte: peso do painel pela Tabela 2 e
  carga adicional de paredes sem posicao definida pela Tabela 11. Dimensionar
  parede a compressao exigiria `f_pk`, fator de eficiencia bloco/prisma e esbeltez
  de parede, que nao existem em nenhuma fonte do acervo.
- **Geometria de degrau e patamar** (NBR 9050/9077) tambem esta fora do acervo -
  mesma limitacao ja declarada em `escada.py`. Marcada A CONFIRMAR no modulo e no
  relatorio da escada.

---

## 3. Afericao

**Solver de viga continua** - conferido contra as solucoes FECHADAS classicas, que
sao independentes do codigo:

| Caso | Grandeza | Fechado | Solver |
|---|---|---|---|
| 2 vaos iguais | M sobre o apoio | `-wL^2/8` | bate |
| 2 vaos iguais | R extremo / R central | `3wL/8` / `10wL/8` | bate |
| 2 vaos iguais | M+ maximo | `9wL^2/128` | bate |
| 3 vaos iguais | M sobre os apoios | `-0,100 wL^2` | bate |
| 3 vaos iguais | R extremo / R interno | `0,400 wL` / `1,100 wL` | bate |
| 3 vaos iguais | M+ externo / central | `0,080` / `0,025 wL^2` | bate |
| 1 a 5 vaos | soma das reacoes | `n*w*L` | bate |

**Descida de cargas** - a conferencia independente e o FECHAMENTO: a soma das
reacoes que chegam aos pilares reproduz a carga total do pavimento (lajes + peso
proprio das vigas + paredes) com erro < 0,01% em todas as malhas testadas. E assim
que se pega uma laje cuja reacao nao foi lancada em nenhuma viga - carga que
simplesmente some, sem que nenhum gate de flexao ou cortante reclame.

**Multiplicador `alpha_n`** - a sequencia reproduz linha a linha as Figuras 12, 13 e
14 do item 6.12, incluindo as tres sutilezas: o pavimento nao redutivel entra com
1,0 e NAO interrompe nem avanca a contagem do grupo; a troca de uso reinicia a
contagem; e grupos de mesmo uso com AREAS diferentes sao grupos distintos.

**Superposicao g/q** - `N_g + N_q` reproduz exatamente o total, e `N_q` reproduz
exatamente `q x area`.

---

## 4. Gates de saturacao silenciosa

O padrao recorrente do projeto (o calculo satura no extremo, o gate nao reprova,
sai OK=True) tem gate proprio em cada ponto onde pode ocorrer:

1. **Faixa de validade da esbeltez** (15.8.1 / 15.8.3.3.2 / 15.8.4). `lambda` e uma
   FAIXA DE VALIDADE, nao uma utilizacao: nao aparece como razao
   solicitante/resistente. Ver a secao 5 - foi um bug REAL e ja existente.
2. **Tabela 11 acima de 3,0 kN/m**: a norma marca NAO PERMITIDO. Saturar na ultima
   faixa (1,0 kN/m2) devolveria OK com a parede pesada fora da posicao de projeto.
   Aqui `ok=False`, e o pavimento inteiro reprova.
3. **Alternancia de cargas (14.6.6.3)**: a dispensa exige carga variavel `<= 5 kN/m2`
   **E** `<= 50%` da total. Uma viga de biblioteca passa em flexao e cortante e
   ainda assim esta subdimensionada se a alternancia for ignorada. Se a dispensa
   nao valer e a alternancia estiver desligada, o resultado sai REPROVADO.
4. **Reducao de 6.12 e uma BONIFICACAO**: ela so alivia. Aplicada onde a norma nao
   permite (garagem, cobertura, estoque - ou a vigas e lajes), nada reprova; o
   pilar so sai mais leve. Por isso a permissao vem marcada linha a linha na
   Tab.10 e `verifica_reducao` confere que nenhum pavimento nao redutivel recebeu
   `alpha < 1`.
5. **Secao de pilar que ENCOLHE ao descer**: nenhum gate de flexo-compressao
   acusaria isso COMO TAL - o lance de baixo so ganharia armadura, ou reprovaria
   por taxa, sem dizer que o lancamento e que esta errado.
6. **Consultas sem fallback**: ambiente fora da Tab.10, espessura de alvenaria fora
   da Tab.2 e revestimento fora de 0/1/2 cm LEVANTAM. Cair no vizinho mais proximo
   e o padrao do "filtro de nome morto": uma `loja` que caisse num default de
   1,5 kN/m2 seria dimensionada com 37% da carga da norma.
7. **Lista de espessuras esgotada** na escada: sai `OK=False` com aviso, nunca a
   ultima tentada dada por boa.

---

## 5. BUG REAL encontrado: pilar dimensionado fora da faixa de validade do metodo

`pilar_concreto.dimensiona_pilar` implementa o metodo do pilar-padrao com CURVATURA
APROXIMADA, que a NBR 6118 15.8.3.3.2 restringe a `lambda <= 90`. **Nao havia
nenhuma verificacao dessa faixa.** O modulo calculava `e2`, somava a `M1d` e devolvia
um `As` perfeitamente formado para qualquer esbeltez.

Consequencia medida no galpao de concreto pre-moldado, com `pe_direito = 6 m`:

| | secao adotada | `lambda_x` | `lambda_y` | resultado |
|---|---|---|---|---|
| antes | 0,20 x 0,40 | 103,9 | **207,8** | `OK: True` |

`lambda_y = 207,8` esta acima do limite ABSOLUTO de 200 que a norma nao admite
(15.8.1, ressalvados os elementos pouco comprimidos, que nao era o caso), e as duas
direcoes estao fora da faixa do metodo aplicado e da faixa em que a fluencia poderia
ser dispensada. Nada reprovava.

**Causa do `lambda` alto:** `galpao_concreto` usava `le = 2H` nas DUAS direcoes. No
plano do portico isso e correto (o pilar e balanco). Na direcao longitudinal, `2H`
significa um pilar de 20 cm de largura e 6 m de altura livre longitudinalmente - e o
modelo do galpao de concreto de fato NAO tem sistema de contraventamento
longitudinal.

**O que foi feito:**

1. `pilar_concreto.valida_esbeltez(lambda, nu)` - gate compartilhado, com os quatro
   limites conferidos literalmente. Entra em `OK` e devolve os avisos por direcao.
   Todo consumidor (galpao, pilar continuo) ganha o gate de uma vez.
2. `galpao_concreto` passa a receber `travamento_longitudinal`, com
   `_le_por_direcao` explicito. O default e `'nenhum'` - o HONESTO para o modelo
   como ele e - e nesse caso o galpao REPROVA com a mensagem dizendo o que fazer.
   Assumir `'topo'` calado seria escolher a hipotese que faz passar.
3. Os specs do proprio framework (selftest, turnkey, fixtures) passaram a DECLARAR
   `travamento_longitudinal='topo'`, porque o galpao real tem esse sistema. Com a
   declaracao, o pilar cai para **0,25 x 0,50 com `lambda = 83,1` nas duas direcoes**
   - dentro da faixa, e com secao MENOR que a tentada sem travamento.

> **Pendencia declarada:** o modelo do galpao de concreto nao tem sistema de
> estabilidade longitudinal modelado. `travamento_longitudinal='topo'` e uma
> DECLARACAO do usuario, nao um calculo. Modelar o contraventamento longitudinal do
> galpao de concreto (o `contraventamento.py` existe, mas serve ao galpao de aco)
> fica como item aberto.

---

## 6. BUG REAL encontrado: toda barra retangular do 3D federado girada 90 graus

Achado por consequencia do item 5: com o pilar do galpao passando a 0,40 x 0,90 (a
maior secao da lista, tentada sem travamento), o teste
`test_montar_3d_federado_vivo_e_consistente_com_aabb` quebrou com
`86 <= 85` - o clash do solido OCCT acusando MAIS interferencias que a caixa AABB,
o que e geometricamente impossivel (um solido esta contido na sua propria caixa).

Diagnostico: o par `C-P4E` (pilar) x `I-ACN1` (acionador de incendio) so aparecia no
OCCT, com volume de sobreposicao de **864 000 mm3 = exatamente o volume inteiro do
acionador** (120 x 120 x 60): o dispositivo estava TOTALMENTE DENTRO do pilar no 3D.

Causa: `build_federado._shape_de_solido` construia o prisma com
`Part.makeBox(bf, d, L)` - largura no eixo local X e altura no local Y. O
`galpao_turnkey._aabb_barra` usa a convencao oposta (`d` no eixo perpendicular
"principal"). As duas discordavam em 90 graus em torno do eixo da barra:

- **viga horizontal** saia DEITADA DE LADO (a altura `d` na horizontal);
- **pilar vertical** saia com o EIXO FORTE fora do plano do portico.

E a mesma classe do bug da coluna do galpao de aco (PR #35), em outro caminho de
codigo. Ficava invisivel em secao quase quadrada e em secao pequena; so apareceu
quando a secao ficou bem nao-quadrada.

Corrigido para `Part.makeBox(d, bf, L)`, o que faz as duas convencoes coincidirem e
recoloca a altura da viga na vertical. Efeito medido: o invariante voltou
(`70 <= 85`) e **16 das 86 interferencias que o OCCT acusava eram artefato das
barras giradas**.

O `_spec()` de `test_build_federado.py` NAO declara `travamento_longitudinal` de
proposito - e o que mantem o pilar na secao bem nao-quadrada que torna o invariante
sensivel a orientacao. Isso esta comentado no proprio teste.

---

## 7. O que o "renderizar-e-olhar" pegou

A planta de formas foi gerada, convertida em PNG (`svglib` + `reportlab.renderPM`)
e ABERTA. Dois defeitos que nenhum teste numerico pegaria:

1. **Rotulos da ultima coluna de pilares (P41/P42/P43) cortados**: eram desenhados
   16 px a direita do pilar, e nessa posicao avancavam por baixo do quadro de
   cargas. A string estava no SVG e todo teste de substring passava. Corrigido
   ancorando o rotulo a ESQUERDA na ultima coluna, e a checagem virou GEOMETRICA
   (`colisoes_de_rotulo`, com um teste que confere que o detector realmente
   detecta).
2. **Rotulos VY do topo amontoados sobre os rotulos dos pilares da fileira
   superior**. Afastados.

O teste do desenho faz `ET.fromstring` (parse, nao substring - licao do PR #154) e
compara as contagens desenhadas com as dos DADOS, nunca com uma contagem
recalculada no proprio laco (licao da grade da planta de incendio).

---

## 8. Bug de distribuicao pego por teste de SIMETRIA

Numa malha 2x2 de paineis iguais os quatro pilares de canto tem de receber a mesma
carga. Nao recebiam: 26,52 kN num canto contra 18,48 kN no oposto.

Causa: os casos de vinculacao da `laje_concreto` nomeiam QUAL borda esta engastada
(o caso 4 e `('x0','y0')`, com o engaste na PRIMEIRA borda de cada par). O
`pavimento_tipo` mapeava o par em ordem fixa (`esq`,`dir`), de modo que o painel de
canto cujo engaste esta em `dir`/`sup` recebia a reacao do engaste na borda LIVRE e
vice-versa.

O fechamento de carga NAO pegava isso: o painel inteiro continuava sendo
distribuido, o total fechava - a carga so ia para os pilares errados. Corrigido
ordenando cada par com a borda engastada primeiro.

---

## 9. Cobertura de teste

**193 testes novos**, todos verdes, e a suite completa passa em **2278 testes, 0 falhas**:

| Arquivo | Testes |
|---|---|
| `test_cargas_nbr6120.py` | 41 |
| `test_viga_continua.py` | 29 |
| `test_pilar_continuo.py` | 17 |
| `test_pavimento_tipo.py` | 24 |
| `test_descida_cargas.py` | 17 |
| `test_escada_concreto.py` | 24 |
| `test_desenho_pavimento.py` | 21 |
| `test_edificio_multipavimento.py` | 20 |

---

## 10. O que fica aberto

1. ~~**Estabilidade global do multipavimento.**~~ **FECHADO** (2026-08-30,
   `estabilidade_edificio.py`): o `gamma_z` passa a sair de uma analise de
   portico plano de 1a ordem com a rigidez de 15.7.3 (0,8 Ec Ic pilares,
   0,4 Ec Ic vigas, Ec = 1,10 Ecs por 15.5.1). O `estabilidade_b1b2` continua
   amarrado a um pavimento, mas ja nao e' o caminho do edificio.
2. ~~**Vento no edificio multipavimento**~~ **FECHADO** (mesma data): vento por
   pavimento pela NBR 6123 (Fa = Ca q Ae, com q recalculado em cada cota pelo
   S2) e desaprumo pela 11.3.3.4.1, combinados pela regra a/b/c dos 30 %.

   Tres coisas que a implementacao obrigou a decidir, e que valem registro:

   - **Ca e' ABACO.** As Figuras 4 e 5 da NBR 6123 nao tem tabela de numeros -
     confirmado no acervo. Digitalizar curva de imagem foi o que produziu as 6
     celulas erradas nas tabelas de Bares e e' o motivo do shed multi-vao seguir
     bloqueado. Ca virou ENTRADA declarada, com proveniencia A CONFIRMAR; sem
     ele o modulo levanta ValueError em vez de arbitrar.
   - **A comparacao dos 30 % usa theta_a SEM theta_1min.** Sutileza literal da
     11.3.3.4.1 que passaria batido: o theta_1min entra no dimensionamento do
     caso (b), nao na comparacao.
   - **A rigidez de 15.7.3 e' exclusiva do ELU.** 14.6.4.1 manda Ecs com secao
     BRUTA para o ELS, e 16.2.4 diz que os modelos de ELS "tem rigidez
     diferente, usualmente maior".

2b. **ELS de deslocamento lateral - gap que nao estava nesta lista.** Com o topo
   em H/619 no ELU, a verificacao de servico foi conferida e faltava inteira:
   Tabela 13.3 limita H/1700 no topo e Hi/850 entre pavimentos, na combinacao
   FREQUENTE (psi_1 = 0,30), com a Nota f mandando excluir a deformacao axial
   dos pilares. Implementado junto. E' o mesmo padrao do "girt sem ELS": o
   gamma_z sozinho declararia OK um predio que balanca demais.
3. **Contraventamento longitudinal do galpao de concreto** (ver secao 5).
4. **Alvenaria estrutural**: bloqueada por fonte (NBR 16868 ausente do acervo).
5. **Pilar de transicao**: a descida exige a mesma malha em toda a altura, e reprova
   explicitamente se as malhas diferirem. Viga de transicao nao esta tratada.
6. **Vibracao de piso e NBR 15575**: continuam abertos, como ja registrado na
   revisao de gaps do G2.

## 11. Nota sobre a politica de secao dos pilares

O orquestrador adota a MENOR secao que atende, como ja faz o `galpao_concreto`. Numa
malha residencial de 9 pavimentos isso leva os pilares de canto e de extremidade a
0,19 x 0,30 m com taxa de armadura de ate ~3,4% (o teto por lance e 4%, 17.3.5.3.2)
e `nu` proximo de 0,98. E conforme e o solver resiste, mas e um dimensionamento no
limite pratico: sao secoes finas e muito armadas. Se a intencao for um projeto mais
folgado, o caminho e passar uma lista `SECOES_PILAR` comecando mais alta - a politica
em si (menor secao que atende) e a mesma do resto do framework e nao foi alterada
aqui.
