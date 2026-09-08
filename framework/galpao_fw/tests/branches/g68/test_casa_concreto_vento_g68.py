"""G68 (medio, independente): a casa de concreto ganha vento.

A casa de concreto - inclusive o sobrado, que a tipologia aceita - tinha
acao_horizontal, estabilidade_global e desaprumo os tres em not_available, e
um sobrado saia ATENDE sem que nenhuma forca horizontal tivesse existido. O
predio multipavimento os tem; a casa estava uma disciplina atras.

Fronteira medida: a terrea dispensa (com o motivo escrito por item) e o
sobrado nao - sobrado de concreto sem vento e' RECUSADO (guarda de recusa no
molde do > 2 pavimentos do G13 e do sobrado_em_alvenaria_pede_vento do G67),
nunca ATENDE silencioso. Com vento (S1/S2/S3 + Ca declarado do abaco da
Fig.4), calcula Fa = Ca.q.Ae por nivel (6123 4.2.3), desaprumo + combinacao
30 % (6118 11.3.3.4.1) e indicador gamma_z + ELS lateral pelo portico plano.
O gamma_z sai como INDICADOR (15.5.3 fora do campo com < 4 andares), nao como
metodo; o gate reprova no ELS (Tab.13.3) e no indicador acima de 1,1.

Tambem reconfere o G13: a viga continua analisada e nunca verificada NAO
vale mais (verifica_vigas tramo a tramo, G34 no edificio, varredura guard).
E trava a licao do D84: estabilidade_b1b2 (MAES de aco, NBR 8800) NAO serve a
casa de concreto - o reuso e' de estabilidade_edificio (NBR 6118).
"""

import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

import estrutura_casa as ec

PAREDE = {"tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14,
          "altura": 2.7, "revestimento_cm": 2.0}

VENTO = {"v0": 40.0, "cat": "II", "classe": "B", "s1": 1.0, "s3": 1.0,
         "ca": {"x": 1.1, "y": 1.1}}

TERREA = {
    "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                  "pe_direito": 2.7},
    "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
    "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
    "viga": {"b": 0.20, "h": 0.45},
    "materiais": {"fck": 25e3, "fyk": 500e3},
    "parede_sobre_vigas": dict(PAREDE),
    "baldrame": {"b": 0.15, "h": 0.40, "parede": dict(PAREDE)},
}

SOBRADO = dict(TERREA, pavimentos=[
    {"nome": "Cobertura", "uso": "cobertura_manutencao"},
    {"nome": "Terreo", "uso": "residencial_dormitorio"}])


def _spec(base, **mudancas):
    spec = copy.deepcopy(base)
    spec.update(copy.deepcopy(mudancas))
    return spec


@pytest.fixture(scope="module")
def sobrado_vento():
    return ec.rodar(_spec(SOBRADO, vento=copy.deepcopy(VENTO)))


# ------------------------------------------------- fronteira com guarda

def test_sobrado_concreto_sem_vento_recusa_com_guarda():
    """O gate de verdade: sobrado que precisa do calculo e nao o tem reprova
    na entrada (molde G13/G67), em vez de ATENDE com not_available mudo."""
    with pytest.raises(ec.EntradaEstrutura) as erro:
        ec.rodar(copy.deepcopy(SOBRADO))
    assert "sobrado_concreto_pede_vento" in str(erro.value)
    assert "6123" in str(erro.value)


def test_mais_de_dois_pavimentos_continua_recusado():
    spec = _spec(TERREA, pavimentos=[{"nome": "Pav %d" % k,
                                      "uso": "residencial_dormitorio"}
                                     for k in range(3)],
                vento=copy.deepcopy(VENTO))
    with pytest.raises(ec.EntradaEstrutura) as erro:
        ec.rodar(spec)
    assert "edificio" in str(erro.value)


def test_terrea_sem_vento_atende_com_dispensa_escrita():
    """A terrea dispensa: ATENDE com o trio em not_available E o motivo
    escrito por item no relatorio (nao silencio)."""
    r = ec.rodar(copy.deepcopy(TERREA))
    assert r["ATENDE"], r["reprovados"]
    assert r["escopo"]["acao_horizontal"] == "not_available"
    assert r["escopo"]["estabilidade_global"] == "not_available"
    assert r["escopo"]["desaprumo"] == "not_available"
    assert "estabilidade_horizontal" not in r["gates"]
    rel = ec.relatorio_pt(r)
    assert "ACAO HORIZONTAL NAO AVALIADA" in rel
    assert "G68" in rel and "11.3.3.4.1" in rel and "15.5.3" in rel


# ------------------------------------------------- sobrado com vento

def test_sobrado_com_vento_atende_e_implementa_o_trio(sobrado_vento):
    assert sobrado_vento["ATENDE"], sobrado_vento["reprovados"]
    assert sobrado_vento["tipologia"] == "sobrado"
    assert sobrado_vento["escopo"]["acao_horizontal"] == "implemented"
    assert sobrado_vento["escopo"]["estabilidade_global"] == "implemented"
    assert sobrado_vento["escopo"]["desaprumo"] == "implemented"
    assert sobrado_vento["horizontal"] is not None


def test_vento_por_nivel_tem_origem_6123(sobrado_vento):
    gh = sobrado_vento["gates"]["estabilidade_horizontal"]
    assert gh["OK"] is True
    for d in ("x", "y"):
        v = gh["por_direcao"][d]
        assert v["F_total_kN"] > 0 and v["M_base_kNm"] > 0
        assert v["combinacao_caso"] in ("a", "b", "c")
        assert v["combinacao_usar"] in ("vento", "desaprumo", "combinado")
        assert v["combinacao_motivo"]
    assert sobrado_vento["horizontal"]["por_direcao"]["x"]["vento"][
        "ca_fonte"].startswith("NBR 6123")


def test_gamma_z_e_indicador_e_els_e_gate(sobrado_vento):
    gh = sobrado_vento["gates"]["estabilidade_horizontal"]
    assert gh["gamma_z_aplicavel"] is False
    assert 1.0 < gh["gamma_z_indicador_max"] <= 1.1
    assert gh["els_OK"] is True
    for d in ("x", "y"):
        v = gh["por_direcao"][d]
        assert v["els_OK"] is True and v["els_u_topo_mm"] > 0
    assert gh["dispensa"] and "M1d,min" in gh["dispensa"]
    rel = ec.relatorio_pt(sobrado_vento)
    assert "G68" in rel and "INDICADOR" in rel and "ELS" in rel


def test_terrea_com_vento_tambem_calcula():
    r = ec.rodar(_spec(TERREA, vento=copy.deepcopy(VENTO)))
    assert r["ATENDE"], r["reprovados"]
    assert r["escopo"]["acao_horizontal"] == "implemented"
    assert r["gates"]["estabilidade_horizontal"]["OK"] is True


def test_ca_numero_unico_vale_nas_duas_direcoes():
    vento = copy.deepcopy(VENTO)
    vento["ca"] = 1.2
    r = ec.rodar(_spec(SOBRADO, vento=vento))
    assert r["ATENDE"], r["reprovados"]
    gh = r["gates"]["estabilidade_horizontal"]
    assert gh["por_direcao"]["x"]["F_total_kN"] > 0
    assert gh["por_direcao"]["y"]["F_total_kN"] > 0


def test_vento_incompleto_recusa_nomeando():
    vento = {"v0": 40.0, "cat": "II", "classe": "B"}  # sem ca: sem origem
    with pytest.raises(ec.EntradaEstrutura) as erro:
        ec.rodar(_spec(SOBRADO, vento=vento))
    assert "vento_concreto_rejeitado" in str(erro.value)


# ------------------------------------------------- o gate tem dentes

def test_gate_reprova_quando_indicador_acima_de_1_1(sobrado_vento):
    h = copy.deepcopy(sobrado_vento["horizontal"])
    h["por_direcao"]["x"]["gamma_z"] = 1.25
    gate = ec.gate_horizontal_casa(h)
    assert gate["OK"] is False
    assert any("1,250" in m or "1.250" in m for m in gate["motivos"])
    assert gate["dispensa"] is None


def test_gate_reprova_quando_els_falha(sobrado_vento):
    h = copy.deepcopy(sobrado_vento["horizontal"])
    h["por_direcao"]["y"]["els"]["OK"] = False
    gate = ec.gate_horizontal_casa(h)
    assert gate["OK"] is False
    assert any("13.3" in m for m in gate["motivos"])


# ------------------------------------------------- G13 reconferido + D84

def test_g13_nao_vale_mais_viga_e_verificada(sobrado_vento):
    """O G13 registrou viga analisada e nunca verificada num dos caminhos:
    reconferido, nao vale mais - todo tramo e' dimensionado (G34 tambem no
    edificio, varredura guard)."""
    vigas = sobrado_vento["vigas"]
    assert sobrado_vento["gates"]["vigas"]["OK"]
    assert vigas["n_tramos"] > 0
    for linha in vigas["por_linha"]:
        for tramo in linha["tramos"]:
            assert tramo["OK"], (linha["nome"], tramo["tramo"])
            assert tramo["As_inf_cm2"] > 0 and tramo["As_sup_cm2"] > 0
            assert tramo["momento_negativo_coberto"]


def test_b1b2_nao_serve_a_casa_d84():
    """Semelhanca de simbolos nao e' parentesco de regra: estabilidade_b1b2
    e' MAES de aco (NBR 8800 Anexo D) do galpao; a casa de concreto reusa o
    portico de concreto (NBR 6118)."""
    fonte = (GALPAO / "estrutura_casa.py").read_text(encoding="utf-8")
    assert "import estabilidade_b1b2" not in fonte
    assert "from estabilidade_b1b2" not in fonte
    assert "estabilidade_edificio" in fonte


# ------------------------------------------------- aviso no adaptador

def test_aviso_nomeia_vento_ou_dispensa():
    import casa_residencial as cr
    com = cr._registro_estrutura(
        _spec(SOBRADO, vento=copy.deepcopy(VENTO)), None, None)[0]
    assert com["native_atende"] is True
    assert any(a["code"] == "vento_concreto_avaliado_G68"
               for a in com["warnings"]), [a["code"] for a in com["warnings"]]
    sem = cr._registro_estrutura(copy.deepcopy(TERREA), None, None)[0]
    assert any(a["code"] == "acao_horizontal_nao_avaliada"
               for a in sem["warnings"])
