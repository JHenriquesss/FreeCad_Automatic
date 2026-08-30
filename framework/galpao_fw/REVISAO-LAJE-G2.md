# G2 - Vertical de LAJE (NBR 6118): o que entrou, como foi aferido, o que ficou

Fecha o gap apontado em `REVISAO-GAPS-G2-LAJE-ALVENARIA-MULTIPAV.md` secao 2:
antes disto o framework nao tinha NENHUM dimensionamento de laje (so
`piso_industrial.py`, que e placa sobre solo - outro problema fisico).

## 1. Modulos

| Arquivo | Conteudo |
|---|---|
| `laje_concreto.py` | Laje macica: Tabela 13.2 (h minimo, gamma_n de balanco), esforcos por teoria das placas (tabelas de Bares, 9 casos de vinculacao, lambda 1,00 a 2,00) e por faixa unitaria acima de lambda 2, compatibilizacao dos momentos negativos, armadura de flexao (17.2.2) e minimos de laje (Tab 19.1), detalhamento 20.1, cortante de laje 19.4.1, ELS de flecha (Bares + Branson + fluencia 17.3.2.1.2) com os limites da Tab 13.3, ELS-W (reusa `fissuracao_nbr6118`), ancoragem (reusa `fundacao_sapata`), reacoes nas vigas (14.7.6.1), laje NERVURADA (13.2.4.2) e quadro de ferros |
| `puncao_nbr6118.py` | Puncao 19.5 para laje lisa: contornos C, C' e C'' construidos como poligonal (pilar interno, de borda e de canto), Wp por integracao, aberturas a menos de 8d (19.5.1), tau_Rd1/tau_Rd2/tau_Rd3, teto de fywd, s_r e 1a linha, 19.5.3.5 e colapso progressivo 19.5.4 |
| `desenho_concreto.py` | `planta_laje_svg` / `gerar_planta_laje`: planta de formas + armacao, quadro de ferros e resumo das verificacoes |

Reuso por primitiva (licao da Fase 6B): `fundacao_sapata` passou a CONSUMIR
`puncao_nbr6118` (K da Tab 19.2, tau_Rd1, tau_Rd2) em vez de ter copia propria, e
`desenho_concreto._esc` passou a delegar para `desenho_svg_base.esc`.

## 2. Afericao

**Exemplo resolvido**: Carvalho & Figueiredo Filho, *Calculo e Detalhamento de
Estruturas Usuais de Concreto Armado segundo a NBR 6118:2014*, 4a ed., EdUFSCar,
Cap.7, Exemplo 1 (p.358-368) - lajes L1/L2/L3. Batem, dentro da tolerancia
declarada em cada teste: os 4 coeficientes de cada laje, os 11 momentos, as 9
areas de aco do quadro da p.364, o Ecs de 21287 MPa, o alpha_f de 1,47 e as tres
flechas elasticas (0,19 / 0,06 / 0,22 cm). Os limites da Tab 13.3 reproduzem os
l/375 e l/525 que o livro usa (2/3 do limite, porque a viga tambem deforma).

**Reacoes nas vigas**: conferidas contra os Quadros 7.8/7.9 do mesmo livro
(q = k*p*lx/10) - k 2,50 na laje quadrada apoiada, 1,83/4,02/2,32 com uma borda
menor engastada. Descoberta: a charneira a 60 graus corresponde a k = tg(60) =
raiz(3) e nao ao 1,5 que se usa por aproximacao - com 1,5 os k dao 2,00/3,60/2,40
e nao fecham com a tabela.

**Tabelas de Bares** (quase mil numeros vindos de OCR): conferidas uma a uma
contra uma solucao INDEPENDENTE de placa de Kirchhoff por diferencas finitas
(`tests/test_laje_tabela_bares.py`, ~2 s). Achados corrigidos, todos marcados com
`[OCR]` no modulo junto com o valor lido: caso 1 mu_y em lambda 1,60 (lido
"3,14"), caso 2 mu_x na faixa 1,65-1,85, caso 4 mu_y em 1,45, caso 5 mu_y' em
1,80, caso 7 mu_x/mu_x' em 1,25 e o alpha do caso 8 entre 1,55 e 1,65.

**Puncao**: NAO ha exemplo resolvido no acervo - checado explicitamente (Carvalho
cap.7 so trata laje sobre vigas; o Vol.4 do Araujo esta digitalizado ate a p.168,
antes da secao 7.5; Botelho declara que nao trata laje lisa; Nilson/MacGregor
resolvem pelo ACI 318). O modulo tem as expressoes literais da norma, a geometria
conferida contra a formula fechada da propria norma e cross-check com a sapata,
mas **nao tem afericao contra exemplo de livro** - fica como item A CONFIRMAR do
acervo, declarado no cabecalho do modulo e no teste.

## 3. Gates de saturacao

O padrao recorrente do projeto (calculo satura no extremo da tabela, o gate nao
reprova e sai OK=True) tem gate proprio em cada ponto onde pode ocorrer:

1. **Tabela de placa acima de lambda 2** - devolver a linha de 2,00 SUBESTIMA o
   momento. Sem `forcar_bares`, o orquestrador troca de modelo (faixa unitaria,
   14.7.6.2); com `forcar_bares`, marca `saturou_tabela` e REPROVA.
2. **Malha esgotada** - se nem a maior bitola no menor espacamento cobre o As, a
   laje esta fina demais: `saturou_malha` e OK=False.
3. **Lista de espessuras esgotada** em `dimensiona_laje` - sai OK=False com
   aviso, nunca a ultima tentada dada como boa.
4. **fywd da armadura de puncao** cortado pelo teto de 300/250 MPa - avisa que o
   aco nao rende fyk/1,15.
5. **19.5.3.5 e 19.5.4** - requisitos que NAO aparecem como razao
   solicitante/resistente; sem gate proprio a ligacao passa sem armadura contra
   colapso progressivo. Ambos reprovam mesmo com tau_Sd <= tau_Rd1.

## 4. O que o "renderizar-e-olhar" e o "rotulo x geometria" pegaram

- **Wp saia 8% baixo**: a integral `|e| dl` calculada pelo ponto MEDIO de cada
  trecho zera os trechos que cruzam o eixo. Pego pela conferencia contra a
  formula fechada da norma; corrigido com integracao exata por trecho.
- **`fill-opacity` nao e honrado** pelo renderizador (o mesmo tipo usado pelo
  TechDraw/QtSvg): a faixa da armadura negativa virava um bloco vermelho solido
  que apagava a malha inteira. Visto ao ABRIR o PNG, nao na barra verde.
- **Armadura negativa contada pela metade**: a planta mostrava DUAS faixas em
  cada direcao no caso 9 (duas bordas engastadas = dois apoios distintos) e o
  quadro de ferros contava UM conjunto. Corrigido com `n_bordas`; a taxa de aco
  do caso 9 foi de 4,6 para 7,0 kg/m2.
- **Chamada N3 vazando do painel** quando a faixa de 0,25 lx e estreita.

## 5. Aberto

- **Puncao sem exemplo resolvido** no acervo (item 2). A geometria de borda/canto
  segue o TEXTO de 19.5.2.3/19.5.2.4; a Figura 19.3 nao existe em texto no
  acervo, e a posicao exata do corte do contorno reduzido fica A CONFIRMAR.
- **Caso 3 do Quadro 7.3**: a coluna mu_y da fonte fica ate ~20% ABAIXO do
  momento no centro obtido pela teoria de placas (e o mu_x tabelado e o maximo,
  nao o do centro). O desvio esta pinado em teste; na pratica e a direcao
  secundaria, onde a armadura minima governa.
- Integracao com o orquestrador (`galpao_concreto`/`galpao_turnkey`), BIM/IFC da
  laje e caderno executivo: nao entraram neste ciclo.
- Itens 1, 4, 5 e 6 da ordem sugerida no documento de gaps (`cargas_nbr6120`,
  multipavimento, vibracao de piso/15575, alvenaria estrutural) continuam abertos.
