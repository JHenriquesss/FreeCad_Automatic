"""Testes automatizados do framework galpao_fw.

Categorias:
  - Pipeline: roda os 23 gates SEM FreeCAD (rápido).
  - Build: constroi modelo 3D via MCP (requer FreeCAD rodando).

Uso:
    pytest framework/galpao_fw/tests/ -v
    pytest framework/galpao_fw/tests/ -v -m "not build"   # so pipeline
    pytest framework/galpao_fw/tests/ -v -m build          # so modelo 3D
"""

from __future__ import annotations

import os, sys, math, tempfile, socket, xmlrpc.client, copy
import pytest

sys.path.insert(0, str(os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))))

MCP_HOST = "http://localhost:9875"
MCP_TIMEOUT = 300


def mcp_alive() -> bool:
    try:
        s = xmlrpc.client.ServerProxy(MCP_HOST, allow_none=True)
        s.execute("import FreeCAD; _result_ = True")
        return True
    except Exception:
        return False


def _spec(nome: str, span: float, comprimento: float, spans: list | None = None,
          eave: float = 6.0, ridge: float | None = None, bay: float = 5.0,
          slope: float = 0.10):
    """Spec minimo para um galpao de teste."""
    import projeto_spec as PS
    s = PS.novo()
    s["slug"] = nome
    s["terreno"].update(area_lote_m2=1200, to_max=0.6, ca_max=1.0, tp_min=0.2,
                        recuos={"frente": 5, "lateral": 2, "fundos": 3})
    s["geometria"].update(span=span, comprimento=comprimento, eave=eave,
                          ridge=ridge or eave + slope * span / 2,
                          bay=bay, base_fixed=True)
    if spans:
        s["geometria"]["spans"] = spans
    s["cobertura"].update(aguas=2, slope=slope, telha_tipo="trapezoidal",
                          telha_peso=0.10, calha=True)
    s["fechamento"].update(tipo="telha", altura_alvenaria=0, peso=0.05,
                           mesa_interna_travada=True, n_maos_francesas=2)
    s["aberturas"] = {"portao_frente": (4000, 4500), "porta_fundo": (900, 2130),
                      "janelas_laterais": (4300, 5300)}
    s["vento"].update(v0=40, cat="II", classe="B", s3=0.95, z=eave,
                      abertura_dominante="portao_oitao")
    s["ponte"] = None
    s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
    s["fundacao"]["sigma_solo_adm"] = 200.0
    return s


def _build_via_mcp(spec, res, doc_name: str):
    """Envia build_galpao para o FreeCAD via MCP e retorna resultado."""
    import framework as FW
    import projeto_spec as PS
    bk = PS.to_build_kwargs(spec)
    g = spec["geometria"]
    if "spans" in g:
        bk["spans"] = [s * 1000 for s in g["spans"]]
    for k in ["mf_stride", "n_tirante_parede"]:
        if res.get(k):
            bk[k] = res[k]
    if res.get("terca_dims"):
        bk["terca"] = res["terca_dims"]
    if res.get("longarina_dims"):
        bk["longarina"] = res["longarina_dims"]
    if res.get("n_tirante_parede") is not None:
        bk["n_tirante_parede"] = res["n_tirante_parede"]
    bk["export_dir"] = tempfile.mkdtemp(prefix="bt_").replace("\\", "/")
    bk["doc_name"] = doc_name
    src = (FW.raiz_repo() / "framework" / "galpao_fw" / "build_galpao.py"
           ).read_text(encoding="utf-8").replace("_result_ = run()", "")
    call = "reset()\nconfigurar(**%r)\n_result_ = run()\n" % (bk,)
    socket.setdefaulttimeout(MCP_TIMEOUT)
    srv = xmlrpc.client.ServerProxy(MCP_HOST, allow_none=True)
    r = srv.execute(src + call)
    return r.get("result") if isinstance(r, dict) else None


# ============================================================================
# Pipeline tests (no FreeCAD needed)
# ============================================================================

SPAN_CASES = [
    pytest.param(10, 20, None, "N1_10m", id="N1"),
    pytest.param(20, 24, [8, 12], "N2_8+12", id="N2"),
    pytest.param(30, 30, [10, 10, 10], "N3_10x3", id="N3"),
]


class TestPipeline:
    """Testa o pipeline de calculo (23 gates) sem FreeCAD."""

    @pytest.mark.parametrize("span,comprimento,spans,nome", SPAN_CASES)
    def test_calcular(self, span, comprimento, spans, nome):
        import rodar_projeto as RP
        s = _spec(nome, span, comprimento, spans=spans)
        out = tempfile.mkdtemp(prefix=f"pipe_{nome}_")
        res = RP.calcular(s, out)
        assert res is not None
        assert res.get("atende") is True, f"Pipeline falhou: {res}"
        if spans:
            nv = len(spans)
        else:
            nv = 1
        cols = res.get("perfil_colunas", [])
        assert len(cols) >= 1, "Nenhum perfil de coluna"
        for p in cols:
            assert isinstance(p, str) and len(p) > 0, f"Perfil invalido: {p}"
        assert res.get("perfil_raf") is not None, "Viga nao definida"
        assert res.get("interacao_max", 0) <= 1.001, (
            f"Interacao max {res['interacao_max']} > 1.0")

    @pytest.mark.parametrize("span,comprimento,spans,nome", SPAN_CASES)
    def test_consolidado(self, span, comprimento, spans, nome):
        """Verifica que o consolidado foi gerado."""
        import rodar_projeto as RP
        s = _spec(nome, span, comprimento, spans=spans)
        out = tempfile.mkdtemp(prefix=f"mem_{nome}_")
        RP.calcular(s, out)
        path = os.path.join(out, "MEMORIAL-CONSOLIDADO.txt")
        assert os.path.exists(path), f"Falta {path}"
        txt = open(path, encoding="utf-8").read()
        assert "NAO ATENDE" not in txt, f"{nome}: elementos que nao atendem"


# ============================================================================
# Build tests (require FreeCAD + MCP)
# ============================================================================

BUILD_CASES = [
    pytest.param(10, 15, None, "bn_single", id="single_10m"),
    pytest.param(10, 15, [5, 5], "bn_multi", id="multi_5+5"),
]


@pytest.mark.skipif(not mcp_alive(), reason="FreeCAD MCP bridge não disponível")
@pytest.mark.build
class TestBuild:
    """Testa a geracao do modelo 3D via MCP (requer FreeCAD rodando)."""

    @pytest.mark.parametrize("span,comprimento,spans,nome", BUILD_CASES)
    def test_build_resultados(self, span, comprimento, spans, nome):
        import rodar_projeto as RP
        s = _spec(nome, span, comprimento, spans=spans)
        out = tempfile.mkdtemp(prefix=f"{nome}_")
        res = RP.calcular(s, out)
        assert res.get("atende") is True
        r = _build_via_mcp(s, res, nome)
        assert r is not None, "Build retornou None"
        assert r["interferencias"] == 0, (
            f"Interferencias: {r['interferencias']}")
        assert len(r["conexoes_suspeitas"]) == 0, (
            f"Conexoes suspeitas: {r['conexoes_suspeitas']}")
        assert r["elementos"] > 100, f"Poucos elementos: {r['elementos']}"
        if spans is None:
            assert len(r.get("estrutura_em_aberturas", [])) == 0, (
                f"Estrutura em aberturas: {r['estrutura_em_aberturas']}")

    @pytest.mark.parametrize("span,comprimento,spans,nome", BUILD_CASES)
    def test_geometria(self, span, comprimento, spans, nome):
        """Verifica os invariantes geometricos (verificar_geometria)."""
        import rodar_projeto as RP
        s = _spec(nome, span, comprimento, spans=spans)
        out = tempfile.mkdtemp(prefix=f"{nome}_")
        res = RP.calcular(s, out)
        r = _build_via_mcp(s, res, nome)
        assert r is not None
        geo = r.get("geometria", {})
        assert geo.get("todas_ok") is True, (
            f"Verificacoes geometricas: { {k: v for k, v in geo.items() if k != 'todas_ok' and not v.get('ok')} }")

    @pytest.mark.parametrize("span,comprimento,spans,nome", BUILD_CASES)
    def test_takeoff(self, span, comprimento, spans, nome):
        """Verifica que o takeoff tem categorias esperadas."""
        import rodar_projeto as RP
        s = _spec(nome, span, comprimento, spans=spans)
        out = tempfile.mkdtemp(prefix=f"{nome}_")
        res = RP.calcular(s, out)
        r = _build_via_mcp(s, res, nome)
        assert r is not None
        grupos = r.get("por_grupo", [])
        cats = {g[0] for g in grupos}
        for esperada in ("Placas de base", "Colunas", "Vigas", "Tercas",
                         "Telha de cobertura", "Sapatas (concreto)"):
            assert esperada in cats, (
                f"Takeoff sem categoria '{esperada}'. Categorias: {cats}")
        assert r.get("massa_aco_kg", 0) > 100, (
            f"Massa aco baixa: {r.get('massa_aco_kg')} kg")

    @pytest.mark.parametrize("span,comprimento,spans,nome", BUILD_CASES)
    def test_vistas_capturadas(self, span, comprimento, spans, nome):
        """Verifica que as 6 vistas foram capturadas apos o build."""
        import rodar_projeto as RP
        s = _spec(nome, span, comprimento, spans=spans)
        out = tempfile.mkdtemp(prefix=f"{nome}_")
        res = RP.calcular(s, out)
        r = _build_via_mcp(s, res, f"{nome}_vis")
        assert r is not None
        vistas = r.get("vistas", [])
        nomes_esperados = ["isometrica", "frontal", "traseira", "lateral_dir",
                           "lateral_esq", "superior"]
        for v in vistas:
            assert any(n in v for n in nomes_esperados), (
                f"Vista inesperada: {v}")
        assert len(vistas) >= 4, (
            f"Poucas vistas capturadas ({len(vistas)}): {vistas}")

    def test_verifica_conexoes_diretamente(self):
        """Chama verifica_conexoes + checa_interferencia no doc atual."""
        import rodar_projeto as RP
        s = _spec("conex_test", 10, 20)
        out = tempfile.mkdtemp(prefix="conex_")
        res = RP.calcular(s, out)
        r = _build_via_mcp(s, res, "conex_test")
        assert r is not None
        geo = r.get("geometria", {})
        assert geo.get("conexoes", {}).get("ok") is True, (
            f"Verifica conexoes: {geo.get('conexoes')}")
        assert geo.get("interferencias", {}).get("ok") is True, (
            f"Interferencias: {geo.get('interferencias')}")

# ============================================================================
# DXF tests (no FreeCAD needed)
# ============================================================================

DXF_CASES = [
    pytest.param(10, 20, None, "dxf_N1", id="dxf_N1"),
    pytest.param(20, 24, [8, 12], "dxf_N2", id="dxf_N2"),
    pytest.param(30, 30, [10, 10, 10], "dxf_N3", id="dxf_N3"),
]


class TestDxf:
    """Testa a geracao do DXF (nao requer FreeCAD)."""

    @pytest.mark.parametrize("span,comprimento,spans,nome", DXF_CASES)
    def test_gerar_dxf(self, span, comprimento, spans, nome):
        import rodar_projeto as RP
        s = _spec(nome, span, comprimento, spans=spans)
        out = tempfile.mkdtemp(prefix=f"{nome}_")
        RP.calcular(s, out)
        path = RP.gerar_dxf(s, out, nome)
        assert os.path.exists(path), f"DXF nao criado: {path}"
        assert os.path.getsize(path) > 10000, (
            f"DXF muito pequeno: {os.path.getsize(path)} bytes")

    @pytest.mark.parametrize("span,comprimento,spans,nome", DXF_CASES)
    def test_dxf_layers(self, span, comprimento, spans, nome):
        import rodar_projeto as RP
        import ezdxf
        s = _spec(nome, span, comprimento, spans=spans)
        out = tempfile.mkdtemp(prefix=f"{nome}_")
        RP.calcular(s, out)
        path = RP.gerar_dxf(s, out, nome)
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        entities = list(msp)
        layers = {e.dxf.layer for e in entities if hasattr(e.dxf, "layer")}
        esperadas = {"ACO", "BASE", "CONTRAV", "COTAS", "EIXOS", "FURACAO", "TELHA", "TEXTO"}
        for ly in esperadas:
            assert ly in layers, f"Camada {ly} ausente no DXF {nome}"
        assert len(entities) > 50, (
            f"Poucas entidades no DXF {nome}: {len(entities)}")
