# G10 — Destino da `casa-residencial-sintetica`

**Decisão: MANTER, documentada como fixture de contrato do núcleo — e blindada
por teste-guarda contra a deleção acidental e contra o esvaziamento silencioso.**

---

## 1. A dívida como estava enunciada

Três adaptadores declaram `project_types=("residencial",)`:

| Adaptador | O que é |
|---|---|
| `casa-residencial` | REAL (G4): arquitetura NBR 5410 9.5.2 + elétrico + hidráulica |
| `casa-residencial-eletrica` | REAL (Fase 6A/6B): vertical elétrica residencial |
| `casa-residencial-sintetica` | fixture: **não calcula nada** |

A sintética nasceu para provar o contrato do núcleo quando não havia tipologia
residencial real. Hoje há duas. Logo: ainda serve, ou é peso morto?

## 2. O que a investigação mudou no enunciado

**Não há colisão de despacho.** O Loop escolhe o adaptador pelo **nome**
declarado no spec (`project_loop.py:347`, default `"galpao"`);
`project_types` é só o gate de compatibilidade do preflight
(`project_loop.py:598`), que reprova com `unsupported_project_type`. Três
adaptadores para o mesmo `project_type` é o estado **normal** do registro, não
uma ambiguidade. A dívida, portanto, nunca foi "dois adaptadores brigam" —
é só "uma fixture não-de-engenharia está no registro de produção".

**Quase toda a cobertura dela é redundante.** Medido, não suposto:

| O que a fixture exercita | Já coberto por |
|---|---|
| `status: blocked` / `needs_review` | `casa_residencial.py:243`, `edificio_adapter.py:357` |
| `native_atende: None` | `residencial_eletrica.py:378`, `edificio_adapter.py:108` |
| contrato mínimo do runner | adaptadores inline em `test_project_loop_adapter_contract.py` |
| entrada por arquivo de spec persistido | `projects/casa-residencial`, `edificio-multipavimento`, `galpao-sjb` |

## 3. O único motivo real para mantê-la

Ela é o **único adaptador nativo registrado com `hooks={}`**:

```
casa-residencial            ['drawings', 'ifc', 'model_3d']
casa-residencial-eletrica   ['drawings', 'ifc']
edificio-multipavimento     ['drawings', 'ifc', 'model_3d']
galpao                      [12 hooks]
casa-residencial-sintetica  []            <-- este
```

Isso é o que ela guarda, e nenhum adaptador real **pode** guardar: quando o
chamador pede IFC + 3D + 2D de um adaptador que não sabe emitir nenhum deles, o
núcleo tem de responder `not_available` e **não produzir um artefato sequer**
fora do conjunto genérico — em vez de estourar, ou pior, de gravar um entregável
vazio e rotulá-lo `generated`. É o teste
`test_residential_missing_hooks_are_not_available_when_requested`, com a lista
`FORBIDDEN_ARTIFACT_MARKERS` (`.ifc`, `.fcstd`, `.pdf`, `.svg`, `.dxf`,
`freecad`).

Isso é da família da **saturação silenciosa** já catalogada no projeto: o modo
de falha não é o vermelho, é o verde mentiroso. Apagar a fixture apagaria a
única prova de que o núcleo degrada com honestidade.

Um adaptador de teste inline poderia cobrir a mesma coisa — mas cobriria o
núcleo contra um registro fabricado pelo próprio teste. Aqui a garantia é
verificada contra o **registro realmente embarcado**.

## 4. A armadilha que a decisão fecha

Manter não bastava. Havia um caminho para perder a cobertura **sem nada ficar
vermelho**: dar um hook à fixture. `ifc`, `drawings` e `model_3d` são hooks de
núcleo (`CORE_HOOKS`), então `register_adapter` os aceita sem exigir nada; e
`test_residential_missing_hooks_...` passaria a testar um adaptador que tem
hooks — ou seja, deixaria de testar o que o nome dele diz.

Por isso a decisão vem com guarda:

- `test_a_fixture_sintetica_e_o_unico_adaptador_nativo_sem_hooks` — falha se a
  fixture ganhar hook **e** falha se um adaptador REAL passar a não ter nenhum
  (aí o defeito é o adaptador real, e a mensagem diz isso).
- `test_a_fixture_sintetica_se_declara_como_nao_sendo_projeto_para_obra` —
  `synthetic_fixture: True` no resultado, aviso `synthetic_fixture` em **toda**
  disciplina, e a descrição do spec persistido.

Conferido morde: ao dar `hooks={"ifc": ...}` à fixture, 4 testes falham,
inclusive o guarda novo, com a mensagem apontando para este documento.

## 5. O que a mantém honesta (já existia, aqui registrado)

- `casa_residencial_sintetica.py` — docstring diz o que é, **e agora por que
  continua**.
- `builtin_adapters.py` — comentário no ponto de registro.
- resultado do adaptador: `synthetic_fixture: True`; os reais emitem `False`
  (`casa_residencial.py:401`, `edificio_adapter.py:348`) — é o discriminador.
- `projects/casa-residencial-sintetica/project-spec.json` — `"fixture de
  contrato; não é projeto para obra"`.
- `COMO-RODAR.md` §9.1 — "`ok: true` significa somente integridade dos
  artefatos e dos hashes; não representa cálculo, validação normativa,
  aprovação técnica ou projeto para obra".

## 6. O que NÃO foi feito, e por quê

Tirá-la de `builtin_adapters.py` para o layer de teste seria mais limpo em
princípio: uma fixture não pertence ao registro de produção. Não foi feito
porque (a) é exatamente por estar no registro embarcado que a garantia da §3
vale, e (b) o escopo desta decisão era resolver a dívida, não reorganizar o
registro. Fica anotado como opção, não como pendência.
