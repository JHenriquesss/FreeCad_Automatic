"""G85: nove modulos que nenhum teste nomeava.

Medido (2026-09-09, branch feat/tipologias-e-verticais-de-projeto): os 9
modulos abaixo eram importados por outros (nao sao ilhas) mas o nome nao
aparecia em nenhum arquivo de `tests/` - entao nenhum teste falharia se o
modulo fosse quebrado em silencio. Re-medido neste goal: 8 continuavam sem
nenhuma mencao; `layout_ambientes` passou a ser nomeado pelo
`test_planta_baixa_g78` (G78, mesma semana) - so no cross-check
`conferir_areas_programa_layout`.

Entregue: um veredito por modulo. Onde nao havia cobertura real, teste
direto com fonte independente (norma, formula fechada, simetria, fisica);
onde havia guarda comportamental sem nomear o modulo, teste direto barato
que nomeia o modulo + registro da guarda transitiva. Cada teste direto tem
par de injecao (monkeypatch em memoria - convenção 2: nunca muta o repo)
que prova a assercao nao-tautologica (convencao 5): com o defeito injetado,
o predicado do teste bom muda de valor.

Nao toca `FOLHAS`/`_PRANCHAS` (nenhuma folha nova aqui) nem redecide o G10.
"""
import math
import pathlib
import sys

import pytest

GALPAO = pathlib.Path(__file__).resolve().parents[1]
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))


# ===========================================================================
# 1. fogo_nbr14323 - aco em incendio (NBR 14323). Normativo, pesado.
# Fonte independente: curva ISO 834, Tab. 6.2 da NBR 14323 (fatores nos nos),
# e a fisica "protecao reduz a temperatura do aco".
# ===========================================================================
import fogo_nbr14323 as fogo


def test_fogo_gases_trrf60_confere_iso834():
    """TRRF 60 min: 20 + 345*log10(8*60+1) = ~945 C (valor de mao, ISO 834)."""
    assert fogo.temp_gases(60) == pytest.approx(20.0 + 345.0 * math.log10(481.0), abs=0.1)
    assert fogo.temp_gases(30) == pytest.approx(20.0 + 345.0 * math.log10(241.0), abs=0.1)


def test_fogo_reducao_nos_nos_da_tabela_nbr14323():
    """Nos exatos da Tab. 6.2: ky(500)=0.78, ky(600)=0.47, kE(600)=0.31."""
    assert fogo.k_y(500.0) == pytest.approx(0.78)
    assert fogo.k_y(600.0) == pytest.approx(0.47)
    assert fogo.k_E(600.0) == pytest.approx(0.31)
    assert fogo.k_y(20.0) == pytest.approx(1.0)
    assert fogo.k_y(1200.0) == pytest.approx(0.0)
    assert fogo.k_y(550.0) == pytest.approx(0.63)  # interpolado entre nos


def test_fogo_verifica_protecao_reduz_temperatura():
    """HEA200, TRRF 60: sem protecao o aco passa de 800 C; com 1,27 mm de
    intumescente fica abaixo - e ky/kE caem abaixo de 1."""
    sec = {"h": 190.0, "b": 200.0, "tw": 6.5, "tf": 10.0}
    sem = fogo.verifica_fogo(sec, 250e3, 100.0, 30.0, TRRF_min=60)
    com = fogo.verifica_fogo(sec, 250e3, 100.0, 30.0, TRRF_min=60,
                              protecao={"tipo": "intumescente", "espessura": 1.27})
    assert 800.0 <= sem["theta_aco_C"] <= 1000.0
    assert com["theta_aco_C"] < sem["theta_aco_C"]
    assert sem["ky"] < 1.0 and sem["kE"] < 1.0
    assert sem["u_A_1m"] > 50.0


def test_fogo_injecao_tabela_corrompida_muda_o_no(monkeypatch):
    """Defeito: ky a 500 C 0.78 -> 0.99. O teste dos nos tem de acusar
    (k_y(500) deixa de ser 0.78) - a assercao e' sensivel a tabela."""
    tabela = [list(linha) for linha in fogo._REDUCAO]
    for linha in tabela:
        if linha[0] == 500:
            linha[1] = 0.99
    monkeypatch.setattr(fogo, "_REDUCAO", [tuple(l) for l in tabela])
    assert fogo.k_y(500.0) != pytest.approx(0.78)
    assert fogo.k_y(500.0) == pytest.approx(0.99)


# ===========================================================================
# 2. distorcional_fsm - Mdist via faixas finitas (pycufsm). Engenharia pesada.
# Fonte independente: simetria da secao Ue (geometria) + flambagem de placa
# da alma sob flexao k=23,9 (formula fechada) como ordem de grandeza do Mcrl.
# ===========================================================================
import distorcional_fsm as fsm

UE_REF = (200.0, 75.0, 20.0, 2.0)


def test_fsm_secao_ue_e_simetrica_e_fechada():
    """A linha media do Ue e' simetrica em y (alma centrada em x=0) e cada
    par de nos vira um elemento com a espessura t."""
    coord, ends = fsm.secao_ue(*UE_REF)
    assert len(ends) == len(coord) - 1
    assert all(e[2] == pytest.approx(UE_REF[3]) for e in ends)
    cima = {(round(float(x), 9), round(float(y), 9)) for x, y in coord}
    espelhada = {(round(float(x), 9), round(-float(y), 9)) for x, y in coord}
    assert cima == espelhada


def test_fsm_minimos_locais_acha_vales_interiores():
    """_minimos_locais: vale interior entra, borda e monotono nao entram."""
    assert fsm._minimos_locais([0, 1, 2], [3.0, 1.0, 2.0]) == [1]
    assert fsm._minimos_locais([0, 1, 2], [1.0, 2.0, 3.0]) == []
    assert fsm._minimos_locais([0, 1], [1.0, 2.0]) == []


@pytest.mark.skipif(not fsm._HAS_PYCUFSM, reason="pycufsm indisponivel")
def test_fsm_mdist_positivo_e_ordenado():
    """Ue200x75x20x2.0: Mdist finito e Lcrd >= Lcrl (distorcional e' o minimo
    intermediario, nao o local)."""
    r = fsm.mdist(*UE_REF, fy=250.0)
    assert r["Mdist_kNm"] > 0.0
    assert r["Mcrl_kNm"] > 0.0
    assert r["Lcrd_mm"] >= r["Lcrl_mm"]


@pytest.mark.skipif(not fsm._HAS_PYCUFSM, reason="pycufsm indisponivel")
def test_fsm_local_confere_placa_da_alma_k23_9():
    """Sanidade independente: a tensao de flambagem LOCAL do FSM tem de ficar
    na ordem da flambagem de placa da alma sob flexao (k=23,9)."""
    r = fsm.mdist(*UE_REF, fy=250.0)
    E, nu, bw, t = 200000.0, 0.3, UE_REF[0], UE_REF[3]
    wc = r["My_kNm"] * 1e6 / 250.0  # Wc = My/fy
    sig_fsm = r["Mcrl_kNm"] * 1e6 / wc
    sig_placa = 23.9 * math.pi ** 2 * E / (12.0 * (1.0 - nu ** 2)) * (t / bw) ** 2
    assert 0.5 < sig_fsm / sig_placa < 2.0


@pytest.mark.skipif(not fsm._HAS_PYCUFSM, reason="pycufsm indisponivel")
def test_fsm_injecao_sem_minimos_vira_erro(monkeypatch):
    """Defeito: detector de minimos cego (retorna []). O mdist bom devolve
    Mdist; com o defeito, devolve `erro` e nenhum Mdist - a extracao depende
    do detector."""
    bom = fsm.mdist(*UE_REF, fy=250.0)
    assert "Mdist_kNm" in bom
    monkeypatch.setattr(fsm, "_minimos_locais", lambda x, y: [])
    quebrado = fsm.mdist(*UE_REF, fy=250.0)
    assert "erro" in quebrado
    assert "Mdist_kNm" not in quebrado


# ===========================================================================
# 3. recalque_edificio - recalque diferencial do predio.
# Cobertura transitiva parcial: tests/branches/g9/test_g9_fundacao_no_loop.py
# e test_edificio_adapter.py asseveram o ESCOPO ("not_available" sem Es), mas
# nada exercia `calcula` com Es nem `declarada`. Testes diretos abaixo.
# Fonte independente: declara-ou-recusa (sem Es nao ha numero) + monotonia
# fisica (mesma sapata, dobro da carga -> dobro do recalque elastico).
# ===========================================================================
import recalque_edificio as rce


def _fundacao_2pilares(n1=400.0, n2=800.0):
    geo = {"B_m": 2.0, "L_m": 2.0}
    return {"por_pilar": {
        "P1": {"geometria": dict(geo), "N_dimensionamento_kN": n1},
        "P2": {"geometria": dict(geo), "N_dimensionamento_kN": n2}}}


def test_recalque_sem_es_recusa_sem_inventar():
    """Sem Es declarado: gate reprovado por motivo escrito, recalques None,
    aviso `recalque_Es_nao_declarado` - nunca um numero arbitrado."""
    r = rce.calcula({}, _fundacao_2pilares())
    assert r["gate"] == {"OK": False, "motivo": "Es_solo nao declarado"}
    assert r["recalque_max_mm"] is None
    assert all(v.get("recalque_mm") is None for v in r["por_pilar"].values())
    assert any(a["code"] == "recalque_Es_nao_declarado" for a in r["avisos"])


def test_recalque_com_es_calcula_e_gate_fecha():
    """Com Es: um numero por pilar (drawing-vs-data), monotono na carga, e o
    gate OK carrega max/min/diferencial consistentes."""
    r = rce.calcula({"recalque": {"Es_solo": 20000.0}}, _fundacao_2pilares())
    assert set(r["por_pilar"]) == {"P1", "P2"}
    p1 = r["por_pilar"]["P1"]["recalque_mm"]
    p2 = r["por_pilar"]["P2"]["recalque_mm"]
    assert p1 is not None and p2 is not None
    assert p2 == pytest.approx(2.0 * p1, rel=1e-2)  # elastico linear em N
    g = r["gate"]
    assert g["OK"] is True
    assert g["recalque_max_mm"] == pytest.approx(p2)
    assert g["diferencial_mm"] == pytest.approx(p2 - p1)
    assert g["reprova_por"] == []


def test_recalque_sobrecarga_reprova_com_motivo():
    """Dobro da carga admissivel estourada: gate False COM `reprova_por`
    (veredito ruim aparece, nao some - familia da saturacao silenciosa)."""
    r = rce.calcula({"recalque": {"Es_solo": 20000.0}},
                     _fundacao_2pilares(n1=400.0, n2=4000.0))
    assert r["gate"]["OK"] is False
    assert r["gate"]["reprova_por"] != []


def test_recalque_declarada_e_entrada_invalida():
    assert rce.declarada({}) is False
    assert rce.declarada({"Es": 1.0}) is True
    assert rce.declarada({"recalque": {"Es_solo": 5.0}}) is True
    with pytest.raises(rce.EntradaRecalque):
        rce.calcula({"recalque": {"Es_solo": -3.0}}, _fundacao_2pilares())


def test_recalque_injecao_tirar_o_es_vira_recusa():
    """Baseline nos dois sentidos: o MESMO calculo que da numero com Es
    recusa sem Es (copia em memoria - o spec do repo nao e' mutado)."""
    fund = _fundacao_2pilares()
    com_es = rce.calcula({"recalque": {"Es_solo": 20000.0}}, fund)
    sem_es = rce.calcula({}, fund)
    assert com_es["por_pilar"]["P1"]["recalque_mm"] is not None
    assert sem_es["por_pilar"]["P1"]["recalque_mm"] is None
    assert sem_es["gate"]["OK"] is False


# ===========================================================================
# 4. junta_dilatacao - junta + movimento termico (FCC Report 65 via Bellei).
# Fonte independente: delta = alpha*dT*L (fisica) e Lmax 62,4 m do guia
# (120*(1-0,33-0,15) para galpao retangular sem aquecimento e base fixa).
# ===========================================================================
import junta_dilatacao as jd


def test_junta_movimento_e_alpha_dT_L():
    assert jd.movimento_termico(100.0, 30.0) == pytest.approx(12e-6 * 30.0 * 100.0)
    assert jd.movimento_termico(50.0, 30.0) * 2.0 == pytest.approx(jd.movimento_termico(100.0, 30.0))


def test_junta_galpao_tipico_Lmax_62_4m():
    lmax, f = jd.comprimento_max_junta(retangular=True, aquecido=False, base_fixa=True)
    assert f == pytest.approx(-0.33 - 0.15)
    assert lmax == pytest.approx(62.4)
    lmax2, f2 = jd.comprimento_max_junta(retangular=False, aquecido=True, base_fixa=False)
    assert lmax2 == pytest.approx(60.0) and f2 == pytest.approx(0.0)


def test_junta_100m_precisa_1_40m_nao_precisa():
    r = jd.verifica_junta(100.0)
    assert r["precisa_junta"] and r["n_juntas"] == 1 and r["n_segmentos"] == 2
    assert r["L_segmento"] == pytest.approx(50.0)
    assert r["delta_segmento_mm"] == pytest.approx(12e-6 * 30.0 * 50.0 * 1000.0)
    r2 = jd.verifica_junta(40.0)
    assert not r2["precisa_junta"] and r2["n_juntas"] == 0 and r2["OK"]


def test_junta_injecao_Lmax_infinito_apaga_a_junta(monkeypatch):
    """Defeito: Lmax infinito. O galpao de 100 m deixa de precisar de junta -
    a guarda `precisa_junta` depende do Lmax, nao e' constante."""
    assert jd.verifica_junta(100.0)["precisa_junta"] is True
    monkeypatch.setattr(jd, "comprimento_max_junta", lambda *a, **k: (1e9, 0.0))
    assert jd.verifica_junta(100.0)["precisa_junta"] is False


# ===========================================================================
# 5. tercas_iteracao - escada Ue, adota a mais leve que passa (NBR 14762).
# Nada a nomeava; `verifica_terca` (tercas_nbr14762) tem testes proprios, mas
# ninguem testava a ADOCAO (a mais leve que passa) nem que o Mdist do FSM
# alimenta a cadeia. Portao: adotado x necessario (convencao 4).
# ===========================================================================
import tercas_iteracao as ti


@pytest.fixture()
def _cfg_tercas_preservado():
    salvo = (ti.BAY, ti.LY, ti.TRIB, ti.THETA, ti.FY)
    try:
        yield
    finally:
        ti.BAY, ti.LY, ti.TRIB, ti.THETA, ti.FY = salvo


def test_tercas_configurar_declara_e_preserva(_cfg_tercas_preservado):
    ti.configurar(bay=6.0, ly=3.0, trib=1.8, fy=300e3)
    assert (ti.BAY, ti.LY, ti.TRIB, ti.FY) == (6.0, 3.0, 1.8, 300e3)
    ti.configurar(bay=None)
    assert ti.BAY == 6.0  # None mantem o atual


def test_tercas_sucao_e_negativa():
    """A pior succao na cobertura e' pressao negativa (fisica, nao codigo)."""
    assert ti._sucao_caracteristica() < 0.0


def test_tercas_melhor_adota_da_escada_com_mdist():
    """O adotado vem da escada, carrega o Mdist do FSM (a cadeia FSM ->
    iteracao esta ligada) e o veredito vem junto (adotado x necessario)."""
    r = ti.melhor()
    assert r["_dims"] in ti.ESCADA
    assert r["Mdist"] is not None and r["Mdist"] > 0.0
    assert r["OK"] in (True, False)  # `and` sobre numpy.bool_ vaza np.bool_; vale o valor
    assert "interacao" in r and "flecha_v" in r


def test_tercas_injecao_tudo_reprovado_adota_ultimo_sem_ok(monkeypatch):
    """Defeito: verificacao que reprova tudo. O `melhor` tem de devolver o
    ultimo COM OK=False - nunca declarar PASSA em cima de reprova (a classe
    de bug da saturacao silenciosa)."""
    import tercas_nbr14762 as tc

    real = tc.verifica_terca

    def tudo_reprova(perfil, cfg):
        r = real(perfil, cfg)
        for c in r["casos"].values():
            c["OK"] = False
            c["interacao"] = 9.99
        return r

    monkeypatch.setattr(tc, "verifica_terca", tudo_reprova)
    r = ti.melhor()
    assert not r["OK"]
    assert r["_dims"] == ti.ESCADA[-1]


def test_tercas_injecao_tudo_aprovado_adota_o_mais_leve(monkeypatch):
    """Defeito inverso: verificacao que aprova tudo. O adotado tem de ser o
    PRIMEIRO da escada (o mais leve) - a ordem da escada decide."""
    import tercas_nbr14762 as tc

    real = tc.verifica_terca

    def tudo_aprova(perfil, cfg):
        r = real(perfil, cfg)
        for c in r["casos"].values():
            c["OK"] = True
            c["interacao"] = 0.01
        r["els"]["ok_grav"] = True
        r["els"]["ok_vento"] = True
        return r

    monkeypatch.setattr(tc, "verifica_terca", tudo_aprova)
    r = ti.melhor()
    assert r["OK"]
    assert r["_dims"] == ti.ESCADA[0]


# ===========================================================================
# 6. layout_ambientes - primitiva de retangulo de comodo.
# O G78 cobre `conferir_areas_programa_layout` em test_planta_baixa_g78
# (nao duplicado aqui); abaixo o resto: validar/duplicar/sobrepor/dentro.
# ===========================================================================
import layout_ambientes as la


def _comodo(id_, x=0.0, y=0.0, w=3.0, d=4.0):
    return {"id": id_, "name": id_, "x_m": x, "y_m": y, "width_m": w, "depth_m": d}


def test_layout_validar_aceita_bom_e_rejeita_ruins():
    erros = []
    comodos = la.validar_comodos({"rooms": [_comodo("sala"), _comodo("coz", x=3.0)]}, erros)
    assert set(comodos) == {"sala", "coz"} and erros == []

    casos = [
        ({"rooms": []}, "missing_layout_field"),
        ({"rooms": [{"id": "s"}]}, "missing_layout_field"),  # campos faltando
        ({"rooms": [_comodo("a"), _comodo("a", x=5.0)]}, "duplicate_layout_room"),
        ({"rooms": [_comodo("a"), _comodo("b", x=1.0)]}, "overlapping_layout_rooms"),
        ({"rooms": [_comodo("a", w=-1.0)]}, "invalid_layout_value"),
    ]
    for layout, codigo in casos:
        erros = []
        la.validar_comodos(layout, erros)
        assert any(e["code"] == codigo for e in erros), (layout, erros)


def test_layout_dentro_e_envolvente():
    c = _comodo("sala", x=1.0, y=2.0, w=3.0, d=4.0)
    assert la.dentro(c, 2.0, 3.0)
    assert not la.dentro(c, 0.9, 3.0)
    env = la.envolvente([c, _comodo("coz", x=4.0, y=0.0, w=2.0, d=2.0)])
    assert env == {"x_min": 1.0, "y_min": 0.0, "x_max": 6.0, "y_max": 6.0}


def test_layout_injecao_sobrepor_acusa_e_afastar_libera():
    """Baseline nos dois sentidos: os mesmos dois comodos sobrepostos acusam;
    afastados (copia em memoria), passam."""
    sobrepostos = {"rooms": [_comodo("a"), _comodo("b", x=1.0)]}
    erros = []
    la.validar_comodos(sobrepostos, erros)
    assert any(e["code"] == "overlapping_layout_rooms" for e in erros)
    afastados = {"rooms": [_comodo("a"), _comodo("b", x=3.0)]}
    erros = []
    la.validar_comodos(afastados, erros)
    assert erros == []


# ===========================================================================
# 7. pycufsm_compat - shim numpy>=2 do pycufsm 0.2.0.
# Cobertura transitiva: tudo que usa FSM (distorcional_fsm, tercas_iteracao)
# passa por `import pycufsm_compat`. Abaixo o teste direto do contrato do
# shim (semantica numpy<2 onde o numpy>=2 quebrou), valido nas duas versoes.
# ===========================================================================
import pycufsm_compat as compat


def test_compat_apply_e_idempotente():
    assert compat.apply() == compat.apply()


def test_compat_diff_desempacota_escalar():
    """np.diff de 2 elementos devolve array(1) no numpy>=1; o shim devolve o
    escalar (a semantica numpy<2 que o prop2 espera)."""
    import numpy as np

    proxy = compat._make_proxy(np)
    assert proxy.diff([1.0, 2.0]) == pytest.approx(1.0)
    assert not isinstance(proxy.diff([1.0, 2.0]), np.ndarray)
    np.testing.assert_allclose(proxy.diff([1.0, 2.0, 4.0]), np.diff([1.0, 2.0, 4.0]))


def test_compat_argwhere_int_seguro_apos_reshape():
    """int(argwhere(...).reshape(1)) e' o que quebrava no numpy>=2 (B)."""
    import numpy as np

    proxy = compat._make_proxy(np)
    r = proxy.argwhere(np.array([5, 0, 5]) == 0)
    assert int(r.reshape(1)) == 1


def test_compat_injecao_passthrough_nao_cumpre_o_contrato():
    """Se o shim virasse pass-through (defeito: delegar sem corrigir), o
    diff de tamanho 1 voltaria a ser ndarray - o teste acima ficaria
    vermelho. Aqui a prova de que o teste distingue shim de no-op."""

    class PassThrough:
        def __getattr__(self, name):
            import numpy as np

            return getattr(np, name)

    import numpy as np

    cru = PassThrough().diff([1.0, 2.0])
    assert isinstance(cru, np.ndarray)  # sem o shim, o contrato quebra


# ===========================================================================
# 8. casa_residencial_sintetica - fixture de contrato (decisao G10 CONFIRMADA,
# nao redecidida: ver REVISAO-G10-FIXTURE-SINTETICA.md).
# Cobertura transitiva: tests/branches/project_loop/
# test_project_loop_generalization.py (guarda `test_a_fixture_sintetica_e_o_
# unico_adaptador_nativo_sem_hooks` + teste de `synthetic_fixture`). Abaixo o
# teste direto que NOMEIA o modulo (era o gap do G85).
# ===========================================================================
import project_loop  # noqa: F401 (ANTES da sintetica: project_loop registra
# builtin_adapters no import; importar a sintetica primeiro cicla)
import casa_residencial_sintetica as sint


def _normalized(disciplinas=("arquitetura", "eletrico")):
    return {"turnkey_spec": {d: {} for d in disciplinas},
            "requested_disciplines": list(disciplinas),
            "project_id": "g85-probe"}


def test_sintetica_resultado_de_contrato_nao_obra(tmp_path):
    """Fixture: `synthetic_fixture` True, ZERO artefatos, aviso em toda
    disciplina; presente -> needs_review, ausente -> blocked com motivo."""
    res, registros = sint._run_residential_synthetic(_normalized(), str(tmp_path))
    assert res["adapter"] == sint.ADAPTER_NAME == "casa-residencial-sintetica"
    assert res["synthetic_fixture"] is True
    for nome, reg in registros.items():
        assert reg["artifacts"] == []
        assert any(a["code"] == "synthetic_fixture" for a in reg["warnings"])
    assert registros["arquitetura"]["status"] == "needs_review"
    res2, reg2 = sint._run_residential_synthetic(
        {"turnkey_spec": {}, "requested_disciplines": ["arquitetura"],
         "project_id": "g85-probe"}, str(tmp_path))
    assert reg2["arquitetura"]["status"] == "blocked"
    assert reg2["arquitetura"]["errors"] == [{"code": "missing_synthetic_input"}]
    assert res2["synthetic_fixture"] is True


def test_sintetica_registrada_sem_hooks():
    """O modulo registra o adaptador e ele continua o unico sem hooks
    (o caminho sem-hook do nucleo que so ela guarda - G10)."""
    import project_loop as pl

    sint.register_residential_adapter()
    assert sint.ADAPTER_NAME in pl._PROJECT_ADAPTERS
    assert sorted(pl._PROJECT_HOOKS[sint.ADAPTER_NAME]) == []


def test_sintetica_injecao_hook_apaga_a_cobertura():
    """Defeito: dar um hook a fixture. O predicado da guarda (sem hooks ==
    [fixture]) quebra - por isso a docstring do modulo proibe hooks."""
    import project_loop as pl

    sint.register_residential_adapter()
    hooks = {n: sorted(v) for n, v in pl._PROJECT_HOOKS.items()}
    assert hooks[sint.ADAPTER_NAME] == []
    hooks[sint.ADAPTER_NAME] = ["ifc"]  # defeito injetado (copia em memoria)
    sem_hooks = sorted(n for n, v in hooks.items() if not v)
    assert sint.ADAPTER_NAME not in sem_hooks  # a guarda acusaria


# ===========================================================================
# 9. smoke_executivo - smoke do executivo (techdraw_exec).
# `rodar()` exige FreeCAD + minutos: NAO coberto aqui de proposito (manual).
# O que e' testavel rapido: `checar_carimbo` (pre-flight sem freecad) e
# `_acha_pendente` (o farejador de PENDENTE vazando no carimbo).
# ===========================================================================
import projeto_spec as PS
import smoke_executivo as smoke


def test_smoke_acha_pendente_no_caminho_certo():
    assert smoke._acha_pendente({"a": {"b": [PS.PENDENTE]}}) == "cfg.a.b[0]"
    assert smoke._acha_pendente({"a": 1, "b": [1, {"c": "ok"}]}) is None


def test_smoke_carimbo_limpo_sem_freecad(capsys):
    """Os 7 casos geometricos nao vazam __PENDENTE__ no carimbo (rapido)."""
    assert smoke.checar_carimbo() is True


def test_smoke_injecao_pendente_vazando_reprova(monkeypatch, capsys):
    """Defeito: config que vaza PENDENTE. O pre-flight tem de reprovar -
    sem ele o carimbo sairia com __PENDENTE__ impresso (regressao que o
    pre-flight trava)."""
    import techdraw_exec as td

    monkeypatch.setattr(td, "config_de_spec",
                        lambda s, f, o: {"vazou": PS.PENDENTE})
    assert smoke.checar_carimbo() is False
