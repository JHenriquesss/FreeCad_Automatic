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
      ->  gerar_dxf      (vistas 2D + quadros)
```

Código (rodar com o python do venv de cálculo):

```python
import sys; sys.path.insert(0, "framework/galpao_fw")
import projeto_spec as PS, rodar_projeto as RP

s = PS.novo()                       # spec com tudo PENDENTE (bloqueia)
# ... preencher os gates (terreno, geometria, cobertura, fechamento,
#     aberturas, vento, ponte, cargas) - ver projects/galpao-nf982/work/spec_nf982.py
RP.calcular(s, "projeto/exports/memoria")          # dimensiona + memoriais
RP.montar_modelo(s, "projeto/exports", "meu_galpao")  # FreeCAD aberto (MCP)
RP.gerar_dxf(s, "projeto/exports/dxf", "meu_galpao")  # vistas DXF
```

`calcular` e `gerar_dxf` NÃO precisam do FreeCAD (rodam no venv). `montar_modelo`
precisa do **FreeCAD aberto** com a ponte MCP (porta 9875).

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

Referência validada: `projects/galpao-nf982/` (20×10, ponte 100 kN) — roda ponta
a ponta com todos os elementos ATENDENDO.

## 5. O que ainda NÃO faz (fora de escopo / próximos)

- **Fundação**: sapata isolada JÁ dimensionada (rígida, NBR 6118), com envelope
  de combinações por elemento (bearing pega N máx gravitacional; tombamento pega
  N mín + M) — ver `REVISAO-FUNDACAO.md`; ainda faltam bloco sobre estacas/
  tubulão, sapata flexível (punção) e detalhamento executivo da armadura;
- tipologias além do portal 1 vão (treliça, multi-vão, alma variável, mezanino,
  formado a frio como principal);
- ligações de **fabricação** (as conexões 3D são conceituais — sem furação/solda
  executiva);
- fachadas/cortes longitudinais detalhados das paredes;
- cargas especiais (sísmica, fadiga, térmica, ponte múltipla).

## 6. Regras do sistema (para o revisor)

- **Ask, Do Not Invent**: toda decisão de engenharia é campo do spec; `validar()`
  bloqueia enquanto houver PENDENTE.
- **Utilização** = solicitação/resistência; `<= 1,0` atende. O memorial e o
  quadro do DXF marcam `NÃO ATENDE` em vermelho quando passa de 1.
- Propriedades de perfil (incl. UPE J/Cw) e alguns dados estão marcados
  **A CONFIRMAR** no catálogo do fornecedor — confirmar antes do executivo.
- Métodos extraídos das normas (pesquisa/aço); não de memória.
