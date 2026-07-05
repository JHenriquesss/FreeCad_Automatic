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
- PERGUNTA B1: as tres combinacoes adotadas estao adequadas?
  C1 = 1,25G + 1,50Q + 0,84W ; C2 = 1,00G + 1,40W (uplift, Q omitida) ;
  C3 = 1,00G + 1,40W + 1,20Q. Confirmar quais governam e se falta alguma.

## C. NBR 6123 - vento - PENDENTE CONFIRMACAO (nao tenho a norma)

O modulo atual usa valores SIMPLIFICADOS. O exemplo CBCA mostra o metodo completo
(zonas, duas direcoes). Preciso confirmar:

- PERGUNTA C1 (Classe): maior dimensao do galpao = 20 m. Classe A (<=20 m) ou
  B (20-50 m)? (o exemplo CBCA e Classe C, edificio grande). Qual para 20 m?
- PERGUNTA C2 (S3): usei S3 = 1,00. O exemplo CBCA usa S3 = 0,95 para "galpao
  para deposito com baixo fator de ocupacao". Adotar 0,95?
- PERGUNTA C3 (S2 com altura): o exemplo calcula S2 (e q) VARIANDO com a altura
  (3 m e cumeeira). Eu uso um unico q no topo (conservador). Manter conservador
  ou variar q com a altura nas paredes?
- PERGUNTA C4 (Cpe paredes, Tabela 4): usei valores unicos +0,70 (barlavento)
  e -0,40 (sotavento). A norma da valores por ZONA (A1,B1,C1,D1) e um Cpe medio,
  em funcao de h/b e a/b. Para h=6, b=10, a=20: quais os Cpe de parede?
- PERGUNTA C5 (Cpe telhado, Tabela 5): ATENCAO - nosso telhado e 10% = 5,71 graus
  (o exemplo CBCA e 10 GRAUS, diferente). Quais os Cpe de cobertura (duas aguas,
  ~5,7 graus) para vento a 0 e a 90 graus? Usei -0,80/-0,40 (chute).
- PERGUNTA C6 (Cpi, item 6.2 / Anexo D): usei +0,30/-0,30. O exemplo CBCA (sem
  abertura dominante) usa +0,20/-0,30. MAS nosso galpao TEM PORTAO grande no
  oitao (abertura dominante) -> pode exigir Anexo D, com Cpi ate +0,7 ou mais.
  Qual Cpi adotar considerando o portao?
- PERGUNTA C7 (direcoes): o exemplo usa 4 casos (vento a 0 e a 90 graus x Cpi
  +0,2/-0,3). Eu so analisei o vento transversal (uma direcao). Precisamos das
  duas direcoes para o portico? (a 90 graus atua mais nos oitoes/contravento).

## D. Cargas permanentes/variaveis - conferir valores

- PERGUNTA D1: permanente da cobertura adotei 0,27 kN/m2 (telha+tercas+suspensas)
  + peso proprio da viga 0,35 kN/m. Os pesos reais (NBR 6120 / catalogo) batem?
- PERGUNTA D2: cargas suspensas - adotei 0,15 kN/m2 provisorio. Valor real?

## E. Analise - premissa

- PERGUNTA E1: analise e de 1a ordem, base rotulada. Confirmar necessidade de
  2a ordem / classificacao de deslocabilidade (o deslocamento deu 170 mm >>
  H/300 = 20 mm, entao a rigidez/base tera que mudar de qualquer forma).

## Resultado atual (com as pendencias acima)

- q (topo) = 0,872 kN/m2 ; momento governante coluna ~85 kN.m (C2).
- Deslocamento lateral 170 mm >> 20 mm -> NAO ATENDE (portico muito flexivel).
- Nada aqui e definitivo ate as perguntas C1-C7 serem confirmadas na NBR 6123.
