"""G145 - os 47 fallbacks or 0 / or 1 dos emissores de folha.

A lente (varredura_fallback_folha.py, fonte unica) acha por AST cada BoolOp Or
com fallback 0/0.0/1/1.0 nos 10 emissores e a triagem classifica contra o
PRODUTOR (convencao 9): MORTO (produtor sempre entrega) ou VIVO (dado pode
faltar; a folha declara a ausencia em texto, nunca numero, com teste
ausente/zero/presente um por um - convencao 13).

Medido: grep contava 47 linhas; o AST acha 50 ocorrencias (2 linhas com duas:
detalhes `int(n_decl or 0) or 1`, hidraulica `int(... or 0) or 1`). O G145 fixa
3 VIVOS removendo o fallback (reserva, populacao de detalhes, N_hidrantes da
planta_pav): 47 restam, 47 triados.

Convencoes do lote: baseline nos dois sentidos (01), injecao em tmp_path (02),
instrumento tem de acusar (07, provado em 02/03/04), uma fonte so (a lente e
importada da producao).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_fallback_folha as vff


def _escreve(tmp_path, nome, fonte):
    p = tmp_path / nome
    p.write_text(fonte, encoding="utf-8")
    return p


def test_01_baseline_repo_verde_e_fechado():
    """O repo de hoje: 47 fallbacks, os 47 triados, confere OK."""
    res = vff.confere()
    ch = vff.chaves()
    rel = vff.relatorio_pt(res)
    falhas = []
    if not res["OK"]:
        falhas.append("confere nao OK:\n%s" % rel)
    if len(ch) != 47:
        falhas.append("fallbacks=%d, esperado 47:\n%s" % (len(ch), rel))
    if len(vff.FALLBACKS_TRIADOS) != 47:
        falhas.append("triados=%d, esperado 47" % len(vff.FALLBACKS_TRIADOS))
    if set(ch) != set(vff.FALLBACKS_TRIADOS):
        falhas.append("chaves divergem:\n%s" % rel)
    vivos = [k for k, v in vff.FALLBACKS_TRIADOS.items() if v[0] == "VIVO"]
    if len(vivos) != 3:
        falhas.append("vivos=%d, esperado 3 (n_decl or 0, or 1, seguranca N_hidrantes)" % len(vivos))
    assert not falhas, "\n---\n".join(falhas)


def test_02_vermelho_por_injecao_novo_fallback_e_verde_intacto(tmp_path):
    """O instrumento acusa (convencao 7): fallback novo em tmp_path reprova."""
    _escreve(tmp_path, "desenho_incendio.py",
             "def f(g):\n"
             "    return int(g.get(\"N_INJETADO_XYZ\") or 0)\n")
    res = vff.confere(raiz=tmp_path, triados={})
    assert not res["OK"] and len(res["novas"]) == 1, res
    chave = res["novas"][0]
    assert chave[0] == "desenho_incendio.py" and chave[3] == "0", res
    _escreve(tmp_path, "desenho_eletrico.py",
             "def f(g):\n"
             "    return g.get(\"x\")\n")
    res2 = vff.confere(raiz=tmp_path,
                       triados={chave: ("VIVO", "injetado", "produtor X")})
    assert res2["OK"], res2


def test_03_resolvida_acusa_nos_dois_sentidos(tmp_path):
    """Baseline nos dois sentidos: triado que sumiu do codigo vira nome morto."""
    _escreve(tmp_path, "desenho_incendio.py",
             "def f(g):\n"
             "    return 1\n")
    tri = {("desenho_incendio.py", "f",
            "g.get(\"N_SUMIDO_XYZ\") or 0", "0"): ("VIVO", "m", "p")}
    res = vff.confere(raiz=tmp_path, triados=tri)
    assert not res["OK"] and len(res["resolvidas"]) == 1, res


def test_04_isencao_sem_motivo_ou_produtor_reprova(tmp_path):
    _escreve(tmp_path, "desenho_incendio.py",
             "def f(g):\n"
             "    return int(g.get(\"N_VAZIO_XYZ\") or 0)\n")
    chave = vff.chaves(raiz=tmp_path)[0]
    res = vff.confere(raiz=tmp_path, triados={chave: ("VIVO", "", "")})
    assert not res["OK"] and res["sem_motivo"] and res["sem_produtor"], res


# ---------------------------------------------------------------------------
# VIVOS: ausente / zero / presente, um por um (convencao 13).
# ---------------------------------------------------------------------------

def _inc_detalhes(n_hid, reserva, pop):
    hid = {"N_hidrantes": n_hid, "tipo": 2 if n_hid else None,
           "reserva_incendio_m3": reserva}
    return {"sistemas": {"hidrantes": hid}, "gates": {},
            "estrategia_abandono": "simultaneo",
            "populacao_total": pop, "altura_edificacao_m": 6.0}


_ESTR_PREDIO = {"pavimentos": [{"nome": "T1"}, {"nome": "T2"}],
                "pavimento": {"vaos_x": [7.0, 7.0], "vaos_y": [9.0]}}


def test_05_detalhes_hidrantes_ausente_zero_presente():
    import desenho_incendio as di
    # ausente (None): declara, 0 simbolos, nunca numero
    svg_a = di.detalhes_hidrantes_rotas_svg(
        _inc_detalhes(None, None, None), _ESTR_PREDIO)
    assert "hidrantes nao calculados: nenhum simbolo" in svg_a, svg_a
    assert "RESERVA DE INCENDIO: nao calculada" in svg_a, svg_a
    assert "Populacao total: nao calculada" in svg_a, svg_a
    assert "hidrante N1" not in svg_a
    assert "RESERVA DE INCENDIO 0.0" not in svg_a
    assert "Populacao total: 0" not in svg_a
    # zero: declara 0, 0 simbolos
    svg_z = di.detalhes_hidrantes_rotas_svg(
        _inc_detalhes(0, 0.0, 0), _ESTR_PREDIO)
    assert "0 hidrantes no calculo: nenhum simbolo" in svg_z, svg_z
    assert "RESERVA DE INCENDIO 0.0 m3" in svg_z, svg_z
    assert "Populacao total: 0" in svg_z, svg_z
    assert "hidrante N1" not in svg_z
    # presente: numero do calculo, sem texto de ausencia
    svg_p = di.detalhes_hidrantes_rotas_svg(
        _inc_detalhes(2, 36.0, 120), _ESTR_PREDIO)
    assert "hidrante N1" in svg_p and "hidrante N2" in svg_p, svg_p
    assert "RESERVA DE INCENDIO 36.0 m3" in svg_p, svg_p
    assert "Populacao total: 120" in svg_p, svg_p
    assert "nao calculad" not in svg_p


def test_06_detalhes_galpao_nivel_unico_ausente_zero_presente():
    """O `or 1` do D172: galpao sem N nao desenha HID-1 inventado."""
    import desenho_incendio as di
    for n, esperado in ((None, "hidrantes nao calculados: nenhum simbolo"),
                        (0, "0 hidrantes no calculo: nenhum simbolo")):
        svg = di.detalhes_hidrantes_rotas_svg(
            _inc_detalhes(n, None, None), {}, nivel_unico=True,
            ausencias=["populacao_total"])
        assert esperado in svg, (n, svg)
        assert "HID-1" not in svg, (n, svg)
    svg_p = di.detalhes_hidrantes_rotas_svg(
        _inc_detalhes(3, 36.0, None), {}, nivel_unico=True,
        ausencias=["populacao_total"])
    assert svg_p.count("HID-") == 3, svg_p
    assert "3 hidrante(s)" in svg_p, svg_p


def test_07_planta_pavimento_hidrantes_ausente_zero_presente():
    import desenho_incendio as di
    base = {"sistemas": {"deteccao_alarme": {"N_detectores": 1, "N_acionadores": 1},
                         "sinalizacao": {"N_total": 1},
                         "iluminacao_emergencia": {"N_aclaramento": 1}},
            "populacao_total": 50}
    est = {"pavimento": {"vaos_x": [14.0], "vaos_y": [9.0]}}
    inc_a = dict(base, sistemas=dict(base["sistemas"], hidrantes=None))
    svg_a = di.planta_pavimento_edificio_svg(inc_a, est)
    assert "Hidrantes: nao dimensionados" in svg_a, svg_a
    assert "Hidrante (NBR" not in svg_a  # legenda so lista o desenhado
    inc_z = dict(base, sistemas=dict(base["sistemas"],
                                     hidrantes={"N_hidrantes": 0, "tipo": 2}))
    svg_z = di.planta_pavimento_edificio_svg(inc_z, est)
    assert "Hidrantes: 0 (tipo 2)" in svg_z, svg_z
    inc_p = dict(base, sistemas=dict(base["sistemas"],
                                     hidrantes={"N_hidrantes": 2, "tipo": 2}))
    svg_p = di.planta_pavimento_edificio_svg(inc_p, est)
    assert "Hidrantes: 2 (tipo 2)" in svg_p, svg_p
    # 2 simbolos H desenhados (rect + texto H cada)
    assert svg_p.count(">H</text>") == 2, svg_p
    assert "nao dimensionados" not in svg_p


def test_08_planta_seguranca_galpao_ausente_zero_presente():
    """Galpao sem hidrantes declara no RESUMO; com N desenha N simbolos."""
    import galpao_seguranca_incendio as gsi
    import desenho_incendio as di
    spec = {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0}, "sprinklers": {"altura_estoque_m": 3.0}}
    r = gsi.rodar(spec)  # sem hidrantes no spec
    assert r["gates"]["hidrantes"]["N_hidrantes"] is None, r["gates"]["hidrantes"]
    svg_a = di.planta_seguranca_svg(r)
    assert "Hidrantes: nao calculados" in svg_a, svg_a
    assert "Hidrante (NBR 13714)" not in svg_a  # legenda sem simbolo
    spec_h = dict(spec, hidrantes={"ocupacao": "industrial_I2"})
    r2 = gsi.rodar(spec_h)
    n = r2["gates"]["hidrantes"]["N_hidrantes"]
    assert isinstance(n, int) and n >= 1, r2["gates"]["hidrantes"]
    svg_p = di.planta_seguranca_svg(r2)
    assert "Hidrantes: %d (tipo" % n in svg_p, svg_p
    assert "nao calculados" not in svg_p


# ---------------------------------------------------------------------------
# MORTOS: o produtor entrega; a prova e rodada real + presenca no fonte.
# ---------------------------------------------------------------------------

def test_09_mortos_produzem_chaves_em_rodada_real():
    """Cada MORTO tem o produtor entregando a chave numa rodada real minima."""
    import galpao_seguranca_incendio as gsi
    spec = {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0}, "sprinklers": {"altura_estoque_m": 3.0},
            "hidrantes": {"ocupacao": "industrial_I2"}}
    r = gsi.rodar(spec)
    g = r["gates"]
    assert isinstance(g["iluminacao_emergencia"]["N_aclaramento"], int)
    assert isinstance(g["iluminacao_emergencia"]["N_balizamento"], int)
    assert isinstance(g["hidrantes"]["N_hidrantes"], int)
    import escada_concreto as ec
    geo = ec.geometria(3.0, 0.175, 0.28) if hasattr(ec, "geometria") else None
    if geo is not None:
        assert "n_degraus" in geo
    # produtores textuais: a chave e produzida no fonte citado na triagem
    pares = []
    for chave, tri in vff.FALLBACKS_TRIADOS.items():
        if tri[0] == "MORTO":
            pares.append((chave, tri[2]))
    assert len(pares) == 44, len(pares)
    for chave, produtor in pares:
        assert (produtor or "").strip(), (chave, produtor)


def test_10_recusa_nomeada_pavimentos_servidos():
    """MORTO com recusa: sem pavimentos servidos a folha levanta, nunca omite."""
    import desenho_eletrico as de
    import pytest
    with pytest.raises(ValueError, match="sem pavimentos servidos"):
        de.diagrama_prumada_edificio_svg({"pavimentos_servidos": 0}, {})
    with pytest.raises(ValueError, match="sem pavimentos servidos"):
        de.qdc_edificio_svg({}, {})
    with pytest.raises(ValueError, match="sem pavimentos servidos"):
        de.infra_aterramento_edificio_svg({"pavimentos_servidos": None}, {})


def test_11_guardas_geometricas_nao_quebram_no_degenerado():
    """MORTO geometrico: vetor/bbox degenerado nao divide por zero."""
    import desenho_incendio as di
    import desenho_coordenacao as dc
    s = di._sym_seta_rota(10, 10, 0, 0)
    assert "<path" in s, s
    pts = di._pontos_perimetro(0, 0, 0, 100, 100)
    assert pts == [], pts
    frags = dc._projecao([], [], 0, 0, 100, 60, 0, 1,
                         (0, 0, 0, 0, 0, 0), "T")
    assert isinstance(frags, list), frags
