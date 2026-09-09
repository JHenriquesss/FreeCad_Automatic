"""G74: o que a dispensa nao cobre (NBR 7190-1 6.5.6 alternativo + 6.6).

Lido na pagina do F136 (renderizado, nao de memoria):
- 6.5.6 dispensa p.27: L1/b <= E0,ef/(beta_M.fm,d), beta_M Tab.8 p.27
  (gama_f=1,4, beta_E=4); alternativo tres linhas abaixo p.27:
  sigma_c,d <= E_c0,ef/((L1/b).beta_M), mesmos Tab.8 e mesmos dados
  (E_c0,ef = E0,ef da 5.8.7 p.15).
- 6.6.2 p.28-29: F1d = Nd/150; Kbr,1,min = 2.alpha_m.pi2.E0,ef.I2/L1^3,
  alpha_m = 1+cos(pi/m) p.29 (Tab.9 confere).
- 6.6.3 p.29: mesmo para banzo comprimido (Nd = maxima do banzo / Rcd).
- 6.6.4 pp.30-31: cobertura sem analise rigorosa = trelicas verticais
  + horizontais/cobertura nas extremidades e intermediarias <= 20 m;
  por no F1d = Nd/150; extremidade Fd >= (2/3).n.F1d (Fig.6 p.30);
  rigidez Kbr >= (2/3).n.Kbr,1,min p.31.
- Booleano vira geometria: mesma licao do travado_borda_comprimida.

Cada teste abre o numero (relacao, nunca congelado) e o vermelho por
injecao mora dentro, nos dois sentidos quando houver baseline.
"""
import copy
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))
import madeira_nbr7190 as mad
import telhado_casa_madeira as tmad
TELHADO_G74 = {
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
VENTO_G74 = {"v0": 45.0, "categoria": "III", "classe": "A", "s1": 1.0,
             "s3": 1.0, "h_edificacao_m": 3.0, "cpi": 0.8,
             "cpi_origem": "6.2.5-c abertura dominante a barlavento"}
ANC_G74 = {"tipo": "fita_metalica",
           "resistencia_arrancamento_kN": 30.0,
           "origem": "catalogo do fabricante"}
def _vento(**over):
    t = copy.deepcopy(TELHADO_G74)
    t["vento"] = dict(VENTO_G74)
    t["travamento_borda_inferior_m"] = 2.0
    t["ancoragem"] = dict(ANC_G74)
    t.update(over)
    return t
def test_656_alternativo_passsa_quando_dispensa_falha():
    prop = mad.propriedades_classe("C24")
    km = mad.kmod("curta", 2, "serrada")
    res = mad.resistencias_calculo(prop, km["kmod"])
    bt, ht = 0.06, 0.16
    Wt = bt * ht ** 2 / 6.0
    Md = 2.0
    r_est = mad.dispensa_estabilidade_lateral_656(
        bt, ht, 5.0, prop["E0m"], res["fmd"], km["kmod"], True)
    assert not r_est["dispensada"]
    r = mad.verifica_flexao(Md, Wt, res["fmd"], r_est)
    assert r["OK"] is True
    assert r.get("criterio_estabilidade") == "6.5.6_alternativo"
    alt = r["alternativo_656"]
    assert alt["sigma_lim_kNm2"] == pytest.approx(
        float(r_est["E0ef_kNm2"]) / (float(r_est["beta_M"]) * (5.0 / 0.06)))
    assert alt["sigma_cd_kNm2"] == pytest.approx(abs(Md) / Wt)
def test_656_alternativo_reprova_quando_tensao_passa_do_limite():
    prop = mad.propriedades_classe("C24")
    km = mad.kmod("curta", 2, "serrada")
    res = mad.resistencias_calculo(prop, km["kmod"])
    bt, ht = 0.06, 0.16
    Wt = bt * ht ** 2 / 6.0
    r_est = mad.dispensa_estabilidade_lateral_656(
        bt, ht, 5.0, prop["E0m"], res["fmd"], km["kmod"], True)
    Md = 3.5
    r = mad.verifica_flexao(Md, Wt, res["fmd"], r_est)
    assert r["OK"] is False
    assert "alternativo" in r["motivo"]
    assert r["alternativo_656"]["sigma_cd_kNm2"] > r["alternativo_656"]["sigma_lim_kNm2"]
    leve = mad.verifica_flexao(2.0, Wt, res["fmd"], r_est)
    assert leve["OK"] is True
def test_656_sem_rotacao_nao_tem_alternativo():
    prop = mad.propriedades_classe("C24")
    km = mad.kmod("curta", 2, "serrada")
    res = mad.resistencias_calculo(prop, km["kmod"])
    bt, ht = 0.06, 0.16
    Wt = bt * ht ** 2 / 6.0
    r_est = mad.dispensa_estabilidade_lateral_656(
        bt, ht, 2.0, prop["E0m"], res["fmd"], km["kmod"], False)
    assert not r_est["dispensada"]
    r = mad.verifica_flexao(2.0, Wt, res["fmd"], r_est)
    assert r["OK"] is False
    assert r.get("criterio_estabilidade") == "6.5.6_teoria_fora_do_lote"
def test_terca_longa_passa_no_alternativo_e_muito_longa_reprova():
    base = copy.deepcopy(TELHADO_G74)
    base["travamento_borda_comprimida_m"] = 5.0
    r = tmad.rodar(base)
    assert r["terca"]["flexao"].get("criterio_estabilidade") == "6.5.6_alternativo"
    assert r["terca"]["OK"] is True
    longa = copy.deepcopy(TELHADO_G74)
    longa["travamento_borda_comprimida_m"] = 12.0
    r2 = tmad.rodar(longa)
    assert r2["terca"]["OK"] is False
    assert "alternativo" in r2["terca"]["flexao"]["motivo"]
def test_booleano_virou_geometria():
    velho = copy.deepcopy(TELHADO_G74)
    velho["contraventamento_banzo_inf"] = True
    del velho["contraventamento_banzo_inf_m"]
    with pytest.raises(tmad.EntradaTelhado, match="contraventamento_banzo_inf_m"):
        tmad.rodar(velho)
    sem = copy.deepcopy(TELHADO_G74)
    del sem["contraventamento_banzo_inf_m"]
    with pytest.raises(tmad.EntradaTelhado, match="contraventamento_banzo_inf_m"):
        tmad.rodar(sem)
    zero = copy.deepcopy(TELHADO_G74)
    zero["contraventamento_banzo_inf_m"] = 0.0
    with pytest.raises(tmad.EntradaTelhado, match="> 0"):
        tmad.rodar(zero)
def test_espacamento_muda_L0_e_o_veredito_com_uplift():
    grav = tmad.rodar(copy.deepcopy(TELHADO_G74))
    assert grav["ATENDE"] is True
    apertado = _vento(contraventamento_banzo_inf_m=2.0)
    r2 = tmad.rodar(apertado)
    assert r2["ATENDE"] is True, r2["reprovados"]
    solto = _vento(contraventamento_banzo_inf_m=8.0)
    r3 = tmad.rodar(solto)
    assert r3["ATENDE"] is False and "barras" in r3["reprovados"]
    assert r3["contraventamento_6_6"]["L1_inf_m"] > r2["contraventamento_6_6"]["L1_inf_m"]
    assert r3["contraventamento_6_6"]["Kbr1min_kN_m"] < r2["contraventamento_6_6"]["Kbr1min_kN_m"]
def test_66_forcas_sao_relacao_nao_numero():
    r = tmad.rodar(copy.deepcopy(TELHADO_G74))
    c = r["contraventamento_6_6"]
    assert c["F1d_kN"] == pytest.approx(c["Nd_governante_kN"] / 150.0, rel=1e-2, abs=2e-3)
    assert c["Fd_extremidade_kN"] == pytest.approx((2.0 / 3.0) * c["n_tesouras"] * c["F1d_kN"], rel=1e-2, abs=2e-3)
    assert c["Kbrmin_kN_m"] == pytest.approx((2.0 / 3.0) * c["n_tesouras"] * c["Kbr1min_kN_m"], rel=1e-2, abs=0.05)
    assert c["n_tesouras"] == int(round(r["extensao_m"] / r["espacamento_m"])) + 1
    assert mad.forca_contraventamento_F1d_662(30.0)["F1d_kN"] == pytest.approx(0.2)
    assert mad.forca_extremidade_Fd_664(6, 0.2)["Fd_kN"] == pytest.approx(0.8)
    assert mad.alpha_m_662(3) == pytest.approx(1.5)
    assert mad.alpha_m_662(2) == pytest.approx(1.0)
    assert mad.alpha_m_662(float("inf")) == pytest.approx(2.0)
def test_66_peca_e_rigidez_nomeiam_a_ausencia_no_escopo():
    assert mad.escopo()["contraventamento_6.6_forcas"] == "implemented"
    assert mad.escopo()["contraventamento_6.6_peca"] == "not_available"
    assert mad.escopo()["contraventamento_6.6_rigidez"] == "not_available"
    assert mad.escopo()["estabilidade_lateral_6.5.6"] == "dispensa_e_alternativo_implementados"
    mot = mad.motivos_escopo()
    assert "6.6.2" in mot["contraventamento_6.6_peca"]
    assert "6.6.4" in mot["contraventamento_6.6_rigidez"]
    r = tmad.rodar(copy.deepcopy(TELHADO_G74))
    assert r["escopo"]["contraventamento_6.6_peca"] == "not_available"
    assert r["contraventamento_6_6"]["peca_contraventamento"]["status"] == "not_available"
    assert r["gates"]["contraventamento_6.6"]["peca"] == "not_available"
def test_66_ext_maior_que_20m_pede_intermediaria():
    longa = copy.deepcopy(TELHADO_G74)
    longa["extensao"] = 22.0
    r = tmad.rodar(longa)
    assert "exigidas" in r["contraventamento_6_6"]["intermediarias_20m"]
    curta = tmad.rodar(copy.deepcopy(TELHADO_G74))
    assert "dispensadas" in curta["contraventamento_6_6"]["intermediarias_20m"]
def test_prancha_mostra_contraventamento_e_mantem_situacao_por_peca():
    import desenho_casa_residencial as dcr
    r = tmad.rodar(copy.deepcopy(TELHADO_G74))
    svg = dcr.telhado_tesoura_svg(r)
    ET.fromstring(svg)
    txt = re.findall(r">([^<]+)</text>", svg)
    linha = next(t for t in txt if t.startswith("contraventamento 6.6:"))
    assert ("F1d=%.3f" % r["contraventamento_6_6"]["F1d_kN"]) in linha
    assert ("Fd=%.3f" % r["contraventamento_6_6"]["Fd_extremidade_kN"]) in linha
    assert "peca nao verificada" in linha
    ruim = copy.deepcopy(TELHADO_G74)
    ruim["secoes"]["diagonal"] = {"b": 0.02, "h": 0.02}
    r2 = tmad.rodar(ruim)
    assert r2["ATENDE"] is False
    svg2 = dcr.telhado_tesoura_svg(r2)
    ET.fromstring(svg2)
    txt2 = re.findall(r">([^<]+)</text>", svg2)
    i = txt2.index("Peca")
    sit = {}
    for k in range(i + 5, len(txt2) - 4, 5):
        sit[txt2[k]] = txt2[k + 4]
    assert sit["diagonal"] == "REPROVA"
    assert sit["banzo_sup"] == sit["terca"] == "ATENDE"
