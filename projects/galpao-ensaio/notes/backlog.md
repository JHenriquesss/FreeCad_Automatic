# Backlog - modulos a construir depois de validar a skill

## MODULO DE PONTE ROLANTE (crane) - prioridade alta

Lacuna detectada no ensaio (Gate 0): a skill descreve a geometria da ponte
(consoles, viga de rolamento, batentes, viga de surto) mas NAO ha modulo que
calcule os esforcos. Necessario para galpoes com ponte (comum em industrial).

Escopo do modulo:
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

## PENDENTE - pecas secundarias (usar Fa do vento longitudinal, ja pronto)
- MONTANTE DE OITAO (HEA160): flexao sob Cpe da empena (barlavento +0,70) - vira
  viga-coluna, reusa check_nbr8800. Falta.
- CONTRAVENTAMENTO (barras d20 so-tracao) + TIRANTES (d16): forca do arrasto
  (Fa/lado) -> tracao + esbeltez + forca minima de travamento (regra 2%). Falta.
- VERGA da porta: flexao local do vao da abertura. Falta (rapido).

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
