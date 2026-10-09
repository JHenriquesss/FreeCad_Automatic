# ============================================================================
# test_pranchas_ifc.py - AS PRANCHAS DO IFC SAEM NUM PASSO SO E SO SE DIZEM
# ENTREGUES COM O ARQUIVO NO DISCO (plano de 2026-10-08, Fases 3 e 4).
# Blender, ODA e Inkscape sao programas de fora: aqui o executor e' trocado por
# um que escreve os arquivos que cada programa escreveria (o desenho no formato
# do ifcopenshell.draw, o mesmo do test_dxf_prancha). O que se cobra e' a
# costura: o IFC do motor nao e' tocado, desenho de corrida anterior nao entra
# em prancha nova, e programa ausente ou que falha vira NAO GERADO com motivo.
# ============================================================================
"""Costura IFC -> desenhos -> DXF -> DWG -> PDF (pranchas_ifc)."""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

ezdxf = pytest.importorskip("ezdxf")
pytest.importorskip("ifcopenshell")

import pranchas_ifc as PI
import test_dxf_prancha as TDP


def _programas(tmp_path, nomes=("blender", "oda", "inkscape")):
    """Ambiente com um executavel de mentira por programa pedido; os outros
    ficam fora da maquina (padroes de busca e PATH esvaziados no monkeypatch)."""
    amb = {}
    for n in nomes:
        exe = tmp_path / (n + ".exe")
        exe.write_text("x")
        amb[PI.PROGRAMAS[n][0]] = str(exe)
    return amb


@pytest.fixture
def so_o_ambiente(monkeypatch):
    """Nada instalado na maquina de teste: so vale o que o ambiente declarar."""
    monkeypatch.setattr(PI, "PROGRAMAS", {
        n: (v[0], (), "programa-que-nao-existe-" + n) for n, v in PI.PROGRAMAS.items()})


def _executor(tmp_path, passos=(("PLANTA", "ok"),), sem_relatorio=False, sem_dwg=False,
              chamadas=None, sem_folha_da_lista=False):
    def rodar(comando, timeout):
        if chamadas is not None:
            chamadas.append(list(comando))
        nome = os.path.basename(comando[0])
        if nome == "blender.exe":
            raiz = os.path.dirname(comando[comando.index("--") + 1])
            os.makedirs(os.path.join(raiz, "drawings"))
            os.makedirs(os.path.join(raiz, "sheets"))
            with open(TDP._svg(tmp_path), encoding="utf-8") as f:
                svg = f.read()
            for vista, estado in passos:
                if estado == "ok":
                    with open(os.path.join(raiz, "drawings", vista + ".svg"), "w",
                              encoding="utf-8") as f:
                        f.write(svg)
            with open(os.path.join(raiz, "sheets", "EST-01.svg"), "w") as f:
                f.write("<svg/>")
            if sem_relatorio:
                return 1, "Error: Bonsai nao instalado"
            rel = {"passos": [[v, e, 1.0] for v, e in passos]}
            if not sem_folha_da_lista:
                rel["folha_da_lista"] = "EST-02"
            if any(e != "ok" for _v, e in passos):
                rel["avisos"] = ["%s: Traceback\nRuntimeError: sem geometria" % v
                                 for v, e in passos if e != "ok"]
            return 0, "Blender 5.2\n" + PI.MARCA_RELATORIO + json.dumps(rel)
        if nome == "oda.exe":
            if not sem_dwg:
                origem, destino = comando[1], comando[2]
                for f in os.listdir(origem):
                    with open(os.path.join(destino, f[:-4] + ".dwg"), "wb") as g:
                        g.write(b"AC1032")
            return 0, ""
        if nome == "inkscape.exe":
            pdf = [a for a in comando if a.startswith("--export-filename=")][0].split("=", 1)[1]
            with open(pdf, "wb") as g:
                g.write(b"%PDF-1.4")
            return 0, ""
        raise AssertionError("programa inesperado: %r" % (comando,))
    return rodar


def _gerar(tmp_path, amb, ifc=None, **kw):
    ifc = ifc or TDP._ifc_com_romaneio(tmp_path)
    executor = _executor(tmp_path, **{k: kw.pop(k) for k in list(kw)
                                      if k in ("passos", "sem_relatorio", "sem_dwg",
                                               "chamadas", "sem_folha_da_lista")})
    return ifc, PI.gerar(ifc, str(tmp_path / "pranchas"), titulo="GALPAO 40x20 m",
                         revisao="02", ambiente=amb, rodar=executor, **kw)


def test_variavel_de_ambiente_para_arquivo_que_nao_existe_reprova(tmp_path, so_o_ambiente):
    with pytest.raises(FileNotFoundError, match="BLENDER_EXE"):
        PI.localizar("blender", {"BLENDER_EXE": str(tmp_path / "nao-ha.exe")})
    assert PI.localizar("blender", {}) is None


def test_sem_blender_nada_e_gerado_e_a_pasta_nao_e_criada(tmp_path, so_o_ambiente):
    _ifc, res = _gerar(tmp_path, {})
    assert res["gerado"] is False
    assert "Blender" in res["nao_gerado"]["desenhos"]
    assert not (tmp_path / "pranchas").exists()
    assert any("NAO GERADO" in ln for ln in PI.resumo_pt(res))


def test_cadeia_inteira_grava_dxf_dwg_e_pdf_e_nao_toca_o_ifc(tmp_path, so_o_ambiente):
    chamadas = []
    ifc0 = TDP._ifc_com_romaneio(tmp_path)
    with open(ifc0, "rb") as f:
        antes = f.read()
    ifc, res = _gerar(tmp_path, _programas(tmp_path), ifc=ifc0, chamadas=chamadas,
                      carimbo={"PROJETO": "Galpao X", "CLIENTE": "Fulano"})
    assert res["gerado"] is True and res["nao_gerado"] == {} and res["avisos"] == []
    with open(ifc, "rb") as f:
        assert f.read() == antes                       # o Bonsai so abre a copia
    copia = chamadas[0][chamadas[0].index("--") + 1]
    assert os.path.isfile(copia) and os.path.abspath(copia) != os.path.abspath(ifc)
    assert chamadas[0][-3:-1] == ["titulo=GALPAO 40x20 m", "revisao=02"]
    # a tabela da lista vai pronta ao Bonsai, na pasta da copia do IFC
    svg_lista = chamadas[0][-1].split("=", 1)[1]
    assert chamadas[0][-1].startswith("lista=") and os.path.isfile(svg_lista)
    assert os.path.dirname(os.path.dirname(svg_lista)) == os.path.dirname(copia)
    assert res["lista"] == {"linhas": res["dxf_resumo"]["lista"]["linhas"],
                            "peso_total_kg": res["dxf_resumo"]["lista"]["peso_total_kg"],
                            "linhas_sem_peso": res["dxf_resumo"]["lista"]["linhas_sem_peso"],
                            "folha_bonsai": "EST-02"}
    for chave in ("dxf", "dwg"):
        assert os.path.isfile(res[chave]) and os.path.getsize(res[chave]) > 0
    assert [os.path.basename(p) for p in res["pdf"]] == ["EST-01.pdf"]
    # o DXF e' lido de volta: a folha da vista e a da lista de material do IFC
    doc = ezdxf.readfile(res["dxf"])
    folhas = [l.name for l in doc.layouts if l.name != "Model"]
    assert len(folhas) == 2 and "lista" in res["dxf_resumo"]
    campos = {a.dxf.tag: a.dxf.text for l in doc.layouts if l.name != "Model"
              for ins in l.query("INSERT") for a in ins.attribs}
    assert campos["PROJETO"] == "Galpao X" and campos["CLIENTE"] == "Fulano"
    assert campos["REVISAO"] == "02"


def test_oda_que_nao_grava_o_dwg_vira_nao_gerado_e_o_dxf_fica(tmp_path, so_o_ambiente):
    _ifc, res = _gerar(tmp_path, _programas(tmp_path), sem_dwg=True)
    assert res["gerado"] is True and os.path.isfile(res["dxf"])
    assert "dwg" not in res and "sem gravar" in res["nao_gerado"]["dwg"]
    assert "pdf" in res


def test_sem_oda_e_sem_inkscape_cada_um_diz_o_que_faltou(tmp_path, so_o_ambiente):
    _ifc, res = _gerar(tmp_path, _programas(tmp_path, ("blender",)))
    assert res["gerado"] is True
    assert sorted(res["nao_gerado"]) == ["dwg", "pdf"]
    assert "ODA_EXE" in res["nao_gerado"]["dwg"] and "INKSCAPE_EXE" in res["nao_gerado"]["pdf"]


def test_blender_sem_relatorio_nao_gera_nada(tmp_path, so_o_ambiente):
    _ifc, res = _gerar(tmp_path, _programas(tmp_path), sem_relatorio=True)
    assert res["gerado"] is False and "dxf" not in res
    assert "codigo 1" in res["nao_gerado"]["desenhos"]
    assert (tmp_path / "pranchas" / "bonsai-saida.log").read_text(
        encoding="utf-8").startswith("Error")


def test_vista_que_falhou_no_bonsai_aparece_como_incompleto(tmp_path, so_o_ambiente):
    _ifc, res = _gerar(tmp_path, _programas(tmp_path),
                       passos=(("PLANTA", "ok"), ("CORTE", "ERRO")))
    assert res["gerado"] is True and res["passos_com_erro"] == ["CORTE"]
    linhas = PI.resumo_pt(res)
    assert any(ln.startswith("INCOMPLETO") and "CORTE" in ln for ln in linhas)
    assert any("sem geometria" in ln for ln in linhas)


def test_corrida_anterior_e_arquivada_e_nao_entra_na_nova(tmp_path, so_o_ambiente):
    amb = _programas(tmp_path)
    _ifc, r1 = _gerar(tmp_path, amb, passos=(("PLANTA", "ok"), ("VELHA", "ok")))
    assert r1["pasta_anterior_arquivada"] is None and len(r1["desenhos"]) == 2
    _ifc, r2 = _gerar(tmp_path, amb)
    arquivada = r2["pasta_anterior_arquivada"]
    assert arquivada and os.path.isfile(
        os.path.join(arquivada, "bonsai", "drawings", "VELHA.svg"))
    assert [os.path.basename(p) for p in r2["desenhos"]] == ["PLANTA.svg"]
    assert len(r2["dxf_resumo"]["folhas"]) == 1


def test_bonsai_que_nao_informa_a_folha_da_lista_vira_nao_gerado(tmp_path, so_o_ambiente):
    _ifc, res = _gerar(tmp_path, _programas(tmp_path), sem_folha_da_lista=True)
    assert res["gerado"] is True and "folha_bonsai" not in res["lista"]
    assert "lista de material" in res["nao_gerado"]["lista_no_bonsai"]


def _textos_do_svg(caminho):
    import xml.etree.ElementTree as ET
    raiz = ET.parse(caminho).getroot()
    ns = "{http://www.w3.org/2000/svg}"
    return raiz, [t.text for t in raiz.iter(ns + "text")], list(raiz.iter(ns + "line"))


def test_tabela_da_lista_e_a_mesma_no_dxf_e_no_svg_do_bonsai(tmp_path):
    import dxf_prancha as DP
    lista = DP.lista_do_ifc(TDP._ifc_com_romaneio(tmp_path))
    tabela = DP.tabela_da_lista(lista)
    destino = str(tmp_path / "lista.svg")
    larg, alt = PI.svg_da_lista(tabela, destino)
    raiz, textos, linhas = _textos_do_svg(destino)
    # toda celula preenchida aparece uma vez por ocorrencia; celula vazia nao vira texto
    esperado = [c for linha in [tabela["cabecalho"]] + tabela["linhas"] + [tabela["total"]]
                for c in linha if c] + tabela["notas"]
    assert textos == esperado and "" not in textos
    assert raiz.attrib["width"] == "%smm" % larg and raiz.attrib["height"] == "%smm" % alt
    assert len(linhas) == 2                             # sob o cabecalho e sob a ultima linha
    # os mesmos textos estao na folha da lista do DXF
    resumo = DP.gerar_dxf([DP.ler_desenho(TDP._svg(tmp_path))], str(tmp_path / "l.dxf"),
                          lista=lista)
    doc = ezdxf.readfile(str(tmp_path / "l.dxf"))
    no_dxf = [e.dxf.text for e in doc.layouts.get(resumo["lista"]["folha"]).query("TEXT")]
    assert [t for t in no_dxf if t] == esperado          # o DXF grava a celula vazia


def test_peso_ausente_fica_vazio_e_o_total_some_quando_nada_foi_pesado(tmp_path):
    import dxf_prancha as DP
    lista = {"linhas": [{"marca": "T<1>", "peca": "Barra & cia", "perfil": "Ue 300",
                         "comprimento_m": None, "qtd": 3, "peso_unit_kg": None,
                         "peso_total_kg": None}],
             "peso_total_kg": None, "linhas_sem_peso": 1}
    tabela = DP.tabela_da_lista(lista)
    assert tabela["linhas"] == [["T<1>", "Barra & cia", "Ue 300", "", "3", "", ""]]
    assert tabela["total"] is None and len(tabela["notas"]) == 1
    destino = str(tmp_path / "lista.svg")
    PI.svg_da_lista(tabela, destino)
    _raiz, textos, _linhas = _textos_do_svg(destino)      # XML valido com < e &
    assert "T<1>" in textos and "Barra & cia" in textos and "TOTAL PESADO" not in textos


def test_lista_que_nao_cabe_na_folha_do_bonsai_reprova(tmp_path):
    tabela = {"cabecalho": ["A"], "larguras_mm": [20.0], "linhas": [["celula"]] * 200,
              "total": None, "notas": []}
    with pytest.raises(ValueError, match="nao cabe"):
        PI.svg_da_lista(tabela, str(tmp_path / "lista.svg"))
    assert not (tmp_path / "lista.svg").exists()

