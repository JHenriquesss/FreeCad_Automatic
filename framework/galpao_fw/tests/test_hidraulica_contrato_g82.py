"""G82: a hidraulica promete tres folhas e o galpao entrega uma.

Contrato (decisao escrita em desenho_hidraulica.COBERTURA_GALPAO):
- GALPAO (terreo, sem prumadas): UM arquivo, esquema-hidraulica.svg, cobre os
  TRES titulos do indice (PE-HI-01/02/03). Separar seria copiar o mesmo
  retangulo 3 vezes.
- PREDIO: uma folha por rede (1:1), com o corte vertical da prumada - ja
  implementado em edificio_adapter._PRANCHA_ARQUIVO.

Triagem da folha magra da agua (planta_rede_edificio_svg rede="agua" desenha
um unico ramal): o calculo dimensiona UMA coluna servindo todos os
pavimentos; o numero real de prumadas e os ramais por unidade dependem da
planta de arquitetura, que o framework nao tem para o edificio (aviso
`tracado_das_prumadas_convencional` em hidraulica_edificio). Desenhar ramais
por aparelho seria geometria inventada (a armadilha do G78). Veredito: o
escopo diz por que nao - folha mantida como esta.

Convencoes do repo seguidas aqui: baseline nos dois sentidos (laco verde com
o arquivo, vermelho sem), vermelho por injecao em tmp_path (nunca mutando a
arvore viva), parse do XML + confere_folha_svg (nunca substring), injeção
drawing-vs-data (nao tautologica: o valor injetado nao deriva do desenho).
"""
import copy
import os
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import desenho_hidraulica as dh
import desenho_svg_base as sb
import galpao_hidraulica as ghi


def _r_galpao():
    return ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                      "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                                     "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}})


def _xml(svg):
    return ET.fromstring(svg)


# ---------------- contrato: 3 codigos, 1 arquivo no galpao ----------------

def test_cobertura_galpao_tres_codigos_um_arquivo():
    """O motivo escrito: um arquivo responde pelos tres codigos."""
    assert set(dh.COBERTURA_GALPAO) == {"PE-HI-01", "PE-HI-02", "PE-HI-03"}
    assert len(set(dh.COBERTURA_GALPAO.values())) == 1


def test_laco_galpao_verde_com_esquema(tmp_path):
    """Baseline bom: com o esquema em disco, os 3 codigos estao cobertos."""
    dh.gerar_esquema(_r_galpao(), str(tmp_path / "esquema-hidraulica.svg"))
    emitidos = [p.name for p in tmp_path.iterdir()]
    conf = dh.confere_cobertura_galpao(emitidos)
    assert conf["cobertos"] == ["PE-HI-01", "PE-HI-02", "PE-HI-03"]
    assert conf["pulados"] == []


def test_laco_galpao_vermelho_sem_esquema(tmp_path):
    """Baseline ruim: sem o esquema, os 3 codigos saem pulados NOMEADOS."""
    conf = dh.confere_cobertura_galpao([p.name for p in tmp_path.iterdir()])
    assert conf["cobertos"] == []
    assert len(conf["pulados"]) == 3
    for p in conf["pulados"]:
        assert p["prancha"] == "esquema-hidraulica.svg"
        assert "G82" in p["motivo"]


def test_laco_galpao_nao_acusa_outro_arquivo(tmp_path):
    """Um arquivo qualquer nao cobre o indice (a cobertura e' pelo nome)."""
    (tmp_path / "outra-folha.svg").write_text("<svg/>", encoding="utf-8")
    conf = dh.confere_cobertura_galpao(["outra-folha.svg"])
    assert conf["cobertos"] == [] and len(conf["pulados"]) == 3


# ---------------- esquema: folha valida + drawing-vs-data ----------------

def test_esquema_parse_e_confere_folha():
    svg = dh.esquema_hidraulica_svg(_r_galpao())
    _xml(svg)  # malformado levanta, nao passa
    assert sb.confere_folha_svg(svg)["ok"]


@pytest.mark.parametrize("rede,chave", [
    ("pluvial", ("redes", "pluvial", "D_mm")),
    ("esgoto", ("redes", "esgoto", "D_mm")),
    ("agua", ("redes", "agua_fria", "D_mm")),
])
def test_esquema_desenhado_igual_calculado_por_rede(rede, chave):
    """Cada rede: DN rotulado == DN calculado; injecao muda o desenho."""
    r = _r_galpao()
    svg = dh.esquema_hidraulica_svg(r)
    dn = r[chave[0]][chave[1]][chave[2]]
    assert ("DN%.0f" % dn) in svg
    r2 = copy.deepcopy(r)
    r2[chave[0]][chave[1]][chave[2]] = 999
    svg2 = dh.esquema_hidraulica_svg(r2)
    assert "DN999" in svg2 and "DN999" not in svg


# ---------------- predio: 3 folhas 1:1 (contrato ja implementado) ----------------

def test_predio_tres_arquivos_distintos():
    """O predio cumpre 1:1 - cada codigo tem o seu arquivo."""
    import edificio_adapter as ea

    arquivos = [ea._PRANCHA_ARQUIVO[c] for c in ("PE-HI-01", "PE-HI-02", "PE-HI-03")]
    assert arquivos == ["hidraulica-agua-fria.svg",
                        "hidraulica-esgoto-ventilacao.svg",
                        "hidraulica-pluvial.svg"]
    assert len(set(arquivos)) == 3


# ---------------- triagem da folha magra da agua ----------------

def _caso_edificio():
    import json
    from pathlib import Path

    import edificio_multipavimento as em
    import hidraulica_edificio as he
    import incendio_edificio as ie
    from edificio_adapter import _contexto_predio

    spec = json.loads((Path(GALPAO).parents[1] / "projects"
                       / "edificio-multipavimento" / "project-spec.json"
                       ).read_text(encoding="utf-8"))
    tk = spec["turnkey"]
    est = {"geometria": tk["estrutura"]["geometria"],
           "pavimentos": tk["estrutura"]["pavimentos"],
           "materiais": tk["estrutura"]["materiais"],
           "laje": tk["estrutura"].get("laje"),
           "viga": tk["estrutura"].get("viga"),
           "vento": tk["estrutura"].get("vento"),
           "fundacao": tk["estrutura"].get("fundacao"),
           "escada": tk["estrutura"].get("escada")}
    R = em.rodar(est)
    ctx0 = _contexto_predio(tk["estrutura"], R, None)
    I = ie.dimensiona(tk["incendio"], ctx0)
    ctx = _contexto_predio(
        tk["estrutura"], R,
        {"incendio": {"populacao_por_pavimento": I["populacao_por_pavimento"]}})
    return R, he.dimensiona(tk["hidraulica"], ctx)


def test_folha_magra_da_agua_e_fiel_ao_calculo():
    """A folha desenha o que foi calculado: 1 ramal + corte + DN + reserva."""
    R, H = _caso_edificio()
    svg = dh.planta_rede_edificio_svg(H, R, rede="agua")
    _xml(svg)
    assert sb.confere_folha_svg(svg)["ok"]
    dn = H["coluna"]["dn"]["DN_mm"]
    assert ("DN%.0f" % dn) in svg  # coluna dimensionada, nao numero fixo
    assert "CORTE" in svg.upper()  # o corte que o galpao nunca teve
    assert "RESERVACAO" in svg.upper()
    assert "ramal" in svg.lower()


def test_folha_magra_da_agua_vermelha_por_injecao():
    H2 = copy.deepcopy(_caso_edificio()[1])
    H2["coluna"]["dn"]["DN_mm"] = 999
    svg2 = dh.planta_rede_edificio_svg(H2, _caso_edificio()[0], rede="agua")
    assert "DN999" in svg2


def test_triagem_magra_escopo_diz_por_que_nao():
    """O que falta na folha (ramais por aparelho, prumadas reais, registros)
    esta fora do escopo DECLARADO - nao e' esquecimento. Se o escopo mudar,
    este teste quebra de proposito e forca re-triagem."""
    R, H = _caso_edificio()
    assert H["escopo"]["tracado_das_prumadas"] == "implemented"
    avisos = {a["code"]: a["detail"] for a in H["avisos"]}
    detalhe = avisos["tracado_das_prumadas_convencional"]
    assert "ramais por unidade" in detalhe
    assert "arquitetura" in detalhe
