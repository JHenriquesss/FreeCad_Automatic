"""G107: o galpao emite as pranchas de esquema puro sem freecad.exe.

Medido (G106): `galpao_adapter._emit_drawings` voltava com
`not_available: freecad.exe nao encontrado` ANTES de qualquer disciplina,
e hidraulica/incendio/climatizacao nao precisam do executavel desde o
G104 (`montar_pranchas(..., backend="svg")` e o default).

Entregue (`galpao_adapter._emit_drawings`): sem freecad.exe o deliverable
`drawings` emite as tres de esquema pela rota SVG e declara por codigo o
que precisa do executavel (aco/concreto/eletrico/coordenacao), cada um
com a causa proxima `freecad.exe nao encontrado` nomeada. O status diz
que e parcial (`partial`), nunca `generated` com metade faltando.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em diretorio temporario (nunca mutando o repo),
parse do manifesto (existencia, nao geometria), saturacao silenciosa (um
por um, nao numero contra numero) e fonte independente (o spec
persistido `projects/galpao-tp-g95/project-spec.json`, nao o resultado).
Os testes que chamam `conferir_indice_disco` seguem a receita do G97
(lados coletados, um assert so).
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(GALPAO))

from test_indice_disco_rodada_g102 import ISENCOES_EXTRA

EXECUTADAS_CHEIAS = ["concreto", "aco", "eletrico", "incendio",
                     "climatizacao", "hidraulica"]

FOLHAS_ESQUEMA = ["HID01_ESQUEMA.pdf", "HID02_QUADRO.pdf",
                  "INC01_PLANTA.pdf", "INC02_RESUMO.pdf",
                  # G138: PE-IN-02 sai da rota SVG (detalhes adaptados do
                  # calculo, sem freecad).
                  "INC03_DETALHES.pdf",
                  "CLI01_ESQUEMA.pdf", "CLI02_QUADRO.pdf"]

CODIGOS_FREECAD = ["PE-CO-01", "PE-CO-02", "PE-CO-03", "PE-CO-04",
                   "PE-ES-01", "PE-ES-02", "PE-ES-03",
                   "PE-EL-01", "PE-EL-02", "PE-EL-03", "PE-EL-04",
                   "PE-CD-01", "PE-CD-02"]


def _turnkey_fatiado():
    """Sub-specs de esquema do spec persistido (fonte independente).

    O calculo das tres cabe em segundos; o turnkey_result da rodada usa
    as executadas cheias (o que o loop entrega numa rodada cheia do
    galpao-tp-g95), para que o laco prometa tambem os codigos que so o
    executavel emite.
    """
    with open(os.path.join(REPO, "projects", "galpao-tp-g95",
                           "project-spec.json"), encoding="utf-8") as fh:
        raw = json.load(fh)
    turnkey = raw["turnkey"]
    return {"slug": "g107", "geometria": copy.deepcopy(turnkey["geometria"]),
            "hidraulica": copy.deepcopy(turnkey["hidraulica"]),
            "incendio": copy.deepcopy(turnkey["incendio"]),
            "climatizacao": copy.deepcopy(turnkey["climatizacao"])}


def _emitir(tmp_path, monkeypatch, desliga_svg=False):
    """Roda `_emit_drawings` de verdade sem freecad.exe, em tmp_path.

    Com desliga_svg=True a rota SVG-direta do G104 e injetada para
    falhar (prova o vermelho): os codigos de esquema voltam a faltar no
    disco e o deliverable vira `failed` sem artefatos.
    """
    import galpao_adapter as ga

    if desliga_svg:
        import prancha_svg_direta as psd

        def rota_morta(r, out_dir, disciplina, spec=None, dpi=150):
            return {"erro": "rota svg desligada (injecao G107)"}

        monkeypatch.setattr(psd, "montar_pranchas_rota_direta", rota_morta)
    monkeypatch.setattr(ga, "_freecad_executable",
                        lambda options: tmp_path / "nao-existe" / "freecad.exe")

    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    manifesto = {"artifacts": [], "deliverables": {}}
    normalizado = {"turnkey_spec": _turnkey_fatiado(),
                   "requested_disciplines": list(EXECUTADAS_CHEIAS),
                   "project_id": "g107", "adapter": "galpao"}
    opcoes = type("O", (), {"generate_2d": True, "generate_caderno": False,
                            "timeout_seconds": 600, "freecad_exe": None,
                            "folga_mm": 0.0, "vol_min_mm3": 0.0,
                            "executivo_aco": True})()
    ga._emit_drawings(manifesto, str(run_dir), normalizado, opcoes,
                      {"executadas": list(EXECUTADAS_CHEIAS)})
    return manifesto, str(run_dir)


def test_01_sem_exe_parcial_nomeado_e_esquema_no_disco(tmp_path, monkeypatch):
    """Lado bom: status `partial`, 6 folhas de esquema no manifesto e no
    disco, cada codigo de TechDraw pulado com a causa proxima."""
    import galpao_adapter as ga
    import pacote_legal as pl
    import varredura_indice_disco as lente

    manifesto, destino = _emitir(tmp_path, monkeypatch)
    desenhos = manifesto["deliverables"]["drawings"]
    gaps = []
    if desenhos.get("status") != "partial":
        gaps.append("status devia ser partial (nao generated nem "
                    "not_available): %r" % (desenhos.get("status"),))
    artefatos = list(desenhos.get("artifacts") or [])
    no_disco = {a.split("/")[-1] for a in artefatos}
    for folha in FOLHAS_ESQUEMA:
        if folha not in no_disco:
            gaps.append("folha de esquema fora dos artifacts: %s" % folha)
    for folha in FOLHAS_ESQUEMA:
        caminho = os.path.join(destino, "drawings")
        achados = []
        for raiz, _ds, arqs in os.walk(caminho):
            if folha in arqs:
                achados.append(os.path.join(raiz, folha))
        if not achados:
            gaps.append("folha dita emitida sem arquivo: %s" % folha)
        elif not os.path.getsize(achados[0]):
            gaps.append("folha vazia no disco: %s" % folha)
    registrados = {a.get("path") for a in manifesto.get("artifacts") or []}
    for artefato in artefatos:
        if artefato not in registrados:
            gaps.append("fora do manifesto %s" % artefato)
    prometidos = sorted(
        [f["codigo"] for f in pl.indice_de_pranchas(
            list(EXECUTADAS_CHEIAS) + ["coordenacao"])
         if f["codigo"] != "PE-IN-03"]
        + [pl.PE_CD_02_GALPAO["codigo"]])
    dispensadas = list(desenhos.get("dispensadas") or [])
    if [d["codigo"] for d in dispensadas] != ["PE-IN-03"]:
        gaps.append("sem escada no spec, PE-IN-03 devia sair dispensada "
                    "(fronteira G101), nao prometida: %r" % (dispensadas,))
    res = lente.conferir_indice_disco(prometidos, ga._PRANCHA_ARQUIVO_GALPAO,
                                      artefatos,
                                      list(desenhos.get("skipped") or []),
                                      ISENCOES_EXTRA)
    for codigo in ("PE-HI-01", "PE-HI-02", "PE-HI-03", "PE-IN-01",
                   "PE-CL-01"):
        if codigo in res["faltando"]:
            gaps.append("codigo de esquema sem arquivo e sem motivo: %s (%r)"
                        % (codigo, res))
    if res["sem_mapa"] or res["extra_no_disco"]:
        gaps.append("lente acusa sem_mapa/extra: %r" % (res,))
    motivos = {p.get("prancha"): p.get("motivo", "")
               for p in (desenhos.get("skipped") or [])}
    for codigo in CODIGOS_FREECAD:
        arquivo = ga._PRANCHA_ARQUIVO_GALPAO[codigo]
        motivo = motivos.get(arquivo, "")
        if "freecad.exe nao encontrado" not in motivo:
            gaps.append("%s (%s) sem a causa proxima nomeada: %r"
                        % (codigo, arquivo, motivo))
    caderno = [a.get("path") for a in manifesto.get("artifacts") or []
               if (a.get("path") or "").endswith(".pdf")
               and "CADERNO" in (a.get("path") or "")]
    if not caderno or not os.path.isfile(os.path.join(destino, caderno[0])):
        gaps.append("caderno executivo fora do manifesto ou sem arquivo: %r"
                    % (caderno,))
    assert not gaps, (
        "G107 lado bom:\n%s" % "\n".join("  - " + g for g in gaps))


def test_02_injecao_sem_rota_svg_falha_nomeada(tmp_path, monkeypatch):
    """Lado vermelho (tmp_path): sem a rota SVG nada de esquema sai — o
    deliverable vira `failed` sem artefatos, e sem a declaracao os
    codigos voltam a `faltando` na lente (o disco manda, nao o mapa)."""
    import galpao_adapter as ga
    import pacote_legal as pl
    import varredura_indice_disco as lente

    manifesto, destino = _emitir(tmp_path, monkeypatch, desliga_svg=True)
    desenhos = manifesto["deliverables"]["drawings"]
    gaps = []
    if desenhos.get("status") != "failed":
        gaps.append("sem a rota SVG o status devia ser failed: %r"
                    % (desenhos.get("status"),))
    if list(desenhos.get("artifacts") or []):
        gaps.append("sem a rota SVG nao devia haver artefatos: %r"
                    % (desenhos.get("artifacts"),))
    for folha in FOLHAS_ESQUEMA:
        achados = []
        for raiz, _ds, arqs in os.walk(os.path.join(destino, "drawings")):
            if folha in arqs:
                achados.append(folha)
        if achados:
            gaps.append("folha de esquema saiu com a rota desligada: %s"
                        % folha)
    prometidos = sorted(
        [f["codigo"] for f in pl.indice_de_pranchas(
            list(EXECUTADAS_CHEIAS) + ["coordenacao"])
         if f["codigo"] != "PE-IN-03"]
        + [pl.PE_CD_02_GALPAO["codigo"]])
    sem_declaracao = lente.conferir_indice_disco(
        prometidos, ga._PRANCHA_ARQUIVO_GALPAO, [], {})
    if "PE-HI-01" not in sem_declaracao["faltando"] \
            or "PE-IN-01" not in sem_declaracao["faltando"] \
            or "PE-CL-01" not in sem_declaracao["faltando"]:
        gaps.append("sem declarar, o esquema devia faltar: %r"
                    % (sem_declaracao,))
    com_declaracao = lente.conferir_indice_disco(
        prometidos, ga._PRANCHA_ARQUIVO_GALPAO, [],
        list(desenhos.get("skipped") or []))
    for codigo in ("PE-HI-01", "PE-IN-01", "PE-CL-01"):
        if codigo in com_declaracao["faltando"]:
            gaps.append("codigo de esquema sem motivo mesmo pulado: %s (%r)"
                        % (codigo, com_declaracao))
    assert not gaps, (
        "G107 lado vermelho:\n%s" % "\n".join("  - " + g for g in gaps))
