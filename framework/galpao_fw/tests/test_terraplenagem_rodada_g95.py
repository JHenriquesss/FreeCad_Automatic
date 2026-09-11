# G95: terraplenagem exercitada por um projeto real, nao so pelo teste.
"""O G89 ligou as folhas PE-TP-01/02 ao Loop e as provou com fixture em
memoria; nenhum spec persistido em projects/ declarava site.terraplenagem,
entao o caminho nunca rodava numa rodada de verdade. Este portao trava o
projeto real projects/galpao-tp-g95: o spec declara os 5 dados pelo
projetista e a rodada emite as duas folhas no manifesto.

Conta a mao (fonte independente, convencao 5 - nunca o proprio desenho):
  grade 3x3 vs plataforma 101.0, area 400 m2 por celula:
    fileira 1: +1.3 +0.8 +0.2 = 2.3 -> 920.0 m3 de corte
    fileira 2: +0.5 0.0 -0.6   -> 200.0 m3 de corte, 240.0 m3 de aterro
    fileira 3: -0.4 -0.9 -1.5  -> 1360.0 - 240.0 = 1120.0 m3 de aterro
    corte = 1120.0 m3, aterro = 1360.0 m3
  drenagem: Q = C.i.A/360 = 0.75*130.0*1.2/360 = 0.325 m3/s.

Baseline nos dois sentidos (convencao 1): o caso bom emite as duas folhas;
a copia sem drenagem emite so a TP-01; a copia sem site.terraplenagem nao
emite folha nenhuma (ausencia declarada, nunca default silencioso).
Vermelho por injecao em copia em memoria / tmp_path (convencao 2): o spec
persistido nunca e mutado. Cada teste coleta todos os lados e falha uma vez
so, com o relatorio completo (receita do G97)."""
import copy
import json
import os
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
import sys
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import galpao_adapter  # noqa: F401  (registra o adaptador no Loop)
import desenho_svg_base as sb
from project_loop import run_project

# --- o projeto real (lido, nunca mutado) ------------------------------------
def _repo():
    d = os.path.abspath(HERE)
    while not os.path.isdir(os.path.join(d, "projects")):
        d = os.path.dirname(d)
    return d


SPEC_G95 = os.path.join(_repo(), "projects", "galpao-tp-g95",
                        "project-spec.json")
SEM_IFC = {"generate_ifc": False}

# conta a mao, ver docstring: nunca recalculada pelo modulo sob teste.
CORTE_M3 = 1120.0
ATERRO_M3 = 1360.0
VAZAO_TXT = "0.3250 m3/s"
FOLHAS = {"drawings/terraplenagem-corte-aterro.svg",
          "drawings/terraplenagem-drenagem.svg"}


class _Coletor:
    """Coleta todos os lados e falha uma vez so (receita do G97)."""

    def __init__(self):
        self.falhas = []

    def exige(self, cond, nome, detalhe=""):
        if not cond:
            self.falhas.append("%s %s" % (nome, detalhe))

    def veredito(self):
        assert not self.falhas, (
            "portao G95 acusa %d lado(s) numa rodada so:\n- %s"
            % (len(self.falhas), "\n- ".join(self.falhas)))


def _spec():
    with open(SPEC_G95, encoding="utf-8") as fh:
        return json.load(fh)


def _conta_celulas(svg):
    raiz = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    return sum(1 for el in list(raiz.iter(ns + "rect")) + list(raiz.iter("rect"))
               if el.get("data-celula") is not None)


def _svg_no_disco(run_dir, caminho):
    with open(os.path.join(run_dir, *caminho.split("/")),
              encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def rodada_g95(tmp_path_factory):
    """A rodada do projeto real, uma vez so para o modulo inteiro."""
    destino = str(tmp_path_factory.mktemp("g95"))
    return run_project(_spec(), destino, SEM_IFC), destino


# --- o spec declara os 5 dados (sem spec nao ha rodada) ----------------------
def test_g95_spec_declara_os_cinco_dados_pelo_projetista():
    c = _Coletor()
    spec = _spec()
    tp = ((spec.get("site") or {}).get("terraplenagem") or {})
    c.exige(tp.get("grid_terreno"), "grade-ausente",
            "sem grid_terreno nao ha celula para a TP-01")
    c.exige(tp.get("cota_plataforma") is not None, "plataforma-ausente",
            "cota de plataforma e dado de projeto, nao default")
    c.exige(tp.get("area_celula_m2"), "celula-ausente",
            "sem area de celula nao ha volume")
    c.exige(tp.get("empolamento") is not None, "empolamento-ausente",
            "empolamento ausente viraria 1.0 silencioso no .get()")
    dren = tp.get("drenagem") or {}
    for chave in ("C", "i_mm_h", "area_ha", "largura_canaleta_m",
                  "declividade"):
        c.exige(dren.get(chave) is not None, "drenagem-incompleta",
                "falta %s: sem o caso completo nao ha TP-02" % chave)
    prov = (spec.get("test_assumptions") or {})
    c.exige("terraplenagem" in json.dumps(prov, ensure_ascii=False),
            "proveniencia-ausente",
            "premissas de sitio exigem procedencia escrita (sondagem/IDF)")
    c.veredito()


# --- caso bom: as duas folhas saem e passam na guarda ------------------------
def test_g95_rodada_emite_as_duas_folhas_no_manifesto(rodada_g95):
    resultado, run_dir = rodada_g95
    c = _Coletor()
    obras = resultado["deliverables"]["obras_sitio"]
    c.exige(obras["status"] == "generated", "status",
            "esperado generated, veio %r" % (obras["status"],))
    c.exige(obras.get("frentes") == ["terraplenagem"], "frentes",
            "veio %r" % (obras.get("frentes"),))
    c.exige(obras.get("frentes_com_falha") == [], "falhas",
            "veio %r" % (obras.get("frentes_com_falha"),))
    artefatos = set(obras.get("artifacts") or ())
    c.exige(FOLHAS <= artefatos, "folhas-no-entregavel",
            "faltando %r em %r" % (FOLHAS - artefatos, artefatos))
    # sexta regra: a folha so existe quando esta no manifesto, com hash.
    no_manifesto = {a["path"]: a for a in resultado["artifacts"]
                    if a["kind"] == "drawing"}
    for folha in sorted(FOLHAS):
        a = no_manifesto.get(folha)
        c.exige(a is not None, "folha-fora-do-manifesto", folha)
        c.exige(bool(a) and a.get("sha256") and a.get("size", 0) > 0,
                "folha-sem-hash", folha)
        svg = _svg_no_disco(run_dir, folha)
        ET.fromstring(svg)  # substring nao prova render: o SVG tem que abrir
        conf = sb.confere_folha_svg(svg)
        c.exige(conf["ok"], "guarda-reprova", "%s: %s" % (folha, conf))
    tp01 = _svg_no_disco(run_dir,
                         "drawings/terraplenagem-corte-aterro.svg")
    c.exige(_conta_celulas(tp01) == 9, "celulas",
            "desenhadas != 9 da malha 3x3")
    tp02 = _svg_no_disco(run_dir, "drawings/terraplenagem-drenagem.svg")
    c.exige(VAZAO_TXT in tp02, "vazao-conta-a-mao",
            "Q=0.75*130*1.2/360=0.325 nao aparece na TP-02")
    with open(os.path.join(run_dir, "sitio", "obras-sitio.json"),
              encoding="utf-8") as fh:
        sitio = json.load(fh)
    bloco = (sitio.get("terraplenagem") or {}).get("corte_aterro") or {}
    c.exige(bloco.get("corte_m3") == CORTE_M3, "corte-conta-a-mao",
            "veio %r, a mao da 1120.0" % (bloco.get("corte_m3"),))
    c.exige(bloco.get("aterro_m3") == ATERRO_M3, "aterro-conta-a-mao",
            "veio %r, a mao da 1360.0" % (bloco.get("aterro_m3"),))
    c.veredito()


# --- outro sentido do baseline: sem drenagem, so a TP-01 --------------------
def test_g95_sem_drenagem_so_sai_tp01(tmp_path):
    """Vermelho por injecao: arrancar a drenagem da copia tira a TP-02 do
    disco e do manifesto - o portao do caso bom acusaria a falta."""
    spec = _spec()
    del spec["site"]["terraplenagem"]["drenagem"]
    resultado = run_project(spec, str(tmp_path), SEM_IFC)
    obras = resultado["deliverables"]["obras_sitio"]
    no_disco = {os.path.relpath(os.path.join(r, f), str(tmp_path)).replace(
        os.sep, "/") for r, _, fs in os.walk(
        os.path.join(str(tmp_path), "drawings")) for f in fs}
    c = _Coletor()
    c.exige(no_disco == {"drawings/terraplenagem-corte-aterro.svg"}, "disco",
            "veio %r" % (no_disco,))
    c.exige("drawings/terraplenagem-drenagem.svg"
            not in set(obras.get("artifacts") or ()), "manifesto",
            "TP-02 sem dado nao pode constar no manifesto")
    c.exige(set(copy.deepcopy(FOLHAS)) - set(obras.get("artifacts") or ())
            == {"drawings/terraplenagem-drenagem.svg"}, "sensibilidade",
            "o defeito injetado tem de aparecer como TP-02 faltando")
    c.veredito()


# --- ausencia total se declara, nunca vira default ----------------------------
def test_g95_sem_sitio_nao_ha_folha_nem_default(tmp_path):
    """Sem site.terraplenagem o entregavel fica not_requested e nenhuma folha
    nasce do nada: o portao acusa folha sem dado declarado."""
    spec = _spec()
    del spec["site"]["terraplenagem"]
    resultado = run_project(spec, str(tmp_path), SEM_IFC)
    obras = resultado["deliverables"]["obras_sitio"]
    pasta = os.path.join(str(tmp_path), "drawings")
    no_disco = set()
    if os.path.isdir(pasta):
        no_disco = {f for _, _, fs in os.walk(pasta) for f in fs}
    c = _Coletor()
    c.exige(obras["status"] == "not_requested", "status",
            "veio %r" % (obras["status"],))
    c.exige("terraplenagem-corte-aterro.svg" not in no_disco
            and "terraplenagem-drenagem.svg" not in no_disco, "disco",
            "folha sem dado declarado e default silencioso: %r" % (no_disco,))
    c.veredito()
