"""G101 - o galpao: escada de emergencia e detalhes de hidrantes, ou a
fronteira escrita.

Medido (fonte independente, nao o proprio laco):
  1. `desenho_escada_edificio.planta_escada_svg({}, None)` levanta
     ValueError ("sem 'geometria'..."): o emissor G81 exige o shape de
     `escada_concreto.dimensiona` + gates de `incendio_edificio`
     (Tab.10/11). Reuso direto no galpao falha.
  2. `galpao_seguranca_incendio.rodar` minimo devolve gates sem nada de
     escada; `projeto_spec` traz `"escada": None` por default. Sem objeto
     escada nao ha o que desenhar.
  3. O dado do corte de hidrante (PE-IN-02) nao existe no `rodar()` do
     galpao: sem DN de coluna/rede, sem tracado vertical, sem pavimentos
     (o corte DN65 so existe em
     `desenho_incendio.detalhes_hidrantes_rotas_svg`, shape do predio).
     Desenha-lo seria inventar dado: PE-IN-02 segue declarado ausente.

Entregue (caminho (b), escrito): sem escada declarada no spec, a
disciplina incendio deixa de prometer PE-IN-03
(`_indice_galpao_com_fronteira`): o codigo sai da promessa com motivo
`not_applicable` escrito e vai para `dispensadas` no manifesto — nao
prometido, nao "faltando". Com escada declarada, segue prometido (e,
sem emissor, sai pulado com o motivo — ausencia declarada, nao
silencio).

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em diretorio temporario (nunca mutando o repo),
fonte independente (o emissor e o vertical, nunca o proprio helper) e
sem valor normativo arbitrado.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)


def _sem_escada():
    return {"raw_spec": {}, "turnkey_spec": {}}


def _com_escada():
    escada = {"desnivel": 3.0, "projecao": 4.5, "largura": 1.2}
    return {"raw_spec": {"escada": dict(escada)},
            "turnkey_spec": {"escada": dict(escada)}}


def test_01_medido_emissor_g81_exige_objeto_escada():
    """Fonte independente 1: sem geometria nao ha folha (prova do shape)."""
    import desenho_escada_edificio as dee

    try:
        dee.planta_escada_svg({}, None)
    except ValueError as exc:
        assert "geometria" in str(exc), exc
    else:
        raise AssertionError(
            "G101: emissor G81 devia recusar escada sem geometria")


def test_02_medido_vertical_galpao_nao_tem_gates_de_escada():
    """Fonte independente 2: o vertical do galpao nao calcula escada."""
    import galpao_seguranca_incendio as gsi

    res = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}})
    gates = res.get("gates") or {}
    com_escada = [k for k in gates if "escada" in k.lower()]
    assert not com_escada, (
        "G101: vertical do galpao nao devia ter gates de escada: %r"
        % (com_escada,))


def test_03_sem_escada_pe_in_03_sai_da_promessa_com_motivo():
    """Baseline, sentido dispensa: sem objeto, nao prometido + escrito."""
    import galpao_adapter as ga

    indice, dispensadas = ga._indice_galpao_com_fronteira(
        ["incendio"], _sem_escada())
    codigos = [f["codigo"] for f in indice]
    gaps = []
    if "PE-IN-03" in codigos:
        gaps.append("PE-IN-03 devia sair da promessa sem escada: %r"
                    % (codigos,))
    if "PE-IN-01" not in codigos or "PE-IN-02" not in codigos:
        gaps.append("PE-IN-01/02 deviam seguir prometidos: %r" % (codigos,))
    if [d["codigo"] for d in dispensadas] != ["PE-IN-03"]:
        gaps.append("dispensadas devia ter so PE-IN-03: %r" % (dispensadas,))
    for disp in dispensadas:
        motivo = disp.get("motivo", "")
        if not motivo.startswith("not_applicable:"):
            gaps.append("dispensa sem status not_applicable: %r" % (motivo,))
        if "PE-IN-03" not in motivo or "escada" not in motivo.lower():
            gaps.append("dispensa sem codigo/dado nomeado: %r" % (motivo,))
        if "nao declarado" not in motivo.lower():
            gaps.append("dispensa sem o dado nomeado: %r" % (motivo,))
    assert not gaps, (
        "G101 fronteira:\n%s" % "\n".join("  - " + g for g in gaps))


def test_04_com_escada_pe_in_03_segue_prometido():
    """Baseline, sentido promessa: com objeto, o codigo morde de novo."""
    import galpao_adapter as ga

    for norm in (_com_escada(),
                 {"raw_spec": {}, "turnkey_spec": _com_escada()["turnkey_spec"]}):
        indice, dispensadas = ga._indice_galpao_com_fronteira(
            ["incendio"], norm)
        codigos = [f["codigo"] for f in indice]
        assert "PE-IN-03" in codigos, (
            "G101: com escada declarada PE-IN-03 devia seguir prometido: "
            "%r (%r)" % (codigos, norm))
        assert dispensadas == [], (
            "G101: com escada declarada nada a dispensar: %r" % (dispensadas,))


def _rodada_stub(tmp_path, monkeypatch, executadas, pdfs_por_disco,
                 normalizado_extra=None):
    """Roda `_emit_drawings` de verdade com o caderno stubado (sem FreeCAD).

    Mesmo molde do G93: o stub escreve os PDFs nomeados em drawings/ e o
    registro em arvore, o laco indice<->disco e o manifesto sao os reais.
    """
    from pathlib import Path

    import caderno_turnkey as ct
    import galpao_adapter as ga

    def falso_montar_caderno(spec, out_dir, disciplinas=None,
                             freecad_exe=None, timeout=1200, R=None,
                             turnkey_result=None, **_kw):
        for rel in pdfs_por_disco:
            p = Path(out_dir) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("folha " + rel, encoding="utf-8")
        return {"path": None, "disciplinas": list(executadas),
                "status": {d: {"ok": True} for d in executadas}}

    monkeypatch.setattr(ct, "montar_caderno", falso_montar_caderno)
    falso_exe = tmp_path / "freecad.exe"
    falso_exe.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(ga, "_freecad_executable", lambda options: falso_exe)

    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    manifesto = {"artifacts": [], "deliverables": {}}
    normalizado = {"turnkey_spec": {}, "requested_disciplines": list(executadas),
                   "project_id": "g101", "adapter": "galpao"}
    normalizado.update(normalizado_extra or {})
    opcoes = type("O", (), {"generate_2d": True, "generate_caderno": False,
                            "timeout_seconds": 10, "freecad_exe": None,
                            "folga_mm": 0.0, "vol_min_mm3": 0.0,
                            "executivo_aco": True})()
    turnkey = {"executadas": list(executadas)}
    ga._emit_drawings(manifesto, str(run_dir), normalizado, opcoes, turnkey)
    return manifesto, str(run_dir)


def test_05_rodada_sem_escada_dispensa_escrita_e_nao_falta(
        tmp_path, monkeypatch):
    """Aceite G101: o portao reflete a escolha (dispensada, nao faltando)."""
    import galpao_adapter as ga
    import pacote_legal as pl
    import varredura_indice_disco as lente

    manifesto, _destino = _rodada_stub(
        tmp_path, monkeypatch, ["incendio"],
        ["incendio/pranchas/INC01_PLANTA.pdf"], {"raw_spec": {}})
    desenhos = manifesto["deliverables"]["drawings"]
    gaps = []
    dispensadas = list(desenhos.get("dispensadas") or [])
    if [d["codigo"] for d in dispensadas] != ["PE-IN-03"]:
        gaps.append("manifesto devia dispensar PE-IN-03: %r" % (dispensadas,))
    pulados = list(desenhos.get("skipped") or [])
    pranchas = [p.get("prancha") for p in pulados]
    if "INC04_ESCADA.pdf" in pranchas:
        gaps.append("PE-IN-03 dispensada nao devia sair pulada: %r" % (pulados,))
    if "INC03_DETALHES.pdf" not in pranchas:
        gaps.append("PE-IN-02 devia sair pulada nomeada: %r" % (pulados,))
    for item in pulados:
        if "nao declarado" not in (item.get("motivo", "") or "").lower() \
                and "not_available" not in (item.get("motivo", "") or ""):
            gaps.append("pulado sem o dado nomeado: %r" % (item,))
    artefatos = list(desenhos.get("artifacts") or [])
    prometidos = sorted(
        f["codigo"] for f in pl.indice_de_pranchas(["incendio", "coordenacao"])
        if f["codigo"] != "PE-IN-03")
    res = lente.conferir_indice_disco(prometidos, ga._PRANCHA_ARQUIVO_GALPAO,
                                      artefatos, pulados)
    if res["faltando"] or res["sem_mapa"]:
        gaps.append("lente G91 acusa na rodada G101: %r" % (res,))
    assert not gaps, (
        "G101 rodada:\n%s" % "\n".join("  - " + g for g in gaps))


def test_06_rodada_com_escada_promete_e_pula_nomeado(tmp_path, monkeypatch):
    """Sentido promessa na rodada: com objeto, sem arquivo, sai nomeado."""
    manifesto, _destino = _rodada_stub(
        tmp_path, monkeypatch, ["incendio"],
        ["incendio/pranchas/INC01_PLANTA.pdf"],
        {"raw_spec": {"escada": {"desnivel": 3.0, "projecao": 4.5,
                                 "largura": 1.2}}})
    desenhos = manifesto["deliverables"]["drawings"]
    gaps = []
    if list(desenhos.get("dispensadas") or []):
        gaps.append("com escada nada a dispensar: %r"
                    % (desenhos.get("dispensadas"),))
    pranchas = [p.get("prancha")
                for p in (desenhos.get("skipped") or [])]
    if "INC04_ESCADA.pdf" not in pranchas:
        gaps.append("PE-IN-03 prometida sem arquivo devia sair pulada: %r"
                    % (pranchas,))
    assert not gaps, (
        "G101 promessa:\n%s" % "\n".join("  - " + g for g in gaps))


def test_07_vermelho_por_injecao_via_tmp_path(tmp_path):
    """O defeito mora numa copia em `tmp_path`: o repo vivo nunca e mutado.

    Nos dois sentidos: o caso bom fecha, o injetado reprova — inclusive o
    lado da folha no disco (PE-IN-03 com arquivo sai OK quando prometida).
    """
    import json

    import galpao_adapter as ga
    import varredura_indice_disco as lente

    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    caminho = tmp_path / "mapa_galpao.json"
    caminho.write_text(json.dumps(mapa), encoding="utf-8")
    gaps = []
    copia = dict(json.loads(caminho.read_text(encoding="utf-8")))
    disco_cheio = sorted(set(copia.values()))
    bom = lente.conferir_indice_disco(sorted(copia), copia, disco_cheio, {})
    if not bom["OK"]:
        gaps.append("caso bom devia fechar: %r" % (bom,))
    sem_entrada = dict(json.loads(caminho.read_text(encoding="utf-8")))
    del sem_entrada["PE-IN-02"]
    quebrado = lente.conferir_indice_disco(sorted(mapa), sem_entrada,
                                           list(disco_cheio), {})
    if quebrado["OK"] or quebrado["sem_mapa"] != ["PE-IN-02"]:
        gaps.append("sem a entrada PE-IN-02 devia acusar sem_mapa: %r"
                    % (quebrado,))
    morto = dict(json.loads(caminho.read_text(encoding="utf-8")))
    morto["PE-XX-99"] = "folha-morta.pdf"
    sobrando = lente.conferir_indice_disco(sorted(mapa), morto,
                                           list(disco_cheio), {})
    if sobrando["OK"] or sobrando["sobrando"] != ["PE-XX-99"]:
        gaps.append("nome morto devia acusar sobrando: %r" % (sobrando,))
    furado = [n for n in disco_cheio if n != "INC03_DETALHES.pdf"]
    sem_pdf = lente.conferir_indice_disco(sorted(mapa), mapa, furado, {})
    if sem_pdf["OK"] or "PE-IN-02" not in sem_pdf["faltando"]:
        gaps.append("sem o INC03 PE-IN-02 devia faltar: %r" % (sem_pdf,))
    assert tmp_path.is_dir()
    assert not gaps, (
        "G101 injecao:\n%s" % "\n".join("  - " + g for g in gaps))
