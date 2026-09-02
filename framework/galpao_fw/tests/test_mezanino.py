"""G20 — Mezanino no galpao: laje+viga+pilar de concreto dentro do envelope metalico.

Primeira costura concreto x metalico em uso real (nao mutacao injetada).
Valida:
 - rodar() ATENDE para a amostra 6x5 a 3 m dentro do galpao 40x20x6;
 - membros_bim: 4 pilares + 4 vigas + 1 laje + 4 sapatas, com contratos
   F01/F03/F04/F05/F15/F18/F19/F20 (dims mm, p1/p2 mm, secao m, ancoragem base,
   volume mm3->m3, geometria m->mm, laje h cm, secao m);
 - posicao DENTRO do envelope (F18) e rejeicao fora;
 - federado com o galpao metalico (modelo_neutro) sem clash revisavel quando
   interior;
 - turnkey orquestra mezanino + concreto + eletrico e gera IFC + quantitativo.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fronteiras as FR
import galpao_mezanino as GMZ
import geometria_membros as GM
import ifc_emit


# ------------------------------------------------------------------ helpers
def _spec_galpao(comp=40.0, vao=20.0, pe=6.0):
    return {"comprimento": comp, "vao": vao, "pe_direito": pe}


def _r_mezanino(Lx=6.0, Ly=5.0, x0=2.0, y0=2.0, h=3.0, q_uso=2.0, **kw):
    spec = {"geometria": _spec_galpao(), "x0": x0, "y0": y0, "Lx": Lx, "Ly": Ly, "h": h, "q_uso": q_uso}
    spec.update(kw)
    return GMZ.rodar(spec)


def _texto(nome):
    import pathlib
    p = pathlib.Path(__file__).parent.parent / (nome + ".py")
    return p.read_text(encoding="utf-8", errors="replace")


def _contem(nome, trecho):
    return trecho in _texto(nome)


# ======================================================================
# F18 — geometria do mezanino em m (fronteira m->mm)
# ======================================================================
def test_fronteira_F18_mezanino_geometria_m_existe_e_casa():
    assert _contem("galpao_mezanino", "x0"), "galpao_mezanino nao declara x0"
    assert _contem("galpao_mezanino", "Lx"), "galpao_mezanino nao declara Lx"
    assert _contem("galpao_mezanino", "* MM"), "galpao_mezanino nao converte m->mm"
    assert _contem("galpao_turnkey", "_run_mezanino"), "turnkey nao despacha mezanino"
    f = FR.FRONTEIRAS["F18_mezanino_geometria_m"]
    assert f["unidade_declarada"] == "m"
    assert "mm" in f["unidade_esperada"]
    # magnitude: mezanino 6x5x3 m -> p1 em mm ~2000..6000
    r = _r_mezanino()
    ms = GMZ.membros_bim(r)
    col = next(m for m in ms if m["tipo"] == "Column")
    # p1 em mm: 2000,2000,0
    assert 1000 < col["p1"][0] < 40000 and 1000 < col["p1"][1] < 40000
    # valida conversao: Lx 6 m -> dims laje 6000 mm
    slab = next(m for m in ms if m["tipo"] == "Slab")
    assert slab["dims"][0] == 6.0 * 1000.0
    assert slab["dims"][1] == 5.0 * 1000.0
    # validador de magnitude
    ok, _ = FR.validar_unidade("F18_mezanino_geometria_m", 6.0)
    assert ok
    ok, _ = FR.validar_unidade("F18_mezanino_geometria_m", 6000.0)
    assert not ok  # 6000 parece mm, nao m


# ======================================================================
# F19 — laje h cm feedback
# ======================================================================
def test_fronteira_F19_mezanino_laje_h_cm_existe_e_casa():
    assert _contem("galpao_mezanino", "h_laje"), "mezanino nao declara h_laje"
    assert _contem("galpao_mezanino", "dimensiona_laje"), "mezanino nao chama dimensiona_laje"
    assert _contem("laje_concreto", "dimensiona_laje"), "laje_concreto nao declara dimensiona_laje"
    f = FR.FRONTEIRAS["F19_mezanino_laje_h_cm"]
    assert f["unidade_declarada"] == "cm"
    r = _r_mezanino()
    h_cm = r["gates"]["laje"]["h_cm"]
    assert 8 < h_cm < 30, "h_cm %.1f fora de cm" % h_cm
    # h_adotada realimenta carga g
    assert r["gates"]["laje_compatibilizada"]["OK"]
    ok, _ = FR.validar_unidade("F19_mezanino_laje_h_cm", h_cm)
    assert ok
    ok, _ = FR.validar_unidade("F19_mezanino_laje_h_cm", 0.12)
    assert not ok  # 0.12 parece m


# ======================================================================
# F20 — secao viga/pilar mezanino em m
# ======================================================================
def test_fronteira_F20_mezanino_secao_m_existe_e_casa():
    assert _contem("galpao_mezanino", '"bf": hx') or _contem("galpao_mezanino", '"bf": b_v'), "sec_pil bf nao declarado"
    assert _contem("geometria_membros", 'secao["bf"] * MM'), "geometria_membros nao faz bf*MM"
    f = FR.FRONTEIRAS["F20_mezanino_viga_pilar_secao_m"]
    assert f["unidade_declarada"] == "m"
    r = _r_mezanino()
    col = next(m for m in GMZ.membros_bim(r) if m["tipo"] == "Column")
    bf = col["secao"]["bf"]; d = col["secao"]["d"]
    assert 0.15 < bf < 1.0 and 0.15 < d < 1.0, "secao bf=%.3f d=%.3f fora de m" % (bf, d)
    assert 50 < bf * 1000 < 2000
    ok, _ = FR.validar_unidade("F20_mezanino_viga_pilar_secao_m", bf)
    assert ok
    ok, _ = FR.validar_unidade("F20_mezanino_viga_pilar_secao_m", 300.0)
    assert not ok


# ======================================================================
# contrato geral: F01/F03/F04/F05/F15 exercitados pelo mezanino (uso real)
# ======================================================================
def test_mezanino_exercita_fronteiras_existentes_em_uso_real():
    r = _r_mezanino()
    ms = GMZ.membros_bim(r)
    # F01: Footing dims em mm -> volume mm3/1e9 plausivel
    foot = next(m for m in ms if m["tipo"] == "Footing")
    B, L, h = foot["dims"]
    assert 500 < B < 5000 and 500 < L < 5000, "Footing dims fora de mm"
    vol = B * L * h / 1e9
    assert 0.2 < vol < 10.0, "volume sapata %.3f implausivel" % vol
    # F03: p1/p2 mm — pilar altura 3 m -> 3000 mm, mas desconta viga (h_viga)
    col = next(m for m in ms if m["tipo"] == "Column")
    assert abs(col["p2"][2] - col["p1"][2] - (3.0*1000 - r["viga_X"]["h"]*1000)) < 1e-6
    # F04: secao m -> aabb conserva dims
    slab = next(m for m in ms if m["tipo"] == "Slab")
    assert slab["dims"][2] > 80  # mm
    # F05: ancoragem base declarada nas vigas
    beams = [m for m in ms if m["tipo"] == "Beam"]
    assert all(m.get("ancoragem") == "base" for m in beams), "viga mezanino sem ancoragem base"
    # F15: volume mm3->m3 via geometria_membros
    vol_col = GM.volume(col)
    assert 0.05 < vol_col < 2.0, "volume coluna mezanino %.3f" % vol_col


# ======================================================================
# rodar() ATENDE e membros
# ======================================================================
def test_mezanino_roda_e_atende_para_amostra_valida():
    r = _r_mezanino()
    assert r["ATENDE"], "reprovados: %r gates: %r" % (r["reprovados"], r["gates"])
    assert r["gates"]["laje"]["OK"]
    assert r["gates"]["vigas"]["OK"]
    assert r["gates"]["pilar"]["OK"]
    assert r["gates"]["fundacao"]["OK"]
    assert r["gates"]["posicao"]["OK"]
    assert r["gates"]["interferencia"]["OK"]


def test_mezanino_membros_contam_e_posicionam_certo():
    r = _r_mezanino(x0=5.0, y0=6.0, Lx=6.0, Ly=5.0, h=3.0)
    ms = GMZ.membros_bim(r)
    assert len([m for m in ms if m["tipo"] == "Column"]) == 4
    assert len([m for m in ms if m["tipo"] == "Beam"]) == 4
    assert len([m for m in ms if m["tipo"] == "Slab"]) == 1
    assert len([m for m in ms if m["tipo"] == "Footing"]) == 4
    slab = next(m for m in ms if m["tipo"] == "Slab")
    # centro = (x0+Lx/2, y0+Ly/2, h - h_laje/2)
    assert abs(slab["centro"][0] - (5.0 + 3.0) * 1000) < 1e-6
    assert abs(slab["centro"][1] - (6.0 + 2.5) * 1000) < 1e-6
    # viga VX1: y = y0
    vx1 = next(m for m in ms if m["marca"] == "M-VX1")
    assert vx1["p1"][1] == 6.0 * 1000 and vx1["p2"][1] == 6.0 * 1000
    assert abs(vx1["p1"][0] - 5.0 * 1000) < 1e-6
    # pilar vai de 0 ate base da viga (h - h_viga)
    col = next(m for m in ms if m["tipo"] == "Column")
    assert col["p1"][2] == 0.0
    zb_esperado = 3.0 * 1000 - max(r["viga_X"]["h"], r["viga_Y"]["h"]) * 1000
    assert abs(col["p2"][2] - zb_esperado) < 1e-6


def test_mezanino_rejeita_fora_do_envelope():
    import pytest
    geo = {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0}
    # x0+Lx excede comprimento
    with pytest.raises(ValueError, match="excede.*comprimento"):
        GMZ.rodar({"geometria": geo, "x0": 38.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0})
    # y0+Ly excede vao
    with pytest.raises(ValueError, match="excede.*vao"):
        GMZ.rodar({"geometria": geo, "x0": 2.0, "y0": 18.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0})
    # h >= pe_direito
    with pytest.raises(ValueError, match="altura.*pe-direito"):
        GMZ.rodar({"geometria": geo, "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 6.0})


def test_mezanino_turnkey_orquestra_e_federa_sem_clash_revisavel():
    import galpao_turnkey as gtk
    spec = {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "concreto": {"vao": 20.0, "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
                     "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "sigma_solo_adm": 250.0,
                     "travamento_longitudinal": "topo"},
        "mezanino": {"x0": 10.0, "y0": 5.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0, "q_uso": 2.0},
        "eletrico": {"tensao_V": 380.0,
                     "cargas": {"motores": [{"P_cv": 5.0, "eta": 0.92, "Fp": 0.86, "n": 1}],
                                "iluminacao_kW": 5.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
    }
    R = gtk.rodar(spec)
    assert "mezanino" in R["executadas"], R["executadas"]
    assert R["disciplinas"]["mezanino"]["ATENDE"], R["disciplinas"]["mezanino"]
    # federado inclui mezanino
    mbs, disc = gtk._membros_federados(R, spec)
    assert "mezanino" in disc
    assert "concreto" in disc
    # clay: concreto x mezanino deve ser ZERO quando ambos tem vao 20 e mezanino interior
    clash = gtk.checa_interferencia_federada(R, spec)
    # filtra so pares concreto x mezanino
    revis = [c for c in clash["revisar"] if "concretoxmezanino" in c["disciplinas"] or "mezaninoxconcreto" in c["disciplinas"]]
    assert not revis, "mezanino nao deveria colidir com o concreto externo quando vaos coincidem e posicao interior: %r" % revis


def test_mezanino_com_aco_sem_clash_revisavel_via_modelo_neutro():
    import galpao_turnkey as gtk
    import modelo_neutro as MN
    # aco: frame primario simples (sem calcular) — envelope 40x20x6, vao unico 20
    geo_aco = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 6.5, "bay": 5.0}
    secoes = {"col": {"nome": "HEA200", "d": 0.19, "bf": 0.20, "tw": 0.0065, "tf": 0.010},
              "raf": {"nome": "HEA180", "d": 0.171, "bf": 0.18, "tw": 0.006, "tf": 0.0095}}
    membros_aco = MN.frame_primario(geo_aco, secoes)
    # marca prefixada A- para federado
    for m in membros_aco:
        m["marca"] = "A-" + m["marca"]
    # mezanino interior (2,2,6x5) — ja em frame comum (X=compr, Y=vao)
    r_mz = _r_mezanino(x0=12.0, y0=7.0, Lx=6.0, Ly=5.0)
    membros_mz = GMZ.membros_bim(r_mz)
    for m in membros_mz:
        m["marca"] = "M-" + m["marca"]
    # aabb clash puro entre aco e mezanino (sem eletrico)
    # o diafragma do galpao e' em Z ~6 m, mezanino em 3 m — nao devem colidir
    todos = membros_aco + membros_mz
    # usa a mesma logica do federado: so pares de disciplinas diferentes
    # aqui simplifica: verifica que nenhum par aco x mezanino tem volume > vol_min
    caixas_aco = [(m, GM.aabb(m)) for m in membros_aco]
    caixas_mz = [(m, GM.aabb(m)) for m in membros_mz]
    v_max = 0
    for ma, ba in caixas_aco:
        for mm, bm in caixas_mz:
            v = GM.volume_comum(ba, bm)
            if v > 1000:
                v_max = max(v_max, v)
    assert v_max == 0, "aco x mezanino nao deveria colidir (v=%.0f mm3) quando mezanino interior a 3 m e aco a 6 m" % v_max


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_mezanino_emite_ifc_com_laje_viga_pilar_sapata(tmp_path):
    import ifcopenshell
    r = _r_mezanino()
    p = str(tmp_path / "mezanino.ifc")
    GMZ.emitir_bim(r, p)
    m = ifcopenshell.open(p)
    assert len(m.by_type("IfcColumn")) == 4
    assert len(m.by_type("IfcBeam")) == 4
    assert len(m.by_type("IfcSlab")) == 1
    assert len(m.by_type("IfcFooting")) == 4


def test_mezanino_quantitativo_e_orcamento_via_turnkey():
    import galpao_turnkey as gtk
    import orcamento as ORC
    spec = {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "mezanino": {"x0": 5.0, "y0": 5.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0, "q_uso": 2.0},
    }
    R = gtk.rodar(spec)
    assert R["disciplinas"]["mezanino"]["ATENDE"]
    q = ORC.quantitativos_de_turnkey(R)
    assert "concreto_estrut" in q and q["concreto_estrut"] > 0
    assert "fundacao_concreto" in q and q["fundacao_concreto"] > 0
    # vol total coerente com geometria: 4 pilares ~0.27*3*4=3.24 + 4 vigas + 1 laje
    assert 5 < q["concreto_estrut"] < 40
