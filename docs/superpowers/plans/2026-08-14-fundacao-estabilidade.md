# Verificação de estabilidade de fundações rasas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar dois métodos auditáveis para estabilidade de sapatas/blocos conforme a NBR 6122:2022, sem dupla majoração e sem tratar FS 1,5 como requisito universal.

**Architecture:** `fundacao_sapata.py` continuará sendo o motor único. Uma função `normaliza_verificacao(caso)` converterá a configuração canônica e o legado em um contrato interno; `estabilidade()` receberá esse contrato e devolverá valores usados, fatores e avisos. `projeto_spec.py`, `rodar_galpao.py` e `galpao_concreto.py` somente transportarão a configuração e declararão se as ações já são características ou de cálculo.

**Tech Stack:** Python 3, pytest, dicionários de configuração existentes, NotebookLM OCR local da NBR 6122:2022.

## Global Constraints

- O modo novo será `nbr6122_valores_calculo`; o modo alternativo será `fs_global_legacy`.
- `gamma_f=1,4`, `gamma_peso_favoravel=1,2` e `gamma_resistencia_solo=1,4` serão os valores padrão apenas no modo NBR.
- Solicitações já fornecidas como valores de cálculo não receberão nova majoração.
- O modo legado exigirá FS de tombamento e deslizamento informado pelo caso novo.
- O FS global 1,1 da flutuação não será usado em tombamento ou deslizamento.
- Empuxo passivo só será contado com `solo_nao_removivel=True` e redução mínima de 2,0.
- Chamadas sem configuração permanecerão temporariamente compatíveis e serão marcadas como `compatibilidade_legacy`.
- Nenhum código de produção será escrito antes do teste correspondente falhar em RED.
- Não serão alteradas fundações profundas nesta fase.

---

# Phase 49: Métodos de estabilidade NBR 6122

## Scope

Entregar o contrato de verificação para sapatas e blocos, aplicar fatores parciais somente no método NBR, manter o caminho legado explicitamente identificado, propagar a configuração pelo template de projeto e registrar os critérios no relatório da fundação.

## Entry condition

- A especificação aprovada existe em `docs/superpowers/specs/2026-08-14-fundacao-estabilidade-design.md`.
- A fonte OCR da NBR 6122:2022 está carregada e validada no NotebookLM de fundações.
- `python -m pytest tools/loops -q` permanece verde antes da implementação.

## Exit condition

- Testes novos de contrato, fatores, contato, empuxo e propagação passam.
- Regressões existentes de `fundacao_sapata`, `projeto_spec`, `rodar_galpao` e `galpao_concreto` passam, descontadas somente as falhas preexistentes já registradas.
- O relatório mostra o método efetivo e os fatores usados.
- Nenhuma chamada nova depende dos defaults legados sem aviso.

## Must-exist checklist

- [ ] `normaliza_verificacao(caso)` valida os dois métodos e produz contrato interno estável.
- [ ] `nbr6122_valores_calculo` aplica fatores a `N_acao_desfavoravel_kN`, `V` e `M` quando característicos, minora o peso favorável e divide a resistência do solo.
- [ ] `fs_global_legacy` exige FS explícito e usa limite de contato de 2/3.
- [ ] O modo NBR usa limite de contato de 50% quando as solicitações são de cálculo.
- [ ] A configuração conflitante de FS global dentro do modo NBR bloqueia o caso.
- [ ] A decomposição de reação vertical característica é validada: `N_acao_desfavoravel_kN + peso_favoravel_superestrutura_kN` deve reproduzir a reação externa `N`.
- [ ] Empuxo passivo sem solo permanente não aumenta a resistência; com solo permanente é reduzido por pelo menos 2,0.
- [ ] Chamadas sem configuração retornam `compatibilidade_legacy` e aviso.
- [ ] `projeto_spec.novo()` e `PARAMS_REF` geram configuração explícita adequada ao fluxo de ações de cálculo.
- [ ] `gate7-fundacao.txt` e a saída de `verifica_sapata_A` expõem método, fatores, limite e avisos.

## Must-not-exist checklist

- [ ] Nenhuma aplicação de `gamma_f` em ação já marcada como `calculo`.
- [ ] Nenhum FS automático 1,5 apresentado como requisito NBR.
- [ ] Nenhuma aplicação do FS 1,1 de flutuação em tombamento/deslizamento.
- [ ] Nenhum empuxo passivo contado sem `solo_nao_removivel=True`.
- [ ] Nenhuma mutação da configuração original ao dimensionar várias geometrias ou combinações.
- [ ] Nenhum teste substituído por mock do motor de fundações.

## Test plan

### Positive

- [ ] Caso NBR com ações de cálculo usa `gamma_f` efetivo 1,0 para `V/M` e ainda registra minoração de peso/resistência.
- [ ] Caso NBR com ações características obtém `V_d=1,4V_k`, `M_d=1,4M_k` e fatores de peso/resistência rastreáveis.
- [ ] Contato de 55% passa no modo NBR de cálculo; contato de 70% passa no modo legado característico.
- [ ] FS legado informado é respeitado exatamente.
- [ ] Configuração é preservada em `dimensiona_sapata_env` para todas as combinações.

### Negative

- [ ] FS legado ausente bloqueia caso novo.
- [ ] FS global fornecido junto com modo NBR bloqueia configuração conflitante.
- [ ] Reação característica agregada sem decomposição vertical torna o resultado inconclusivo.
- [ ] Empuxo passivo com solo removível é ignorado e gera aviso.
- [ ] Coeficiente parcial nulo ou menor que 1 bloqueia configuração.
- [ ] A chamada sem configuração passa somente pelo caminho de compatibilidade e gera aviso.

## Test tree integration

- Trunk touch point: jornada de dimensionamento de fundação no Gate 7, antes da geração de `gate7-fundacao.txt` e do modelo BIM da sapata.
- New branches added: contrato de método; fatores NBR; FS legado; contato NBR 7.6.2; empuxo passivo NBR 7.6.3; wiring de `projeto_spec` e `rodar_galpao`.

## Next phase seed

Revisar combinações de ações e decomposição de cargas em cada tipologia de fundação, incluindo estacas, radier e fundação de divisa.

---

### Task 1: Criar fixture e testes RED do contrato

**Files:**
- Create: `framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py`
- Reference: `framework/galpao_fw/fundacao_sapata.py`

**Interfaces:**
- Consumes: `fundacao_sapata.normaliza_verificacao(caso)` (a ser criado).
- Produces: testes que fixam os nomes dos métodos, defaults e erros de configuração.

- [ ] **Step 1: Escrever os testes falhos**

```python
def test_normaliza_nbr_usa_fatores_e_tipo_de_acao():
    c = {"verificacao_estabilidade": {
        "metodo": "nbr6122_valores_calculo",
        "tipo_acoes": "caracteristicas",
        "N_acao_desfavoravel_kN": 80.0,
        "peso_favoravel_superestrutura_kN": 20.0,
    }}
    r = fs.normaliza_verificacao(c)
    assert r["metodo"] == "nbr6122_valores_calculo"
    assert r["tipo_acoes"] == "caracteristicas"
    assert r["gamma_f"] == pytest.approx(1.4)
    assert r["gamma_peso_favoravel"] == pytest.approx(1.2)


def test_normaliza_legacy_exige_fs_explicito():
    c = {"verificacao_estabilidade": {
        "metodo": "fs_global_legacy",
        "tipo_acoes": "caracteristicas",
    }}
    with pytest.raises(ValueError, match="fs_tombamento|fs_deslizamento"):
        fs.normaliza_verificacao(c)


def test_normaliza_sem_configuracao_marca_compatibilidade():
    r = fs.normaliza_verificacao({})
    assert r["metodo"] == "compatibilidade_legacy"
    assert r["avisos"]
```

- [ ] **Step 2: Rodar RED**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py -q`

Expected: FAIL because `normaliza_verificacao` ainda não existe.

### Task 2: Implementar o normalizador mínimo

**Files:**
- Modify: `framework/galpao_fw/fundacao_sapata.py` perto das constantes de estabilidade.
- Test: `framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py`

**Interfaces:**
- Consumes: `caso["verificacao_estabilidade"]`, além de `fs_tomb_min`/`fs_desl_min` somente para compatibilidade.
- Produces: `normaliza_verificacao(caso) -> dict` com `metodo`, `tipo_acoes`, três gammas, FS, empuxo e `avisos`.

- [ ] **Step 1: Implementar somente o contrato usado pelos testes**

```python
def normaliza_verificacao(caso):
    cfg = caso.get("verificacao_estabilidade")
    if cfg is None:
        return {"metodo": "compatibilidade_legacy", "tipo_acoes": "caracteristicas",
                "gamma_f": 1.0, "gamma_peso_favoravel": 1.0,
                "gamma_resistencia_solo": 1.0,
                "fs_tombamento": caso.get("fs_tomb_min", FS_TOMB_MIN),
                "fs_deslizamento": caso.get("fs_desl_min", FS_DESL_MIN),
                "empuxo_passivo_kN": 0.0, "solo_nao_removivel": False,
                "avisos": ["sem verificacao_estabilidade: caminho legado"]}
    metodo = cfg.get("metodo")
    tipo = cfg.get("tipo_acoes", "calculo")
    if metodo not in ("nbr6122_valores_calculo", "fs_global_legacy"):
        raise ValueError("metodo de verificacao invalido")
    if tipo not in ("caracteristicas", "calculo"):
        raise ValueError("tipo_acoes invalido")
    if metodo == "fs_global_legacy" and tipo != "caracteristicas":
        raise ValueError("fs_global_legacy exige tipo_acoes=caracteristicas")
    defaults = {"gamma_f": 1.4, "gamma_peso_favoravel": 1.2,
                "gamma_resistencia_solo": 1.4}
    out = {k: cfg.get(k, v) for k, v in defaults.items()}
    if any(out[k] <= 0 for k in defaults):
        raise ValueError("coeficientes de verificacao devem ser positivos")
    fs_t = cfg.get("fs_tombamento")
    fs_d = cfg.get("fs_deslizamento")
    if metodo == "fs_global_legacy" and (fs_t is None or fs_d is None):
        raise ValueError("fs_tombamento e fs_deslizamento sao obrigatorios")
    if metodo == "nbr6122_valores_calculo" and (fs_t is not None or fs_d is not None):
        raise ValueError("FS global nao pode ser misturado ao modo NBR")
    out.update(metodo=metodo, tipo_acoes=tipo, fs_tombamento=fs_t,
               fs_deslizamento=fs_d,
               empuxo_passivo_kN=cfg.get("empuxo_passivo_kN", 0.0),
               solo_nao_removivel=bool(cfg.get("solo_nao_removivel", False)),
               avisos=[])
    return out
```

- [ ] **Step 2: Rodar GREEN do contrato**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py -q`

Expected: PASS for the contract tests.

### Task 3: Escrever testes RED do cálculo e do contato

**Files:**
- Modify: `framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py`

**Interfaces:**
- Consumes: `fs.verifica_sapata_A(caso)` and `fs.estabilidade(...)`.
- Produces: failing behavioral tests for factor application and NBR 7.6.2.

- [ ] **Step 1: Adicionar casos físicos sem mocks**

```python
def _caso_base(**extra):
    c = {"N": 100.0, "V": 0.0, "M": 0.0, "B": 2.0, "L": 2.0, "h": 0.40,
         "mu": 0.50, "coesao": 0.0, "sigma_solo_adm": 250.0,
         "h_reaterro": 0.0, "d_ped": 0.30, "b_ped": 0.30, "h_ped": 0.50}
    c.update(extra)
    return c


def test_nbr_calculo_nao_reaplica_gamma_f_em_v_m():
    c = _caso_base(V=20.0, M=10.0, verificacao_estabilidade={
        "metodo": "nbr6122_valores_calculo", "tipo_acoes": "calculo"})
    r = fs.verifica_sapata_A(c)
    assert r["tipo_acoes"] == "calculo"
    assert r["fatores_verificacao"]["gamma_f"] == pytest.approx(1.4)
    assert r["V_verificacao"] == pytest.approx(20.0)
    assert r["M_verificacao"] == pytest.approx(10.0)


def test_nbr_caracteristico_majora_v_m_e_mostra_limite_de_contato():
    c = _caso_base(V=20.0, M=10.0, verificacao_estabilidade={
        "metodo": "nbr6122_valores_calculo", "tipo_acoes": "caracteristicas",
        "N_acao_desfavoravel_kN": 100.0,
        "peso_favoravel_superestrutura_kN": 0.0})
    r = fs.verifica_sapata_A(c)
    assert r["V_verificacao"] == pytest.approx(28.0)
    assert r["M_verificacao"] == pytest.approx(14.0)
    assert r["limite_area_comprimida"] == pytest.approx(0.50)


def test_contato_legado_caracteristico_exige_dois_tercos():
    c = _caso_base(M=120.0, verificacao_estabilidade={
        "metodo": "fs_global_legacy", "tipo_acoes": "caracteristicas",
        "fs_tombamento": 1.0, "fs_deslizamento": 1.0})
    r = fs.verifica_sapata_A(c)
    assert r["limite_area_comprimida"] == pytest.approx(2.0 / 3.0)
    assert r["area_comprimida_ratio"] < r["limite_area_comprimida"]
    assert not r["ok_contato"]
```

- [ ] **Step 2: Rodar RED**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py -q`

Expected: FAIL because the current motor does not return the method metadata, transformed actions or the 50%/2/3 limits.

### Task 4: Implementar fatores parciais e critérios de contato

**Files:**
- Modify: `framework/galpao_fw/fundacao_sapata.py` in `estabilidade` and `verifica_sapata_A`.
- Test: `framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py`

**Interfaces:**
- Consumes: normalized contract from `normaliza_verificacao`.
- Produces: `V_verificacao`, `M_verificacao`, `N_tot`, `Pp_verificacao`, `resistencia_deslizamento_verificacao`, `area_comprimida_ratio`, `limite_area_comprimida`, `fatores_verificacao` and `avisos_verificacao`.

- [ ] **Step 1: Alterar `estabilidade` com argumento opcional**

Use a assinatura compatível:

```python
def estabilidade(N, V, M, B, L, h, mu, coesao=0.0, h_reaterro=0.0,
                 d_ped=0.0, b_ped=0.0, h_ped=0.0, verificacao=None,
                 peso_favoravel_superestrutura=0.0):
```

No modo NBR, calcular `Pp_verificacao = Pp/gamma_peso_favoravel`, `peso_extra_verificacao = peso_extra/gamma_peso_favoravel`, `V_verificacao = V*gamma_f` e `M_verificacao = M*gamma_f` somente para ações características; dividir a soma de atrito, coesão e empuxo passivo pelo `gamma_resistencia_solo`. No modo legado e no caminho de compatibilidade, conservar a aritmética anterior.

- [ ] **Step 2: Alterar `verifica_sapata_A` sem remover chaves antigas**

Calcular as tensões com os esforços de verificação, escolher o limite de contato por método/tipo de ação, usar FS mínimo 1,0 no modo NBR e manter FS explícito no modo legado. Para ações características, validar `N_acao_desfavoravel_kN` e `peso_favoravel_superestrutura_kN`; se a soma não reproduzir `N`, retornar `OK_A=False`, `inconclusivo=True` e aviso claro.

- [ ] **Step 3: Rodar GREEN**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py -q`

Expected: PASS.

### Task 5: Escrever testes RED de empuxo, erros e compatibilidade

**Files:**
- Modify: `framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py`

**Interfaces:**
- Consumes: output de `verifica_sapata_A`.
- Produces: regressões para os anti-objetivos normativos.

- [ ] **Step 1: Adicionar os testes**

```python
def test_empuxo_passivo_so_entra_com_solo_nao_removivel():
    base = _caso_base(V=80.0, M=20.0, verificacao_estabilidade={
        "metodo": "nbr6122_valores_calculo", "tipo_acoes": "calculo",
        "empuxo_passivo_kN": 100.0})
    r0 = fs.verifica_sapata_A(base)
    base["verificacao_estabilidade"]["solo_nao_removivel"] = True
    r1 = fs.verifica_sapata_A(base)
    assert r0["empuxo_passivo_verificacao_kN"] == pytest.approx(0.0)
    assert r1["empuxo_passivo_verificacao_kN"] == pytest.approx(50.0 / 1.4)
    assert any("remov" in x.lower() for x in r0["avisos_verificacao"])


def test_nbr_rejeita_fs_global_misturado():
    c = _caso_base(verificacao_estabilidade={
        "metodo": "nbr6122_valores_calculo", "tipo_acoes": "calculo",
        "fs_tombamento": 1.5, "fs_deslizamento": 1.5})
    with pytest.raises(ValueError, match="FS|fs"):
        fs.verifica_sapata_A(c)


def test_sem_configuracao_e_compatibilidade_explicita():
    r = fs.verifica_sapata_A(_caso_base())
    assert r["metodo_verificacao"] == "compatibilidade_legacy"
    assert any("legado" in x.lower() for x in r["avisos_verificacao"])
```

- [ ] **Step 2: Rodar RED**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py -q`

Expected: FAIL in the new assertions until the guards e o empuxo condicionado forem implementados.

### Task 6: Implementar empuxo, validações e relatório unitário

**Files:**
- Modify: `framework/galpao_fw/fundacao_sapata.py` in `normaliza_verificacao`, `estabilidade`, `verifica_sapata_A` and `_tabela_sapata`.
- Test: `framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py`

**Interfaces:**
- Consumes: `empuxo_passivo_kN`, `solo_nao_removivel`, FS e coeficientes.
- Produces: erros determinísticos para configuração conflitante, empuxo auditável e relatório com método/fatores.

- [ ] **Step 1: Implementar validação de enum, coeficientes e FS**

Bloquear método desconhecido, tipo de ações incompatível, fator menor ou igual a zero, FS legado ausente e FS NBR misturado. Preservar a conversão dos campos antigos somente no caminho `compatibilidade_legacy`.

- [ ] **Step 2: Implementar empuxo condicionado**

Somar `empuxo_passivo_kN / max(fator_reducao_empuxo, 2.0)` somente quando `solo_nao_removivel` for verdadeiro; caso contrário, retornar zero e aviso.

- [ ] **Step 3: Atualizar `_tabela_sapata`**

Adicionar uma linha com método, tipo de ação, fatores, limite de contato e avisos, sem retirar as colunas atuais de FS para preservar relatórios existentes.

- [ ] **Step 4: Rodar GREEN**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py -q`

Expected: PASS.

### Task 7: Escrever testes RED do wiring de projeto e galpão

**Files:**
- Create: `framework/galpao_fw/tests/test_fundacao_estabilidade_wiring.py`.
- Reference: `framework/galpao_fw/projeto_spec.py`, `framework/galpao_fw/rodar_galpao.py`, `framework/galpao_fw/galpao_concreto.py`.

**Interfaces:**
- Consumes: `projeto_spec.novo()`, `projeto_spec.to_rodar_params()`, `rodar_galpao.PARAMS_REF` and `galpao_concreto.rodar`.
- Produces: tests that prove configuration survives mapping and is not mutated between combinations.

- [ ] **Step 1: Adicionar testes falhos**

```python
def test_template_novo_declara_metodo_de_estabilidade():
    s = PS.novo()
    v = s["fundacao"]["verificacao_estabilidade"]
    assert v["metodo"] == "nbr6122_valores_calculo"
    assert v["tipo_acoes"] == "calculo"


def test_mapper_preserva_verificacao_estabilidade():
    s = PS.novo()
    s["fundacao"]["verificacao_estabilidade"] = {
        "metodo": "fs_global_legacy", "tipo_acoes": "caracteristicas",
        "fs_tombamento": 1.35, "fs_deslizamento": 1.25}
    p = PS.to_rodar_params(s)
    assert p["fundacao"]["verificacao_estabilidade"]["fs_tombamento"] == pytest.approx(1.35)
    assert p["fundacao"]["verificacao_estabilidade"] is not s["fundacao"]["verificacao_estabilidade"]


def test_parametros_referencia_declararam_acoes_de_calculo():
    import rodar_galpao as R
    v = R.PARAMS_REF["fundacao"]["verificacao_estabilidade"]
    assert v["metodo"] == "nbr6122_valores_calculo"
    assert v["tipo_acoes"] == "calculo"
```

- [ ] **Step 2: Rodar RED**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_wiring.py -q`

Expected: FAIL because the template and reference parameters ainda não declaram o bloco de verificação.

### Task 8: Implementar o wiring e atualizar documentação

**Files:**
- Modify: `framework/galpao_fw/projeto_spec.py` in `novo` and `to_rodar_params`.
- Modify: `framework/galpao_fw/rodar_galpao.py` in `PARAMS_REF` only; preserve combinations already in values de cálculo.
- Modify: `framework/galpao_fw/galpao_concreto.py` to pass optional `verificacao_estabilidade` into `caso_sap`.
- Modify: `framework/galpao_fw/REVISAO-FUNDACAO.md` to replace the old universal terço médio/FS 1,5 description.
- Test: `framework/galpao_fw/tests/test_fundacao_estabilidade_wiring.py`.

**Interfaces:**
- Consumes: nested `fundacao.verificacao_estabilidade`.
- Produces: explicit configuration in new specs and correct propagation into the two foundation orchestrators.

- [ ] **Step 1: Adicionar default NBR/calculo ao template**

Use `metodo="nbr6122_valores_calculo"`, `tipo_acoes="calculo"`, `gamma_f=1.4`, `gamma_peso_favoravel=1.2`, `gamma_resistencia_solo=1.4`, FS fields `None`, empuxo zero e `solo_nao_removivel=False`.

- [ ] **Step 2: Propagar cópia profunda lógica**

Manter a configuração aninhada no dicionário de fundação passado ao `rodar_galpao`; não compartilhar o mesmo objeto mutável entre o spec e os parâmetros derivados.

- [ ] **Step 3: Passar configuração no galpão de concreto**

Adicionar `verificacao_estabilidade=spec.get("verificacao_estabilidade")` ao caso da sapata. Se ausente, manter o caminho de compatibilidade com aviso.

- [ ] **Step 4: Atualizar revisão e relatório**

Documentar que o contato antigo de 1/3 é somente compatibilidade, que 2/3 corresponde a solicitações características e 50% a solicitações de cálculo, e que FS 1,5 não é universal na fonte consultada.

- [ ] **Step 5: Rodar GREEN do wiring**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_wiring.py -q`

Expected: PASS.

### Task 9: Regressão proporcional e revisão final

**Files:**
- Test: `framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py`
- Test: `framework/galpao_fw/tests/test_fundacao_estabilidade_wiring.py`
- Reference: todos os arquivos alterados nesta fase.

- [ ] **Step 1: Rodar testes focados**

Run: `python -m pytest framework/galpao_fw/tests/test_fundacao_estabilidade_metodos.py framework/galpao_fw/tests/test_fundacao_estabilidade_wiring.py framework/galpao_fw/tests/test_validacao_alonso.py framework/galpao_fw/tests/test_bloco_fundacao.py -q`

Expected: PASS.

- [ ] **Step 2: Rodar a suíte do framework**

Run: `python -m pytest framework/galpao_fw/tests -q`

Expected: nenhum novo failure causado pela fase; falhas antigas devem coincidir com o inventário do supervisor.

- [ ] **Step 3: Rodar verificações estáticas**

Run: `git diff --check`

Expected: saída vazia e código de retorno zero.

- [ ] **Step 4: Revisar diff**

Confirmar que não houve alteração em fontes, notebooks ou artefatos `.loop-runtime`, que as chaves antigas foram preservadas e que todo novo caminho tem teste.
