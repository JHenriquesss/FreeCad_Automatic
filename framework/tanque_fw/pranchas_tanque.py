# ============================================================================
# pranchas_tanque.py - IFC, PRANCHAS E RENDER DO TANQUE-BASE NUM PASSO SO
# Emite o IFC (ifc_tanque) e entrega ao orquestrador do galpao
# (galpao_fw/pranchas_ifc.gerar), trocando os scripts de vistas e de render.
# Saem: folhas A1 em SVG e PDF, DXF, DWG, lista de material, a folha de notas,
# soldas e componentes e os renders.
#
# Tres ajustes sobre o fluxo do galpao, feitos aqui para nao mexer nele:
#  - a lista de material ignora as aberturas (IfcOpeningElement) e chama de
#    "Acessorio" as pecas sem classe propria;
#  - a folha de notas entra no Bonsai por um SVG passado em variavel de ambiente;
#  - a mesma folha e' acrescentada ao DXF, e o DWG e' convertido de novo.
# ============================================================================
"""Pranchas (Bonsai), DXF, DWG, PDF e render do tanque-base."""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "galpao_fw"))

import dxf_prancha       # noqa: E402
import ifc_tanque        # noqa: E402
import pranchas_ifc      # noqa: E402
import projeto_rev02 as P  # noqa: E402

SCRIPT_BONSAI = os.path.join(AQUI, "scripts", "pranchas_tanque_bonsai.py")
SCRIPT_RENDER = os.path.join(AQUI, "scripts", "render_tanque.py")
VAR_NOTAS = "TANQUE_NOTAS_SVG"
NOME_NOTAS = "NOTAS-SOLDAS-COMPONENTES"
_lista_do_galpao = dxf_prancha.lista_do_ifc


def lista_do_tanque(caminho_ifc):
    """Lista de material do IFC sem as aberturas e com nome para os acessorios."""
    lista = _lista_do_galpao(caminho_ifc)
    linhas = [ln for ln in lista["linhas"] if ln["peca"] != "OpeningElement"]
    for ln in linhas:
        if ln["peca"] == "BuildingElementProxy":
            ln["peca"] = "Acessorio"
    lista["linhas"] = linhas
    lista["linhas_sem_peso"] = sum(1 for ln in linhas if ln["peso_total_kg"] is None)
    return lista


def tabela_de_notas(spec):
    """Notas gerais, soldas e componentes no formato de tabela do `svg_da_lista`."""
    f = lambda x: ("%.0f" % x)
    linhas = [["SOLDAS", "", "", "", ""]]
    for junta, tipo, perna, qtd, comp, obs in P.juntas_soldadas(spec):
        linhas.append([junta, tipo, f(perna), "%d x %s" % (qtd, f(comp)), obs])
    linhas += [["", "", "", "", ""], ["COMPONENTES COMPRADOS", "", "", "", ""]]
    for item, espec, qtd in P.componentes(spec):
        linhas.append([item, espec, "", str(qtd), ""])
    return {"cabecalho": ["JUNTA / ITEM", "TIPO / ESPECIFICACAO", "PERNA (mm)",
                          "QTD x COMPR. (mm)", "OBSERVACAO"],
            "larguras_mm": [70.0, 150.0, 22.0, 34.0, 70.0],
            "linhas": linhas, "total": None, "notas": [""] + P.notas_gerais(spec)}


def _folha_de_notas_no_dxf(dxf, tabela, carimbo):
    """Acrescenta ao DXF uma folha A2 com a mesma tabela (o DXF do galpao so' traz a lista)."""
    import ezdxf
    doc = ezdxf.readfile(dxf)
    DP = dxf_prancha
    _n, fw, fh = DP.FORMATOS[1]
    total = len(doc.layouts)            # as folhas existentes mais esta (o Model nao conta)
    folha = doc.layouts.new("%02d-NOTAS-E-SOLDAS" % total)
    folha.page_setup(size=(fw, fh), margins=(0, 0, 0, 0), units="mm")
    cam = {"layer": DP.CAMADA_FOLHA}
    qx0, qy0, qx1, qy1 = DP.MARGEM_ESQ, DP.MARGEM, fw - DP.MARGEM, fh - DP.MARGEM
    folha.add_lwpolyline([(qx0, qy0), (qx1, qy0), (qx1, qy1), (qx0, qy1)], close=True,
                         dxfattribs=cam)
    valores = dict(carimbo, TITULO="NOTAS, SOLDAS E COMPONENTES", ESCALA="-",
                   FOLHA="%02d/%02d  A2" % (total, total))
    ref = folha.add_blockref("CARIMBO", (qx1 - DP.CARIMBO_L, qy0), dxfattribs=cam)
    ref.add_auto_attribs({c: str(valores.get(c, "")) for c in DP.CAMPOS_CARIMBO})
    passo, x0, y = 6.0, qx0 + 8.0, qy1 - 14.0
    texto = {"layer": DP.CAMADA_TEXTO, "style": "TEXTO"}

    def _linha(celulas):
        x = x0
        for larg, cel in zip(tabela["larguras_mm"], celulas):
            if cel:
                folha.add_text(cel, height=DP.ALTURA_TEXTO,
                               dxfattribs=dict(texto, insert=(x + 1.5, y + 1.6)))
            x += larg

    _linha(tabela["cabecalho"])
    folha.add_line((x0, y), (x0 + sum(tabela["larguras_mm"]), y), dxfattribs=cam)
    for celulas in tabela["linhas"]:
        y -= passo
        _linha(celulas)
    for nota in tabela["notas"]:
        y -= passo
        if nota:
            folha.add_text(nota, height=DP.ALTURA_TEXTO,
                           dxfattribs=dict(texto, insert=(x0 + 1.5, y + 1.6)))
    if y < qy0 + DP.CARIMBO_H:
        raise ValueError("a folha de notas nao coube no A2")
    doc.saveas(dxf)
    return folha.name


def gerar(pasta, spec=None, render=True):
    spec = spec or P.SPEC_REV02
    os.makedirs(pasta, exist_ok=True)
    ifc = os.path.join(pasta, "tanque_base_rev02.ifc")
    res = {"ifc": ifc_tanque.emitir(ifc, spec)}
    tabela = tabela_de_notas(spec)
    svg_notas = os.path.join(pasta, NOME_NOTAS + ".svg")
    pranchas_ifc.svg_da_lista(tabela, svg_notas)
    carimbo = {"PROJETO": spec["documento"]}
    original = pranchas_ifc.SCRIPT_BONSAI, pranchas_ifc.SCRIPT_RENDER
    pranchas_ifc.SCRIPT_BONSAI, pranchas_ifc.SCRIPT_RENDER = SCRIPT_BONSAI, SCRIPT_RENDER
    dxf_prancha.lista_do_ifc = lista_do_tanque
    os.environ[VAR_NOTAS] = svg_notas
    try:
        pr = res["pranchas"] = pranchas_ifc.gerar(
            ifc, os.path.join(pasta, "pranchas"), titulo="TANQUE-BASE",
            revisao="02", carimbo=carimbo, render=render)
        if "dxf" in pr:
            pr["folha_de_notas_dxf"] = _folha_de_notas_no_dxf(
                pr["dxf"], tabela, dict(carimbo, REVISAO="02"))
            oda = pranchas_ifc.localizar("oda")
            if oda and "dwg" in pr:
                # o DWG ja' convertido nao tem a folha nova: guarda-se o primeiro e converte de novo
                os.replace(pr["dwg"], pr["dwg"][:-4] + ".sem-notas.dwg")
                pr["dwg"] = pranchas_ifc._dwg(oda, pr["dxf"], os.path.dirname(pr["dwg"]), 600,
                                              pranchas_ifc._rodar)
        if render:
            # segundo render, com o conteiner de referencia em cima da base
            ifc_c = os.path.join(pasta, "tanque_base_rev02_com_conteiner.ifc")
            ifc_tanque.emitir(ifc_c, spec, com_conteiner=True)
            png = os.path.join(pasta, "pranchas", "render", "apresentacao_com_conteiner.png")
            try:
                pranchas_ifc._render(pranchas_ifc.localizar("blender"), ifc_c, png, 3600,
                                     pranchas_ifc._rodar)
                res["render_com_conteiner"] = png
            except Exception as ex:
                res["render_com_conteiner_erro"] = str(ex)
    finally:
        pranchas_ifc.SCRIPT_BONSAI, pranchas_ifc.SCRIPT_RENDER = original
        dxf_prancha.lista_do_ifc = _lista_do_galpao
        os.environ.pop(VAR_NOTAS, None)
    return res


if __name__ == "__main__":
    raiz = os.path.dirname(os.path.dirname(AQUI))
    r = gerar(os.path.join(raiz, "ENTREGA_TANQUE_BASE_REV02", "modelo"),
              render="--sem-render" not in sys.argv)
    pr = r["pranchas"]
    print("IFC:", r["ifc"])
    print(pranchas_ifc.resumo_pt(pr))
    for k in ("render_com_conteiner", "render_com_conteiner_erro", ):
        if k in r:
            print(k, r[k])
    print("folha de notas no DXF:", pr.get("folha_de_notas_dxf"), "| DWG:", pr.get("dwg"))
