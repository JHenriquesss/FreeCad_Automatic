"""G162 - a demanda que chegava a folha como um numero sem origem.

Medido (resultado real na mao, antes de mudar, conta intacta):
  - `desenho_eletrico_residencial.py:273-276` imprimia so
    `"demanda %s kVA" % final_kva`: sem fonte (WKI/F131), sem item, sem
    fator locacional, sem composicao;
  - recusa de motor (bifasico, sem linha exata, qtd > 10): o modulo
    devolvia ok=False com `calculation` PRESENTE (numero so-dos-comodos)
    e a folha imprimia o numero como se ATENDESSE, sem dizer a recusa
    (saturacao silenciosa);
  - fator locacional fora da tabela: `calculation` vazio e a folha saia
    com `demanda A CONFIRMAR kVA` sem dizer por que (padrao G106);
  - `extrair_veredito(circuits)` devolvia (True, []) nos dois casos: a
    recusa morria no resultado, nunca chegava ao veredito que a folha le.

Entregue (fonte unica, nunca copia):
  - `demanda_residencial_enel.fonte_demanda/linha_fonte_demanda` +
    `calculation["fonte"]`: a linha da demanda declara codigo, acervo,
    itens e fator locacional usado (G154/G131);
  - `residencial_eletrica` grava `calculation["demand_errors"]` (vale
    tambem quando o numero falta);
  - `veredito_folha_g152.gates_demanda` (lido em `extrair_veredito`):
    cada recusa vira gate nomeado (`demanda-motor-bifasico`,
    `demanda-motor-sem-linha`, `demanda-motor-qtd-acima-10`,
    `demanda-fator-locacional`, `demanda-<code>`);
  - o unifilar declara a fonte numa faixa propria (sem colisao) e a
    recusa pelo veredito; a folha nunca para de sair e nunca decide gate.

Aceite: vermelho por injecao para cada recusa (a folha declara e nomeia);
ATENDE byte-identica (hash) quando nada recusa; PNG olhado da folha com
demanda e da folha com demanda recusada; `test_veredito_folha_g152` e
`g155` verdes; G102 casa verde.
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

SPEC_EL = json.loads((Path(HERE).parents[2] / "projects"
                      / "casa-residencial-eletrica-sintetica"
                      / "project-spec.json").read_text(encoding="utf-8"))
SPEC_CASA = Path(HERE).parents[2] / "projects" / "casa-residencial" \
    / "project-spec.json"


def _h(svg):
    return hashlib.sha256(svg.encode("utf-8")).hexdigest()


def _norm_el(payload):
    return {"project_id": "casa-g162",
            "turnkey_spec": {"eletrico": payload},
            "source_refs": SPEC_EL["source_refs"]["eletrico"],
            "requested_disciplines": ["eletrico"]}


def _run_el(payload):
    from residencial_eletrica import run_residential_electrical
    return run_residential_electrical(_norm_el(payload), None)


def _payload_base():
    return copy.deepcopy(SPEC_EL["turnkey"]["eletrico"])


# cada recusa do modulo, numa porta de entrada que o produto aceita
# (convencao 11: o payload turnkey.eletrico do adaptador).
RECUSAS = {
    "bifasico": ("demanda-motor-bifasico",
                 {"quantity": 1, "power_cv": "1",
                  "connection": "bifasica"}),
    "sem-linha": ("demanda-motor-sem-linha",
                  {"quantity": 1, "power_cv": "9 3/4",
                   "connection": "trifasica"}),
    "qtd-acima-10": ("demanda-motor-qtd-acima-10",
                     {"quantity": 11, "power_cv": "1",
                      "connection": "trifasica"}),
}
FATOR_GATE = "demanda-fator-locacional"


def _payload_recusa(nome):
    payload = _payload_base()
    if nome == "fator":
        payload["network"]["location_factor"] = 0.99
        return payload
    payload["loads"]["motors"] = [dict(RECUSAS[nome][1])]
    return payload


def test_01_ok_byte_identica_e_fonte_declarada():
    """Baseline nos dois sentidos (convencao 1): sem recusa, o gerar sai
    byte-identico ao cru (o veredito ATENDIDO nao declara nada) e a linha
    da demanda diz de onde veio o numero."""
    import desenho_eletrico_residencial as der

    result, _ = _run_el(_payload_base())
    assert result["status"] != "blocked"
    assert result["calculation"].get("demand_errors") == []
    fonte = result["calculation"].get("fonte") or {}
    assert fonte.get("codigo") == "WKI-OMBR-MAT-18-0263-INBR-R01"
    assert fonte.get("acervo") == "F131"
    assert float(fonte.get("fator_locacional")) == float(
        _payload_base()["network"]["location_factor"])
    cru = der.unifilar_residencial_svg(result)
    ET.fromstring(cru)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        emitido = der.gerar_desenhos_residenciais(result, tmp)
        assert {"unifilar.svg", "quadro-cargas.svg"} <= set(emitido["files"])
        gen = Path(tmp, "unifilar.svg").read_text(encoding="utf-8")
    assert _h(cru) == _h(gen), "ATENDE mudou o byte"
    assert "VEREDITO" not in gen
    assert "STATUS" not in gen
    assert "demanda " in gen and "kVA" in gen
    for parte in ("WKI-OMBR-MAT-18-0263-INBR-R01", "F131",
                  "fator locacional"):
        assert parte in gen, "fonte sem %r" % parte
    # a faixa propria nao encosta em rotulo (regua do G129): o instrumento
    # tem de conseguir acusar (convencao 7).
    from desenho_svg_base import colisoes_de_rotulo_svg
    pares = colisoes_de_rotulo_svg(gen)
    assert pares == [], "fonte colide: %r" % (pares[:3],)


def test_02_vermelho_cada_recusa_a_folha_nomeia(tmp_path):
    """Injecao em copia (convencao 2): cada recusa do modulo sai na folha
    com o nome da recusa + STATUS; a folha continua saindo (nunca para)."""
    import desenho_eletrico_residencial as der

    lados = []
    esperados = {nome: gate for nome, (gate, _m) in RECUSAS.items()}
    esperados["fator"] = FATOR_GATE
    for nome, gate_esp in sorted(esperados.items()):
        result, _ = _run_el(_payload_recusa(nome))
        if result["status"] != "blocked":
            lados.append("%s: recusa sem blocked" % nome)
        derr = (result.get("calculation") or {}).get("demand_errors") or []
        if not derr:
            lados.append("%s: sem demand_errors no calculo" % nome)
        out = tmp_path / nome
        out.mkdir(exist_ok=True)
        der.gerar_desenhos_residenciais(result, out)
        txt = (out / "unifilar.svg").read_text(encoding="utf-8")
        try:
            ET.fromstring(txt)
        except ET.ParseError as exc:
            lados.append("%s: svg malformado: %s" % (nome, exc))
            continue
        if gate_esp not in txt:
            lados.append("%s: gate %r fora da folha" % (nome, gate_esp))
        if "VEREDITO: REPROVADO em " not in txt:
            lados.append("%s: sem a linha VEREDITO: REPROVADO" % nome)
        if "REPROVADO - VER MEMORIAL" not in txt:
            lados.append("%s: sem o STATUS" % nome)
        if nome == "fator":
            if "demanda A CONFIRMAR kVA" not in txt:
                lados.append("fator: sem o A_CONFIRMAR do numero")
            if "fonte da demanda A CONFIRMAR" not in txt:
                lados.append("fator: fonte some sem aviso (G106)")
        else:
            # recusa de motor: o numero dos comodos continua saindo (a
            # folha nao para), mas a recusa vai junto, nomeada.
            if "demanda A CONFIRMAR" in txt:
                lados.append("%s: numero sumiu (a folha nao para)" % nome)
            if "WKI-OMBR-MAT-18-0263-INBR-R01" not in txt:
                lados.append("%s: fonte sumiu com a recusa" % nome)
    # as recusas de motor sao distintas entre si (qual recusa, nao so que
    # recusou): o mesmo codigo, tres gates.
    gates = sorted(esperados[n] for n in ("bifasico", "sem-linha",
                                          "qtd-acima-10"))
    if len(set(gates)) != 3:
        lados.append("gates de motor indistintos: %r" % (gates,))
    assert not lados, "injecao G162 reprova:\n" + "\n".join(lados)


def test_03_fonte_unica_le_a_demanda_sem_decidir():
    """A lente parte de onde o dado e PRODUZIDO (convencao 9): literais a
    mao (convencao 5), nos dois sentidos (convencao 1)."""
    lados = []

    def _confere(fonte, at_esp, gates_esp):
        at, gates = V152.extrair_veredito(fonte)
        if at != at_esp or list(gates) != list(gates_esp):
            return ("extrair %r: esperado (%r, %r), saiu (%r, %r)"
                    % (fonte, at_esp, gates_esp, at, gates))
        return None

    bif = {"code": "motor_outside_table",
           "message": "motor bifásico recusado: as TABELAS 2 e 3 da WKI"}
    sem = {"code": "motor_outside_table",
           "message": "combinação de motor sem linha exata nas TABELAS 2 e 3"}
    qtd = {"code": "motor_outside_table",
           "message": "quantidade de motores acima de 10 recusada"}
    loc = {"code": "invalid_location_factor",
           "message": "fator locacional fora da tabela"}
    base_ok = {"ok": True, "errors": [], "designs": []}
    casos = [
        (dict(base_ok), True, []),
        (dict(base_ok, demand_errors=[]), True, []),
        (dict(base_ok, demand_errors=[bif]),
         False, ["demanda-motor-bifasico"]),
        (dict(base_ok, demand_errors=[sem]),
         False, ["demanda-motor-sem-linha"]),
        (dict(base_ok, demand_errors=[qtd]),
         False, ["demanda-motor-qtd-acima-10"]),
        (dict(base_ok, demand_errors=[loc]),
         False, ["demanda-fator-locacional"]),
        # o circuito reprovado continua nomeado junto (soma, nunca troca).
        ({"ok": False, "errors": [{"code": "zz", "design_id": "C-9"}],
          "designs": [], "demand_errors": [bif]},
         False, ["C-9", "demanda-motor-bifasico"]),
        # resultado eletrico inteiro passado direto (robustez): le do
        # calculation sem o circuits mudar.
        ({"calculation": {"demand_errors": [loc]}}, False,
         ["demanda-fator-locacional"]),
        ({}, None, []),
        (None, None, []),
    ]
    for fonte, at_esp, gates_esp in casos:
        erro = _confere(fonte, at_esp, gates_esp)
        if erro:
            lados.append(erro)
    # ATENDE/parametro ausente seguem byte-identicos; so a REPROVA declara.
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><text>a</text></svg>'
    if V152.injetar_veredito_no_svg(
            svg, dict(base_ok)) != svg:
        lados.append("injetar ATENDE sem demand_errors devia ser byte-identico")
    if V152.injetar_veredito_no_svg(svg, None) != svg:
        lados.append("injetar fonte ausente devia ser byte-identico")
    rep = V152.injetar_veredito_no_svg(
        svg, dict(base_ok, demand_errors=[bif]))
    if "VEREDITO: REPROVADO em demanda-motor-bifasico" not in rep:
        lados.append("injetar recusa sem a linha nomeada")
    if "STATUS: REPROVADO - VER MEMORIAL" not in rep:
        lados.append("injetar recusa sem o STATUS")
    ET.fromstring(rep)
    assert not lados, "fonte unica G162 reprova:\n" + "\n".join(lados)


def test_04_casa_a_outra_porta_composta_declara(tmp_path):
    """Convencao 11: a recusa entra pela outra porta que o produto aceita
    (o vertical da casa, composto pelo `casa_residencial`)."""
    import desenho_eletrico_residencial as der
    from project_loop import normalize_spec
    import casa_residencial as cr

    if not SPEC_CASA.is_file():
        raise AssertionError("spec da casa ausente: %s" % SPEC_CASA)
    spec_ok = json.loads(SPEC_CASA.read_text(encoding="utf-8"))
    resultado_ok, _ = cr.run_casa_residencial(normalize_spec(spec_ok), None)
    el_ok = resultado_ok.get("eletrico") or {}
    assert (el_ok.get("calculation") or {}).get("fonte", {}).get(
        "codigo") == "WKI-OMBR-MAT-18-0263-INBR-R01"
    der.gerar_desenhos_residenciais(el_ok, tmp_path / "casa-ok")
    txt_ok = (tmp_path / "casa-ok" / "unifilar.svg").read_text(
        encoding="utf-8")
    ET.fromstring(txt_ok)
    if "WKI-OMBR-MAT-18-0263-INBR-R01" not in txt_ok:
        raise AssertionError("casa ok sem a fonte da demanda")

    spec_rep = copy.deepcopy(spec_ok)
    spec_rep["turnkey"]["eletrico"]["loads"]["motors"] = [
        {"quantity": 1, "power_cv": "1", "connection": "bifasica"}]
    resultado_rep, _ = cr.run_casa_residencial(
        normalize_spec(spec_rep), None)
    el_rep = resultado_rep.get("eletrico") or {}
    derr = (el_rep.get("calculation") or {}).get("demand_errors") or []
    assert derr, "porta casa: recusa nao chegou ao calculo eletrico"
    der.gerar_desenhos_residenciais(el_rep, tmp_path / "casa-rep")
    txt_rep = (tmp_path / "casa-rep" / "unifilar.svg").read_text(
        encoding="utf-8")
    ET.fromstring(txt_rep)
    lados = []
    if "demanda-motor-bifasico" not in txt_rep:
        lados.append("porta casa: gate da recusa fora da folha")
    if "VEREDITO: REPROVADO" not in txt_rep:
        lados.append("porta casa: sem a linha de veredito")
    assert not lados, "casa G162 reprova:\n" + "\n".join(lados)


def test_05_muda_nada_no_numero_nem_no_carimbo():
    """Nao fazer do goal: o numero e o mesmo com e sem a mudanca de
    composicao, e nenhum drawing_number/codigo de prancha muda aqui."""
    from demanda_residencial_enel import calculate_residential_demand

    payload = {"network": {"location_factor": 0.88},
               "rooms": {"quarto": 2, "sala": 1, "banheiro": 1,
                         "cozinha": 1, "area_servico": 1, "outros": 0},
               "loads": {"heating": [], "motors": [], "special_lighting": []}}
    out = calculate_residential_demand(payload)
    assert out["ok"] is True
    calc = out["calculation"]
    # numero intocado (afericao da suite de demanda): 10.30/1.20 com o
    # fator 0,88 sobre os comodos (cozinha_1: 2 quartos).
    import pytest
    assert calc["demand"]["final_kva"] == pytest.approx(
        (2 * 1.50 + 1.60 + 2.30 + 1.50 + 1.90) / 1.20 * 0.88)
    assert calc["fonte"]["fator_locacional"] == pytest.approx(0.88)
    # segunda chamada (a dos warnings) traz a mesma composicao (G131).
    out2 = calculate_residential_demand(copy.deepcopy(payload))
    assert out2["calculation"]["fonte"] == calc["fonte"]
    assert out2.get("warnings", []) == out.get("warnings", [])


def test_06_manifesto_traz_as_folhas_que_dizem_o_que_desenham(tmp_path):
    """Tres aceites da folha (convencao 6): esta certa (test_05), sai no
    manifesto e diz o que desenha (titulo)."""
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    spec = copy.deepcopy(SPEC_EL)
    turnkey = copy.deepcopy(spec["turnkey"])
    turnkey["geometria"] = spec["geometry"]
    loop_spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "adapter": "casa-residencial-eletrica",
        "project": {"slug": "casa-g162", "type": "residencial"},
        "geometria": spec["geometry"],
        "turnkey": turnkey,
        "source_refs": spec["source_refs"],
    }
    manifest = run_project(loop_spec, tmp_path, options={
        "generate_ifc": False, "generate_2d": True,
        "require_source_refs": True})
    desenhos = manifest["deliverables"]["drawings"]
    assert desenhos["status"] == "generated"
    assert "drawings/unifilar.svg" in desenhos["artifacts"]
    assert "drawings/quadro-cargas.svg" in desenhos["artifacts"]
    uni = (tmp_path / "drawings" / "unifilar.svg").read_text(
        encoding="utf-8")
    ET.fromstring(uni)
    assert "DIAGRAMA UNIFILAR" in uni
    assert "WKI-OMBR-MAT-18-0263-INBR-R01" in uni


def test_07_png_olhado_com_demanda_e_recusada(tmp_path):
    """Substring -> parse -> renderizar (convencao 3): as duas folhas
    renderizam em PNG com a fonte legivel; a recusada com o veredito. Os
    PNG ficam em tmp_path para o olho humano (artefato da prova)."""
    try:
        import fitz
    except ImportError:
        import pymupdf as fitz
    import desenho_eletrico_residencial as der

    result_ok, _ = _run_el(_payload_base())
    result_rep, _ = _run_el(_payload_recusa("bifasico"))
    der.gerar_desenhos_residenciais(result_ok, tmp_path / "ok")
    der.gerar_desenhos_residenciais(result_rep, tmp_path / "rep")
    folhas = {
        "unifilar-com-demanda": (tmp_path / "ok" / "unifilar.svg"),
        "unifilar-demanda-recusada": (tmp_path / "rep" / "unifilar.svg"),
    }
    lados = []
    for nome, base in folhas.items():
        svg = base.read_text(encoding="utf-8")
        try:
            doc = fitz.open(str(base))
            pix = doc[0].get_pixmap(dpi=80)
            png = tmp_path / (nome + ".png")
            pix.save(str(png))
            if png.stat().st_size < 2000:
                lados.append("%s: png vazio (%d bytes)"
                             % (nome, png.stat().st_size))
        except Exception as exc:  # noqa: BLE001
            lados.append("%s: nao renderiza em PNG: %r" % (nome, exc))
            continue
        if "WKI-OMBR-MAT-18-0263-INBR-R01" not in svg:
            lados.append("%s: sem a fonte no SVG" % nome)
        if "recusada" in nome and "VEREDITO: REPROVADO" not in svg:
            lados.append("%s: recusada sem o veredito" % nome)
        if nome.endswith("-com-demanda") and "VEREDITO" in svg:
            lados.append("%s: ATENDE com VEREDITO" % nome)
    assert not lados, "png G162 reprova:\n" + "\n".join(lados)
