# G77: as 28 folhas que continuavam sem guarda nem pixel.
"""Toda folha `*_svg` da arvore passa pela guarda generica do G76.

O buraco do G76 nao foi a guarda faltar - foi NINGUEM ter olhado 28 das 32
folhas. Guarda aplicada a 4 folhas e uma lente que ninguem passa nas outras
28 nao impede nada. Este arquivo fecha os dois lados:

  1. `test_censo_...`  - o conjunto que a ARVORE emite tem de ser exatamente o
     conjunto que esta suite EXERCITA (mais as isencoes nomeadas). Emissor novo
     sem cobertura fica vermelho. Sem este portao a cobertura encolhe em
     silencio - a licao de que varredura sem baseline nos dois sentidos e'
     relatorio, nao guarda.
  2. `test_folha_...`  - cada folha e' emitida de verdade, parseada como XML e
     medida por `confere_folha_svg` (viewBox == WxH, desenho contido na folha).

A escada continua sendo substring -> parse -> renderizar. Este arquivo e o
segundo degrau para as 32; o terceiro (renderizar-e-olhar) fica na amostragem
que o G76 abriu e nas folhas que esta varredura acusar.
"""
import copy
import json
import pathlib
import xml.etree.ElementTree as ET

import pytest

import desenho_svg_base as sb

GALPAO = pathlib.Path(__file__).resolve().parents[1]
REPO = GALPAO.parents[1]

_CACHE = {}


# ===========================================================================
# fixtures pesadas - uma vez por sessao, reusadas por varias folhas
# ===========================================================================

def _galpao_eletrico():
    if "ge" not in _CACHE:
        import galpao_eletrico as ge
        _CACHE["ge"] = ge.rodar({
            "tensao_V": 380.0, "sistema": "trifasico",
            "origem": "subestacao_propria",
            "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2},
                                   {"P_cv": 30.0, "eta": 0.90, "Fp": 0.86, "n": 3}],
                       "iluminacao_kW": 20.0, "ilum_fp": 0.92,
                       "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR",
                            "temp_amb": 40.0},
            "transformador": {"Sn_kVA": 300.0, "z_pct": 4.5},
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "spda": {"NP": "III", "Ng": 5.0, "R1": 2e-5},
            "aterramento": {"tipo": "malha", "rho": 100.0, "A": 800.0,
                            "L_cond": 400.0}})
    return _CACHE["ge"]


def _galpao_incendio():
    if "gi" not in _CACHE:
        import galpao_seguranca_incendio as gsi
        _CACHE["gi"] = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                                  "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                                  "deteccao": {"viga_m": 0.0},
                                  "sprinklers": {"altura_estoque_m": 3.0}})
    return _CACHE["gi"]


def _galpao_concreto():
    if "gc" not in _CACHE:
        import galpao_concreto as gc
        _CACHE["gc"] = gc.rodar({"vao": 10.0, "comprimento": 40.0,
                                 "pe_direito": 6.0, "n_porticos": 7, "v0": 40.0,
                                 "cat": "IV", "classe": "B", "G_roof": 0.30,
                                 "Q_roof": 0.25, "fck": 30e3,
                                 "sigma_solo_adm": 250.0})
    return _CACHE["gc"]


def _edificio():
    """Predio real do spec persistido: estrutura + as tres instalacoes."""
    if "ed" not in _CACHE:
        from tests.test_edificio_pranchas_g56 import _caso
        _CACHE["ed"] = _caso()                       # (R, H, E, I)
    return _CACHE["ed"]


def _casa_alvenaria():
    if "ca" not in _CACHE:
        import estrutura_casa as ec
        from tests.test_alvenaria_bim_pranchas_g62 import BASE
        r = ec.rodar(copy.deepcopy(BASE))
        assert r["ATENDE"], r["reprovados"]
        _CACHE["ca"] = r
    return _CACHE["ca"]


def _casa_run():
    """Casa residencial completa (spec persistido), com os desenhos no disco."""
    if "cr" not in _CACHE:
        import tempfile
        from builtin_adapters import register_builtin_adapters
        from project_loop import normalize_spec, run_project     # noqa: F401
        register_builtin_adapters()
        spec = json.loads((REPO / "projects" / "casa-residencial" /
                           "project-spec.json").read_text(encoding="utf-8"))
        destino = pathlib.Path(tempfile.mkdtemp(prefix="g77-casa-")) / "run"
        manifesto = run_project(spec, destino, {"generate_2d": True})
        _CACHE["cr"] = (manifesto, destino, spec)
    return _CACHE["cr"]


def _casa_resultado():
    """O `result` bruto da casa - as folhas recebem os sub-dicts dele."""
    if "crr" not in _CACHE:
        import casa_residencial as cres
        from builtin_adapters import register_builtin_adapters
        from project_loop import normalize_spec
        register_builtin_adapters()
        spec = json.loads((REPO / "projects" / "casa-residencial" /
                           "project-spec.json").read_text(encoding="utf-8"))
        resultado, _reg = cres.run_casa_residencial(normalize_spec(spec), None)
        _CACHE["crr"] = resultado
    return _CACHE["crr"]


def _casa_eletrica():
    """Resultado do adaptador residencial ELETRICO (fase 6B)."""
    if "ce" not in _CACHE:
        from tests.branches.phase6b.test_residential_electrical_deliverables \
            import _result
        _CACHE["ce"] = _result()
    return _CACHE["ce"]


def _layout_casa_g78():
    """O layout canonico da casa (G78), validado contra o programa.

    Passa pelo mesmo caminho do hook de desenhos (`_layout_para_planta` com
    o turnkey persistido): proveniencia arquitetura.layout, nunca o espelho
    eletrico direto."""
    if "g78lay" not in _CACHE:
        import desenho_casa_residencial as dcr
        spec = json.loads((REPO / "projects" / "casa-residencial" /
                           "project-spec.json").read_text(encoding="utf-8"))
        layout, _prov, erros = dcr._layout_para_planta(
            _casa_resultado(), spec.get("turnkey"))
        assert layout is not None, erros
        _CACHE["g78lay"] = layout
    return _CACHE["g78lay"]


def _telhado():
    if "tm" not in _CACHE:
        import telhado_casa_madeira as tm
        from tests.test_telhado_madeira_g66 import TELHADO_VIGA
        _CACHE["tm"] = tm.rodar(copy.deepcopy(TELHADO_VIGA))
    return _CACHE["tm"]


# ===========================================================================
# o registro: uma entrada por folha da arvore
# ===========================================================================

def _f_laje():
    import desenho_concreto as dc
    import laje_concreto as lj
    r = lj.verifica_laje(dict(lx=4.0, ly=6.0, h=0.12, fck=20e3, fyk=500e3,
                              caso=4, g=0.56, q=3.0, phi_mm=10.0))
    return dc.planta_laje_svg(r)


def _f_elevacao():
    import desenho_alvenaria as da
    r = _casa_alvenaria()
    alv = r["alvenaria"]
    pe = r["H_total_m"] / r["n_pavimentos"]
    return da.elevacao_paredes_svg(alv, pe, alv["te_m"])


def _f_fiadas():
    import desenho_alvenaria as da
    r = _casa_alvenaria()
    return da.planta_fiadas_svg(r["alvenaria"], r["pavimento"]["vaos_x"],
                                r["pavimento"]["vaos_y"], r["alvenaria"]["te_m"])


def _f_coordenacao():
    """Federado minimo com as chaves que o modulo LE (`p1`/`p2`, nao `bbox`).

    A federacao em si e' exercitada em `test_coordenacao`; aqui o alvo e' a
    geometria da FOLHA, e para isso basta o modelo ter extremos reais em duas
    disciplinas mais um clash no resumo.
    """
    import desenho_coordenacao as dco
    membros = [
        {"marca": "EST-C1", "disciplina": "estrutura",
         "p1": [0, 0, 0], "p2": [0, 0, 6000]},
        {"marca": "EST-C2", "disciplina": "estrutura",
         "p1": [20000, 0, 0], "p2": [20000, 0, 6000]},
        {"marca": "EST-V1", "disciplina": "estrutura",
         "p1": [0, 0, 6000], "p2": [20000, 0, 6000]},
        {"marca": "ELE-E1", "disciplina": "eletrico",
         "p1": [1000, 500, 3000], "p2": [19000, 500, 3000]},
        {"marca": "HID-T1", "disciplina": "hidraulica",
         "p1": [1000, 4000, 2500], "p2": [19000, 4000, 2500]},
    ]
    clash = {"revisar": [{"a": "ELE-E1", "b": "HID-T1",
                          "pontos": [[10000, 2000, 2750]]}]}
    return dco.coordenacao_svg(membros, clash)


def _f_matriz():
    import compatibilizacao as cp
    from tests.test_compatibilizacao import _rep
    return cp.matriz_svg(_rep())


def _f_curva_s():
    import cronograma as cr
    return cr.curva_s_svg(cr.cronograma(
        cr.aplica_custos(cr._WBS_GALPAO, {"estr": 400000, "fund": 90000})))


def _f_fv():
    import fotovoltaico as fv
    return fv.grafico_svg(fv.dimensiona_fv({"area_cobertura_m2": 800.0,
                                            "HSP": 5.2,
                                            "consumo_kwh_mes": 18000.0}))


def _f_juntas():
    import desenho_piso as dpi
    import piso_industrial as pi
    return dpi.planta_juntas_svg(pi.verifica_piso(
        {"L": 40.0, "W": 20.0, "fck_MPa": 30.0, "k_MN_m3": 60.0,
         "cargas": [{"nome": "empilhadeira 3t", "P_kN": 30.0,
                     "area_contato_cm2": 300.0}]}))


def _f_tp01():
    import desenho_terraplenagem as dte
    import terraplenagem as tp
    grid = [[102.3, 101.8, 101.2], [101.5, 101.0, 100.4], [100.6, 100.1, 99.5]]
    vols = tp.volumes_corte_aterro(grid, 101.0, 400.0)
    return dte.mapa_corte_aterro_svg(
        {"grid_terreno": grid, "cota_plataforma": 101.0,
         "area_celula_m2": 400.0, "empolamento": 1.25, "volumes": vols,
         "greide": tp.greide_equilibrio(grid, 400.0, empolamento=1.25),
         "movimento": tp.movimento_terra(vols["corte_m3"], vols["aterro_m3"],
                                         1.25)})


def _f_tp02():
    import desenho_terraplenagem as dte
    import terraplenagem as tp
    caso = {"C": 0.75, "i_mm_h": 130.0, "area_ha": 1.2,
            "largura_canaleta_m": 0.4, "declividade": 0.008}
    return dte.planta_drenagem_svg(
        {"caso": caso, "resultado": tp.dimensiona_drenagem(caso)})


#: nome do censo -> funcao que EMITE a folha de verdade (nada sintetico).
FOLHAS = {
    # ---- galpao: eletrico / incendio / hidraulica / climatizacao ----------
    "desenho_eletrico.diagrama_unifilar_svg":
        lambda: __import__("desenho_eletrico").diagrama_unifilar_svg(_galpao_eletrico()),
    "desenho_eletrico.quadro_cargas_svg":
        lambda: __import__("desenho_eletrico").quadro_cargas_svg(_galpao_eletrico()),
    "desenho_eletrico.planta_eletrica_svg":
        lambda: __import__("desenho_eletrico").planta_eletrica_svg(_galpao_eletrico()),
    "desenho_incendio.planta_seguranca_svg":
        lambda: __import__("desenho_incendio").planta_seguranca_svg(_galpao_incendio()),
    "desenho_hidraulica.esquema_hidraulica_svg":
        lambda: __import__("desenho_hidraulica").esquema_hidraulica_svg(
            __import__("galpao_hidraulica").rodar(
                {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                 "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                                "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}})),
    "desenho_climatizacao.esquema_climatizacao_svg":
        lambda: __import__("desenho_climatizacao").esquema_climatizacao_svg(
            __import__("galpao_climatizacao").rodar(
                {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "tipo": "galpao"})),

    # ---- edificio multipavimento -----------------------------------------
    "desenho_eletrico.diagrama_prumada_edificio_svg":
        lambda: __import__("desenho_eletrico").diagrama_prumada_edificio_svg(
            _edificio()[2], _edificio()[0]),
    "desenho_eletrico.planta_eletrica_pavimento_svg":
        lambda: __import__("desenho_eletrico").planta_eletrica_pavimento_svg(
            _edificio()[2], _edificio()[0]),
    "desenho_eletrico.qdc_edificio_svg":
        lambda: __import__("desenho_eletrico").qdc_edificio_svg(
            _edificio()[2], _edificio()[0]),
    "desenho_eletrico.infra_aterramento_edificio_svg":
        lambda: __import__("desenho_eletrico").infra_aterramento_edificio_svg(
            _edificio()[2], _edificio()[0]),
    "desenho_hidraulica.planta_rede_edificio_svg":
        lambda: __import__("desenho_hidraulica").planta_rede_edificio_svg(
            _edificio()[1], _edificio()[0], rede="agua"),
    "desenho_incendio.planta_pavimento_edificio_svg":
        lambda: __import__("desenho_incendio").planta_pavimento_edificio_svg(
            _edificio()[3], _edificio()[0]),
    "desenho_incendio.detalhes_hidrantes_rotas_svg":
        lambda: __import__("desenho_incendio").detalhes_hidrantes_rotas_svg(
            _edificio()[3], _edificio()[0]),
    "desenho_escada_edificio.planta_escada_svg":
        # G81: a escada calculada vira folha (PE-IN-03).
        lambda: __import__("desenho_escada_edificio").planta_escada_svg(
            _edificio()[0]["escada"], _edificio()[3]),
    "desenho_pavimento.planta_formas_svg":
        lambda: __import__("desenho_pavimento").planta_formas_svg(
            _edificio()[0]["pavimento"]),
    "desenho_pavimento.prancha_armacao_vigas_svg":
        # a folha le `vigas_verificacao` (7 linhas / 17 tramos do G34), NAO o
        # `pavimento`: com o dict errado ela emite a tabela VAZIA sem reclamar.
        lambda: __import__("desenho_pavimento").prancha_armacao_vigas_svg(
            _edificio()[0]["vigas_verificacao"]),
    "desenho_fundacao_edificio.planta_fundacao_svg":
        # G80: a fundacao dimensionada por pilar vira folha (PE-CO-04).
        lambda: __import__("desenho_fundacao_edificio").planta_fundacao_svg(
            _edificio()[0]["fundacao"], _edificio()[0]),

    # ---- concreto (galpao pre-moldado + laje) -----------------------------
    "desenho_concreto.prancha_armacao_svg":
        lambda: __import__("desenho_concreto").prancha_armacao_svg(_galpao_concreto()),
    "desenho_concreto.planta_formas_svg":
        lambda: __import__("desenho_concreto").planta_formas_svg(_galpao_concreto()),
    "desenho_concreto.planta_laje_svg": _f_laje,

    # ---- alvenaria estrutural --------------------------------------------
    "desenho_alvenaria.elevacao_paredes_svg": _f_elevacao,
    "desenho_alvenaria.planta_fiadas_svg": _f_fiadas,

    # ---- casa residencial -------------------------------------------------
    "desenho_casa_residencial.quadro_ambientes_svg":
        lambda: __import__("desenho_casa_residencial").quadro_ambientes_svg(
            _casa_resultado()["arquitetura"]),
    "desenho_casa_residencial.conferencia_svg":
        lambda: __import__("desenho_casa_residencial").conferencia_svg(
            _casa_resultado()["eletrico"]["conferencia_nbr5410"]),
    "desenho_casa_residencial.esquema_hidraulico_svg":
        lambda: __import__("desenho_casa_residencial").esquema_hidraulico_svg(
            _casa_resultado()["hidraulica"]),
    "desenho_casa_residencial.telhado_tesoura_svg":
        lambda: __import__("desenho_casa_residencial").telhado_tesoura_svg(_telhado()),
    "desenho_casa_residencial.planta_baixa_svg":
        lambda: __import__("desenho_casa_residencial").planta_baixa_svg(
            _casa_resultado()["arquitetura"], _layout_casa_g78()),

    # ---- eletrica residencial (fase 6B) ----------------------------------
    "desenho_eletrico_residencial.unifilar_residencial_svg":
        lambda: __import__("desenho_eletrico_residencial").unifilar_residencial_svg(
            _casa_eletrica()),
    "desenho_eletrico_residencial.quadro_cargas_residencial_svg":
        lambda: __import__("desenho_eletrico_residencial"
                           ).quadro_cargas_residencial_svg(_casa_eletrica()),
    "desenho_eletrico_residencial.planta_eletrica_residencial_svg":
        lambda: __import__("desenho_eletrico_residencial"
                           ).planta_eletrica_residencial_svg(_casa_eletrica()),

    # ---- avulsos (gestao e sistemas) --------------------------------------
    "desenho_coordenacao.coordenacao_svg": _f_coordenacao,
    "compatibilizacao.matriz_svg": _f_matriz,
    "cronograma.curva_s_svg": _f_curva_s,
    "fotovoltaico.grafico_svg": _f_fv,
    "desenho_piso.planta_juntas_svg": _f_juntas,
    "desenho_terraplenagem.mapa_corte_aterro_svg": _f_tp01,
    "desenho_terraplenagem.planta_drenagem_svg": _f_tp02,
}

#: folhas conhecidas que esta suite NAO exercita, com o motivo escrito. Vazio
#: hoje: manter assim exige que folha nova venha com caso, ou com a razao.
ISENTAS = {}


# ===========================================================================
# 1. o portao: censo da arvore x cobertura desta suite
# ===========================================================================

def test_censo_encontra_as_folhas_da_arvore():
    """Baseline: a lente enxerga folha, e nao enxerga o que nao e' folha."""
    censo = sb.censo_de_folhas(GALPAO)
    assert len(censo) >= 30, censo
    # amostra: folha conhecida entra, com arquivo e linha
    arq, linha = censo["desenho_alvenaria.elevacao_paredes_svg"]
    assert arq == "desenho_alvenaria.py" and linha > 0
    # e as tres que NAO sao folha ficam de fora, por nome (nao heuristica)
    nomes = {k.split(".", 1)[1] for k in censo}
    assert nomes.isdisjoint(set(sb.NAO_E_FOLHA))
    assert "desenho_svg_base.abre_svg" not in censo


def test_toda_folha_da_arvore_esta_coberta_ou_isenta():
    """O portao. Emissor novo sem caso deixa esta suite VERMELHA.

    Sem ele, `FOLHAS` viraria um relatorio do que alguem lembrou de cobrir - e
    a proxima folha nasceria sem ninguem olhar, exatamente como as 28 do G76.
    """
    censo = set(sb.censo_de_folhas(GALPAO))
    coberto = set(FOLHAS) | set(ISENTAS)
    sem_caso = sorted(censo - coberto)
    assert sem_caso == [], (
        "folha emitida pela arvore e nao exercitada por esta suite: %s "
        "(adicione um caso em FOLHAS ou uma isencao com motivo em ISENTAS)"
        % sem_caso)
    fantasmas = sorted(coberto - censo)
    assert fantasmas == [], (
        "caso apontando para folha que nao existe mais na arvore: %s" % fantasmas)


def test_o_portao_fica_vermelho_com_folha_nova_sem_caso(tmp_path):
    """Vermelho por INJECAO, em diretorio temporario - nunca mutando o repo.

    Baseline no outro sentido: o mesmo diretorio sem o emissor novo passa.
    """
    (tmp_path / "desenho_ficticio.py").write_text(
        "def planta_nova_svg(r):\n    return '<svg/>'\n", encoding="utf-8")
    (tmp_path / "desenho_vazio.py").write_text(
        "def ajuda():\n    return 1\n", encoding="utf-8")
    censo = sb.censo_de_folhas(tmp_path)
    assert set(censo) == {"desenho_ficticio.planta_nova_svg"}, censo
    # o portao, aplicado a este diretorio, acusaria a folha sem caso
    assert sorted(set(censo) - set(FOLHAS)) == ["desenho_ficticio.planta_nova_svg"]
    # outro sentido: sem o emissor, nada a acusar
    (tmp_path / "desenho_ficticio.py").unlink()
    assert sb.censo_de_folhas(tmp_path) == {}


def test_censo_ignora_funcao_aninhada_e_arquivo_de_teste(tmp_path):
    """So `def` de nivel de MODULO conta - closure interna nao e' folha."""
    (tmp_path / "desenho_interno.py").write_text(
        "def gera(r):\n"
        "    def parcial_svg(x):\n"
        "        return '<svg/>'\n"
        "    return parcial_svg(r)\n", encoding="utf-8")
    (tmp_path / "test_algo.py").write_text(
        "def prancha_svg(r):\n    return '<svg/>'\n", encoding="utf-8")
    assert sb.censo_de_folhas(tmp_path) == {}


# ===========================================================================
# 2. a guarda, folha por folha
# ===========================================================================

@pytest.mark.parametrize("nome", sorted(FOLHAS))
def test_folha_passa_na_guarda_generica(nome):
    """Parse XML (nunca substring) + viewBox == WxH + desenho dentro da folha."""
    svg = FOLHAS[nome]()
    assert isinstance(svg, str) and svg.lstrip().startswith("<svg"), nome
    ET.fromstring(svg)                       # XML de verdade; malformado levanta
    c = sb.confere_folha_svg(svg)
    assert c["ok"], "%s: %s" % (nome, c["motivo"])


@pytest.mark.parametrize("nome", sorted(FOLHAS))
def test_folha_nao_sai_em_branco(nome):
    """Folha valida e VAZIA continua sendo folha que ninguem pode entregar.

    A elevacao do G76 era XML valido, com width/height/viewBox e todos os
    atributos que tres guardas conferiam - e nao desenhava nada. O piso aqui e'
    CONTEUDO: descontados o fundo branco (o rect do tamanho da folha) e o
    titulo, tem de sobrar desenho ou texto. Uma folha de TABELA (a armacao de
    vigas e' quase so texto) e uma de GEOMETRIA (a tesoura e' quase so linha)
    passam pelo mesmo criterio sem que ele vire tautologia.
    """
    svg = FOLHAS[nome]()
    raiz = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    W, H = float(raiz.get("width")), float(raiz.get("height"))

    def _todos(tag):
        return list(raiz.iter(ns + tag)) + list(raiz.iter(tag))

    def _num(el, chave):
        try:
            return float(el.get(chave, 0.0))
        except (TypeError, ValueError):
            return 0.0

    desenho = []
    for tag in ("rect", "line", "circle", "ellipse", "path", "polyline",
                "polygon"):
        for el in _todos(tag):
            fundo = (tag == "rect" and _num(el, "width") >= W - 1
                     and _num(el, "height") >= H - 1)
            if not fundo:                         # o fundo branco nao e conteudo
                desenho.append(el)
    textos = [el for el in _todos("text") if (el.text or "").strip()]
    util = len(desenho) + max(0, len(textos) - 1)   # -1: o titulo tampouco conta
    assert util >= 6, ("%s: folha praticamente vazia - %d elementos de desenho "
                       "(fora o fundo) e %d textos"
                       % (nome, len(desenho), len(textos)))


# ===========================================================================
# 3. o defeito que esta varredura achou: a folha de armacao tinha altura fixa
# ===========================================================================

def _armacao(**kw):
    import galpao_concreto as gc
    import desenho_concreto as dc
    sp = {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
          "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30, "Q_roof": 0.25,
          "fck": 30e3, "sigma_solo_adm": 250.0}
    sp.update(kw)
    r = gc.rodar(sp)
    return r, dc.prancha_armacao_svg(r)


def _cota_mais_baixa(svg):
    """y do texto mais baixo da folha (as cotas de largura ficam sob a secao)."""
    raiz = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    ys = [float(el.get("y", 0.0))
          for el in list(raiz.iter(ns + "text")) + list(raiz.iter("text"))]
    return max(ys), float(raiz.get("height"))


def test_prancha_de_armacao_acompanha_a_altura_da_secao():
    """O defeito: `Hn = 380` fixo enquanto a secao cresce com a peca.

    O pilar de 90 cm dava 315 px de altura e jogava a cota de largura em
    y = 383,5 - emitida, valida no XML, e FORA da folha entregue. A guarda
    antiga (`test_tudo_cabe_no_canvas`) so olhava o X, e por substring.
    """
    r_alto, svg_alto = _armacao()                       # pilar 90 cm
    r_baixo, svg_baixo = _armacao(vao=8.0, pe_direito=4.0)   # pilar 70 cm
    assert r_alto["pilar"]["hx"] > r_baixo["pilar"]["hx"]

    y_alto, h_alto = _cota_mais_baixa(svg_alto)
    y_baixo, h_baixo = _cota_mais_baixa(svg_baixo)
    # a folha cresce com a peca (nao e' constante)
    assert h_alto > h_baixo, (h_alto, h_baixo)
    # e em ambas a cota mais baixa CABE
    assert y_alto <= h_alto and y_baixo <= h_baixo, (y_alto, h_alto, y_baixo, h_baixo)
    # baseline no outro sentido: com a altura FIXA de antes, a peca alta
    # estouraria - e a baixa nao. Foi por isso que o defeito passou despercebido:
    # dependia de qual fixture a pessoa abrisse.
    ALTURA_FIXA_ANTIGA = 380.0
    assert y_alto > ALTURA_FIXA_ANTIGA, y_alto
    assert y_baixo <= ALTURA_FIXA_ANTIGA, y_baixo


def test_nota_c55_c90_nao_pisa_na_cota_da_secao():
    """A NOTA e' escrita no rodape; a folha reserva a linha dela."""
    import desenho_concreto as dc
    r_sem, svg_sem = _armacao()
    r_com, svg_com = _armacao(fck=60e3)
    if not dc._exige_gancho_135(r_com):
        pytest.skip("fixture nao caiu em C55-C90")
    assert not dc._exige_gancho_135(r_sem)
    h_sem = float(ET.fromstring(svg_sem).get("height"))
    h_com = float(ET.fromstring(svg_com).get("height"))
    assert h_com >= h_sem + dc.ALTURA_NOTA - 1e-6, (h_sem, h_com)
    assert sb.confere_folha_svg(svg_com)["ok"], sb.confere_folha_svg(svg_com)
    y_texto, h = _cota_mais_baixa(svg_com)
    assert y_texto <= h
