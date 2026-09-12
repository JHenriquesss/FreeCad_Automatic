# ============================================================================
# test_pe05_topo_g118.py - G118: a vista de topo da PE05 nao leva TIRANTE.
#
# A PE05 travava o recompute (>1200 s, 2x no harness + 540 s no diag, D133).
# Fatiado vista a vista no modelo galpao-ufpe (44x90, 2798 solidos): lateral
# sozinha passa (t_hlr 123 s), topo sozinho trava, e o veneno sao os 432
# TIRANTEs vistos de topo/fundo sem os planos oclusores da cobertura
# (432 tirantes sozinhos no topo = 548 s de recompute; o contexto de 955 com
# oclusores sai em ~60 s). O topo mostra so os CONTRAV (12, ~5 s); tirantes,
# esticadores e porticos seguem cobertos na lateral (Source da V05_CV_LAT).
#
# Sem FreeCAD: FreeCAD fake (so Vector) + stubs de doc/vista. O repo vivo
# nunca e mutado.
# ============================================================================
"""Portao G118: topo da PE05 sem TIRANTE (o que travava o recompute)."""

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import techdraw_exec as TD


class _FakeVector(tuple):
    def __new__(cls, *args):
        return super().__new__(cls, [float(a) for a in args])


def _fake_freecad():
    mod = types.ModuleType("FreeCAD")

    def Vector(*args):
        return _FakeVector(*args)

    mod.Vector = Vector
    mod.getResourceDir = lambda: "X"
    return mod


class _FakeBBox:
    def __init__(self, xl=7500.0, yl=44000.0, zl=7000.0):
        self.XLength, self.YLength, self.ZLength = xl, yl, zl
        self.XMin, self.YMin, self.ZMin = 0.0, 0.0, 0.0
        self.XMax, self.YMax, self.ZMax = xl, yl, zl

    def united(self, other):
        return _FakeBBox(max(self.XLength, other.XLength),
                         max(self.YLength, other.YLength),
                         max(self.ZLength, other.ZLength))


class _FakeShape:
    def __init__(self):
        self._bb = _FakeBBox()

    def isNull(self):
        return False

    @property
    def BoundBox(self):
        return self._bb


class _FakeObj:
    def __init__(self, label):
        self.Label = label
        self.Name = label
        self.TypeId = "Part::Feature"
        self.Shape = _FakeShape()


class _FakeView:
    def __init__(self, name):
        self.Name = name
        self.Source = []
        self.views = []

    def addView(self, v):
        self.views.append(v)


class _FakeTpl:
    def __init__(self):
        self.Template = ""
        self.EditableTexts = {"title": "", "drawing_number": "",
                              "scale": "", "sheet_number": ""}


class _FakeDoc:
    def __init__(self):
        self.made = []

    def addObject(self, tipo, nome):
        if tipo == "TechDraw::DrawSVGTemplate":
            o = _FakeTpl()
        else:
            o = _FakeView(nome)
        o.TypeId = tipo
        self.made.append((tipo, nome, o))
        return o


def _cfg():
    return {"geo": {"comprimento": 90000.0, "bay": 7500.0,
                    "eave": 7000.0, "ridge": 8100.0,
                    "span": 44000.0, "slope": 0.1},
            "descricao": "galpao teste", "slug": "galpao-teste",
            "materiais": None, "perfil_col": "HEA240",
            "perfil_raf": "IPE400"}


def _modelo():
    objs = [_FakeObj("CONTRAV_COBERTURA_01_A"),
            _FakeObj("TIRANTE_PAREDE_E_01_01"),
            _FakeObj("TIRANTE_S00_0001"),
            _FakeObj("PORTICO_01_C00")]
    todos = list(objs) + [_FakeObj("ESTICADOR_COBERTURA_01_A")]
    return objs, todos


def _vistas(doc):
    return [o for _, _, o in doc.made
            if getattr(o, "TypeId", "") == "TechDraw::DrawViewPart"]


def _guarda_topo_sem_tirante(vistas):
    """O topo (V05_CV_COB) so leva CONTRAV; todo o resto vai na lateral."""
    probs = []
    topo = [v for v in vistas if v.Name == "V05_CV_COB"]
    lat = [v for v in vistas if v.Name == "V05_CV_LAT"]
    if len(topo) != 1 or len(lat) != 1:
        return ["esperava 1 lateral + 1 topo, achei %d vistas" % len(vistas)]
    for s in topo[0].Source:
        if not s.Label.startswith("CONTRAV"):
            probs.append("topo leva %s (veneno do G118)" % s.Label)
    lat_labels = [s.Label for s in lat[0].Source]
    for pref in ("CONTRAV", "TIRANTE", "PORTICO", "ESTICADOR"):
        if not any(lb.startswith(pref) for lb in lat_labels):
            probs.append("lateral perdeu %s (saturacao silenciosa)" % pref)
    return probs


def test_01_topo_da_pe05_sem_tirante():
    """A producao passa na guarda: topo so CONTRAV, lateral cobre tudo."""
    sys.modules["FreeCAD"] = _fake_freecad()
    try:
        doc = _FakeDoc()
        objs, todos = _modelo()
        paginas, cotadores = TD._pr_contravent(doc, _cfg(), objs, todos)
        assert len(paginas) == 1 and len(cotadores) == 1
        probs = _guarda_topo_sem_tirante(_vistas(doc))
        assert probs == [], "PE05 fora do G118:\n" + "\n".join(probs)
    finally:
        sys.modules.pop("FreeCAD", None)


def test_02_vermelho_por_injecao_tirante_no_topo(tmp_path):
    """A guarda nao e tautologica: topo com TIRANTE reprova."""
    sys.modules["FreeCAD"] = _fake_freecad()
    try:
        doc = _FakeDoc()
        objs, todos = _modelo()
        TD._pr_contravent(doc, _cfg(), objs, todos)
        vistas = _vistas(doc)
        topo = [v for v in vistas if v.Name == "V05_CV_COB"][0]
        topo.Source = list(topo.Source) + [_FakeObj("TIRANTE_S00_0001")]
        (tmp_path / "injetado.txt").write_text(
            ",".join(s.Label for s in topo.Source), encoding="utf-8")
        lido = (tmp_path / "injetado.txt").read_text(
            encoding="utf-8").split(",")
        assert "TIRANTE_S00_0001" in lido
        probs = _guarda_topo_sem_tirante(vistas)
        assert len(probs) == 1 and "TIRANTE_S00_0001" in probs[0]
    finally:
        sys.modules.pop("FreeCAD", None)


# ---------------------------------------------------------------- G119
def test_03_modelo_sem_contrav_declara_ausencia_em_vez_de_quebrar():
    """Auditoria do G118: a guarda de entrada aceita CONTRAV *ou* TIRANTE,
    e desde o G118 o topo so leva CONTRAV. Modelo so-tirante passava a
    entrada e estourava `AttributeError` em `_fit_escala(_bbox([]), ...)`
    (medido: `_bbox([])` devolve None). Agora a vista de topo nao sai e a
    folha DECLARA isso - ausencia declarada, nunca vista vazia nem excecao.
    """
    sys.modules["FreeCAD"] = _fake_freecad()
    try:
        doc = _FakeDoc()
        objs = [_FakeObj("TIRANTE_PAREDE_E_01_01"),
                _FakeObj("TIRANTE_S00_0001"),
                _FakeObj("PORTICO_01_C00")]
        todos = list(objs) + [_FakeObj("ESTICADOR_PAREDE_E_01_A")]
        assert TD._pref(objs, ("CONTRAV", "TIRANTE")), \
            "o caso perde o sentido se a guarda de entrada barrar o modelo"
        assert TD._pref(objs, ("CONTRAV",)) == [], "o topo tem de ficar vazio"
        paginas, _cot = TD._pr_contravent(doc, _cfg(), objs, todos)
        assert len(paginas) == 1
        vistas = _vistas(doc)
        assert [v.Name for v in vistas] == ["V05_CV_LAT"], \
            "sem CONTRAV nao ha vista de topo: %r" % [v.Name for v in vistas]
        # a lateral segue levando tudo o que existe (nada omitido em silencio)
        lat = [s.Label for s in vistas[0].Source]
        for pref in ("TIRANTE", "PORTICO", "ESTICADOR"):
            assert any(lb.startswith(pref) for lb in lat), \
                "lateral perdeu %s" % pref
        # e a folha diz o que NAO desenhou
        notas = [o for _t, _n, o in doc.made if hasattr(o, "Text")]
        texto = " ".join(str(getattr(o, "Text", "")) for o in notas)
        assert TD._AUSENCIA_CONTRAV_COBERTURA in texto, \
            "a ausencia da vista de topo nao foi declarada na folha: %r" % texto
    finally:
        sys.modules.pop("FreeCAD", None)
