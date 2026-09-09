"""G71: o telhado voa - succao e uplift na tesoura (NBR 6123 Tab.5).

O telhado nasceu no G66 com a cadeia gravitacional inteira e sem vento.
Cada teste abre o numero (relacao, nunca congelado, molde G52) e o
vermelho-por-injecao garante que o defeito volta a reprovar - nos dois
sentidos quando houver baseline (vento forte exige ancoragem; vento fraco
nao pode exigi-la).
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

import estrutura_casa as ec
import gestao_casa as gc
import telhado_casa_madeira as tmad
import vento_nbr6123 as vi

TELHADO_GRAV = {
    "vao": 8.0, "inclinacao_graus": 25.0, "extensao": 10.4,
    "espacamento": 2.0, "n_paineis": 2,
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
    "contraventamento_banzo_inf": True,
    "apoio_comprimento_m": 0.2,
    "ligacao": {
        "tipo_pino": "parafuso", "d_mm": 12.0, "fu_MPa": 415.0,
        "t_chapa_mm": 6.3,
        "n_pinos": 4, "config_73": "chapa_central_dupla",
        "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                         "a3c": 80, "a4t": 60, "a4c": 60},
        "he_mm": 90.0},
}

VENTO_FORTE = {"v0": 45.0, "categoria": "III", "classe": "A", "s1": 1.0,
               "s3": 1.0, "h_edificacao_m": 3.0, "cpi": 0.8,
               "cpi_origem": "6.2.5-c abertura dominante a barlavento"}
ANCORAGEM = {"tipo": "fita_metalica",
             "resistencia_arrancamento_kN": 30.0,
             "origem": "catalogo do fabricante"}


def _telhado_vento(**override):
    tel = copy.deepcopy(TELHADO_GRAV)
    tel["vento"] = dict(VENTO_FORTE)
    tel["travamento_borda_inferior_m"] = 2.0
    tel["ancoragem"] = dict(ANCORAGEM)
    tel.update(override)
    return tel


# --- Tab.5 lida na pagina ------------------------------------------------------

def test_tab5_bloco_e_valores_da_pagina():
    """NBR 6123 Tab.5 p.15: a casa terrea (h/b <= 1/2) NAO usa os numeros do
    galpao (bloco 1/2-3/2, GH -0,60). No bloco da casa GH = -0,40."""
    casa = tmad.cpe_telhado_2aguas(5.0, 0.375)
    assert casa["bloco"] == "h<=1/2"
    assert casa["alfa90"] == (-0.9, -0.4)
    galpao = tmad.cpe_telhado_2aguas(5.0, 0.6)
    assert galpao["bloco"] == "1/2-3/2"
    assert galpao["alfa90"] == pytest.approx((-0.9, -0.6))
    # e confere com a tabela que o galpao consulta.
    assert vi.cpe_telhado(5.0) == {"cobertura_barlavento": -0.9,
                                  "cobertura_sotavento": -0.6}
    # interpolacao em theta: 25 graus no bloco da casa (20: -0,4/0 a 30).
    meio = tmad.cpe_telhado_2aguas(25.0, 0.375)
    assert meio["alfa90"] == pytest.approx((-0.2, -0.4))
    assert meio["alfa0"][0] == pytest.approx(-0.7)  # EG governa o simetrico
    with pytest.raises(tmad.EntradaTelhado, match="Tab.5"):
        tmad.cpe_telhado_2aguas(25.0, 7.0)


def test_cpi_declarado_com_origem_e_faixa():
    """cpi sai da 6.2 (pp.12-13), nao da memoria: sem origem ou fora da
    envoltoria [-0,9, +0,8] a entrada e' recusada."""
    tel = _telhado_vento()
    tel["vento"] = dict(VENTO_FORTE, cpi=0.9)
    with pytest.raises(tmad.EntradaTelhado, match="cpi"):
        tmad.rodar(tel)
    tel["vento"] = dict(VENTO_FORTE, cpi_origem="  ")
    with pytest.raises(tmad.EntradaTelhado, match="cpi_origem"):
        tmad.rodar(tel)
    tel["vento"] = dict(VENTO_FORTE)
    del tel["vento"]["v0"]
    with pytest.raises(tmad.EntradaTelhado, match="vento.v0"):
        tmad.rodar(tel)


def test_q_vem_do_sitio_declarado():
    """q = 0,613.Vk2 com S2 da Tab.1 (a mesma do galpao): relacao, nao
    numero congelado."""
    r = tmad.rodar(_telhado_vento())
    _b, _fr, _p, s2 = vi.s2_factor("III", "A", 3.0)
    vk = 45.0 * 1.0 * s2 * 1.0
    assert r["vento"]["q_kNm2"] == pytest.approx(0.613 * vk ** 2 / 1000.0,
                                                rel=1e-3)


# --- a guarda nomeada: succao tem de inverter o sinal --------------------------

def test_succao_inverte_a_reacao_nao_so_diminui():
    """O bug _wind_unico do galpao: succao sem sinal dava 'um numero
    plausivel'. Com cpe negativo e cpi positivo a reacao de projeto tem
    de MUDAR de sinal - nao basta ficar menor."""
    r = tmad.rodar(_telhado_vento())
    ry_grav = r["reacoes_caracteristicas"]["RyL_kN"]
    assert ry_grav > 0
    for caso, an in r["casos_W"].items():
        rd = 0.9 * ry_grav + 1.4 * an["RyL"]
        assert an["W_tot_kN"] > 0  # para cima, na convencao do modulo
        assert rd < 0, (caso, rd)  # inverte: arrancamento, nao alivio
    arr = r["descida"]["arrancamento_por_tesoura_kN"]
    assert arr["L_kN"] > 0 and arr["R_kN"] > 0
    assert r["descida"]["arrancamento_total_kN"] == pytest.approx(
        (arr["L_kN"] + arr["R_kN"]) * r["n_tesouras"], rel=1e-3)


def test_vento_fraco_nao_inventa_arrancamento():
    """Baseline no outro sentido: brisa nao pode exigir ancoragem (guarda
    que so sabe reprovar nao e' gate)."""
    tel = _telhado_vento()
    tel["vento"] = dict(VENTO_FORTE, v0=5.0)
    del tel["ancoragem"]
    r = tmad.rodar(tel)
    assert r["descida"]["arrancamento_total_kN"] == pytest.approx(0.0)
    assert r["ancoragem"]["OK"] is True
    assert "sem arrancamento" in r["ancoragem"]["motivo"]


# --- o par (gravidade, uplift) barra a barra ------------------------------------

def test_cada_barra_guarda_o_par_e_verifica_os_dois():
    """Nd_grav = 1,4.(G+Q); Nd_uplift = 0,9.G+1,4.W no pior caso - relacao
    recomposta aqui sem passar pelo par guardado."""
    r = tmad.rodar(_telhado_vento())
    assert r["vento_ativo"] is True
    assert "0,9.G+1,4.W" in r["combinacoes"]["uplift"]
    flips = 0
    for b in r["barras"]:
        assert b["Nd_grav_kN"] == pytest.approx(
            1.4 * (b["Nk_G_kN"] + b["Nk_Q_kN"]), abs=0.05)
        assert b["Nd_uplift_kN"] is not None and b["uplift_caso"] is not None
        Nk_w = r["casos_W"][b["uplift_caso"]]["esforcos_Nk"][
            next(k for k in r["casos_W"][b["uplift_caso"]][
                "esforcos_Nk"] if "%s-%s" % (k[0], k[1]) == b["barra"])]
        assert b["Nd_uplift_kN"] == pytest.approx(
            0.9 * b["Nk_G_kN"] + 1.4 * Nk_w, abs=0.05)
        assert b["util_uplift"] is not None  # o segundo lado foi verificado
        if b["Nd_grav_kN"] * b["Nd_uplift_kN"] < 0:
            flips += 1
            # trocou de tracao para compressao: tem estabilidade conferida.
            comp = next(x for x in r["barras"] if x["barra"] == b["barra"])
            assert comp["OK"] is True or "uplift" in " ".join(
                r["gates"]["barras"]["reprovadas"])
    assert flips >= 1, "nenhuma barra inverte: o vento nao entrou na trelica"


def test_ancoragem_ausente_reprova_nomeando_a_peca():
    """'A gravidade segura' nao e' verificacao: com arrancamento e sem peca
    declarada, o telhado reprova dizendo o que falta."""
    tel = _telhado_vento()
    del tel["ancoragem"]
    r = tmad.rodar(tel)
    assert r["ATENDE"] is False
    assert "ancoragem_uplift" in r["reprovados"]
    assert "ancoragem" in r["ancoragem"]["motivo"]
    fraca = _telhado_vento()
    fraca["ancoragem"] = dict(ANCORAGEM, resistencia_arrancamento_kN=1.0)
    r2 = tmad.rodar(fraca)
    assert r2["ATENDE"] is False
    assert r2["ancoragem"]["util"] > 1.0
    assert r2["gates"]["ancoragem_uplift"]["OK"] is False


def test_telhado_completo_atende_quando_tudo_declarado():
    r = tmad.rodar(_telhado_vento())
    assert r["ATENDE"] is True, r["reprovados"]
    assert r["gates"]["ancoragem_uplift"]["OK"] is True
    assert r["terca"]["uplift"]["OK"] is True


# --- a terca sob momento invertido ------------------------------------------------

def test_terca_sem_L1_inferior_reprova_com_o_motivo():
    """Sob succao a comprimida e' a borda inferior: sem L1 dela declarado,
    reprova - o L1 da superior nao vale."""
    tel = _telhado_vento()
    del tel["travamento_borda_inferior_m"]
    r = tmad.rodar(tel)
    assert r["ATENDE"] is False and "tercas" in r["reprovados"]
    assert "borda inferior" in r["terca"]["uplift"]["motivo"]
    assert r["terca"]["uplift"]["inverte"] is True


def test_terca_L1_inferior_longo_reprova_na_656():
    """Com L1 inferior declarado e longo, a 6.5.6 reprova pelo numero -
    medida aqui contra o limite do proprio resultado."""
    tel = _telhado_vento(travamento_borda_inferior_m=6.0)
    r = tmad.rodar(tel)
    up = r["terca"]["uplift"]
    assert up["OK"] is False
    assert "6.5.6-b" in up["motivo"]
    assert up["L1_inf_m"] > up["estabilidade_borda_inferior"]["L1_limite_m"]


# --- descida: a casa fica sabendo do alivio ----------------------------------------

REVEST = 1.6
PAREDE = {"tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14,
          "altura": 2.7, "revestimento_cm": 2.0}


def _casa_concreto(telhado=None):
    return {
        "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                      "pe_direito": 2.7},
        "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": REVEST},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
        "parede_sobre_vigas": dict(PAREDE),
        "baldrame": {"b": 0.15, "h": 0.40, "parede": dict(PAREDE)},
    } | ({"telhado_madeira": telhado} if telhado is not None else {})


def _casa_portante(telhado=None):
    return {
        "geometria": {"vaos_x": [4.0], "vaos_y": [3.0],
                      "pe_direito": 2.7},
        "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": REVEST},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
        "alvenaria_portante": {
            "fpk": 4000.0, "material": "bloco", "te": 0.14,
            "combinacao": "normal", "habitacao_terrea": True,
            "parede_6120": {"tipo": "bloco_ceramico_furo_horizontal",
                            "espessura_cm": 14, "revestimento_cm": 2.0,
                            "altura_m": 2.7},
            "linhas": "contorno"},
        "baldrame": {"b": 0.15, "h": 0.40, "parede": dict(PAREDE)},
        "fundacao": {"tipo": "sapata_corrida", "cota_apoio_m": 1.0,
                     "sigma_solo_adm": 150.0,
                     "sigma_solo_proveniencia": "ensaio declarada no teste"},
    } | ({"telhado_madeira": telhado} if telhado is not None else {})


def _telhado_casa(apoio):
    tel = _telhado_vento(apoio=apoio)
    if apoio == "parede":
        tel.update(vao=3.0, extensao=4.0, espacamento=2.0, n_paineis=1)
    else:
        tel.update(vao=8.0, extensao=10.4, espacamento=2.0, n_paineis=2)
    return tel


def test_descida_leva_o_alivio_a_casa():
    tel = _telhado_casa("viga")
    r = ec.rodar(_casa_concreto(copy.deepcopy(tel)))
    g = r["gates"]["telhado_madeira"]
    assert g["OK"] is True
    assert g["vento_ativo"] is True
    assert g["arrancamento_total_kN"] > 0
    assert r["telhado_descida"]["arrancamento_por_pilar_kN"] > 0
    # a gravidade nao foi abatida: o W total segue o do telhado.
    assert g["W_total_kN"] == pytest.approx(
        r["telhado"]["descida"]["W_total_kN"])
    # pilares do beiral carregam o alivio em chave propria.
    com_arr = [p for p in r["telhado_descida"]["pilares"]
               if r["descida"]["pilares"][p]["lances"][0].get("N_telh_arr")]
    assert com_arr, "o alivio nao chegou aos pilares do beiral"


def test_portante_leva_o_alivio_por_linha():
    tel = _telhado_casa("parede")
    r = ec.rodar(_casa_portante(copy.deepcopy(tel)))
    assert r["gates"]["telhado_madeira"]["OK"] is True
    alivio = r["telhado_alivio_por_linha_kN"]
    assert set(alivio) == set(r["gates"]["telhado_madeira"][
        "alivio_por_linha_kN"])
    assert sum(alivio.values()) == pytest.approx(
        r["telhado"]["descida"]["arrancamento_total_kN"] / 2.0 * 2,
        rel=1e-3)
    assert all(v > 0 for v in alivio.values())


def test_memorial_diz_o_alivio():
    r = ec.rodar(_casa_concreto(_telhado_casa("viga")))
    mem = gc.memorial({"estrutura": r})
    tel_item = next(it for it in mem["disciplinas"]
                    if it["disciplina"] == "telhado_madeira")
    assert "uplift" in tel_item["detalhe"]
    assert "Alivio G71" in ec.relatorio_pt(r)


# --- fora do escopo nomeado ----------------------------------------------------------

def test_fora_do_escopo_nomeado():
    esc = tmad.escopo()
    assert esc["vento_succao_uplift"] == "implemented"
    assert esc["vento_dinamico_cap9_6123"] == "not_available"
    assert esc["vento_mais_de_2_aguas"] == "not_available"
    mot = tmad.motivos_escopo()
    assert mot["vento_dinamico_cap9_6123"] and mot["vento_mais_de_2_aguas"]


# --- abrir a folha e olhar --------------------------------------------------------------

def test_prancha_mostra_o_uplift_e_mantem_a_situacao_por_peca():
    """Renderizar-e-olhar G71: a folha diz o arrancamento e a ancoragem;
    sem vento, diz que a cadeia e' gravitacional. A situacao segue por
    peca (llicao do G66)."""
    import desenho_casa_residencial as dcr

    r = tmad.rodar(_telhado_vento())
    svg = dcr.telhado_tesoura_svg(r)
    ET.fromstring(svg)
    assert "uplift" in svg and "ancoragem ATENDE" in svg
    grav = tmad.rodar(copy.deepcopy(TELHADO_GRAV))
    assert "gravitacional" in dcr.telhado_tesoura_svg(grav)
    ruim = _telhado_vento()
    ruim["secoes"] = dict(ruim["secoes"], diagonal={"b": 0.02, "h": 0.02})
    rr = tmad.rodar(ruim)
    assert rr["ATENDE"] is False
    txt = re.findall(r">([^<]+)</text>", dcr.telhado_tesoura_svg(rr))
    i = txt.index("Peca")
    situacao = {}
    for k in range(i + 5, len(txt) - 4, 5):
        situacao[txt[k]] = txt[k + 4]
    assert situacao["diagonal"] == "REPROVA"
    assert situacao["banzo_sup"] == "ATENDE"
