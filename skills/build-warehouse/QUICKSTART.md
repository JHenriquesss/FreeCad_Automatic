# Quickstart — rodar a skill do zero (checklist do operador)

Roteiro para conduzir um projeto de galpão do zero (ex.: demonstracao com o
engenheiro senior). A skill pergunta tudo em etapas; este checklist evita
travas de ambiente e mostra o que esperar.

## 0. Pre-voo (ambiente) — 1 minuto

- [ ] **numpy < 2** no venv (`python -c "import numpy;print(numpy.__version__)"` ->
  1.26.x). Necessario para o `distorcional_fsm` (pycufsm). Se estiver em numpy 2:
  `pip install "numpy<2"`. Os demais modulos rodam em qualquer numpy.
- [ ] **pycufsm** importa (`python -c "import pycufsm"`).
- [ ] **FreeCAD aberto** com a ponte MCP ativa. Teste:
  `python -c "import xmlrpc.client;print(xmlrpc.client.ServerProxy('http://127.0.0.1:9875/',allow_none=True).ping())"`
  -> `{'pong': True, ...}`. Se falhar, reinicie o FreeCAD (a ponte sobe no
  InitGui.py) e confirme as portas 9875/9876.
- [ ] Self-test rapido dos modulos de calculo (opcional):
  cada `calc/*.py` tem `_selftest()` ou roda como `__main__`.

## 1. Iniciar a skill

- A build-warehouse **nao e um slash-command**: e uma skill de repositorio.
  Aponte o agente para `skills/build-warehouse/SKILL.md` e peca para segui-la
  ("rode a skill build-warehouse"). O agente le SKILL.md + `references/gates.md`
  + `references/calc-modules.md` e conduz o fluxo.
- Ela roda em **10 gates**, um por vez, "Ask, Do Not Invent" (toda decisao
  critica vira pergunta com recomendacao justificada).
- **Comece num slug NOVO**: `projects/<slug-novo>/` (nao reaproveite `galpao/`,
  que fica como referencia validada). Crie a pasta + `AGENT_SCOPE.md`.
- **Motor de calculo:** use o orquestrador `calc/rodar_galpao.py` (nao chame os
  modulos avulsos). Monte o dict de params com as respostas dos gates
  (geometria, base, perfis, cargas) e chame `rodar(params, out_dir)`. A geometria
  e parametrica via `gp.configurar(...)` / `build_galpao.configurar(...)`.

## 2. Sequencia dos gates (o que cada um pergunta / roda)

| Gate | Pergunta ao usuario | Roda |
|------|---------------------|------|
| 0 uso/volumetria | vao, comprimento, pe-direito, uso | — (modela) |
| 1 telhado/inclinacao | duas aguas?, inclinacao, cumeeira | — |
| 2 secundario/estabilidade | espacamento de porticos, contraventamento | — |
| 3 envelope | telha, tapamento | — |
| 4 aberturas | portoes, portas, janelas (+ check estrutura-em-abertura) | — |
| 5 acoes/site | V0, categoria, classe, cargas G/Q | **vento_nbr6123** |
| 6 analise | condicao de base (rotulada/engastada), combinacoes | **galpao_portico + estabilidade_b1b2** |
| 7 dimensionamento | perfis, perfil da terca (Ue), fck, chumbadores | **check + redimensionamento + tercas(+fsm) + base + ligacoes** |
| 8 perfis reais | (confirma) | atualiza o modelo FreeCAD |
| 9 documentos | (confirma) | memorial consolidado + takeoff |

Detalhe de cada modulo (inputs/saidas/ordem): `references/calc-modules.md`.

## 3. Onde caem os resultados

- Memoriais PT: `projects/<slug>/exports/memoria/*.txt` (um por modulo) +
  `MEMORIAL-CONSOLIDADO.txt` no Gate 9.
- Modelo: `exports/freecad/*.FCStd` e `exports/step/*.step`.
- Levantamento de material: `exports/takeoff/*.csv`.
- Screenshots por gate: `exports/screenshots/`.

## 4. Regra de ouro (dizer ao senior)

- A skill **calcula** e emite os memoriais; **o engenheiro revisa e assina** (ART).
  Nada e "verificado" antes disso.
- **Taxa de utilizacao** = solicitacao/resistencia. **<= 1,0 atende** a norma;
  margem confortavel ~0,7-0,9; ~0,95 passa mas sem folga; muito baixo (ex. 0,24)
  = governado por minimo/rigidez, nao pela resistencia.
- Formulas extraidas dos PDFs das normas (`pesquisa/aco/`), com self-test. Se
  surgir duvida de metodo, volta-se ao PDF da norma — nunca de memoria.

## 5. Pendencias que NAO sao erros (falar antes que o senior pergunte)

- Cone de arrancamento/ancoragem do concreto: projeto de fundacao (NBR 6118/ACI).
- Espessura da chapa da ligacao de momento + acao de alavanca (prying) +
  enrijecedores: detalhe de ligacao, fora do `ligacoes`.
- Block shear / estados-limite da chapa alem do esmagamento.
- Propriedades da terca Ue pela linha media (prop2): CONFIRMAR no catalogo.
- Secoes secundarias (escoras, longarinas): verificacao propria.

## 6. Referencia validada

O projeto `projects/galpao/` (20x10, base engastada) foi rodado ponta a ponta
pelos Gates 0-9 e serve de gabarito: HEA200/HEA180, terca Ue 200x75x25x2,65,
base 450x550x40 + 4 d20, joelho 4 M24. Compare os numeros se algo destoar.
