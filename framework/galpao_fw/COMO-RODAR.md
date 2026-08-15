# Como rodar o framework de galpão (guia de execução)

CONCEITUAL — o framework **calcula, dimensiona e desenha**; o **engenheiro
responsável revisa e assina (ART)**. Nada aqui é projeto executivo.

## 1. Preparar um PC novo (uma vez)

Na raiz do repositório, duplo-clique em **`install.bat`** (ou
`powershell -ExecutionPolicy Bypass -File install.ps1`). Ele monta:

- o servidor MCP do FreeCAD (uv tool) + o workbench `RobustMCPBridge`;
- o **ambiente Python do cálculo** em `framework/galpao_fw/.venv`
  (Python 3.12, `numpy<2`, `pycufsm`, `ezdxf`) — é onde o cálculo e o DXF rodam.

Pré-requisitos: FreeCAD instalado; `uv` no PATH (ou rode com `-InstallUvIfMissing`).

O `.venv` NÃO vai no git — cada PC monta o seu pelo instalador.

## 2. Rodar um projeto

O projeto é dirigido por um **spec** (fonte única da verdade). Fluxo:

```
spec  ->  validar (trava se faltar decisão)
      ->  calcular       (dimensiona perfil, base, joelho, terça, longarina...)
      ->  montar_modelo  (modelo 3D no FreeCAD, com conexões + auditor)
      ->  rodar_executivo (pranchas 2D + DXF)
```

Código (rodar com o python do venv de cálculo):

```python
import sys; sys.path.insert(0, "framework/galpao_fw")
import projeto_spec as PS, rodar_projeto as RP

s = PS.novo()                       # spec com tudo PENDENTE (bloqueia)
# ... preencher os gates (terreno, geometria, cobertura, fechamento,
#     aberturas, vento, ponte, cargas) - pasta de projeto criada por framework.novo_projeto
RP.calcular(s, "projeto/exports/memoria")          # dimensiona + memoriais
RP.montar_modelo(s, "projeto/exports", "meu_galpao")  # FreeCAD aberto (MCP)
RP.rodar_executivo(s, "projeto/exports", "projeto/exports/freecad/meu_galpao.FCStd")  # pranchas 2D + DXF
```

`calcular` roda no venv puro (não precisa do FreeCAD). `montar_modelo` usa o
FreeCAD pela ponte MCP (porta 9875). Não existe `gerar_dxf`: o DXF sai junto
com as pranchas 2D do `rodar_executivo` (freecad.exe headless, TechDraw).

Para criar uma pasta de projeto isolada nova: `framework.novo_projeto("slug")`.

## 3. O que sai (exports/)

- `memoria/` — memoriais PT por etapa + **MEMORIAL-CONSOLIDADO** (abre com um
  QUADRO DE VERIFICAÇÕES e grita `!!! NÃO ATENDEM !!!` se algo passar de 1,0);
- `freecad/*.FCStd` + `step/*.step` — modelo 3D;
- `takeoff/*.csv` — levantamento de material (aço);
- `dxf/*.dxf` — pórtico, elevação, planta, corte (terças/telha), detalhes do
  joelho e da base, eixos numerados, níveis, quadro de verificações e de
  materiais. Camadas com cor fixa (visível em fundo branco e preto).

## 4. O que o framework FAZ

Portal de 1 vão, 2 águas, base engastada/rotulada, com ou sem ponte rolante:

- vento NBR 6123 (transversal + longitudinal, Cat I–V);
- pórtico 1ª + 2ª ordem (MAES) e **redimensiona** coluna/viga (HEA→HEB300/IPE550);
- **dimensiona** base (placa/chumbadores/espessura), joelho (chapa/parafusos),
  terça (Ue), longarina (UPE + tirantes), escora/montante (HEA);
- **dimensiona** a sapata isolada (NBR 6118): tensão no solo + FS tombamento/
  deslizamento (Parte A) e concreto — rigidez 22.6.1, armadura de flexão
  (22.6.3+17.2.2), compressão diagonal 19.5.3.1 (Parte B, sapata rígida);
- terças NBR 14762 (+ distorcional FSM), mão-francesa, contraventamento;
- modelo 3D com conexões detalhadas + **auditor geométrico** (mede a forma real
  e pega erro de conexão no build);
- DXF com quadros de verificação e materiais.

Referência validada: galpão 20×10 m com ponte rolante 100 kN — roda ponta a
ponta com todos os elementos ATENDENDO (a pasta `projects/<slug>/` é criada em
runtime por `framework.novo_projeto`; não fica no repositório).

## 5. O que ainda NÃO faz (fora de escopo / próximos)

> **Já implementado posteriormente** (saiu desta lista): bloco sobre estacas e
> punção (fase 3 + D8, 2026-07-07/10), armadura executiva (item 24 do índice),
> treliça e alma variável (fases 6.c/6.b, 2026-07-10), multi-vão (D51,
> 2026-07-16, PR #12), sismo (D18, 2026-07-08), fadiga (D10/D16, 2026-07-08),
> fabricação — piece marks 3D + lista de corte + tolerâncias (PR #46,
> 2026-07-22; D37, 2026-07-09) e plano de montagem (PR #47, 2026-07-22).

- **Fundação**: sapata isolada JÁ dimensionada (rígida, NBR 6118), com envelope
  de combinações por elemento (bearing pega N máx gravitacional; tombamento pega
  N mín + M) — ver `REVISAO-FUNDACAO.md`; ainda falta **tubulão** (bloco sobre
  estacas, punção e armadura executiva já implementados — ver nota);
- mezanino e formado a frio como principal (treliça, multi-vão e alma variável
  já implementados — ver nota);
- fachadas/cortes longitudinais detalhados das paredes;
- cargas especiais: ponte múltipla e carga térmica plena (sísmica e fadiga já
  implementadas — ver nota; `junta_dilatacao` cobre só o movimento térmico).

## 6. Regras do sistema (para o revisor)

- **Ask, Do Not Invent**: toda decisão de engenharia é campo do spec; `validar()`
  bloqueia enquanto houver PENDENTE.
- **Utilização** = solicitação/resistência; `<= 1,0` atende. O memorial e o
  quadro do DXF marcam `NÃO ATENDE` em vermelho quando passa de 1.
- Propriedades de perfil (incl. UPE J/Cw) e alguns dados estão marcados
  **A CONFIRMAR** no catálogo do fornecedor — confirmar antes do executivo.
- Métodos extraídos das normas — lidos verbatim do PDF, não de memória (ex.:
  `estaca_profunda.py` registra "LIDO do PDF").

### 9.1 Fixture residencial sintética

Para exercitar a entrada por arquivo e o adaptador residencial sintético:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/casa-residencial-sintetica/project-spec.json `
  --out-dir .loop-runtime/project-loop/casa-residencial-sintetica `
  --no-ifc

python framework/galpao_fw/project_loop_cli.py `
  --verify-run .loop-runtime/project-loop/casa-residencial-sintetica
```

Para esta fixture, `needs_review` é o resultado esperado. A saída `ok: true`
do segundo comando significa somente integridade dos artefatos persistidos e
dos hashes; não representa cálculo, validação normativa, aprovação técnica ou
projeto para obra. A fixture não gera IFC, modelo 3D, desenhos nem caderno.
