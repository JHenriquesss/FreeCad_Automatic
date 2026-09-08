"""G62: a alvenaria ganha BIM e prancha.

Cada folha nova: (a) parseia o SVG como XML, nao substring; (b) confere
geometria contra o dado (desenhado == calculado); (c) roda colisoes de
rotulo. Par vermelho-por-injecao em cada guarda geometrica (drawing-vs-data).
"""
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import desenho_svg_base as sb

GALPAO = Path(__file__).resolve().parents[1]

BASE = {
    "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                  "pe_direito": 2.7},
    "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
    "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
    "viga": {"b": 0.20, "h": 0.45},
    "materiais": {"fck": 25e3, "fyk": 500e3},
    "alvenaria_portante": {
        "fpk": 4000.0, "material": "bloco", "te": 0.14,
        "combinacao": "normal", "habitacao_terrea": True,
        "parede_6120": {"tipo": "bloco_concreto_estrutural",
                        "espessura_cm": 14.0, "revestimento_cm": 2.0},
        "linhas": "todas",
        "vaos": {"BX-0": [{"pos_m": 1.0, "larg_m": 0.9, "alt_m": 2.1,
                           "peitoril_m": 0.0, "tipo": "porta"}],
                 "BY-0": [{"pos_m": 2.0, "larg_m": 1.2, "alt_m": 1.0,
                           "peitoril_m": 1.1, "tipo": "janela"}]}},
    "baldrame": {"b": 0.15, "h": 0.40,
                 "parede": {"tipo": "bloco_ceramico_furo_horizontal",
                            "espessura_cm": 14, "altura": 2.7,
                            "revestimento_cm": 1.0}},
    "fundacao": {"tipo": "sapata_corrida", "sigma_solo_adm": 150.0,
                 "cota_apoio_m": 1.0},
}

_CACHE = {}


@pytest.fixture(scope="module")
def estrutura():
    if "r" not in _CACHE:
        import estrutura_casa as ec

        _CACHE["r"] = ec.rodar(copy.deepcopy(BASE))
    assert _CACHE["r"]["ATENDE"], _CACHE["r"]["reprovados"]
    return _CACHE["r"]


def _xml(svg):
    return ET.fromstring(svg)


# ---------------- primitivas unificadas, nunca modulo paralelo -----------

def test_sem_escape_proprio_no_desenhista():
    import desenho_alvenaria as da

    src = Path(da.__file__).read_text(encoding="utf-8")
    assert "from desenho_svg_base import" in src
    assert "def _esc(" not in src
    assert "def _t(" not in src and "def _line(" not in src


# ---------------- elevacao: XML + geometria + colisoes --------------------

def test_elevacao_xml_e_geometria(estrutura):
    import desenho_alvenaria as da

    alv = estrutura["alvenaria"]
    pe = estrutura["H_total_m"] / estrutura["n_pavimentos"]
    svg = da.elevacao_paredes_svg(alv, pe, alv["te_m"])
    root = _xml(svg)
    assert len(root.findall(".//{http://www.w3.org/2000/svg}text")
               or root.findall(".//text")) > 0
    conf = da.confere_elevacao(svg, alv, pe)
    assert conf["ok"], conf
    # a contagem sai do RESULTADO, nunca de um literal: a foto do dia
    # cristaliza (a licao do AR300 e do len(arts) == 3 do G34).
    n_paredes = len(alv["por_linha"])
    assert conf["paredes_desenhadas"] == n_paredes
    assert conf["vaos_desenhados"] == conf["vaos_declarados"] == 2
    assert conf["fiadas_por_parede"] == 13     # 2,70 / 0,20, resto 0,10
    assert conf["ajustes_desenhados"] == n_paredes
    assert sb.colisoes_de_rotulo_svg(svg) == []
    # quadro segue o dado: inteiros/meios e areas do calculo
    q = da.quadro_parede(10.4, pe, [])
    assert q["inteiros"] > 0 and q["area_bruta_m2"] == round(10.4 * pe, 2)


def test_elevacao_vermelha_por_injecao(estrutura):
    import desenho_alvenaria as da

    alv = copy.deepcopy(estrutura["alvenaria"])
    pe = 2.7
    svg_antes = da.elevacao_paredes_svg(alv, pe, alv["te_m"])
    alv["por_linha"][0]["comprimento_m"] = 5.0      # muta o dado...
    svg_depois = da.elevacao_paredes_svg(alv, pe, alv["te_m"])
    assert svg_antes != svg_depois                  # ...o desenho segue
    conf = da.confere_elevacao(svg_depois, alv, pe)
    assert conf["ok"]                               # e continua fechando
    # NRd rotulado e' o calculado, nao numero fixo
    alv["por_linha"][1]["verificacao"] = dict(
        alv["por_linha"][1]["verificacao"], NRd_kN=1234.5)
    assert "1234.5" in da.elevacao_paredes_svg(alv, pe, alv["te_m"])


def test_vaos_invalidos_recusam_com_motivo():
    import estrutura_casa as ec

    s = copy.deepcopy(BASE)
    s["alvenaria_portante"]["vaos"] = {
        "BX-0": [{"pos_m": 1.0, "larg_m": 0.9, "alt_m": 2.1},
                 {"pos_m": 1.5, "larg_m": 0.9, "alt_m": 2.1}]}   # sobrepoe
    r = ec.rodar(s)
    assert r["ATENDE"] is False
    assert "alvenaria_portante" in r["reprovados"]
    assert "sobrepoem" in (r["alvenaria_erro"] or "")
    s2 = copy.deepcopy(BASE)
    s2["alvenaria_portante"]["vaos"] = {
        "BX-0": [{"pos_m": 9.9, "larg_m": 2.0, "alt_m": 2.1}]}   # fora
    r2 = ec.rodar(s2)
    assert r2["ATENDE"] is False
    assert "fora_da_parede" in (r2["alvenaria_erro"] or "")
    s3 = copy.deepcopy(BASE)
    s3["alvenaria_portante"]["vaos"] = {
        "P99": [{"pos_m": 1.0, "larg_m": 0.9, "alt_m": 2.1}]}    # linha morta
    r3 = ec.rodar(s3)
    assert r3["ATENDE"] is False
    assert "inexistente" in (r3["alvenaria_erro"] or "")


# ---------------- fiadas: XML + amarracao + colisoes -----------------------

def test_fiadas_xml_amarracao_e_geometria(estrutura):
    import desenho_alvenaria as da

    alv = estrutura["alvenaria"]
    pav = estrutura["pavimento"]
    svg = da.planta_fiadas_svg(alv, pav["vaos_x"], pav["vaos_y"], alv["te_m"])
    _xml(svg)
    conf = da.confere_fiadas(svg, alv)
    assert conf["ok"], conf
    assert conf["paredes_por_fiada"] == len(alv["por_linha"])
    assert conf["vaos_por_fiada"] == 2
    # amarracao: a 2a fiada desloca as juntas em meio bloco
    assert da._juntas_do_curso(4.0, False)[0] == da.PASSO_C
    assert da._juntas_do_curso(4.0, True)[0] == da.MEIO_BLOCO + da.JUNTA
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_fiadas_vermelhas_por_injecao(estrutura):
    import desenho_alvenaria as da

    alv = copy.deepcopy(estrutura["alvenaria"])
    pav = estrutura["pavimento"]
    svg_antes = da.planta_fiadas_svg(alv, pav["vaos_x"], pav["vaos_y"],
                                     alv["te_m"])
    alv["por_linha"][2]["vaos"].append(
        {"pos_m": 0.5, "larg_m": 1.0, "alt_m": 2.1, "peitoril_m": 0.0,
         "tipo": "porta"})
    svg_depois = da.planta_fiadas_svg(alv, pav["vaos_x"], pav["vaos_y"],
                                      alv["te_m"])
    assert svg_antes != svg_depois
    assert da.confere_fiadas(svg_depois, alv)["ok"]


# ---------------- hook de desenhos: arquivos + pulados ---------------------

def test_hook_emite_as_duas_folhas_e_nomeia_as_puladas(estrutura, tmp_path):
    import desenho_casa_residencial as dcr

    out = dcr.gerar_desenhos_casa({"estrutura": estrutura,
                                   "arquitetura": {"ambientes": []},
                                   "eletrico": {}, "hidraulica": {}},
                                  tmp_path / "d")
    assert "elevacao-paredes.svg" in out["files"]
    assert "planta-fiadas.svg" in out["files"]
    for nome in out["files"]:
        ET.parse(str(tmp_path / "d" / nome))       # cada arquivo abre em XML
    vazio = dcr.gerar_desenhos_casa({"estrutura": {"pavimento": None}},
                                    tmp_path / "d2")
    assert vazio["skipped"]["elevacao-paredes.svg"] == \
        "parede_portante_nao_calculada"
    assert vazio["skipped"]["planta-fiadas.svg"] == \
        "parede_portante_nao_calculada"


# ---------------- indice: PE-AL entra, laco continua fechando ---------------

def test_indice_tem_as_folhas_de_alvenaria():
    import pacote_legal as pl

    assert "alvenaria_estrutural" in pl._PRANCHAS
    pref, titulos = pl._PRANCHAS["alvenaria_estrutural"]
    assert pref == "PE-AL" and len(titulos) == 2
    indice = pl.indice_de_pranchas(["concreto", "alvenaria_estrutural"])
    cods = [p["codigo"] for p in indice]
    assert "PE-AL-01" in cods and "PE-AL-02" in cods
    arts = {a["disciplina"]: a for a in
            pl.lista_art(["concreto", "alvenaria_estrutural"])}
    assert arts["alvenaria_estrutural"]["conselho"] == "CREA"


def test_laco_indice_disco_da_casa_com_alvenaria(estrutura, tmp_path):
    import desenho_casa_residencial as dcr
    import pacote_legal as pl
    from gestao_casa import disciplinas_pacote

    result = {"estrutura": estrutura,
              "arquitetura": {"ambientes": [{"nome": "Sala"}]},
              "eletrico": {}, "hidraulica": {}}
    assert "alvenaria_estrutural" in disciplinas_pacote(result)
    indice = pl.indice_de_pranchas(disciplinas_pacote(result))
    assert any(p["codigo"].startswith("PE-AL") for p in indice)
    out = dcr.gerar_desenhos_casa(result, tmp_path / "d3")
    alv_arquivos = [f for f in out["files"]
                    if f in ("elevacao-paredes.svg", "planta-fiadas.svg")]
    assert len(alv_arquivos) == 2           # nenhuma folha evapora no hook
    for nome in alv_arquivos:
        assert (tmp_path / "d3" / nome).is_file()


# ---------------- BIM: membros, conferencia, IFC medido ----------------------

def test_modelo_neutro_paredes_e_corrida(estrutura):
    import bim_edificio as be

    membros = be.membros_bim(estrutura)
    tipos = {}
    for m in membros:
        tipos[m["tipo"]] = tipos.get(m["tipo"], 0) + 1
    n_linhas = len(estrutura["alvenaria"]["por_linha"])
    # a parede em Y e cortada em cada cruzamento (um membro por trecho):
    # duas paredes nao podem ocupar o mesmo volume.
    assert tipos.get("Wall") == be.n_trechos_parede(estrutura)
    assert tipos.get("Footing") == be.n_trechos_parede(estrutura)
    assert "Column" not in tipos             # sem portico, sem pilar
    conf = be.confere_modelo(estrutura, membros)
    assert conf["ok"], conf
    assert be.confere_empilhamento(membros)["OK"]
    # secao em m (fronteira), dims em mm
    parede = next(m for m in membros if m["marca"].startswith("PAR-BX-0"))
    assert parede["secao"] == {"forma": "RECT", "bf": 0.14, "d": 2.6}
    assert parede["p1"][2] == 0.0


def test_modelo_vermelho_por_injecao(estrutura):
    import bim_edificio as be

    pav = estrutura["pavimento"]
    xs, ys = be._eixos(pav["vaos_x"]), be._eixos(pav["vaos_y"])
    antes = be.membros_parede(estrutura, xs, ys, 2.7, 0.10)
    alv2 = copy.deepcopy(estrutura)
    alv2["alvenaria"]["por_linha"][0]["comprimento_m"] = 5.0
    depois = be.membros_parede(alv2, xs, ys, 2.7, 0.10)
    assert antes[0]["p2"] != depois[0]["p2"]   # o membro segue o dado


ifcopenshell = pytest.importorskip("ifcopenshell")


def _caixa(entidade):
    import ifcopenshell.geom as geom
    import ifcopenshell.util.shape as shape

    ajustes = geom.settings()
    ajustes.set("use-world-coords", True)
    forma = geom.create_shape(ajustes, entidade)
    return shape.get_bbox(shape.get_vertices(forma.geometry))


def _por_nome(modelo, nome):
    return next(e for e in modelo.by_type("IfcProduct") if e.Name == nome)


@pytest.fixture(scope="module")
def modelo_ifc(estrutura, tmp_path_factory):
    import bim_edificio as be

    destino = tmp_path_factory.mktemp("bim-g62") / "alvenaria.ifc"
    be.emitir_bim(estrutura, str(destino), nome="CasaAlvenaria")
    return ifcopenshell.open(str(destino))


def test_ifc_tem_paredes_lajes_e_corridas(modelo_ifc, estrutura):
    assert modelo_ifc.schema == "IFC4"
    import bim_edificio as be
    n_linhas = len(estrutura["alvenaria"]["por_linha"])
    n_paineis = estrutura["pavimento"]["n_paineis"]
    assert len(modelo_ifc.by_type("IfcWall")) == be.n_trechos_parede(estrutura)
    assert len(modelo_ifc.by_type("IfcSlab")) == n_paineis
    assert len(modelo_ifc.by_type("IfcFooting")) == be.n_trechos_parede(estrutura)


def test_ifc_em_metros_nao_milimetros(modelo_ifc, estrutura):
    """A licao do m x mm: a bbox da parede mede metros, nao milimetros."""
    te = estrutura["alvenaria"]["te_m"]
    minimo, maximo = _caixa(_por_nome(modelo_ifc, "PAR-BX-0-Cobertura"))
    dims = maximo - minimo
    assert dims[0] == pytest.approx(10.4, abs=1e-3), dims
    assert dims[1] == pytest.approx(te, abs=1e-4), dims
    assert dims[2] == pytest.approx(2.6, abs=1e-3), dims
    _minimo, maximo_f = _caixa(_por_nome(modelo_ifc, "COR-BX-0"))
    assert maximo_f[2] == pytest.approx(
        -estrutura["fundacao"]["cota_apoio_m"], abs=1e-4)


def test_nenhuma_parede_fica_fora_da_arvore(modelo_ifc):
    contidos = set()
    for relacao in modelo_ifc.by_type("IfcRelContainedInSpatialStructure"):
        contidos.update(e.id() for e in relacao.RelatedElements)
    produtos = [e for e in modelo_ifc.by_type("IfcProduct")
                if e.is_a() in ("IfcWall", "IfcSlab", "IfcFooting")]
    assert produtos
    assert [e.Name for e in produtos if e.id() not in contidos] == []


def test_verga_desenhada_nao_se_faz_passar_por_dimensionada():
    """A folha desenha verga/contraverga; ninguem as calcula — e isso e dito.

    Desenho que sugere um calculo inexistente e rotulo dirigindo geometria.
    O escopo tem de dizer `not_available` COM motivo enquanto nao houver
    conta; no dia em que houver, este teste pede a atualizacao junto.
    """
    import alvenaria_estrutural as alv
    esc = alv.escopo()
    assert esc["verga_contraverga"] == "not_available"
    motivo = alv.motivos_escopo()["verga_contraverga"]
    assert "dimensiona" in motivo and "verga" in motivo
