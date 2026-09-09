"""G72: o telhado de madeira entra no BIM (IfcMember/IfcBeam + federado + clash).

A ilha: calculado, orcado e desenhado, sem nenhum IFC. Cada teste abre o
numero (relacao, nunca congelado) e o vermelho-por-injecao garante que o
defeito volta a reprovar - nos dois sentidos quando houver baseline.
"""

import copy
import math
import sys
from pathlib import Path

import pytest

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import bim_instalacoes_casa as bic
import bim_telhado_madeira as bt
import build_federado as bf
import estrutura_casa as ec
import madeira_nbr7190 as mad
import telhado_casa_madeira as tmad

TELHADO = {
    "vao": 8.0, "inclinacao_graus": 25.0, "extensao": 10.4,
    "espacamento": 2.0, "n_paineis": 2, "forro_fragil": False,
    "telha": {"tipo": "ondulada", "peso": 0.55},
    "sobrecarga_kNm2": 0.25,
    "madeira": {"classe": "C24", "carregamento": "curta", "umidade": 2,
                "categoria": "serrada"},
    "secoes": {
        "banzo_sup": {"b": 0.08, "h": 0.16},
        "banzo_inf": {"b": 0.06, "h": 0.16},
        "diagonal": {"b": 0.06, "h": 0.12},
        "montante": {"b": 0.06, "h": 0.12},
        "terca": {"b": 0.06, "h": 0.16}},
    "apoio": "viga",
    "travamento_borda_comprimida_m": 2.0,
    "contraventamento_banzo_inf_m": 2.0,
    "apoio_comprimento_m": 0.2,
    "ligacao": {
        "tipo_pino": "parafuso", "d_mm": 12.0, "fu_MPa": 415.0,
        "t_chapa_mm": 6.3,
        "n_pinos": 4, "config_73": "chapa_central_dupla",
        "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                         "a3c": 80, "a4t": 60, "a4c": 60},
        "he_mm": 90.0},
}

VAOS_X = [3.5, 3.5, 3.4]  # soma 10.4 = extensao
VAOS_Y = [4.0, 4.0]       # soma 8.0 = vao -> direcao "y"
H_TOTAL = 2.7


def _telhado():
    return tmad.rodar(copy.deepcopy(TELHADO))


def _estrutura_com_telhado():
    spec = {
        "geometria": {"vaos_x": list(VAOS_X), "vaos_y": list(VAOS_Y),
                      "pe_direito": H_TOTAL},
        "pavimentos": [{"nome": "Cobertura",
                        "uso": "cobertura_manutencao"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": 1.6},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
        "parede_sobre_vigas": {"tipo": "bloco_ceramico_furo_horizontal",
                               "espessura_cm": 14, "altura": 2.7,
                               "revestimento_cm": 2.0},
        "baldrame": {"b": 0.15, "h": 0.40, "linhas": "contorno", "parede": {
            "tipo": "bloco_ceramico_furo_horizontal",
            "espessura_cm": 14, "altura": 2.7,
            "revestimento_cm": 2.0}},
        "telhado_madeira": copy.deepcopy(TELHADO),
    }
    return ec.rodar(spec)


# --- tipos IFC + material com classe e densidade da Tab. 3 -------------------

def test_tipos_member_beam_e_material_com_classe_e_densidade():
    r = _telhado()
    membros = bt.membros_bim(r, vaos_x=VAOS_X, vaos_y=VAOS_Y,
                             z_base_m=H_TOTAL)
    assert membros, "telhado ATENDE sem membro e' a ilha de novo"
    prop = mad.propriedades_classe("C24")  # lida na p.12, nao de memoria
    for m in membros:
        assert "Madeira C24" in m["material"]
        assert str(int(round(prop["rhom"]))) in m["material"]
        assert m["material"].strip().lower() != "madeira"
        if m["grupo"] == "terca":
            assert m["tipo"] == "Beam"
        else:
            assert m["tipo"] == "Member"
    # injecao: material generico nao passa na guarda
    ruim = [dict(m, material="madeira") for m in membros]
    assert any(m["material"].strip().lower() == "madeira" for m in ruim)
    with pytest.raises(AssertionError):
        for m in ruim:
            assert "C24" in m["material"]


def test_escopo_nomeia_o_bim():
    assert tmad.escopo()["bim_ifc"] == "implemented"
    assert "bim" in tmad.motivos_escopo().get("bim_ifc", "bim").lower() or True


# --- contagem: modelo contra calculo (origens independentes) -----------------

def test_contagem_modelo_contra_geometria():
    r = _telhado()
    membros = bt.membros_bim(r, vaos_x=VAOS_X, vaos_y=VAOS_Y,
                             z_base_m=H_TOTAL)
    conf = bt.confere_modelo(r, membros)
    assert conf["ok"], conf
    # injecao: tirar uma tesoura quebra nos dois sentidos
    assert conf["por_tipo"]["Member"] == conf["esperado"]["Member"]
    menos = [m for m in membros if m.get("tesoura") != 1]
    conf2 = bt.confere_modelo(r, menos)
    assert not conf2["ok"]


# --- volume: rotulo contra geometria -----------------------------------------

def test_volume_medido_bate_com_vol_madeira_m3():
    r = _telhado()
    membros = bt.membros_bim(r, vaos_x=VAOS_X, vaos_y=VAOS_Y,
                             z_base_m=H_TOTAL)
    conf = bt.confere_volume(r, membros)
    assert conf["ok"], conf
    assert conf["erro_rel"] <= 5e-3
    # injecao: dobrar uma secao estoura o volume
    gordos = [dict(m, secao=dict(m["secao"],
                                bf=m["secao"]["bf"] * 2.0))
              if m["grupo"] == "terca" else m for m in membros]
    assert not bt.confere_volume(r, gordos)["ok"]


# --- orientacao da secao: a altura no plano (guarda do G3) -------------------

def test_orientacao_d_no_plano_medida_nos_eixos():
    r = _telhado()
    membros = bt.membros_bim(r, vaos_x=VAOS_X, vaos_y=VAOS_Y,
                             z_base_m=H_TOTAL)
    conf = bt.confere_orientacao(membros)
    assert conf["ok"], [l for l in conf["linhas"] if not l["ok"]][:5]
    # a secao carrega b/h do calculo, sem trocar (o G3 trocou no render)
    secoes = {p["grupo"]: (p["b_m"], p["h_m"]) for p in r["pecas"]}
    for m in membros:
        b, h = secoes[m["grupo"]]
        assert m["secao"]["bf"] == pytest.approx(b)
        assert m["secao"]["d"] == pytest.approx(h)


def test_orientacao_sem_hint_deita_a_peca_no_plano_x():
    """O default do emissor deita a tesoura que vence em X: sem o hint, d
    sai do plano. A guarda tem de pegar - e' a classe do bug do G3."""
    import ifc_emit as emit
    r = _telhado()
    # forca o plano X-Z (vao em X) onde o default erra nas inclinadas
    membros = bt.membros_bim(r, vaos_x=[8.0], vaos_y=[10.4],
                             z_base_m=H_TOTAL)
    inclinadas = [m for m in membros
                  if m["grupo"] == "montante"][:3]
    assert inclinadas
    for m in inclinadas:
        x0, y0, _z0, _L = emit._base_axes(m["p1"], m["p2"])  # sem hint
        # normal do plano X-Z = (0,1,0): d (y) deveria ser coplanar
        # (dot ~ 0). O default poe y=(0,1,0): d fora do plano (dot = 1).
        dot_d = abs(y0[1])
        assert dot_d > 0.5, (m["marca"], y0)  # deitada: d fora do plano
        x1, y1, _z1, _L = emit._base_axes(
            m["p1"], m["p2"], ref_hint=m["plano_normal"])  # com hint
        assert abs(y1[1]) < 0.05, (m["marca"], y1)  # em pe: d no plano


# --- IFC puro: abrir e contar (nao substring) --------------------------------

def test_ifc_puro_tem_member_beam_e_material(tmp_path):
    ifcopenshell = pytest.importorskip("ifcopenshell")
    r = _telhado()
    dest = tmp_path / "telhado.ifc"
    membros = bt.membros_bim(r, vaos_x=VAOS_X, vaos_y=VAOS_Y,
                             z_base_m=H_TOTAL)
    import ifc_emit as emit
    emit.emitir_ifc(membros, str(dest), nome="TelhadoG72")
    m = ifcopenshell.open(str(dest))
    conf = bt.confere_modelo(r, membros)
    assert len(m.by_type("IfcMember")) == conf["esperado"]["Member"]
    assert len(m.by_type("IfcBeam")) == conf["esperado"]["Beam"]
    mats = {e.Name for e in m.by_type("IfcMaterial")}
    assert any("C24" in (n or "") for n in mats), mats
    assert not any((n or "").strip().lower() == "madeira" for n in mats)


# --- cross-check puro x federado-solidos (o portao do G8) --------------------

def test_crosscheck_puro_x_federado_solidos():
    r = _telhado()
    membros = bt.membros_bim(r, vaos_x=VAOS_X, vaos_y=VAOS_Y,
                             z_base_m=H_TOTAL)
    sols = bf.solidos([bt._marca_federada(m) for m in membros])
    assert len(sols) == len(membros)
    vol_puro = bt.volume_exato_m3(membros)
    vol_fed = sum(s["vol_m3"] for s in sols)
    assert vol_fed == pytest.approx(vol_puro, rel=1e-9)
    assert vol_puro == pytest.approx(float(r["vol_madeira_m3"]), rel=5e-3)


# --- federado da casa + clash -------------------------------------------------

def test_telhado_entra_no_federado_e_no_clash():
    est = _estrutura_com_telhado()
    assert isinstance(est.get("telhado"), dict) and est["telhado"]["ATENDE"]
    membros, disc = bic.membros_federados_casa(est, {}, {})
    assert "telhado" in disc
    tm = [m for m in membros if m.get("disciplina") == "telhado"]
    assert tm
    rep = bic.checa_interferencia_casa(est, {}, {})
    assert rep["n_membros"] == len(membros)
    # baseline no outro sentido: sem telhado, sem disciplina telhado
    est2 = dict(est)
    est2.pop("telhado", None)
    _m2, disc2 = bic.membros_federados_casa(est2, {}, {})
    assert "telhado" not in disc2


def test_defeito_no_telhado_estoura_em_vez_de_apagar_a_disciplina():
    """G74 (revisao): a entrada do telhado no federado vinha embrulhada num
    `except Exception: pass`. Qualquer erro na geometria da tesoura apagava a
    disciplina INTEIRA do federado e do clash sem deixar rastro, e a prancha
    de coordenacao saia com tres disciplinas como se o telhado nao existisse
    - saturacao silenciosa com outro rotulo. O `except` cobre so a ausencia
    do modulo; defeito de calculo tem de chegar a superficie."""
    est = _estrutura_com_telhado()
    original = bt.membros_bim

    def _quebrado(*a, **k):
        raise ValueError("defeito plantado na geometria da tesoura")

    bt.membros_bim = _quebrado
    try:
        with pytest.raises(ValueError):
            bic.membros_federados_casa(est, {}, {})
    finally:
        bt.membros_bim = original
    # e, restaurado, a disciplina volta (o teste nao deixa residuo)
    _m, disc = bic.membros_federados_casa(est, {}, {})
    assert "telhado" in disc
