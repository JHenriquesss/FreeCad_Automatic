# ============================================================================
# test_fase610_cortante_tapered.py - RED tests da Fase 6.10.
# Cortante da ALMA em barra de secao variavel: as mesas inclinadas carregam parte
# da cortante via componente transversal da forca de mesa. Por EQUILIBRIO (NAO e
# clausula da NBR - Anexo J so tem J.1-J.4, cortante remetido a 5.4.3 por J.1.2):
#   V_alma = V - (M/h_m)*(dh/dx)    [braco = h_m ; 2 mesas -> (M/h_m)*dh/dx]
# Favoravel (alivio) e OPT-IN do engenheiro (default conservador); adverso
# (acrescimo) e SEMPRE contado.
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

FY = 250e3


# ==================== me-1: geometria + V_alma efetivo ====================
def test_dhdx_tapered_e_prismatico():
    import cortante_tapered as ct
    assert ct.dh_dx(0.60, 0.90, 3.0) == pytest.approx(0.10, rel=1e-9)
    assert ct.dh_dx(0.50, 0.50, 3.0) == 0.0            # prismatico


def test_haunch_alivio():
    # sentido=+1 (profundidade cresce onde |M| cresce) -> V_alma < V
    import cortante_tapered as ct
    V = 200.0; M = 300.0; h = 0.9; dhdx = 0.10
    Vef = ct.v_alma_efetivo(M, V, h, dhdx, sentido=+1)
    assert abs(Vef) < abs(V), "haunch deve aliviar o cortante da alma"


def test_prismatico_sem_efeito():
    import cortante_tapered as ct
    V = 200.0
    assert ct.v_alma_efetivo(300.0, V, 0.9, 0.0, sentido=+1) == pytest.approx(V, rel=1e-12)


def test_M_zero_sem_efeito():
    import cortante_tapered as ct
    V = 200.0
    assert ct.v_alma_efetivo(0.0, V, 0.9, 0.10, sentido=+1) == pytest.approx(V, rel=1e-12)


def test_adverso_acrescimo():
    # sentido=-1 -> a mesa AUMENTA o cortante da alma
    import cortante_tapered as ct
    V = 200.0
    Vef = ct.v_alma_efetivo(300.0, V, 0.9, 0.10, sentido=-1)
    assert abs(Vef) > abs(V), "geometria adversa deve aumentar o cortante da alma"


# ==================== me-2: wrapper conservador ==========================
def test_conservador_favoravel_nao_credita():
    import cortante_tapered as ct
    r = ct.cortante_efetivo_conservador(300.0, 200.0, 0.9, 0.10, sentido=+1,
                                        creditar=False)
    assert r["V_usar"] == pytest.approx(200.0), "default nao credita alivio"
    assert r["alivio"] > 0.0


def test_conservador_favoravel_credita():
    import cortante_tapered as ct
    r = ct.cortante_efetivo_conservador(300.0, 200.0, 0.9, 0.10, sentido=+1,
                                        creditar=True)
    assert r["V_usar"] < 200.0, "com opt-in, credita o alivio"
    assert r["V_usar"] == pytest.approx(abs(r["V_efetivo"]))


def test_conservador_adverso_sempre_conta():
    import cortante_tapered as ct
    r = ct.cortante_efetivo_conservador(300.0, 200.0, 0.9, 0.10, sentido=-1,
                                        creditar=False)
    assert r["V_usar"] > 200.0, "adverso deve entrar mesmo sem opt-in (mne-3)"
    assert r["acrescimo"] > 0.0


def test_adverso_usa_braco_exato_h0():
    # parecer item 40: no caso ADVERSO o braco deve ser h0 = h_m - tf (exato,
    # MENOR que h_m) -> forca de mesa MAIOR -> acrescimo MAIOR (seguro). Passar tf>0
    # deve aumentar |V_ef| adverso vs tf=0 (aproximacao h_m).
    import cortante_tapered as ct
    v_hm = ct.v_alma_efetivo(300.0, 200.0, 0.90, 0.10, sentido=-1, tf=0.0)
    v_h0 = ct.v_alma_efetivo(300.0, 200.0, 0.90, 0.10, sentido=-1, tf=0.02)
    assert abs(v_h0) > abs(v_hm) + 1e-9, \
        "adverso deve usar braco exato h0=h_m-tf (acrescimo maior, seguro)"


def test_favoravel_mantem_hm_conservador():
    # no caso FAVORAVEL (alivio) o braco deve permanecer h_m (MAIOR) -> forca de mesa
    # MENOR -> menos credito -> conservador. tf nao deve alterar o alivio favoravel.
    import cortante_tapered as ct
    v_hm = ct.v_alma_efetivo(300.0, 200.0, 0.90, 0.10, sentido=+1, tf=0.0)
    v_tf = ct.v_alma_efetivo(300.0, 200.0, 0.90, 0.10, sentido=+1, tf=0.02)
    assert v_tf == pytest.approx(v_hm, rel=1e-12), \
        "favoravel deve manter h_m (credito menor, conservador) mesmo com tf"


def test_conservador_prismatico_creditar_nada_muda():
    # mne-5: prismatico (dh/dx=0) -> nada muda mesmo com creditar=True
    import cortante_tapered as ct
    r = ct.cortante_efetivo_conservador(300.0, 200.0, 0.9, 0.0, sentido=+1,
                                        creditar=True)
    assert r["V_usar"] == pytest.approx(200.0)
    assert r["alivio"] == 0.0 and r["acrescimo"] == 0.0


def test_selftest_roda():
    import cortante_tapered as ct
    ct._selftest()


# ==================== me-3: integracao rodar =============================
def _spec_tapered(creditar=False):
    from test_fase6b_alma_variavel import _spec
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 0.90, "h_cumeeira": 0.45, "h_col_base": 0.35,
                       "bf": 0.22, "tw": 0.006, "tf": 0.014})
    s["estrutura"]["creditar_cortante_mesa_inclinada"] = creditar
    return s


def test_integra_reporta_reserva(tmp_path):
    import rodar_projeto as RP
    r = RP.calcular(_spec_tapered(creditar=False), str(tmp_path))
    av = r.get("alma_variavel", {})
    assert "cortante_mesa_alivio_kN" in av, "res deve reportar a reserva de cortante da mesa"
    assert av["cortante_mesa_alivio_kN"] >= 0.0


def test_credito_nao_piora_utilizacao(tmp_path):
    # creditar=True (haunch) NAO pode aumentar a interacao da coluna vs default.
    import rodar_projeto as RP
    a = RP.calcular(_spec_tapered(creditar=False), str(tmp_path / "a"))
    b = RP.calcular(_spec_tapered(creditar=True), str(tmp_path / "b"))
    ua = a["alma_variavel"].get("interacao_max_col")
    ub = b["alma_variavel"].get("interacao_max_col")
    if ua is not None and ub is not None:
        assert ub <= ua + 1e-9, "creditar alivio nao pode piorar a utilizacao"
