# REVISAO — G11: vibracao de piso (NBR 8800 Anexo L) e desempenho NBR 15575

Fecha os dois ultimos itens abertos da auditoria de gaps do G2
(`REVISAO-GAPS-G2-LAJE-ALVENARIA-MULTIPAV.md`, secoes 4.4 e 5), que o
`edificio_adapter` publicava como `not_available` desde entao.

---

## 0. A primeira pergunta era de ACERVO, nao de engenharia

O enunciado do G11 dizia: conferir se a 15575 esta no acervo antes de
implementar; se nao estiver, e' bloqueio de fonte como a alvenaria estrutural.

**Nao ha bloqueio.** Conferido fonte a fonte no NotebookLM:

| Fonte | Notebook | Situacao |
|---|---|---|
| NBR 15575-1:2025 (setima edicao, 05.12.2025) | `0f83b41b` | presente |
| NBR 15575-2:2013 (sistemas estruturais) | `0f83b41b` | presente |
| NBR 15575-3:2021 (sistemas de pisos) | `0f83b41b` | presente |
| NBR 15575-4:2013 EM2:2021 (vedacoes) | `0f83b41b` | presente |
| NBR 15575-5:2021 / 15575-6:2021 | `0f83b41b` | presentes |
| NBR 8800:2008 (11.4 + Anexos L e S.4) | `cad0c145` | presente |

O contraste com a alvenaria estrutural e' nitido: la a NBR 16868 **nao existe**
nas fontes, e nenhuma quantidade de trabalho supre isso. Aqui as seis partes da
15575 estao no acervo, entao G11 e' trabalho tecnico e foi executado.

**O que continua fora, e por fonte:** as referencias do **S.4** da NBR 8800
(Murray/Allen/Ungar AISC DG11, Wyatt SCI P076, CEB 209, NBCC, ATC DG1), que sao
os procedimentos da avaliacao PRECISA de L.2. Nenhuma esta no acervo — e por
isso o modulo nunca calcula aceleracao de pico nem estima frequencia natural.

---

## 1. O que a norma da, e o que ela NAO da

Tudo abaixo foi transcrito LITERALMENTE da fonte antes de qualquer linha de
codigo (precedente "AR300": valor lembrado de cabeca cristaliza erro em teste).

### NBR 8800:2008, 11.4 e Anexo L

- **L.1.2** — "Em nenhum caso a frequencia natural da estrutura do piso pode ser
  inferior a **3 Hz**." Piso absoluto, vale para toda classe.
- **L.3.2** — caminhada regular (residencias, escritorios): `f_n >= 4 Hz`.
  Satisfeita se o deslocamento vertical **total** do piso, causado pelas acoes
  permanentes **excluindo a parcela dependente do tempo** e pelas acoes
  variaveis, calculado **considerando-se as vigas como BIAPOIADAS** e com as
  combinacoes **frequentes** de servico (4.7.7.3.3), nao superar **20 mm**.
- **L.3.3** — saltos/danca ritmica: `f_n >= 6 Hz` (**9 mm**); aumentada para
  `8 Hz` (**5 mm**) se muito repetitiva, como ginastica aerobica.
- **L.3.1** — "A opcao por esse tipo de avaliacao fica a criterio do projetista e
  **pode nao constituir uma solucao adequada para o problema**."
- **psi_1 da Tabela 2**: 0,4 (linha 1, nota b: residenciais de acesso restrito);
  0,6 (linha 2, nota c: **comerciais, de escritorios** e de acesso publico);
  0,7 (linha 3: bibliotecas, arquivos, depositos, oficinas e garagens).

> **A NORMA NAO DA FORMULA PARA `f_n`.** Nao existe no Anexo L expressao do tipo
> `f = k/raiz(delta)`, nem tabela de amortecimento — checado explicitamente na
> fonte. A via simplificada e' uma **dispensa** de calculo dinamico, nao uma
> estimativa dele. Por isso `vibracao_piso` **nunca estima f_n**: ou o
> projetista DECLARA o `f_n` que saiu da sua analise dinamica, ou a verificacao
> e' a do deslocamento. Inventar a formula seria inventar o dado que decide o
> gate.

### NBR 15575

- **15575-2:2013 7.3.1** — Tabela 1 (deslocamentos-limites) e Tabela 2 (flechas
  maximas), transcritas INTEIRAS em `desempenho_nbr15575.py`; fissura
  `<= 0,6 mm` **em qualquer situacao**; topo do edificio
  `<= min(H_total/500 ; 3 cm)` **para qualquer tipo de solicitacao**.
- **Notas da Tabela 2**: (a) balancos admitem **1,5 vez** os valores;
  (b) com detalhes que absorvam as tensoes no contorno das aberturas a parede
  pode ser considerada "sem aberturas"; (c) na flecha final, **reduzir a rigidez
  pela metade**.
- **15575-3:2021 7.5.1** — carga concentrada de **1 kN** no ponto mais
  desfavoravel, `d_v <= L/500` (rigido) ou `L/300` (ductil). A parte 3 **nao tem
  criterio proprio de carga distribuida** (remete a parte 2) e **nao trata de
  vibracao** — o conforto vibratorio e' do Anexo L da 8800.
- **15575-4:2013 7.2.1** — fachada sob `Sd = 0,9 Sgk + 0,8 Swk`;
  `d_h <= h/500` e `d_hr <= h/2500` (funcao estrutural); `d_h <= h/350` e
  `d_hr <= h/1750` (vedacao); parede leve (`G <= 60 kgf/m2`) sem funcao
  estrutural pode dobrar **so o `d_h`**.
- **15575-1:2025 nao revogou nada disso**: o item 9.2.1-c remete de volta as
  partes 2 a 6.

---

## 2. Correcoes a auditoria do G2

A auditoria pre-G2 levantou os gaps corretamente, mas duas de suas anotacoes nao
sobreviveram a leitura literal da fonte:

1. **"Deslocamento horizontal entre pavimentos" da 15575.** A secao 4.5 da
   auditoria sugeria que a 15575-2 impunha um limite entre pavimentos
   adjacentes. **Nao impoe.** A 15575-2 tem o teto do TOPO (nota a da Tabela 1)
   e distorcoes POR ELEMENTO (`H/500`, `H/400`); o limite entre pavimentos e' da
   Tabela C.1 da NBR 8800 e da Tabela 13.3 da NBR 6118 — que
   `estabilidade_edificio` ja implementa. Implementar como 15575 teria criado
   uma exigencia normativa inexistente.

2. **Tabela 2 listada pela metade.** A auditoria citou 4 linhas; a tabela tem
   **10**. Faltavam as paredes em paineis de juntas flexiveis
   (`L/1050 · L/1700 · L/730 · L/330` com aberturas; `L/850 · L/1400 · L/600 ·
   L/300` sem), os dois forros e a viga calha. Um modulo escrito a partir do
   resumo teria classificado gesso acartonado como parede rigida e usado
   `L/750` no lugar de `L/850`.

Uma terceira anotacao ficou mais precisa: a auditoria dizia "deslocamento
vertical total na combinacao frequente <= 20 mm", omitindo **"considerando-se as
vigas como biapoiadas"**. Essa clausula e' o coracao do criterio (ver 3.1).

---

## 3. As armadilhas que os modulos existem para nao cair

### 3.1 Viga BIAPOIADA — a maior delas

L.3.2/L.3.3 mandam calcular a viga como **biapoiada ainda que ela seja
continua**. O framework ja tinha, aferida e a mao, a flecha da viga continua
(`viga_baldrame._flecha_alvenaria` com `continua=True`, coeficiente `2,6/384`).
Reaproveita-la aqui seria a coisa obvia a fazer — e daria **menos da metade** do
deslocamento correto:

- so pelos coeficientes de flecha, `5/384 ÷ 2,6/384 = 1,92`;
- na pratica a razao e' **maior** (medida: **2,26** na fixture), porque o momento
  de servico tambem muda (`1/8` contra `1/10`), a biapoiada fissura mais e o
  `I_eq` de Branson cai.

Um piso com 18 mm reais sairia com 8 mm e passaria calado nos 20 mm. Ha um
teste-guarda dedicado (`test_viga_entra_biapoiada_e_nao_continua`).

**A laje nao muda de vinculacao.** A norma diz "vigas", nao "lajes"; um painel
engastado continua engastado. Ha teste para isso tambem.

### 3.2 Parcela dependente do tempo

O deslocamento do Anexo L e' o **imediato**. Todo o resto do framework calcula a
flecha DIFERIDA (`x (1+alpha_f)`) para a Tabela 13.3 da NBR 6118. Sao dois ELS
distintos que convivem: usar a diferida aqui reprovaria pisos que atendem, e
trocar o criterio de 13.3 por este reprovaria o inverso.

### 3.3 Classificacao sem default (saturacao silenciosa)

`CLASSE_POR_USO` mapeia as chaves da Tabela 10 da NBR 6120 e **nao tem
fallback**. Um uso fora do mapa sai `nao_classificado` e o gate **reprova**.
Motivo: classificar um ginasio como "caminhada" troca **9 mm por 20 mm** em
silencio — a forma exata da saturacao silenciosa que este framework persegue.
Cobertura e forro saem `nao_aplicavel` **nomeado**, que e' diferente de passar.

Armadilha correlata ja embutida: **escritorio cai na linha 2 da Tabela 2**
(`psi_1 = 0,6`), nao na linha 1. A nota c e' explicita — "comerciais, **de
escritorios** e de acesso publico" — e quase todo mundo usa 0,4.

### 3.4 Reuso que devolve secao bruta em silencio

`_flecha_alvenaria` faz `I_eq = I_c` quando `As <= 0` (`viga_baldrame.py:81`).
Chamada sem armadura, ela devolve a flecha de **secao bruta** sem reclamar — que
subestima assim que a viga fissura. `flecha_viga_biapoiada` detecta o caso
(`Ma > Mr` e `As` ausente), marca `avaliavel=False` e o gate **nao pode** dar o
piso por atendido. Piso conservador para dado ausente.

Na cadeia do edificio isso nao chega a acontecer: `edificio_multipavimento`
dimensiona o tramo critico com `viga_concreto.verifica_viga` e passa a
**armadura real**.

### 3.5 Duas convencoes de flecha final que nao se somam

A 15575 obtem a flecha final **reduzindo a rigidez pela metade** (nota c); a NBR
6118 a obtem por fluencia (`x (1+alpha_f)`, 17.3.2.1.2). Encadear as duas conta
o efeito diferido **duas vezes**; usar a da 6118 achando que atende a 15575
**subestima**. `des.flecha_final()` implementa a convencao da 15575 e diz isso no
nome, com teste que trava a diferenca.

Correlato: a Tabela 2 tem **combinacao propria** (`Sgk + 0,7 Sqk`, coeficiente
fixo da propria tabela — nao e' o `psi_1` da 6118 nem o da 8800). A cadeia
**recalcula** a flecha nessa combinacao em vez de reaproveitar a
quase-permanente que a laje ja tinha: comparar a flecha de uma combinacao com o
limite de outra e' erro que nenhuma barra verde pega.

### 3.6 Aprovar por vacuidade

`desempenho_nbr15575.verifica` distingue tres coisas que costumam virar uma so:

| campo | significado |
|---|---|
| `OK` | nenhum limite foi excedido |
| `completo` | nada ficou por verificar |
| `nada_verificado` | o cfg nao permitiu verificar coisa alguma |

Um gate do qual **nada** foi verificado devolve `OK=False`. E `nao_verificados`
viaja no gate, no manifesto do adaptador e no relatorio — a 15575 exige mais do
que este framework calcula, e o que nao foi verificado tem de aparecer.

### 3.7 A ressalva de L.3.1 acompanha o resultado

Atender 20/9/5 mm **nao e' certificado de conforto**: a propria norma diz que a
via simplificada "pode nao constituir uma solucao adequada". Todo resultado pela
via simplificada carrega esse aviso, e o adaptador o publica como
`vibracao_avaliacao_simplificada` no manifesto.

---

## 4. O que foi entregue

**Modulos novos**

- `vibracao_piso.py` — NBR 8800 11.4 e Anexo L: classes, `psi_1` da Tabela 2,
  mapa uso→classe sem default, deslocamento da combinacao frequente com a viga
  biapoiada, verificacao por `f_n` quando declarada.
- `desempenho_nbr15575.py` — Tabelas 1 e 2 da parte 2 completas, notas a/b/c,
  topo, fissura de 0,6 mm, carga concentrada de 1 kN da parte 3, fachada da
  parte 4, e orquestrador com `OK`/`completo`/`nada_verificado`.

**Ligacoes**

- `pavimento_tipo._resolve_linha` passa a publicar `g_tramos`, `q_tramos`, `b` e
  `h` por linha de viga. A analise devolvia esforcos; sem o carregamento por
  tramo nao havia como montar nenhuma combinacao de servico por fora dela.
- `edificio_multipavimento.rodar` encadeia os dois: escolhe a viga critica por
  `w_freq · L^4` (nao pelo maior vao — com parede so nas linhas de contorno a
  que mais flecha pode ter vao MENOR), dimensiona esse tramo para obter a
  armadura real, e alimenta os gates `vibracao_piso` e `desempenho_15575`.
  `habitacional` e' deduzido das chaves da Tabela 10 da NBR 6120 (dado
  declarado, nao arbitrado) e pode ser sobreposto no spec.
- `edificio_adapter` — `vibracao_piso` sai de `ESCOPO_NAO_COBERTO` e vira
  `implemented`, junto com `desempenho_15575`. Entram no lugar, como
  `not_available` nomeados, os requisitos que a 15575 verifica por **ENSAIO**:
  `desempenho_15575_impacto_corpo_mole_duro`,
  `desempenho_15575_carga_concentrada_piso` e `desempenho_15575_fachada`.

**Testes** — 51 novos: `tests/test_vibracao_piso.py` (18),
`tests/test_desempenho_nbr15575.py` (19) e
`tests/branches/edificio/test_g11_vibracao_desempenho.py` (14).

---

## 5. O que continua aberto

| Item | Por que |
|---|---|
| Avaliacao precisa de L.2 (aceleracao de pico, amortecimento modal) | **bloqueio de fonte**: as referencias do S.4 (AISC DG11, SCI P076, CEB 209, NBCC, ATC DG1) nao estao no acervo |
| Impacto de corpo mole e corpo duro (15575-2 7.4) | verificacao por **ensaio** em prototipo/obra (Anexos A e B), nao por calculo |
| Carga concentrada de 1 kN (15575-3 7.5.1) | o modulo verifica o criterio; falta a flecha de carga PONTUAL no painel, que nenhum modulo do framework calcula hoje |
| Deslocamento residual de fachada `d_hr` (15575-4) | vem de **ensaio**; sem ele `verifica_fachada` recusa dar a fachada por atendida |
| VUP, desempenho termico, acustico e luminico (15575-1) | fora do escopo estrutural; nao foram tocados |
| Alvenaria estrutural | segue **bloqueada por fonte** (NBR 16868 ausente) |
