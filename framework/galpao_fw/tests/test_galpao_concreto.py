"""Galpao de concreto pre-moldado - orquestrador galpao_concreto.py.

Sistema: pilares engastados (balanco) + viga de cobertura biapoiada + sapata,
reusando vento_nbr6123 / viga_concreto / pilar_concreto / fundacao_sapata.
STATELESS (rodar(spec) recebe dict explicito - sem estado global).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import galpao_concreto as gc


def _spec(vao=10.0, **kw):
    base = {"vao": vao, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
            "v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
            "sigma_solo_adm": 250.0}
    base.update(kw)
    return base


def test_galpao_rc_tipico_atende():
    r = gc.rodar(_spec(vao=10.0))
    assert r["ATENDE"] and not r["reprovados"]
    for k in ("vento", "viga_cobertura", "pilar", "fundacao"):
        assert r["gates"][k]["OK"], k


def test_vento_gera_momento_de_base():
    # w_h = (Cpe_bar - Cpe_sot)*q*s = 1,30*q*s ; M_base = w_h*H^2/2
    r = gc.rodar(_spec())
    q = r["vento"]["q_kN_m2"]; s = r["spec"]["s"]; H = r["spec"]["H"]
    assert abs(r["gates"]["vento"]["w_h"] - 1.30 * q * s) < 0.05
    assert abs(r["gates"]["vento"]["M_base_k"] - 1.30 * q * s * H ** 2 / 2.0) < 0.5


def test_pilar_e_balanco_le_2H():
    r = gc.rodar(_spec())
    # o pilar do galpao e balanco: le = 2H em ambas direcoes
    assert abs(r["pilar"]["dir"]["x"]["le"] - 2 * r["spec"]["H"]) < 1e-9


def test_vao_grande_roteia_para_protensao():
    # 15 m: o concreto armado nao vence -> o sistema roteia p/ viga PROTENDIDA e ATENDE
    r = gc.rodar(_spec(vao=15.0))
    assert r["tipo_viga"] == "protendida"
    assert r["viga_prot"] is not None and r["viga_prot"]["OK"]
    assert r["gates"]["viga_cobertura"]["OK"] and r["ATENDE"]


def test_vao_pequeno_fica_em_concreto_armado():
    r = gc.rodar(_spec(vao=10.0))
    assert r["tipo_viga"] == "concreto armado" and r["viga_prot"] is None


def test_solo_fraco_reprova_fundacao_ou_cresce():
    # solo muito fraco: a sapata cresce; se nem a maior passa, gate REPROVA
    r = gc.rodar(_spec(sigma_solo_adm=40.0))
    # nao deve estourar; fundacao decide OK/REPROVA sem exception
    assert isinstance(r["gates"]["fundacao"]["OK"], bool)


def test_stateless_dois_specs_nao_interferem():
    r1 = gc.rodar(_spec(vao=8.0))
    r2 = gc.rodar(_spec(vao=12.0))
    assert r1["spec"]["vao"] == 8.0 and r2["spec"]["vao"] == 12.0
    assert r1["viga"]["h"] <= r2["viga"]["h"]      # vao maior -> viga maior/igual


def test_galpao_tem_gate_calice_e_icamento():
    # ligacao pre-moldada (NBR 9062): o galpao ganha calice + situacao transitoria
    r = gc.rodar(_spec(vao=10.0))
    assert r["gates"]["calice"]["OK"] and r["gates"]["icamento"]["OK"]
    # Lemb respeita o piso de 40 cm e a interface default e rugosa
    assert r["calice"]["Lemb"] >= 0.40
    assert r["gates"]["calice"]["interface"] == "rugosa"


def test_calice_interface_chaves_reduz_embutimento():
    # chaves de cisalhamento (1,2h->1,6h) exigem embutimento MENOR que rugosa (1,5h->2,0h)
    r_rug = gc.rodar(_spec(vao=10.0, interface_calice="rugosa"))
    r_cha = gc.rodar(_spec(vao=10.0, interface_calice="chaves"))
    assert r_cha["calice"]["Lemb"] <= r_rug["calice"]["Lemb"]


def test_galpao_sem_trrf_isento_com_nota():
    r = gc.rodar(_spec(vao=10.0))
    assert r["gates"]["fogo"]["OK"] and r["gates"]["fogo"]["TRRF"] is None
    assert "ISENTO" in r["gates"]["fogo"]["nota"]


def test_galpao_trrf_pilar_1face_atende():
    r = gc.rodar(_spec(vao=10.0, TRRF=60, faces_fogo_pilar=1))
    assert r["gates"]["fogo"]["OK"]


def test_galpao_trrf_pilar_multiface_requer_anexo_E():
    # pilar exposto em 4 faces + TRRF -> tabular nao cobre, gate acusa (nao finge)
    r = gc.rodar(_spec(vao=10.0, TRRF=90, faces_fogo_pilar=4))
    assert not r["gates"]["fogo"]["OK"]
    assert "Anexo E" in r["gates"]["fogo"]["nota"]


def test_selftest_roda():
    gc._selftest()
