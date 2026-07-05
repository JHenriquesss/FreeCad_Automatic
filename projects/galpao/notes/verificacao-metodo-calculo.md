# Verificacao do Metodo de Calculo - Perguntas para conferir na norma

Objetivo: garantir ZERO erro de metodo. Cada item lista o que o script faz, a
fonte, e o status. Itens NBR 6123 precisam de confirmacao (nao tenho a norma
aqui). Itens NBR 8800 foram conferidos no PDF da norma.

Referencia de apoio: exemplo resolvido do Manual CBCA "Galpoes para Usos Gerais"
(Cap. 2), que segue NBR 6123/88 e NBR 8800/2008.

## A. Solver de portico (frame2d) - OK

- Metodo da rigidez direta, elemento viga-coluna 2D. Validado contra solucao
  fechada: cantilever (PL^3/3EI e M=PL) e viga biapoiada (M=wL^2/8), exatos.
- STATUS: verificado.

## B. NBR 8800 - combinacoes - CONFERIDO no PDF (corrigido)

- Coef. permanente (peso proprio metalico): gamma_g = 1,25 (desfav.) / 1,00
  (favor.) - Tabela 1. OK.
- Coef. variavel: vento gamma_q = 1,40 ; sobrecarga = 1,50 - Tabela 1. OK.
- Fatores psi0 (Tabela 2): sobrecarga em cobertura = 0,8 ; vento = 0,6.
  CORRIGIDO (antes usei 0,5 para a sobrecarga - ERRADO).
- Sobrecarga minima em cobertura 0,25 kN/m2 (B.5.2). OK (usado).
- RESOLVIDO B1 (combinacoes): acao variavel FAVORAVEL entra com gamma=0. Nas
  combinacoes de uplift com G favoravel (gamma_g=1,00), a sobrecarga Q atua para
  baixo e RESISTE ao levantamento -> favoravel -> Q=0. Corrigido C3_vento_Gfav
  (antes somava 1,20Q, mascarando a tracao) e mantido C2_uplift sem Q. Erro
  apontado pelo engenheiro senior.
  Combinacoes: C1 = 1,25G + 1,50Q + 0,84W ; C2 = 1,00G + 1,40W (uplift, Q=0) ;
  C3g_desf = 1,25G + 1,40W + 1,20Q ; C3g_fav = 1,00G + 1,40W (Q=0).

## C. NBR 6123 - vento - CORRIGIDO com as tabelas reais (norma lida)

Valores agora extraidos direto da NBR 6123 (Tabelas 4, 5 e item 6.2.5-c):

- RESOLVIDO C4 (Cpe paredes, Tabela 4, h/b=0,6, a/b=2, alpha=90): barlavento
  (A) = +0,70 ; sotavento (B) = -0,60. (antes -0,40, ERRADO)
- RESOLVIDO C5 (Cpe telhado, Tabela 5, bloco 1/2<h/b<=3/2, theta=5,71 interp.
  5-10 graus): CORRIGIDO PARA alpha=90 (colunas EF/GH, MESMA incidencia das
  paredes) -> barlavento (EF) = -0,93 ; sotavento (GH) = -0,60. Antes eu havia
  lido as colunas EG/FH que sao de alpha=0 (vento LONGITUDINAL) - erro apontado
  pelo engenheiro senior: nao se pode misturar vento a 90 nas paredes com vento
  a 0 no telhado. Conferido na imagem da Tabela 5 da NBR 6123 (pagina 15).
- RESOLVIDO C6 (Cpi, item 6.2.5-c, PORTAO abertura dominante): portao a
  barlavento Cpi = +0,80 (conservador, razao >=6) ; portao a sotavento Cpi =
  -0,60 (= Cpe da face). (antes +/-0,30, subestimava muito o uplift)
- RESOLVIDO C2 (S3): adotado 0,95 (galpao deposito, conforme exemplo CBCA).

Ainda a confirmar pelo engenheiro:

- PERGUNTA C1 (Classe): maior dimensao = 20 m. Adotei Classe B (20-50 m). Como
  20 m e o limite A/B, confirmar se e Classe A ou B (muda pouco o S2).
- PERGUNTA C3 (S2 com altura): uso um unico q no topo (conservador). Variar q
  com a altura nas paredes (mais refinado) ou manter conservador?
- PERGUNTA C6b (razao de areas do portao): adotei Cpi = +0,80 (razao >=6,
  conservador). Calcular a razao real (area do portao / demais aberturas sob
  succao) pela Tabela de 6.2.5-c e refinar (+0,1 a +0,8).
- PERGUNTA C7 (direcoes): so analisei o vento transversal (perpendicular a
  cumeeira). Falta o vento a 90 graus (longitudinal, no oitao do portao) para
  os contraventamentos e oitoes. Rodar tambem?
- PERGUNTA C-map (mapeamento): confirmar que o vento transversal corresponde a
  Tabela 4 alpha=90 (paredes longas A/B) e Tabela 5 alpha=0 (aguas EG/FH).

## D. Cargas permanentes/variaveis - conferir valores

- PERGUNTA D1: permanente da cobertura adotei 0,27 kN/m2 (telha+tercas+suspensas)
  + peso proprio da viga 0,35 kN/m. Os pesos reais (NBR 6120 / catalogo) batem?
- PERGUNTA D2: cargas suspensas - adotei 0,15 kN/m2 provisorio. Valor real?

## E. Analise - premissa

- RESOLVIDO E1 (2a ordem): criado o modulo estabilidade_b1b2.py (MAES, NBR 8800
  Anexo D). Decomposicao nt/lt com contencoes ficticias nos beirais. B2,max =
  1,177 (C2 uplift) -> MEDIA deslocabilidade (1,1 < B2 <= 1,4). Esforcos
  amplificados: coluna Msd=124,1 / Nsd=51,5 ; viga Msd=123,9 / Nsd=4,1 kN.
  B1 ~ 1,0-1,03 (barras pouco esbeltas no plano). Nota: em MEDIA deslocabilidade
  a norma pede recalcular B1/B2 com EI e EA reduzidos a 80% (a fazer). O check
  de perfil deve passar a usar K=1 (4.9.6.2) com estes esforcos amplificados.
- RESOLVIDO E2 (limite de flecha lateral ELS): H/300 e para porticos que
  suportam ALVENARIA. Para galpao com TELHA METALICA (sem elementos frageis)
  admite-se H/200 ou H/150 (Bellei; NBR 8800 Anexo C, nota). O script agora
  mostra a escada de limites (H/300..H/150). Mesmo com H/150 = 40 mm, os 179 mm
  NAO ATENDEM -> confirma que a estrutura precisa ser enrijecida (engaste na
  base e/ou perfil maior e/ou mao-francesa no joelho). Ponto do eng. senior.

## Resultado atual (com as pendencias acima)

- q (topo) = 0,872 kN/m2 ; momento governante coluna ~85 kN.m (C2).
- Deslocamento lateral 170 mm >> 20 mm -> NAO ATENDE (portico muito flexivel).
- Nada aqui e definitivo ate as perguntas C1-C7 serem confirmadas na NBR 6123.
