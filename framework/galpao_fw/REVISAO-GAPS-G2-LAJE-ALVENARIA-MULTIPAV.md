# REVISAO — Gaps normativos de LAJE / ALVENARIA / MULTIPAVIMENTO (pre-G2)

Auditoria de acervo (NotebookLM) x codigo, feita ANTES de codar G2. Metodo: para
cada exigencia normativa levantada nas fontes, procurar a implementacao no codigo
antes de declarar gap (precedente S16/S18/S41: a auditoria ja rendeu tanto gaps
reais quanto falsos-positivos do tipo "puncao/Ief faltando" que ja estavam cobertos).

Notebooks consultados:
- `6949283a` 01 Concreto Armado e Materiais (NBR 6118:2014 + EM1:2026, Araujo, Carvalho)
- `261e7432` 04 Acoes e Equipamentos (NBR 6120:2019, 6123, 8681:2025, 15421)
- `cad0c145` 02 Estruturas de Aco (NBR 8800:2008, Fakury mistos, Bellei multiplos andares)
- `0f83b41b` 13 Arquitetura e Desempenho (NBR 15575 partes 1 a 6)

---

## 0. Resumo executivo

| Frente | Situacao | Blocante p/ G2? |
|---|---|---|
| LAJE (macica/nervurada/lisa) | modulo NAO EXISTE (`piso_industrial.py` e placa sobre solo, nao laje de piso) | SIM |
| Puncao laje-pilar (19.5 completo) | PARCIAL — nucleo ja existe em `fundacao_sapata.py` | SIM (extensao) |
| ALVENARIA (estrutural) | acervo NAO COBRE (confirmado: NBR 16868 ausente das 48 fontes) | SIM (bloqueio de fonte) |
| ALVENARIA (vedacao, como acao) | JA COBERTO parcialmente (`projeto_spec` fechamento) | nao |
| Cargas de uso NBR 6120 | modulo NAO EXISTE (so `Q_ESCADA=3.0` solto) | SIM |
| MULTIPAVIMENTO — 2a ordem | PARCIAL — `estabilidade_b1b2.py` correto mas amarrado a 1 pavimento | SIM |
| Vigas/lajes mistas, pilar misto (Anexos O/P/Q) | NAO EXISTE | SIM se estrutura mista |
| Vibracao de piso (Anexo L) | NAO EXISTE | SIM |
| NBR 15575 (desempenho) | ZERO ocorrencias no codigo | SIM p/ habitacional |

---

## 1. FALSOS-POSITIVOS EVITADOS (ja implementado — nao reimplementar)

Verificado no codigo, com linha:

1. **Puncao — nucleo das tensoes resistentes.** `fundacao_sapata.py:793` implementa
   literalmente `tau_Rd1 = 0,13*(1+raiz(20/d[cm]))*(100*rho*fck)^(1/3)` (19.5.3.2) e
   `fundacao_sapata.py:899` implementa `tau_Rd2 = 0,27*alpha_v*fcd` (19.5.3.1).
   O coeficiente **K da Tabela 19.2 ja existe** (`fundacao_sapata.py:737`) e o `Wp`
   ja e calculado (`:905`). => a laje REUSA isso; nao ha o que reescrever do nucleo.
2. **Flecha por Branson + fluencia.** `viga_baldrame._flecha_alvenaria` (`:62`) ja faz
   17.3.2 (rigidez equivalente de Branson) + fluencia, e ja aplica o limite da
   **Tab 13.3 para alvenaria: min(L/500 ; 10 mm)** (`viga_baldrame.py:94`), com a
   sutileza correta de contar so a parcela POS-parede. `viga_concreto.py:106-118` ja
   reusa via `suporta_alvenaria`/`q_alvenaria`.
3. **Rigidez reduzida de 80% e forca nocional.** `estabilidade_b1b2.py:46`
   (`FN_FRAC=0.003`, item 4.9.7.1.1) e `:245-275` (limite de validade do MAES: 1,40
   com rigidez original / 1,55 com rigidez reduzida; imprime "Rigidez reduzida 80%").
   O metodo esta correto — o problema e outro (ver 4.1).
4. **gamma_n de secao pequena.** `pilar_concreto.py` ja implementa 13.2.3/Tab.13.1
   (`1,95 - 0,05*b`). A **Tabela 13.2 da laje em balanco usa a MESMA expressao**
   `gamma_n = 1,95 - 0,05*h` — reuso direto, nao duplicar.
5. **alpha1 multipavimento.** `estabilidade_global_nbr6118.alpha_limite` (`:27`) ja
   trata `n_andares>=4 -> 0,5/0,7/0,6 por sistema` e `n<=3 -> 0,2+0,1n`, e ja
   sinaliza que gamma_z so vale com >=4 andares. A funcao generica esta pronta.

---

## 2. LAJE — gaps reais (NBR 6118:2014)

Nao existe nenhum modulo de laje de piso. `piso_industrial.py` e placa sobre base de
Winkler (Westergaard) — outro problema fisico, nao serve.

### 2.1 Geometria e minimos (13.2.4.1 / Tabela 13.2)
Espessura minima h: **7 cm** cobertura sem balanco; **8 cm** piso sem balanco;
**10 cm** em balanco; **10 cm** veiculo <= 30 kN; **12 cm** veiculo > 30 kN;
**15 cm** laje protendida sobre vigas (min L/42 biapoiada, L/50 continua);
**16 cm laje lisa** e **14 cm laje-cogumelo** fora do capitel.
Balanco com h < 19 cm: majorar esforcos por `gamma_n = 1,95 - 0,05h` (h em cm).

### 2.2 Laje nervurada (13.2.4.2)
- Mesa: `hf >= max(4 cm ; l0/15)`; com tubulacao `phi<=10mm` -> min 5 cm; com
  `phi>10mm` -> `4cm + phi` (ou `4cm + 2phi` se houver cruzamento).
- Nervura: `bw >= 5 cm`; **nervura < 8 cm nao pode ter armadura de compressao**.
- Criterio de dispensa por espacamento entre eixos de nervuras:
  `<= 65 cm` dispensa flexao da mesa e o cisalhamento e verificado como LAJE (19.4.1);
  `65-110 cm` exige flexao da mesa e cisalhamento como VIGA (permitido como laje ate
  90 cm se `bw,medio > 12 cm`); `> 110 cm` -> mesa projetada como laje macica.

### 2.3 Cortante sem armadura transversal (19.4.1)
`V_Rd1 = [tau_Rd * k * (1,2 + 40*rho1) + 0,15*sigma_cp] * bw * d`, com
`tau_Rd = 0,25*fctd`; `k = 1` se 50% da armadura inferior nao chega ao apoio, senao
`k = |1,6 - d| >= 1` (d em m); `rho1 = As1/(bw*d) <= 0,02`. Verificar tambem a biela
`V_Rd2 = 0,5*alpha_v1*fcd*bw*0,9d`.
**Nao existe no codigo** — `viga_concreto` faz cortante de VIGA (modelo de trelica),
que e formulacao diferente.

### 2.4 Puncao — o que falta alem do nucleo ja pronto
O `fundacao_sapata` cobre o **pilar interno** no contorno C' a 2d. Para laje lisa faltam:
- **Pilar de borda (19.5.2.3)** e **de canto (19.5.2.4)**: perimetro reduzido `u*`
  (interrompido na borda a `min(1,5d ; 0,5*C1)`), `M_Sd1 = (M_Sd - F_Sd*e*) >= 0`, e
  no canto a segunda parcela `K2*M_Sd2/(Wp2*d)`.
- **Armadura de puncao (19.5.3.3)**:
  `tau_Rd3 = 0,10*(1+raiz(20/d))*(100*rho*fck)^(1/3) + 0,10*sigma_cp + 1,5*(d/sr)*Asw*fywd*sen(alpha)/(u*d)`,
  com `sr <= 0,75d`, primeiro contorno de conectores a no maximo `0,5d` da face, e o
  teto **fywd <= 300 MPa (stud) / 250 MPa (estribo)**.
- **Contorno C'' (19.5.3.4)**: 2d alem da ultima linha de conectores, onde volta a
  valer `tau_Sd <= tau_Rd1` no perimetro `u'`.
- **Aberturas a menos de 8d do contorno C (19.5.1)**: descontar do contorno C' a
  projecao radial delimitada pelas retas que tangenciam os vertices da abertura.
- **19.5.3.5**: se a estabilidade global do edificio depender da resistencia da laje
  a puncao, armadura de puncao e OBRIGATORIA para no minimo **50% de F_Sd**, mesmo
  com `tau_Sd <= tau_Rd1`.
- **Colapso progressivo (19.5.4)**: `fyd * As,ccp >= 1,5 * F_Sd` (armadura inferior
  que cruza o contorno C, ancorada alem de C'/C''), podendo calcular com `gamma_f = 1,2`.

> **ALERTA de saturacao silenciosa (padrao recorrente):** os itens 19.5.3.5 e 19.5.4
> sao exatamente do tipo que "passa" sem reprovar — sao requisitos ADICIONAIS que nao
> aparecem como razao tau_Sd/tau_Rd. Um gate que so olhe `tau_Sd <= tau_Rd1` devolve
> OK=True com a ligacao laje-pilar sem armadura contra colapso progressivo.

### 2.5 Armaduras minimas e detalhamento (19.3.3 / Tab 19.1 / 20.1)
`rho_s >= rho_min` (negativa; e positiva de laje armada em 1 direcao);
`>= 0,67 rho_min` (negativa de borda sem continuidade — estendida ate 0,15 do vao
menor a partir da face do apoio, 19.3.3.2 — e positiva de laje armada em 2 direcoes);
distribuicao: `As/s >= 0,20*As,principal`, `>= 0,9 cm2/m`, `rho_s >= 0,5 rho_min`.
Detalhamento (20.1): `phi <= h/8`; `s_max <= min(2h ; 20 cm)` na regiao dos maiores
momentos; armadura secundaria `s_max <= 33 cm`.

### 2.6 ELS (17.3.2 + Tab 13.3)
Alem do L/500;10mm ja implementado, faltam para laje: **L/250** (visual, com `l` = o
MENOR vao do painel), **L/350** (vibracao sentida no piso, so cargas acidentais),
**L/250** para superficies que devem drenar agua, **L/350 + contraflecha** com
**L/600 apos a construcao do piso** (pavimentos que devem permanecer planos), e
**L/250 ; 25 mm** para divisorias leves/caixilhos telescopicos. Rotacao no apoio
`theta <= 0,0017 rad`.

---

## 3. ALVENARIA — bloqueio de FONTE, nao de codigo

**O acervo nao cobre alvenaria estrutural.** Consulta explicita ao notebook 01
retornou NAO: nas 48 fontes a palavra "alvenaria" so aparece como acao permanente de
vedacao; a NBR 16868 e citada nominalmente na introducao da NBR 14931:2023 apenas
como norma setorial fora de escopo. Nao ha `f_pk`, fator de eficiencia bloco/prisma,
esbeltez de parede nem verificacao a compressao simples em nenhuma fonte.

Consequencia direta, e **decisao do usuario**:
- (a) subir NBR 16868-1/-2/-3 (ou apostila equivalente) ao acervo antes de codar; ou
- (b) escopar G2 como **estrutura reticulada (concreto/aco) com alvenaria de VEDACAO**,
  que o acervo cobre bem — e nesse caso a alvenaria entra so como acao (secao 4.2).

Regra do projeto: nao inventar valores de norma de memoria (precedente do "AR300"
inventado, que ainda criou teste cristalizando o erro). Sem fonte, nao codar 16868.

O que JA existe de alvenaria-como-acao: `projeto_spec.py:93` (`fechamento.tipo`,
`altura_alvenaria`, `peso`), `:687-697` (tipos `alvenaria` / `alvenaria_telha`, com a
alvenaria autoportante descendo pelo baldrame e NAO pela coluna de aco) e
`rodar_galpao.py:758-789`. Isso e reusavel; o que falta e a tabela de pesos (4.2).

---

## 4. MULTIPAVIMENTO — gaps reais

### 4.1 Estabilidade de 2a ordem esta amarrada a UM pavimento
`estabilidade_b1b2.py` implementa o MAES corretamente, mas e **estado global acoplado
a geometria do galpao**: `H_STORY = gp.EAVE` (em `sincronizar`), `GVERT/QVERT`
montados de `gp.G_ROOF/Q_ROOF/BAY/N_VAOS`, secoes replicadas como "colunas + 2 vigas
por vao". Nao existe o conceito de "andar". Para multipavimento e preciso `B2` **por
pavimento**, com o somatorio `sum(P_Sd)` e o cortante `sum(H_Sd)` daquele andar:
`B2 = 1/(1 - (1/Rs)*(sum(P_Sd)*delta_h)/(h*sum(H_Sd)))`, `Rs = 0,85` portico rigido /
`1,0` travado por diagonais ou nucleo rigido.
Desaprumo (4.9.7.1.1): `delta = h/333` entre pavimentos **ou** forca nocional
`Fn = 0,003*sum(P_Sd)` por pavimento, aplicada independentemente nas duas direcoes
ortogonais. Rigidez reduzida `0,80EA` / `0,80EI` para media deslocabilidade
(`1,1 < B2 <= 1,4`). Classificacao: `B2 <= 1,1` pequena, `1,1 < B2 <= 1,4` media,
`B2 > 1,4` grande deslocabilidade.

Analogo no concreto: `galpao_concreto.py:148` chama
`verifica_estabilidade_galpao(..., n_andares=1)` **fixo**, e a propria funcao
(`estabilidade_global_nbr6118.py:72`) so modela pilar em balanco. O `alpha_limite`
generico ja esta pronto; o que falta e o `gamma_z` receber `dM_tot_d` de uma analise
real de multiplos pavimentos (hoje nada alimenta essa funcao).

### 4.2 Cargas NBR 6120:2019 — nao existe modulo
Hoje so ha `escada.Q_ESCADA = 3.0` solto e `plataforma.py:87` marcando
"A CONFIRMAR: carga de utilizacao (NBR 6120)". Faltam, transcritos da norma:
- **Tabela 10**: cargas variaveis de uso por ambiente (uniformemente distribuida +
  concentrada). Nota da norma: cozinhas nao residenciais e depositos de uso geral
  devem ser **validados caso a caso**, respeitando o minimo tabelado.
- **Tabela 11 — paredes divisorias sem posicao definida** (carga adicional
  uniformemente distribuida, por peso proprio da parede acabada):
  `p.p. <= 1,0 kN/m -> 0,5 kN/m2` ; `1,0 < p.p. <= 2,0 -> 0,75` ;
  `2,0 < p.p. <= 3,0 -> 1,0` ; **`p.p. > 3,0 -> NAO PERMITIDO`** (tem de entrar como
  carga linear permanente, na posicao de projeto). Dispensada quando a carga variavel
  do pavimento for `>= 4,0 kN/m2`, **exceto** para parede com p.p. > 3,0 kN/m.
- **Tabela 1** (peso especifico aparente dos materiais), **Tabela 2** (alvenarias, em
  kN/m2 por espessura nominal e por espessura de revestimento por face — separa
  ALVENARIA ESTRUTURAL de ALVENARIA DE VEDACAO) e **Tabela 3** (divisorias e
  caixilhos, drywall). Isso da fonte ao `fechamento.peso` que hoje o usuario chuta.
- **Tabela 19 — reducao de cargas variaveis (item 6.12)**, para esforcos em PILARES e
  FUNDACOES que suportem n andares de mesmo tipo de uso: `1 a 3 pisos -> 1,0` ;
  `4 -> 0,8` ; `5 -> 0,6` ; `6 ou mais -> 0,4`. **Nao permitida** em garagens,
  reservatorios, coberturas, jardins, depositos e areas de estoque, areas tecnicas,
  industrias, estadios, teatros/cinemas, passarelas e assembleias. As reducoes
  adotadas **devem ser registradas nos documentos do projeto** (=> tem de sair no
  memorial/executivo, nao so no calculo).
- **Tabela 12 — forcas horizontais em guarda-corpos e barreiras**, aplicadas a
  **1,1 m acima do piso acabado**, perpendiculares ao eixo longitudinal:
  `0,4 kN/m` (passarela so de inspecao/manutencao); `1,0 kN/m` (areas privativas
  residenciais/escritorios/quartos, coberturas e terracos sem acesso publico, escadas
  privativas e de emergencia, areas com acesso publico); `2,0 kN/m` (escada
  panoramica; barreira paralela ao fluxo em area de acesso publico); `3,0 kN/m`
  (barreira perpendicular ao fluxo). Eventos extremos: recomendado `>= 5,0 kN/m`.
  Ancoragem de balancim/cabo de seguranca de fachada: forca concentrada de calculo
  **Fd = 15 kN** em qualquer direcao, nao concomitante com a Tabela 12.

> **ALERTA rotulo x geometria:** a Tabela 2 da 6120 da o peso **por m2 de parede, ja
> com o revestimento por face (0, 1 ou 2 cm)**. O `fechamento.peso` atual e usado como
> kN/m2 por metro de altura em `projeto_spec.py:697` (`w_mas = peso * h`). Ao plugar a
> tabela e preciso conferir que a grandeza tabelada e kN/m2 de parede e nao kN/m3 —
> errar isso e o mesmo tipo de erro do "bbox nao e eixo".

### 4.3 Estrutura mista aco-concreto (NBR 8800 Anexos O, P, Q) — nao existe
Se G2 admitir piso em steel deck / viga mista (o caminho normal de edificio em aco):
- **Viga mista (Anexo O)**: largura efetiva `b` (O.2.2 — menor entre L/8 por lado,
  metade da distancia entre vigas adjacentes, ou a distancia ate a borda em balanco;
  continuas usam 4/5 do vao extremo e 7/10 do vao interno para momento positivo, e
  1/4 da soma dos vaos adjacentes para momento negativo); conector stud (O.4.2.1.1)
  `Q_Rd = min[ 0,5*Acs*raiz(fck*Ec)/gamma_cs ; Rg*Rp*Acs*fucs/gamma_cs ]`,
  `gamma_cs = 1,25` (normal/especial/construcao) e `1,10` (excepcional),
  `hcs >= 4*dcs`, cobrimento superior >= 10 mm; grau de interacao
  `eta_i = sum(Q_Rd)/F_hd` com `F_hd = min(Aa*fyd ; 0,85*fcd*b*tc)` e minimo
  `eta_i >= 0,40` **e** `eta_i >= 0,75 - 0,015*L` para `L <= 20 m` (acima de 20 m a
  interacao tem de ser completa). Construcao nao escorada (O.2.3.2) exige verificar o
  perfil isolado — inclusive **FLT da mesa comprimida na fase de montagem** — antes de
  o concreto atingir `0,75 fck`.
- **Laje mista / steel deck (O.2.6 + Anexo Q)**: `hF <= 75 mm`, `bF >= 50 mm`,
  projecao do conector acima da forma `>= 40 mm`, `tc >= 50 mm`; ELUs obrigatorios na
  fase de construcao (flexao da chapa, **web crippling** sobre os apoios, flecha) e na
  fase mista (flexao positiva e negativa, cisalhamento vertical da nervura de concreto
  e **cisalhamento longitudinal na interface aco-concreto**, metodo m-k).
- **Pilar misto (Anexo P)**: fator de contribuicao do aco `delta = Aa*fyd/N_pl,Rd`,
  com faixa de validade **0,2 < delta < 0,9** (fora dela e pilar de concreto pela 6118
  ou pilar de aco puro pela 8800); `N_pl,Rd = Aa*fyd + alpha*Ac*fcd + As*fsd`, com
  `alpha = 0,95` para tubular circular preenchido e `0,85` nas demais secoes;
  transferencia de carga no no viga-pilar por atrito (Tab. P.1) ou conectores.

> **ALERTA de saturacao silenciosa:** `eta_i` e `delta` sao FAIXAS DE VALIDADE, nao
> utilizacoes. Um gate que so compare Msd/MRd devolve OK=True com `delta = 0,95`
> (secao que a norma manda dimensionar como aco puro) ou com `eta_i = 0,30` (que a
> norma proibe tratar como mista). Tem de reprovar por FAIXA, nao por razao.

### 4.4 Vibracao de piso (NBR 8800 item 11.4 / Anexo L) — nao existe
- **Em nenhum caso `f_n < 3 Hz`** (L.1.2).
- Caminhada regular (residencias e escritorios, L.3.2): `f_n >= 4 Hz`, condicao
  considerada atendida se o deslocamento vertical total na combinacao FREQUENTE de
  servico `<= 20 mm`.
- Atividades ritmicas (L.3.3): `f_n >= 6 Hz` (flecha `<= 9 mm`); ginastica aerobica /
  atividade altamente repetitiva `f_n >= 8 Hz` (flecha `<= 5 mm`).
- Avaliacao precisa: aceleracao de pico com amortecimento modal, referencia do
  Anexo S.4 (AISC/CISC Design Guide 11).
Cruza com a Tab 13.3 do concreto (L/350 para vibracao sentida no piso) — a laje de
concreto tem o criterio analogo e tambem nao esta implementado (2.6).

### 4.5 Deslocamento horizontal entre pavimentos
O codigo so conhece o drift do galpao a `H/300` (`galpao_portico.py:734`,
`redimensionamento.py:157`). Multipavimento exige o limite **entre pavimentos
adjacentes** da Tabela C.1 da NBR 8800, alem do topo do edificio. Complementarmente a
NBR 15575-2 impoe **topo do edificio <= min(H_total/500 ; 3 cm)** (ver secao 5).

---

## 5. DESEMPENHO NBR 15575 — zero ocorrencias no codigo

`grep -rn "15575" framework/ tools/` nao retorna nenhuma linha de codigo do projeto
(so ruido de digitos dentro do `.venv`). Para edificacao habitacional a 15575 e
exigivel e traz limites MAIS RESTRITIVOS que a 6118/8800 — ou seja, hoje um projeto
habitacional passaria nos gates atuais e reprovaria na 15575.

**15575-2 (sistemas estruturais)**: fissura `<= 0,6 mm` em qualquer situacao;
deslocamento horizontal no topo `<= min(H_total/500 ; 3 cm)`;
Tabela 1 (visual `L/250` ou `H/300`; caixilhos/instalacoes/acabamentos rigidos
`L/800`; divisorias leves e acabamentos flexiveis `L/600`; vedacoes rigidas sob
temperatura/vento/recalque `L/500` ou `H/500`; flexiveis `L/400` ou `H/400`);
Tabela 2 (flechas por tipo de vedacao, com colunas separadas para `Sgk`, `Sqk`,
`Sgk+0,7Sqk` imediata e final — ex.: alvenaria com aberturas
`L/1000 / L/2800 / L/800 / L/400`; alvenaria sem aberturas
`L/750 / L/2100 / L/600 / L/340`; piso rigido `L/700 / L/1500 / L/530 / L/320`;
laje de cobertura impermeabilizada com `i>=2%` `L/850 / L/1400 / L/600 / L/320`).
Para balancos, multiplicar os limites por **1,5**; na flecha final, reduzir a rigidez
a flexao **pela metade**.
Impacto de corpo mole (percussor de 40 kg) e corpo duro, com os patamares em J
(960/720/480/360/240/180/120 J conforme face e acesso publico; 20 J e 3,75 J para
corpo duro externo, 10 J e 2,5 J internos) e os criterios `d_h <= h/250` e
`d_hr <= h/1250` (pilares) / `d_h <= L/200` e `d_hr <= L/1000` (vigas).
VUP minima: estrutura principal `>= 50 anos`; fachadas `>= 40`; vedacoes internas
`>= 20`; cobertura `>= 20`; hidrossanitario `>= 20`; pisos internos `>= 13`.

**15575-4 (vedacoes verticais)**: pecas suspensas por mao-francesa padrao (2 pontos a
50 cm, braco de 30 cm): `0,4 kN` por ponto / `0,8 kN` total, com `d_h <= h/500` e
`d_hr <= h/2500`, carga aplicada em patamares de 50 N a cada 3 min e mantida por 24 h;
cantoneira "L" com coeficiente de seguranca 3; rede de dormir `2 kN` a 60 graus com
coeficiente 2. Vento em fachada: `Sd = 0,9Sgk + 0,8Swk`, com `d_h <= h/500` (parede
com funcao estrutural) ou `h/350` (parede de vedacao; o dobro para parede leve
`G <= 60 kgf/m2`). Descolamento de revestimento de fachada `<= 0,10 m2` individual e
`<= 5%` do pano.

**15575-3 (pisos)**: carga concentrada de `1 kN` no ponto mais desfavoravel sem
ruptura ou dano, com `d_v <= L/500` (rigido) / `L/300` (ductil).

---

## 6. Ordem sugerida para G2 (por dependencia, nao por tamanho)

1. **`cargas_nbr6120.py`** — Tabelas 1/2/3/10/11/12/19. Nao depende de nada e todo o
   resto consome. Fecha tambem o "A CONFIRMAR" de `plataforma.py:87` e da fonte ao
   `fechamento.peso` que hoje o usuario chuta.
2. **`laje_concreto.py`** — 13.2.4, 19.3.3/20.1, 19.4.1, ELS Tab 13.3
   (reusando `viga_baldrame._flecha_alvenaria`).
3. **`puncao_nbr6118.py`** — extrair o nucleo ja existente em `fundacao_sapata`
   (`:737` K, `:793` tau_Rd1, `:899` tau_Rd2) para um modulo compartilhado e
   acrescentar borda/canto, `tau_Rd3`, C'', aberturas, 19.5.3.5 e colapso progressivo.
   **Reuso por primitivas, uma so implementacao** (licao da Fase 6B).
4. **Multipavimento**: generalizar `estabilidade_b1b2` para `B2` por pavimento e
   destravar o `n_andares` fixo em `galpao_concreto.py:148`.
5. **`vibracao_piso.py`** (Anexo L) e **`desempenho_nbr15575.py`** — ambos sao gates
   de ELS que so fazem sentido depois que a laje existir.
6. **Alvenaria estrutural**: bloqueado por fonte. Decisao do usuario (secao 3).

## 7. Tecnicas de caca a aplicar quando G2 for codado

- **Renderizar-e-olhar**: a planta de formas e o detalhamento da laje tem de ser
  ABERTOS (PNG/PDF). A barra verde nao cobre o artefato final — foi assim que
  apareceram o quadro de materiais sumindo em silencio e o SVG XML-malformado.
- **Rotulo x geometria**: conferir o peso tabelado da 6120 (kN/m2 de parede JA com
  revestimento) contra como `projeto_spec.py:697` usa `peso*h`.
- **Saturacao silenciosa**: os candidatos ja identificados sao 19.5.3.5, 19.5.4, o
  `eta_i` minimo da viga mista e a faixa `0,2 < delta < 0,9` do pilar misto — todos
  requisitos que nao aparecem como razao solicitante/resistente e por isso "passam"
  calados.
