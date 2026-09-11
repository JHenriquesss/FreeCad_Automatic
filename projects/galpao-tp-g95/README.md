# galpao-tp-g95 — terraplenagem ponta a ponta (G95)

Clone do `galpao-ufpe` (44×90, 2 vãos) com **`site.terraplenagem` preenchido**, para exercitar
as folhas PE-TP-01 (corte/aterro) e PE-TP-02 (drenagem do lote) numa rodada de verdade.

O G89 ligou os dois emissores ao Loop (`entregaveis_projeto.emitir_obras_sitio`) e os provou
com fixture em memória; nenhum spec persistido declarava a frente, então **o caminho estava
ligado e nunca rodava**. Este projeto fecha isso.

## ⚠ Os números da terraplenagem são PREMISSA DE TESTE

`test_assumptions` no próprio spec diz, e vale repetir aqui:

- `status: not_real_engineering_input`
- `source: agent_assumed_values`

Grade do terreno, cota de plataforma, empolamento, C, IDF e taxa de infiltração **exigem
levantamento topográfico e ensaio**. Nada aqui é levantamento real. Antes de qualquer uso
executivo, o responsável técnico substitui ou confirma cada um.

O portão do G95 (`tests/test_terraplenagem_rodada_g95.py`) **exige a procedência escrita**: sem
o bloco `test_assumptions` mencionando a terraplenagem, o teste reprova. Um número inventado
num spec persistido sobrevive ao goal — é por isso que a marcação é obrigatória, e não um
comentário de cortesia.

## O que a rodada entrega

`obras_sitio` com `status: generated` e três artefatos: `sitio/obras-sitio.json`,
`drawings/terraplenagem-corte-aterro.svg` e `drawings/terraplenagem-drenagem.svg`.

Conferência independente (conta a mão, na docstring do teste — nunca recalculada pelo módulo
sob teste): corte 1120,0 m³, aterro 1360,0 m³, Q = 0,3250 m³/s.

## Rodar

```bash
cd framework/galpao_fw
python -c "
import json, sys; sys.path.insert(0, '.')
from builtin_adapters import register_builtin_adapters
from project_loop import run_project
register_builtin_adapters()
spec = json.load(open('../../projects/galpao-tp-g95/project-spec.json', encoding='utf-8'))
m = run_project(spec, 'out/galpao-tp-g95', {'generate_2d': True, 'generate_ifc': False})
print(m['deliverables']['obras_sitio']['status'])
"
```

A pasta `iterations/` é saída de rodada e **não** é versionada (o repo guarda spec + README).
