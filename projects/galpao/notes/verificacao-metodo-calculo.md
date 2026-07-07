# Verificacao do Metodo de Calculo - Perguntas para conferir na norma

Objetivo: garantir ZERO erro de metodo. Cada item lista o que o script faz, a
fonte, e o status. Itens NBR 6123 precisam de confirmacao (nao tenho a norma
aqui). Itens NBR 8800 foram conferidos no PDF da norma.

## STATUS GERAL (toolkit de calculo) - 10/10 MODULOS APROVADOS PELO SENIOR

Todos com formulas extraidas dos PDFs das normas, self-test, saidas em PT e
markdown (codigo + resultado) em notes/scripts-md/:
- frame2d (rigidez direta) ; vento_nbr6123 (NBR 6123) ; galpao_portico ;
  estabilidade_b1b2 (NBR 8800 Anexo D, MAES) ; check_nbr8800 (Anexos F/G) ;
  tercas_nbr14762 (NBR 14762 + Anexo F) ; base_chumbador (6.3/6.6 + AISC DG1) ;
  ligacoes (6.2/6.3/6.1.5) ; perfis (biblioteca) ; redimensionamento (driver).
Limitacoes conhecidas (documentadas, delegadas a entrada/software externo):
- terca: Mdist distorcional (quando nao dispensa Tab.14) -> falta FSM/CUFSM;
  Ief e Wef,y rigorosos -> entrada de catalogo.
- base: cone de arrancamento do concreto (NBR 6118/ACI) -> projeto de fundacao.
- ligacoes: block shear / flexao da chapa alem do esmagamento.
Proximo: integrar na skill (a skill pergunta tudo ao usuario e chama os modulos).

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

- RESOLVIDO E1 (2a ordem) - COMPLETO: modulo estabilidade_b1b2.py (MAES, NBR
  8800 Anexo D), validado pelo eng. senior. Decomposicao nt/lt com contencoes
  ficticias nos beirais. B2,max integral = 1,177 -> MEDIA deslocabilidade.
  Rigidez reduzida a 80% aplicada (4.9.7.1.2): B2 final = 1,231. Forca nocional
  0,3% incluida (4.9.7.1.1). Esforcos finais: coluna Msd=129,3/Nsd=52,3 ;
  viga Msd=129,1/Nsd=5,9 kN.
- RESOLVIDO E3 (check com 2a ordem): check_nbr8800 agora consome os esforcos
  amplificados e usa K=1 (4.9.6.2). Veredito ELU do perfil ATUAL:
  coluna HEA200 interacao 1,35 (M/Mrd=1,33) NAO PASSA ; viga HEA180 interacao
  1,75 (M/Mrd=1,75) NAO PASSA. Falha por FLEXAO (Msd~129 >> Mrd 97,6/73,8).
  Proximo: redimensionar (perfil maior / engaste na base / mao-francesa).
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
