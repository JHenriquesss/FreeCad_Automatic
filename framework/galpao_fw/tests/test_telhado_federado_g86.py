"""G86: o telhado reprovado entra no federado, carimbado - nunca some.

Contrato (a) do G86 (D101/G72 redesenhado): o telhado CALCULADO entra
sempre no federado, ATENDA ou nao. O clash e' sobre ocupacao fisica, e a
geometria da tesoura existe nos dois casos. Cada membro carrega
`situacao` ("ATENDE"/"REPROVADO", lida do calculo). Sem telhado calculado
nao ha membro (ausencia honesta). A folha ja carimbava REPROVA; o
orçamento e o memorial tambem - o federado era o unico que sumia.

Convencoes do repo, uma a uma:
1. baseline nos dois sentidos (reprovado entra, ATENDE entra, ausente some);
2. defeito por calculo reprovado em memoria - nenhum arquivo do repo e'
   mutado, nada em tmp_path e' preciso porque nada e' escrito;
3. substring -> parse -> renderizar: aqui nao ha folha nova (nenhum SVG
   tocado), entao parse/render nao se aplicam; as assercoes leem estrutura
   de dados, nunca substring;
4. saturacao silenciosa: o portao e' a contagem (83 barras no caso bom ==
   83 no reprovado) e a disciplina presente no clash;
5. sem tautologia: a contagem esperada do reprovado vem do caso ATENDE
   (mesma geometria, so a carga muda) e a `situacao` confere contra o
   veredito do CALCULO (telhado["ATENDE"]/reprovados), nunca contra os
   proprios membros.
"""

import copy
import sys
from pathlib import Path

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import bim_instalacoes_casa as bic
import bim_telhado_madeira as bt
import estrutura_casa as ec

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

VAOS_X = [3.5, 3.5, 3.4]
VAOS_Y = [4.0, 4.0]


def _casa(telhado):
    spec = {
        "geometria": {"vaos_x": list(VAOS_X), "vaos_y": list(VAOS_Y),
                      "pe_direito": 2.7},
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
    }
    if telhado is not None:
        spec["telhado_madeira"] = telhado
    return ec.rodar(spec)


def _telhado_atende():
    return copy.deepcopy(TELHADO)


def _telhado_reprovado():
    # Mesma geometria, carga absurda: o calculo reprova (barras, tercas,
    # ligacoes, apoio) mas entrega pecas, volume e tesouras.
    ruim = copy.deepcopy(TELHADO)
    ruim["telha"] = {"tipo": "ondulada", "peso": 5.0}
    ruim["sobrecarga_kNm2"] = 5.0
    return ruim


# --- sentido 1: o reprovado entra, carimbado ---------------------------------

def test_reprovado_entra_no_federado_carimbado():
    est = _casa(_telhado_reprovado())
    tel = est["telhado"]
    assert tel["ATENDE"] is False
    assert tel["reprovados"], "a fixture tem de reprovar de verdade"
    membros, disc = bic.membros_federados_casa(est, {}, {})
    assert "telhado" in disc, (
        "telhado calculado e reprovado sumiu do federado: %s" % disc)
    tm = [m for m in membros if m.get("disciplina") == "telhado"]
    assert tm
    # O carimbo vem do CALCULO (fonte independente), nao dos membros.
    assert {m.get("situacao") for m in tm} == {"REPROVADO"}
    for gate in tel["reprovados"]:
        assert gate, "gate reprovado sem nome nao carimba nada"


def test_reprovado_tem_a_mesma_geometria_do_atende():
    # Fonte independente da contagem: o caso bom (mesma geometria, carga
    # normal). Se o reprovado perdesse barra, a saturacao voltava.
    est_ok = _casa(_telhado_atende())
    est_ruim = _casa(_telhado_reprovado())
    m_ok, _ = bic.membros_federados_casa(est_ok, {}, {})
    m_ruim, _ = bic.membros_federados_casa(est_ruim, {}, {})
    n_ok = len([m for m in m_ok if m.get("disciplina") == "telhado"])
    n_ruim = len([m for m in m_ruim if m.get("disciplina") == "telhado"])
    assert n_ok > 0
    assert n_ruim == n_ok, (n_ruim, n_ok)
    conf = bt.confere_volume(
        est_ruim["telhado"],
        [m for m in m_ruim if m.get("disciplina") == "telhado"])
    assert conf["ok"], conf  # rotulo (vol_madeira_m3) x geometria medida


def test_reprovado_entra_no_clash():
    est = _casa(_telhado_reprovado())
    rep = bic.checa_interferencia_casa(est, {}, {})
    marcas = [m.get("marca", "") for m in
              bic.membros_federados_casa(est, {}, {})[0]]
    assert any(str(m).startswith("T-") for m in marcas)
    assert rep["n_membros"] == len(marcas)
    sem = _casa(None)
    rep_sem = bic.checa_interferencia_casa(sem, {}, {})
    assert rep["n_membros"] > rep_sem["n_membros"], (
        "o clash com telhado reprovado tem de ver mais membros que sem ele")


def test_reprovado_tem_escopo_e_memorial_proprios():
    est = _casa(_telhado_reprovado())
    assert est["escopo"]["telhado_madeira"] == "implemented"
    texto = ec.relatorio_pt(est)
    assert "REPROVA" in texto
    assert ("[A CONFIRMAR: estrutura de telhado em madeira fora do "
            "escopo.]") not in texto


def test_reprovado_emite_ifc(tmp_path):
    ifcopenshell = __import__("pytest").importorskip("ifcopenshell")
    est = _casa(_telhado_reprovado())
    dest = tmp_path / "telhado-reprovado.ifc"
    membros, _ = bic.membros_federados_casa(est, {}, {})
    tm = [m for m in membros if m.get("disciplina") == "telhado"]
    import ifc_emit as emit

    emit.emitir_ifc(tm, str(dest), nome="TelhadoReprovadoG86")
    m = ifcopenshell.open(str(dest))
    conf = bt.confere_modelo(est["telhado"], tm)
    assert len(m.by_type("IfcMember")) == conf["esperado"]["Member"]
    assert len(m.by_type("IfcBeam")) == conf["esperado"]["Beam"]


# --- sentido 2: o caso bom nao mudou ------------------------------------------

def test_atende_continua_carimbado_atende():
    est = _casa(_telhado_atende())
    assert est["telhado"]["ATENDE"] is True
    membros, disc = bic.membros_federados_casa(est, {}, {})
    assert "telhado" in disc
    tm = [m for m in membros if m.get("disciplina") == "telhado"]
    assert tm
    assert {m.get("situacao") for m in tm} == {"ATENDE"}


# --- outro sentido: sem telhado, sem disciplina --------------------------------

def test_sem_telhado_sem_disciplina_nem_carimbo():
    est = _casa(None)
    assert est["telhado"] is None
    membros, disc = bic.membros_federados_casa(est, {}, {})
    assert "telhado" not in disc
    assert not [m for m in membros if m.get("disciplina") == "telhado"]
    assert est["escopo"]["telhado_madeira"] == "not_available"
