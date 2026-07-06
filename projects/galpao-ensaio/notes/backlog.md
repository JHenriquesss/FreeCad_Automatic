# Backlog - modulos a construir depois de validar a skill

## MODULO DE PONTE ROLANTE (crane) - CONSTRUIDO 2026-07-05 (falta so integrar no portico)

FEITO: calc/ponte_rolante.py (fundamentado no livro Dimensionamento cap.4 +
NBR 8800/8400). Calcula cargas de roda (impacto phi), surto transversal, frenagem
longitudinal; verifica a viga de rolamento (momento maximo absoluto de 2 rodas,
flexao lateral, ELS L/600..L/1000, fadiga sinalizada) e EMPACOTA a reacao no
portico (R_vert, M_exc, H_transv, H_long). phi/fracoes = fabricante/NBR 8400,
FLAGADOS "A CONFIRMAR". Ref (ponte 100 kN): viga VS500 interacao 0,34 OK;
reacao R_vert=132,9 kN, M_exc=39,9 kN.m.

INTEGRADO NO PORTICO 2026-07-05: gp.configurar(ponte=...) injeta a reacao como
caso de carga (case_ponte: R_vert + M_exc no no do console + surto) e adiciona os
combos C4 (ponte principal: G+1,5*Ponte+1,4*0,6*Vento) e C5 (vento principal,
ponte psi0=0,7). Flui por 1a ordem, MAES 2a ordem (estabilidade_b1b2), check de
perfil, base e joelho. Tudo GUARDADO por PONTE=None -> galpao SEM ponte fica
byte-identico a referencia (0,67/0,93, B2 1,036). Orquestrador: params["ponte"]
liga; rodar_galpao.py --ponte roda o exemplo de 100 kN. Testes: ponte leve
(100 kN) nao governa (uplift 0,67 manda); ponte pesada (250 kN) governa (coluna
1,8 -> redimensionar). PENDENTE: re-revisao do senior (mexeu em gp + estabilidade
aprovados).

Escopo original do modulo:
- Cargas da ponte: capacidade Q, peso da ponte + carro, cargas por roda Rmax
  (ponte encostada num trilho, carro junto), n de rodas e espacamento.
- IMPACTO VERTICAL: coeficiente de impacto (~1,10 a 1,25 conforme a classe;
  siderurgica ~1,25). Confirmar na NBR 8800 / NBR 8400.
- FRENAGEM longitudinal (ao longo do trilho): fracao das cargas de roda.
- SURTO/forca LATERAL transversal: fracao de (carga icada + carro), dividida
  nos dois trilhos.
- VIGA DE ROLAMENTO: momento maximo por carga movel (teorema de Barre), flexao
  lateral do surto, flecha (limite ~L/600 a L/800 conforme capacidade), FADIGA
  (ponte pesada = muitos ciclos; NBR 8800 Anexo K).
- CONSOLE (misula) + reacao excentrica no pilar -> entra na analise do portico.
- Contraventamento de arrasto longitudinal (rigidez para a frenagem).

Fonte: extrair de NBR 8800 (impacto/fadiga), NBR 8400 (classes de ponte),
exemplo do Manual CBCA Galpoes. NAO codar de memoria (zero-erro).

## Outras lacunas conhecidas (ja documentadas)
- Cone de arrancamento do concreto (fundacao, NBR 6118) - base_chumbador flag.
- Block shear / flexao da chapa alem do esmagamento - ligacoes.

## Pecas secundarias - TODAS VERIFICADAS (2026-07-05)
- [OK] MONTANTE DE OITAO (HEA160): verifica_montante_oitao. Ref 0,43 OK.
- [OK] CONTRAVENTAMENTO + TIRANTES + MAO-FRANCESA (barras): contraventamento.py
  (tracao 5.2 + esbeltez + forca 2%). Ref u_max 0,66 OK.
- [OK] VERGA da porta (UPE100): reusa verifica_longarina. Ref 0,04 OK.
- Falta so refinar entradas "A CONFIRMAR": Ca (Figura 4), Nsd do tirante de
  cobertura (componente do peso na agua), props de catalogo.

## RESOLVIDO (2026-07-05)
- Mao-francesa deixou de ser heuristica: calc/mao_francesa.py deriva o passo por
  inversao da interacao 5.5.1.2 (Lb da viga), ligado ao build (MF_STRIDE) e ao
  check. Ref 20x10: 2 bracos/portico, Lb=3,35 m, interacao da viga 0,93.
- Secoes secundarias verificadas: secundarios_nbr8800 (longarina U biaxial Anexo
  G + escora I flexo-compressao). Achado: UPE100 exige 2 tirantes de parede
  (0,99); escora HEA160 OK.
- VENTO LONGITUDINAL (alpha=0) pronto em vento_nbr6123: Cpe da empena (Tab.4) +
  arrasto Fa=Ca*q*Ae (Ca da Figura 4, A CONFIRMAR). Ref: Fa=59 kN, 29,5 kN/lado.
  Ja alimenta o Nsd da escora (-> 0,07 OK). Falta consumir o Fa no oitao e no
  contraventamento (ver PENDENTE acima).
