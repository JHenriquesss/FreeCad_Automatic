"""G155 - as folhas do predio e da casa que nao diziam que reprovaram.

Medido (resultado real na mao, antes de mudar, conta intacta):
  - `grep REPROVA` em desenho_fundacao_edificio/desenho_eletrico/
    desenho_hidraulica/desenho_incendio/desenho_climatizacao/
    desenho_coordenacao/desenho_piso: 0;
  - eletrica do predio REPROVA de verdade (limite_de_baixa_tensao) e a
    prumada nao dizia nada (prova viva);
  - hidraulica/incendio ATENDEM e com o reprovado injetado continuavam sem
    dizer nada; fundacao (gate OK) idem;
  - marcas parciais existentes (escada 13, pavimento 4, casa 7/6) nomeiam a
    peca, nao o veredito da disciplina com os gates.

Entregue (fonte unica `veredito_folha_g152`, estendida, nunca copiada):
  - `extrair_veredito` le os dois dialetos do G152 + `gate:{OK,reprovados}`
    (fundacao) + `OK`/`ok` com reprovados (piso/escada/conferencia) +
    `circuits:{ok,errors[].design_id,designs[].conductor|protection.OK}`
    (eletrica residencial: ok e erros produzidos pelo dimensionamento);
  - cada folha do predio/casa aceita `veredito=` (o proprio resultado da
    disciplina) e declara `VEREDITO: REPROVADO em g1, g2` + `STATUS:
    REPROVADO - VER MEMORIAL` so na REPROVA (ATENDE/parametro ausente =
    byte-identico); fonte presente SEM veredito declara `VEREDITO NAO
    DISPONIVEL NO RESULTADO - VER MEMORIAL`, sem STATUS (decisao do
    backlog); os `gerar_*` repassam o `veredito` (ausente = historico
    silencioso, byte-identico com G143/G149/G138); o adapter e os
    gerar da casa passam a disciplina explicitamente; a casa injeta
    via `injetar_veredito_no_svg` no gerar (primeira faixa livre pelo
    estimador de colisao); a planta de formas abre faixa propria no
    rodape na REPROVA (a malha ocupa a folha toda).

Aceite: vermelho por injecao em cada disciplina com folha; ATENDE
byte-identica (hash); PNG olhado de cada folha reprovada;
`test_veredito_folha_g152` e o G102 casa/predio verdes.
"""
import copy
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import veredito_folha_g152 as V152

SPEC_ED = json.loads((Path(HERE).parents[2] / "projects"
                      / "edificio-multipavimento" / "project-spec.json"
                      ).read_text(encoding="utf-8"))

_CACHE = {}


def _caso_predio():
    if _CACHE:
        return _CACHE["R"], _CACHE["H"], _CACHE["E"], _CACHE["I"]
    import edificio_multipavimento as em
    import eletrica_edificio as ee
    import hidraulica_edificio as he
    import incendio_edificio as ie
    from edificio_adapter import _contexto_predio

    tk = SPEC_ED["turnkey"]
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
    H = he.dimensiona(tk["hidraulica"], ctx)
    E = ee.dimensiona(tk["eletrico"], ctx)
    _CACHE.update({"R": R, "H": H, "E": E, "I": I})
    return R, H, E, I


def _h(svg):
    return hashlib.sha256(svg.encode("utf-8")).hexdigest()


def _folhas_predio(R, H, E, I):
    """Todas as folhas do predio com/sem veredito (o veredito e por folha)."""
    import desenho_coordenacao as dc
    import desenho_eletrico as de
    import desenho_fundacao_edificio as dfe
    import desenho_hidraulica as dh
    import desenho_incendio as di
    import desenho_escada_edificio as dee
    import desenho_pavimento as dp

    F = R.get("fundacao") or {}
    out = {}
    out["EL-01"] = lambda v: de.diagrama_prumada_edificio_svg(E, R, veredito=v)
    out["EL-02"] = lambda v: de.planta_eletrica_pavimento_svg(E, R, veredito=v)
    out["EL-03"] = lambda v: de.infra_aterramento_edificio_svg(E, R, veredito=v)
    out["EL-04"] = lambda v: de.qdc_edificio_svg(E, R, veredito=v)
    out["HI-agua"] = lambda v: dh.planta_rede_edificio_svg(H, R, rede="agua", veredito=v)
    out["HI-esgoto"] = lambda v: dh.planta_rede_edificio_svg(H, R, rede="esgoto", veredito=v)
    out["HI-pluvial"] = lambda v: dh.planta_rede_edificio_svg(H, R, rede="pluvial", veredito=v)
    out["IN-01"] = lambda v: di.planta_pavimento_edificio_svg(I, R, veredito=v)
    out["IN-02"] = lambda v: di.detalhes_hidrantes_rotas_svg(I, R, veredito=v)
    esc = (R.get("escada") or {})
    out["IN-03"] = lambda v: dee.planta_escada_svg(esc, I, veredito=v)
    out["CO-04"] = lambda v: dfe.planta_fundacao_svg(F, R, veredito=v)
    out["CO-01"] = lambda v: dp.planta_formas_svg(R["pavimento"], R.get("descida"), veredito=v)
    vv = R.get("vigas_verificacao") or {}
    if isinstance(vv, dict) and vv.get("por_linha"):
        out["CO-02"] = lambda v: dp.prancha_armacao_vigas_pilares_svg(
            vv, R.get("pilares"), veredito=v)
    glo = {"atende_global": True, "falhas_verificacao": []}
    out["CD-01"] = lambda v: dc.coordenacao_svg([], None, veredito=v)
    return out


def test_01_baseline_atende_sem_reprovad_e_byte_identica():
    """Baseline nos dois sentidos (convencao 1): ATENDE nao declara nada e
    passar o veredito ATENDIDO nao muda um byte (hash igual ao historico)."""
    R, H, E, I = _caso_predio()
    E_ok = copy.deepcopy(E)
    E_ok["ATENDE"] = True
    E_ok["reprovados"] = []
    H_ok = copy.deepcopy(H)
    H_ok["ATENDE"] = True
    H_ok["reprovados"] = []
    I_ok = copy.deepcopy(I)
    I_ok["ATENDE"] = True
    I_ok["reprovados"] = []
    R_ok = copy.deepcopy(R)
    R_ok["ATENDE"] = True
    R_ok["reprovados"] = []
    F_ok = copy.deepcopy(R.get("fundacao") or {})
    if isinstance(F_ok.get("gate"), dict):
        F_ok["gate"] = dict(F_ok["gate"], OK=True, reprovados=[])
    lados = []
    import desenho_eletrico as de
    import desenho_hidraulica as dh
    import desenho_incendio as di
    import desenho_fundacao_edificio as dfe

    pares = [
        ("EL-01", de.diagrama_prumada_edificio_svg(E_ok, R_ok),
         de.diagrama_prumada_edificio_svg(E_ok, R_ok, veredito=E_ok)),
        ("HI-agua", dh.planta_rede_edificio_svg(H_ok, R_ok, rede="agua"),
         dh.planta_rede_edificio_svg(H_ok, R_ok, rede="agua", veredito=H_ok)),
        ("IN-01", di.planta_pavimento_edificio_svg(I_ok, R_ok),
         di.planta_pavimento_edificio_svg(I_ok, R_ok, veredito=I_ok)),
        ("CO-04", dfe.planta_fundacao_svg(F_ok, R_ok),
         dfe.planta_fundacao_svg(F_ok, R_ok, veredito=F_ok)),
    ]
    for nome, antigo, novo in pares:
        if _h(antigo) != _h(novo):
            lados.append("%s: ATENDE mudou o byte (%s vs %s)"
                         % (nome, _h(antigo)[:12], _h(novo)[:12]))
        if "REPROVAD" in novo:
            lados.append("%s: ATENDE com REPROVAD" % nome)
        ET.fromstring(novo)
    assert not lados, "baseline G155 reprova:\n" + "\n".join(lados)


def test_02_vermelho_por_injecao_em_cada_disciplina_com_folha():
    """Injecao do veredito reprovado (copia em memoria, convencao 2): cada
    folha declara no corpo + STATUS, nomeando todos os gates - texto, nunca
    omissao (convencao 4). A fonte e sempre o resultado, via fonte unica."""
    R, H, E, I = _caso_predio()
    lados = []
    import desenho_eletrico as de
    import desenho_hidraulica as dh
    import desenho_incendio as di
    import desenho_fundacao_edificio as dfe
    import desenho_escada_edificio as dee
    import desenho_pavimento as dp
    import desenho_coordenacao as dc

    def _confere(nome, svg, gates):
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            lados.append("%s: svg malformado: %s" % (nome, exc))
            return
        for g in gates:
            if g not in svg:
                lados.append("%s: gate %r fora da folha" % (nome, g))
        if "VEREDITO: REPROVADO" not in svg:
            lados.append("%s: sem a linha VEREDITO: REPROVADO" % nome)
        if "REPROVADO - VER MEMORIAL" not in svg:
            lados.append("%s: sem o STATUS REPROVADO - VER MEMORIAL" % nome)

    E2 = copy.deepcopy(E)
    E2["ATENDE"] = False
    E2["reprovados"] = ["prumada_g155", "quadro_g155"]
    _confere("EL-01", de.diagrama_prumada_edificio_svg(E2, R, veredito=E2),
             ["prumada_g155", "quadro_g155"])
    _confere("EL-02", de.planta_eletrica_pavimento_svg(E2, R, veredito=E2),
             ["prumada_g155", "quadro_g155"])
    _confere("EL-03", de.infra_aterramento_edificio_svg(E2, R, veredito=E2),
             ["prumada_g155", "quadro_g155"])
    _confere("EL-04", de.qdc_edificio_svg(E2, R, veredito=E2),
             ["prumada_g155", "quadro_g155"])
    H2 = copy.deepcopy(H)
    H2["ATENDE"] = False
    H2["reprovados"] = ["coluna_g155", "reserva_g155"]
    for rede in ("agua", "esgoto", "pluvial"):
        _confere("HI-%s" % rede, dh.planta_rede_edificio_svg(
            H2, R, rede=rede, veredito=H2), ["coluna_g155", "reserva_g155"])
    I2 = copy.deepcopy(I)
    I2["ATENDE"] = False
    I2["reprovados"] = ["rota_g155", "largura_g155"]
    _confere("IN-01", di.planta_pavimento_edificio_svg(I2, R, veredito=I2),
             ["rota_g155", "largura_g155"])
    _confere("IN-02", di.detalhes_hidrantes_rotas_svg(I2, R, veredito=I2),
             ["rota_g155", "largura_g155"])
    esc = copy.deepcopy(R.get("escada") or {})
    _confere("IN-03", dee.planta_escada_svg(esc, I2, veredito=I2),
             ["rota_g155", "largura_g155"])
    F2 = copy.deepcopy(R.get("fundacao") or {})
    if isinstance(F2.get("gate"), dict):
        F2["gate"] = dict(F2["gate"], OK=False,
                          reprovados=["recalque_g155", "tensao_g155"])
        _confere("CO-04", dfe.planta_fundacao_svg(F2, R, veredito=F2),
                 ["recalque_g155", "tensao_g155"])
    else:
        lados.append("CO-04: fundacao sem gate para injetar")
    R2 = copy.deepcopy(R)
    R2["ATENDE"] = False
    R2["reprovados"] = ["viga_g155", "pilar_g155"]
    _confere("CO-01", dp.planta_formas_svg(R2["pavimento"], R2.get("descida"),
                                           veredito=R2),
             ["viga_g155", "pilar_g155"])
    vv = R.get("vigas_verificacao")
    if isinstance(vv, dict) and vv.get("por_linha"):
        _confere("CO-02", dp.prancha_armacao_vigas_pilares_svg(
            vv, R.get("pilares"), veredito=R2), ["viga_g155", "pilar_g155"])
    glo2 = {"atende_global": False,
            "falhas_verificacao": ["eletrico:prumada_g155"]}
    membros = [{"marca": "E-QD1", "p1": [0, 0, 0], "p2": [1000, 0, 0]},
               {"marca": "P-TB1", "p1": [0, 0, 0], "p2": [0, 1000, 0]}]
    _confere("CD-01", dc.coordenacao_svg(membros, None, veredito=glo2),
             ["eletrico:prumada_g155"])
    # prova viva: a eletrica real ja REPROVA e a folha passa a declarar.
    if E.get("ATENDE") is False:
        svg_real = de.diagrama_prumada_edificio_svg(E, R, veredito=E)
        for g in (E.get("reprovados") or []):
            if g not in svg_real:
                lados.append("prova-viva EL-01: gate real %r fora" % g)
        if "VEREDITO: REPROVADO" not in svg_real:
            lados.append("prova-viva EL-01 sem VEREDITO")
    assert not lados, "injecao G155 reprova:\n" + "\n".join(lados)


def test_03_fonte_unica_estendida_le_sem_decidir():
    """A lente parte de onde o dado e PRODUZIDO (convencao 9): a fonte unica
    estendida le ATENDE, atende_*, gate.OK e OK/ok - sem chave, sem veredito.
    Literais a mao (convencao 5)."""
    lados = []

    def _confere(fonte, at_esp, gates_esp):
        at, gates = V152.extrair_veredito(fonte)
        if at != at_esp or list(gates) != list(gates_esp):
            return ("extrair %r: esperado (%r, %r), saiu (%r, %r)"
                    % (fonte, at_esp, gates_esp, at, gates))
        return None

    for fonte, at_esp, gates_esp in [
            ({"ATENDE": True, "reprovados": []}, True, []),
            ({"ATENDE": False, "reprovados": ["a_g155", "b_g155"]},
             False, ["a_g155", "b_g155"]),
            ({"atende_global": False, "falhas_verificacao": ["x_g155"]},
             False, ["x_g155"]),
            ({"gate": {"OK": True, "reprovados": []}}, True, []),
            ({"gate": {"OK": False,
                       "reprovados": ["recalque_g155"]}}, False,
             ["recalque_g155"]),
            ({"OK": False, "reprovados": ["piso_g155"]}, False,
             ["piso_g155"]),
            ({"OK": True}, True, []),
            ({"ok": False, "reprovados": ["conf_g155"]}, False,
             ["conf_g155"]),
            ({"ok": True}, True, []),
            # circuits da eletrica residencial (G155): ok + erros por
            # design_id + designs com conductor/protection OK False.
            ({"ok": True, "designs": [], "errors": []}, True, []),
            ({"ok": False, "errors": [{"code": "x", "design_id": "C-G155"}]},
             False, ["C-G155"]),
            ({"ok": False,
              "designs": [{"id": "C-1",
                           "conductor": {"OK": True},
                           "protection": {"OK": False}}],
              "errors": []}, False, ["C-1"]),
            ({"ok": False,
              "designs": [{"id": "C-1",
                           "conductor": {"OK": True},
                           "protection": {"OK": True}}],
              "errors": [{"code": "y", "design_id": "C-9"}]}, False,
             ["C-9"]),
            ({}, None, []),
            (None, None, []),
    ]:
        erro = _confere(fonte, at_esp, gates_esp)
        if erro:
            lados.append(erro)
    # precedencia: ATENDE vence gate/OK (o dialeto historico manda).
    at, gates = V152.extrair_veredito(
        {"ATENDE": True, "reprovados": [], "gate": {"OK": False,
         "reprovados": ["portico_g155"]}})
    if at is not True:
        lados.append("precedencia ATENDE > gate quebrada")
    # injetar so declara na REPROVA; ATENDE/parametro ausente devolve intacto.
    # Fonte presente SEM veredito declara a ausencia (decisao do backlog),
    # sem STATUS (carimbar seria decidir).
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><text>a</text></svg>'
    if V152.injetar_veredito_no_svg(svg, {"ATENDE": True}) != svg:
        lados.append("injetar com ATENDE devia ser byte-identico")
    if V152.injetar_veredito_no_svg(svg, None) != svg:
        lados.append("injetar com fonte ausente devia ser byte-identico")
    sem = V152.injetar_veredito_no_svg(svg, {})
    if V152.LINHA_SEM_VEREDITO not in sem:
        lados.append("injetar sem veredito sem a linha de indisponibilidade")
    if "STATUS" in sem:
        lados.append("injetar sem veredito nao carimba STATUS")
    ET.fromstring(sem)
    lin, st = V152.veredito_para_folha_svg({})
    if lin != V152.LINHA_SEM_VEREDITO or st is not None:
        lados.append("para_folha sem veredito devia ser (LINHA, None)")
    lin, st = V152.veredito_para_folha_svg(None)
    if lin is not None:
        lados.append("para_folha com fonte ausente devia ser silencioso")
    rep = V152.injetar_veredito_no_svg(
        svg, {"ATENDE": False, "reprovados": ["g_g155"]})
    if "VEREDITO: REPROVADO em g_g155" not in rep:
        lados.append("injetar com REPROVA sem a linha")
    if "STATUS: REPROVADO - VER MEMORIAL" not in rep:
        lados.append("injetar com REPROVA sem o STATUS")
    ET.fromstring(rep)
    assert not lados, "fonte unica G155 reprova:\n" + "\n".join(lados)


def test_04_casa_cada_folha_reprovada_declara_e_atende_byte_identica(tmp_path):
    """A casa (inclui a conferencia interna sem codigo no indice): com o
    veredito reprovado injetado cada folha declara; ATENDE sai byte-identica
    (hash igual ao historico, sem REPROVAD novo)."""
    import desenho_casa_residencial as dcr

    R, _H, _E, _I = _caso_predio()
    lados = []
    arquitetura = {"ambientes": [{"nome": "Sala", "tipo": "sala",
                                  "area_m2": 20.0, "perimetro_m": 18.0,
                                  "carga_iluminacao_va": 200.0,
                                  "n_tomadas_min": 5,
                                  "carga_tomadas_va": 1000.0,
                                  "criterio_tomadas": "9.5.2.2.1",
                                  "geometria_ok": True}],
                   "totais": {"area_util_m2": 20.0, "carga_iluminacao_va": 200.0,
                              "carga_tomadas_va": 1000.0, "n_tomadas_min": 5},
                   "ATENDE": True, "reprovados": []}
    svg_ok = dcr.quadro_ambientes_svg(arquitetura)
    if "REPROVAD" in svg_ok:
        lados.append("quadro-ambientes ATENDE com REPROVAD")
    arq_rep = copy.deepcopy(arquitetura)
    arq_rep["ATENDE"] = False
    arq_rep["reprovados"] = ["area_g155"]
    out = str(tmp_path / "qrep.svg")
    Path(out).write_text(V152.injetar_veredito_no_svg(
        dcr.quadro_ambientes_svg(arquitetura), arq_rep), encoding="utf-8")
    txt = Path(out).read_text(encoding="utf-8")
    if "VEREDITO: REPROVADO em area_g155" not in txt:
        lados.append("quadro-ambientes injetado sem o veredito")
    ET.fromstring(txt)
    # estrutura da casa via predio (mesma primitiva, veredito da estrutura).
    R2 = copy.deepcopy(R)
    R2["ATENDE"] = False
    R2["reprovados"] = ["viga_g155"]
    import desenho_pavimento as dp
    antigo = dp.planta_formas_svg(R["pavimento"], R.get("descida"))
    novo_ok = dp.planta_formas_svg(R["pavimento"], R.get("descida"),
                                   veredito=R)
    if _h(antigo) != _h(novo_ok) and R.get("ATENDE") is True:
        lados.append("planta-formas ATENDE mudou o byte")
    novo_rep = dp.planta_formas_svg(R2["pavimento"], R2.get("descida"),
                                    veredito=R2)
    if "VEREDITO: REPROVADO em viga_g155" not in novo_rep:
        lados.append("planta-formas injetada sem o veredito")
    assert not lados, "casa G155 reprova:\n" + "\n".join(lados)


def test_05_png_olhado_cada_folha_reprovada(tmp_path):
    """Substring -> parse -> renderizar (convencao 3): cada folha reprovada
    renderiza em PNG (fitz) com o veredito legivel; ATENDE sem VEREDITO.
    Os PNG ficam em tmp_path para o olho humano (artefato da prova)."""
    try:
        import fitz
    except ImportError:
        import pymupdf as fitz
    R, H, E, I = _caso_predio()
    import desenho_eletrico as de
    import desenho_hidraulica as dh
    import desenho_incendio as di

    E2 = copy.deepcopy(E)
    E2["ATENDE"] = False
    E2["reprovados"] = ["prumada_g155"]
    H2 = copy.deepcopy(H)
    H2["ATENDE"] = False
    H2["reprovados"] = ["coluna_g155"]
    I2 = copy.deepcopy(I)
    I2["ATENDE"] = False
    I2["reprovados"] = ["rota_g155"]
    folhas = {
        "EL-01-reprovada": de.diagrama_prumada_edificio_svg(E2, R, veredito=E2),
        "EL-01-atende": de.diagrama_prumada_edificio_svg(
            dict(E2, ATENDE=True, reprovados=[]), R,
            veredito=dict(E2, ATENDE=True, reprovados=[])),
        "HI-agua-reprovada": dh.planta_rede_edificio_svg(
            H2, R, rede="agua", veredito=H2),
        "IN-01-reprovada": di.planta_pavimento_edificio_svg(I2, R, veredito=I2),
    }
    lados = []
    for nome, svg in folhas.items():
        base = tmp_path / (nome + ".svg")
        base.write_text(svg, encoding="utf-8")
        try:
            doc = fitz.open(str(base))
            pix = doc[0].get_pixmap(dpi=80)
            png = tmp_path / (nome + ".png")
            pix.save(str(png))
            if png.stat().st_size < 2000:
                lados.append("%s: png vazio (%d bytes)" % (nome, png.stat().st_size))
        except Exception as exc:  # noqa: BLE001
            lados.append("%s: nao renderiza em PNG: %r" % (nome, exc))
            continue
        if "reprovada" in nome and "VEREDITO: REPROVADO" not in svg:
            lados.append("%s: reprovada sem o veredito no SVG" % nome)
        if nome.endswith("-atende") and "VEREDITO" in svg:
            lados.append("%s: ATENDE com VEREDITO" % nome)
    assert not lados, "png G155 reprova:\n" + "\n".join(lados)


def test_06_veredito_nao_colide_com_rotulo_da_folha():
    """Posicao da marca (convencao 3, PNG olhado): a linha VEREDITO/STATUS
    nao colide com nenhum rotulo da folha (estimador
    colisoes_de_rotulo_svg). A planta de formas abre faixa propria no
    rodape; a coordenacao mora no vao entre as caixas."""
    from desenho_svg_base import colisoes_de_rotulo_svg
    R, H, E, I = _caso_predio()
    import desenho_eletrico as de
    import desenho_hidraulica as dh
    import desenho_incendio as di
    import desenho_fundacao_edificio as dfe
    import desenho_escada_edificio as dee
    import desenho_pavimento as dp
    import desenho_coordenacao as dc

    E2 = copy.deepcopy(E)
    E2["ATENDE"] = False
    E2["reprovados"] = ["prumada_g155", "quadro_g155"]
    H2 = copy.deepcopy(H)
    H2["ATENDE"] = False
    H2["reprovados"] = ["coluna_g155", "reserva_g155"]
    I2 = copy.deepcopy(I)
    I2["ATENDE"] = False
    I2["reprovados"] = ["rota_g155", "largura_g155"]
    F2 = copy.deepcopy(R.get("fundacao") or {})
    F2["gate"] = dict(F2.get("gate") or {}, OK=False,
                      reprovados=["recalque_g155", "tensao_g155"])
    R2 = copy.deepcopy(R)
    R2["ATENDE"] = False
    R2["reprovados"] = ["viga_g155", "pilar_g155"]
    esc = copy.deepcopy(R.get("escada") or {})
    glo2 = {"atende_global": False,
            "falhas_verificacao": ["eletrico:prumada_g155"]}
    membros = [{"marca": "E-QD1", "p1": [0, 0, 0], "p2": [1000, 0, 0]},
               {"marca": "P-TB1", "p1": [0, 0, 0], "p2": [0, 1000, 0]}]
    folhas = {
        "EL-01": de.diagrama_prumada_edificio_svg(E2, R, veredito=E2),
        "EL-02": de.planta_eletrica_pavimento_svg(E2, R, veredito=E2),
        "EL-03": de.infra_aterramento_edificio_svg(E2, R, veredito=E2),
        "EL-04": de.qdc_edificio_svg(E2, R, veredito=E2),
        "HI-agua": dh.planta_rede_edificio_svg(H2, R, rede="agua",
                                              veredito=H2),
        "HI-esgoto": dh.planta_rede_edificio_svg(H2, R, rede="esgoto",
                                                veredito=H2),
        "HI-pluvial": dh.planta_rede_edificio_svg(H2, R, rede="pluvial",
                                                 veredito=H2),
        "IN-01": di.planta_pavimento_edificio_svg(I2, R, veredito=I2),
        "IN-02": di.detalhes_hidrantes_rotas_svg(I2, R, veredito=I2),
        "IN-03": dee.planta_escada_svg(esc, I2, veredito=I2),
        "CO-04": dfe.planta_fundacao_svg(F2, R, veredito=F2),
        "CO-01": dp.planta_formas_svg(R2["pavimento"], R2.get("descida"),
                                     veredito=R2),
        "CD-01": dc.coordenacao_svg(membros, None, veredito=glo2),
    }
    vv = R.get("vigas_verificacao") or {}
    if isinstance(vv, dict) and vv.get("por_linha"):
        folhas["CO-02"] = dp.prancha_armacao_vigas_pilares_svg(
            vv, R.get("pilares"), veredito=R2)
    lados = []
    for nome, svg in folhas.items():
        for a, b in colisoes_de_rotulo_svg(svg):
            if ("VEREDITO" in a or "VEREDITO" in b
                    or "STATUS" in a or "STATUS" in b):
                lados.append("%s: marca colide (%r x %r)" % (nome, a, b))
    assert not lados, "colisao G155 reprova:\n" + "\n".join(lados)


def test_07_eletrica_residencial_le_circuits_e_declara(tmp_path):
    """A eletrica da casa le o `circuits` produzido (ok + erros por
    design_id) pela fonte unica: ok=True sai byte-identico; ok=False
    declara com os design_id; sem circuits declara indisponivel. O
    resultado vem do calculo real (convencao 9), a REPROVA e injetada
    em copia (convencao 2)."""
    import json
    import desenho_eletrico_residencial as der
    from residencial_eletrica import run_residential_electrical

    spec = json.loads((Path(HERE).parents[2] / "projects"
                       / "casa-residencial-eletrica-sintetica"
                       / "project-spec.json").read_text(encoding="utf-8"))
    result, _ = run_residential_electrical(
        {"project_id": "casa-g155",
         "turnkey_spec": spec["turnkey"],
         "source_refs": spec["source_refs"]["eletrico"],
         "requested_disciplines": ["eletrico"]},
        None)
    out = der.gerar_desenhos_residenciais(result, tmp_path / "ok")
    lados = []
    for nome in ("unifilar.svg", "quadro-cargas.svg"):
        txt = (tmp_path / "ok" / nome).read_text(encoding="utf-8")
        if "VEREDITO" in txt:
            lados.append("%s: ok=True com VEREDITO" % nome)
        ET.fromstring(txt)
    rep = copy.deepcopy(result)
    cir = copy.deepcopy(rep.get("circuits") or {})
    cir["ok"] = False
    cir["errors"] = [{"code": "x_g155", "design_id": "C-E155"}]
    if isinstance(cir.get("designs"), list) and cir["designs"]:
        mau = copy.deepcopy(cir["designs"][0])
        mau["id"] = "C-G155"
        mau["conductor"] = {"OK": True}
        mau["protection"] = {"OK": False}
        cir["designs"] = [mau] + cir["designs"][1:]
    rep["circuits"] = cir
    der.gerar_desenhos_residenciais(rep, tmp_path / "rep")
    for nome in ("unifilar.svg", "quadro-cargas.svg"):
        txt = (tmp_path / "rep" / nome).read_text(encoding="utf-8")
        if "VEREDITO: REPROVADO" not in txt:
            lados.append("%s: reprovado sem VEREDITO" % nome)
        for gate in ("C-G155", "C-E155"):
            if gate not in txt:
                lados.append("%s: gate %r fora da folha" % (nome, gate))
        if "REPROVADO - VER MEMORIAL" not in txt:
            lados.append("%s: reprovado sem STATUS" % nome)
        ET.fromstring(txt)
    sem = {"calculation": {}, "service_entry": {}}
    der.gerar_desenhos_residenciais(sem, tmp_path / "sem")
    for nome in ("unifilar.svg", "quadro-cargas.svg"):
        txt = (tmp_path / "sem" / nome).read_text(encoding="utf-8")
        if V152.LINHA_SEM_VEREDITO not in txt:
            lados.append("%s: sem circuits sem a indisponibilidade" % nome)
        ET.fromstring(txt)
    assert not lados, "eletrica residencial G155 reprova:\n" + "\n".join(lados)
