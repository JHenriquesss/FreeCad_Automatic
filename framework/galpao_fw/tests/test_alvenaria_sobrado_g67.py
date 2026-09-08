"""G67 (grande): o G63 ganha consumidor — sobrado de 2 pav em alvenaria.

O G63 entregou 9.6.2 + 11.5 + Anexo C e nenhuma tipologia os alcancava; a
11.4 seguia not_available ("Vd reportado mas nao verificado") e o vento nao
tinha origem (Qh avulsa recusava, certo). Este lote sobe a fronteira para 2
pavimentos NA MEDIDA em que passa a calcular:

  vento NBR 6123 por nivel (Fa = Ca.q.Ae, Ca declarado do abaco) ->
  Fi por parede na 9.6.2 (flange 6t na 10.1.3) ->
  parede verificada na 11.5 (Nd + Md) E no cisalhamento 11.4 (Vd) ->
  vertical por nivel nas charneiras da 14.7.6.1 com fechamento total+simetria.

Cada teste prova relacao, nunca numero congelado (licao D86/D88/AR300).
"""
import copy
import sys
from pathlib import Path

import pytest

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import alvenaria_estrutural as alv  # noqa: E402
import estrutura_casa as ec  # noqa: E402


BASE = {
    "geometria": {"vaos_x": [4.0], "vaos_y": [5.0], "pe_direito": 2.7},
    "pavimentos": [{"nome": "Sup", "uso": "residencial_dormitorio"},
                   {"nome": "Ter", "uso": "residencial_dormitorio"}],
    "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
    "viga": {"b": 0.20, "h": 0.45},
    "materiais": {"fck": 25e3, "fyk": 500e3},
    "alvenaria_portante": {
        "fpk": 4000.0, "material": "bloco", "te": 0.14,
        "combinacao": "normal", "habitacao_terrea": False,
        "parede_6120": {"tipo": "bloco_concreto_estrutural",
                        "espessura_cm": 14.0, "revestimento_cm": 2.0},
        "linhas": "todas", "fa_MPa": 5.0},
    "vento": {"v0": 35.0, "cat": "II", "classe": "B",
              "ca": {"x": 0.9, "y": 1.1}},
    "baldrame": {"b": 0.15, "h": 0.40, "q_parede": 5.0},
    "fundacao": {"tipo": "sapata_corrida", "sigma_solo_adm": 150.0,
                 "cota_apoio_m": 1.0},
}


def _spec(**mud):
    s = copy.deepcopy(BASE)
    for k, v in mud.items():
        s[k] = copy.deepcopy(v)
    return s


@pytest.fixture(scope="module")
def sobrado():
    return ec.rodar(copy.deepcopy(BASE))


# --- o sobrado calcula e atende -------------------------------------------

def test_sobrado_roda_e_atende_com_tipologia_e_escopo(sobrado):
    assert sobrado["ATENDE"], sobrado["reprovados"]
    assert sobrado["tipologia"] == "alvenaria_sobrado"
    assert sobrado["n_pavimentos"] == 2
    assert sobrado["gates"]["alvenaria_portante"]["OK"] is True
    assert sobrado["gates"]["alvenaria_portante"]["n_pavimentos"] == 2
    assert sobrado["gates"]["alvenaria_portante"]["cisalhamento_11_4_OK"] is True
    assert sobrado["escopo"]["alvenaria_estrutural"] == "implemented"
    assert sobrado["escopo"]["vento_alvenaria_6123"] == "implemented"
    txt = ec.relatorio_pt(sobrado)
    assert "alvenaria_sobrado" in txt.upper() or "SOBRADO" in txt
    assert "11.4" in txt and "6123" in txt


def test_memorial_cita_vento_e_114_sem_fonte_ausente(sobrado):
    txt = ec.relatorio_pt(sobrado)
    assert "ausente" not in txt
    assert alv.linha_memorial_cadeia_gravitacional() in txt
    assert "G67" in alv.linha_memorial_cadeia_gravitacional()


# --- o Qh chega por nivel, da 6123, nao avulso ------------------------------

def test_qh_por_nivel_e_fa_da_6123_como_relacao(sobrado):
    import vento_nbr6123 as vt
    vento = sobrado["alvenaria"]["vento"]["por_direcao"]
    for direcao, l1 in (("x", 5.0), ("y", 4.0)):
        fa = vento[direcao]
        assert len(fa["niveis"]) == 2
        for niv in fa["niveis"]:
            _b, _fr, _p, s2 = vt.s2_factor("II", "B", niv["z_m"])
            q = 0.613 * (35.0 * s2) ** 2 / 1000.0
            assert niv["q_kN_m2"] == pytest.approx(q, abs=1e-4)
            ca = {"x": 0.9, "y": 1.1}[direcao]
            assert niv["Fa_kN"] == pytest.approx(
                ca * q * niv["Ae_m2"], abs=1e-3)
        assert fa["F_total_kN"] == pytest.approx(
            sum(v["Fa_kN"] for v in fa["niveis"]), abs=1e-6)


def test_distribuicao_fecha_por_nivel_como_relacao(sobrado):
    for chave, d in sobrado["alvenaria"]["vento"]["distribuicao"].items():
        direcao, nivel = chave.split("_n")
        nivel = int(nivel)
        fa = next(v["Fa_kN"] for v in
                  sobrado["alvenaria"]["vento"]["por_direcao"][
                      direcao]["niveis"] if v["nivel"] == nivel)
        assert d["soma_Fi_kN"] == pytest.approx(fa, abs=1e-6)
        assert alv.confere_fechamento_horizontal(d, fa)["OK"] is True
    # e a parede da base acumula os niveis (V = soma Fi, M = soma Fi.z)
    reg = next(r for r in sobrado["alvenaria"]["por_linha"]
               if r["nome"] == "BX-0")
    fis = {f["nivel"]: f for f in reg["fis_por_nivel"]}
    assert reg["V_kN"] == pytest.approx(
        sum(f["Fi_kN"] for f in fis.values()), abs=1e-3)
    assert reg["M_kNm"] == pytest.approx(
        sum(f["Fi_kN"] * f["z_m"] for f in fis.values()), abs=1e-3)
    assert reg["Vd_kN"] == pytest.approx(1.4 * reg["V_kN"], abs=1e-3)
    assert reg["Md_kNm"] == pytest.approx(1.4 * reg["M_kNm"], abs=1e-3)


def test_qh_avulsa_segue_recusando_regressao():
    s = _spec()
    s["alvenaria_portante"] = dict(s["alvenaria_portante"],
                                   acao_horizontal_kN=5.0)
    r = ec.rodar(s)
    assert r["alvenaria_erro"] is not None
    assert "avulsa" in r["alvenaria_erro"]


def test_sobrado_sem_vento_recusa_nomeando():
    s = _spec()
    del s["vento"]
    r = ec.rodar(s)
    assert r["alvenaria_erro"] is not None
    assert "pede_vento" in r["alvenaria_erro"]


def test_sobrado_sem_fa_recusa_nomeando():
    s = _spec()
    del s["alvenaria_portante"]["fa_MPa"]
    r = ec.rodar(s)
    assert r["alvenaria_erro"] is not None
    assert "fa_MPa" in r["alvenaria_erro"]


def test_acima_de_2_pavimentos_recusa_nomeando():
    s = _spec(pavimentos=[{"nome": "C%d" % i,
                           "uso": "residencial_dormitorio"} for i in range(3)])
    with pytest.raises(ec.EntradaEstrutura, match="ate 2 pavimentos"):
        ec.rodar(s)


# --- a 11.4: fvk da Tab.4, tau contra fvd, fail-closed -----------------------

def test_fvk_tabela_4_por_faixa_como_relacao():
    for fa, tau0, teto in ((2.0, 0.10, 1.0), (5.0, 0.15, 1.4),
                           (8.0, 0.35, 1.7)):
        f = alv.fvk_caracteristico_6226(fa, 0.39)
        assert f["fvk_MPa"] == pytest.approx(
            min(tau0 + 0.5 * 0.39, teto), abs=1e-9)
        assert f["fvk_kN_m2"] == pytest.approx(f["fvk_MPa"] * 1000.0,
                                              abs=1e-6)
    with pytest.raises(alv.EntradaAlvenaria, match="fa_nao_declarada"):
        alv.fvk_caracteristico_6226(None, 0.39)
    with pytest.raises(alv.EntradaAlvenaria, match="fa_fora_da_tabela_4"):
        alv.fvk_caracteristico_6226(1.0, 0.39)


def test_114_fail_closed_nos_dois_lados_e_peso_zero():
    r = alv.verifica_cisalhamento_114(10.0, 60.0, 0.14, 2.40, 5.0)
    assert r["OK"] is True and r["peso_proprio_interno_kN"] == 0.0
    assert r["tau_vd_kN_m2"] == pytest.approx(10.0 / (0.14 * 2.40), abs=1e-3)
    assert r["VRd_kN"] == pytest.approx(r["fvd_kN_m2"] * 0.14 * 2.40,
                                       abs=1e-2)
    vrd = r["VRd_kN"]
    assert alv.verifica_cisalhamento_114(
        vrd * 0.999, 60.0, 0.14, 2.40, 5.0)["OK"] is True
    assert alv.verifica_cisalhamento_114(
        vrd * 1.001, 60.0, 0.14, 2.40, 5.0)["OK"] is False
    ruim = alv.verifica_cisalhamento_114(
        vrd * 1.001, 60.0, 0.14, 2.40, 5.0)
    assert "cisalhamento_insuficiente" in ruim["motivo"]
    # sigma leva o 0,9 favoravel por dentro: dobrar N_perm dobra a folga
    r2 = alv.verifica_cisalhamento_114(10.0, 120.0, 0.14, 2.40, 5.0)
    assert r2["sigma_MPa"] == pytest.approx(2 * r["sigma_MPa"], abs=1e-4)
    assert r2["fvk_MPa"] > r["fvk_MPa"]


def test_114_sem_junta_preenchida_recusa():
    r = alv.verifica_cisalhamento_114(10.0, 60.0, 0.14, 2.40, 5.0,
                                      juntas_verticais_preenchidas=False)
    assert r["OK"] is False and r["veredito"] == "recusado"
    assert "juntas_verticais" in r["motivo"]


def test_114_governa_sozinha_na_integracao():
    # vento forte + parede armada na 11.5: a flexao passa e o cisalhamento
    # reprova — a parede que recebe o Fi cai na 11.4, nao so na compressao.
    s = _spec()
    s["alvenaria_portante"] = dict(s["alvenaria_portante"], fa_MPa=2.0,
                                   As_m2=4e-4, fyk=500e3)
    s["vento"] = {"v0": 100.0, "cat": "II", "classe": "B",
                  "ca": {"x": 0.9, "y": 1.1}}
    r = ec.rodar(s)
    assert r["ATENDE"] is False
    assert "alvenaria_portante" in r["reprovados"]
    reg = next(x for x in r["alvenaria"]["por_linha"] if x["nome"] == "BX-0")
    assert reg["verificacao"]["OK"] is True
    assert reg["cisalhamento_11_4"]["OK"] is False
    assert "cisalhamento_insuficiente" in reg["cisalhamento_11_4"]["motivo"]
    assert r["gates"]["alvenaria_portante"]["cisalhamento_11_4_OK"] is False


# --- o vertical do G61 por cima: charneiras por nivel ------------------------

def test_quinhao_gq_soma_no_total_e_vem_da_charneira(sobrado):
    import estrutura_casa as _ec
    pavs = sobrado["alvenaria"]
    assert pavs["n_pavimentos"] == 2
    # G+Q por linha somam no N_laje da base (dois niveis acumulados)
    for reg in sobrado["alvenaria"]["por_linha"]:
        assert reg["N_laje_kN"] == pytest.approx(
            reg["N_laje_G_kN"] + reg["N_laje_Q_kN"], abs=1e-2)
    # a soma G+Q das funcoes coincide com o quinhao total (relacao)
    assert _ec.quinhao_laje_por_linha_gq is not None


def test_fechamento_total_e_simetria_por_nivel(sobrado):
    fch = sobrado["alvenaria"]["fechamento"]
    assert fch["ok"] is True and fch["simetria_ok"] is True
    assert fch["simetria_pares"] >= 1
    for s in sobrado["alvenaria"]["simetrias_por_nivel"]:
        assert s["ok"] is True


def test_quinhao_por_nivel_e_o_da_charneira_nao_o_comprimento():
    import laje_concreto as lj
    s = _spec()
    s["geometria"] = {"vaos_x": [4.0], "vaos_y": [9.0], "pe_direito": 2.7}
    del s["baldrame"]
    del s["fundacao"]
    r = ec.rodar(s)
    assert r["gates"]["alvenaria_portante"]["OK"], \
        r["gates"]["alvenaria_portante"]["reprovadas"]
    pav = r["pavimento"]
    p = pav["g_kN_m2"] + pav["q_kN_m2"]
    esperado = lj.reacoes_apoios(1, 4.0, 9.0, p)
    v_longa = esperado["x0"]["v"]
    por = {reg["nome"]: (reg["N_laje_G_kN"] + reg["N_laje_Q_kN"])
           / reg["comprimento_m"] / 2.0
           for reg in r["alvenaria"]["por_linha"]}
    assert por["BY-0"] == pytest.approx(v_longa, rel=1e-6)


# --- 10.1.1 e Tab.9 reprovam sem NRd no sobrado -------------------------------

def test_esbeltez_reprova_sem_nrd_no_sobrado():
    s = _spec()
    s["geometria"] = {"vaos_x": [4.0], "vaos_y": [5.0], "pe_direito": 4.5}
    r = ec.rodar(s)
    assert r["ATENDE"] is False
    v = r["alvenaria"]["por_linha"][0]["verificacao"]
    assert "esbeltez_acima_do_teto" in v["motivo"]
    assert "NRd_kN" not in v


def test_espessura_1011_no_terceiro_pavimento():
    r = alv.verifica_parede_compressao(1.0, 4000.0, 2.40, 0.10, 0.10,
                                       n_pavimentos=3)
    assert r["OK"] is False and "espessura_minima_14cm" in r["motivo"]


# --- escopo publica o dentro --------------------------------------------------

def test_escopo_g67_implemented():
    esc = alv.escopo()
    assert esc["cisalhamento_11_4"] == "implemented"
    assert esc["vento_por_nivel_6123"] == "implemented"
    assert "11.4" in alv.motivos_escopo()["cisalhamento_11_4"]
    assert alv._selftest() is True
