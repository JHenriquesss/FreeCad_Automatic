"""G93 - o galpao deixa de contar folhas e passa a nomear codigos.

Medido: `entregaveis_projeto.pacote_no_manifesto` confrontava numero contra
numero (desenhos a mais, de qualquer nome, fechavam a conta sem que um unico
codigo do indice tivesse sido conferido). O galpao era a unica tipologia sem
mapa codigo->arquivo.

Entregue:
  1. `_PRANCHA_ARQUIVO_GALPAO` (galpao_adapter): os 35 codigos que o turnkey
     promete (G137: 19 + 14 do aco; G139: + PE-CD-02 para a segunda folha
     da coordenacao; G141: + PE-MZ-01 para o mezanino calculado;
     concreto/mezanino/aco/eletrico/hidraulica/
     incendio/climatizacao + coordenacao) -> PDF em drawings/, medido pagina
     a pagina nos gerar_executivo_* (nao suposto; PE-MZ-01 declarada sem
     emissor, sempre pulada com motivo);
  2. o laco da lente do G91 em `galpao_adapter._emit_drawings`, com os
     pulados nomeados um por um;
  3. a conta de `pacote_no_manifesto` continua no .md como informacao ao
     leitor, mas o portao e o laco.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em diretorio temporario (nunca mutando o repo),
parse do XML/manifesto (existencia, nao geometria — o FreeCAD nao roda em
CI), saturacao silenciosa (um por um, nao numero contra numero) e fonte
independente (techdraw_* via AST e `_PRANCHAS`, nunca o proprio mapa).
"""
import ast
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

# Os 35 prometidos (G137: 19 + 14 do aco; G139: + PE-CD-02 para a
# segunda folha da coordenacao; G141: + PE-MZ-01 para o mezanino calculado;
# mesma conta do test_06 do G91, fonte viva).
# PE-ES-01..17 (3 historicos + 12 do D165 + 2 condicionais).
PROMETIDOS_ESPERADOS = (
    ["PE-CO-%02d" % i for i in (1, 2, 3, 4)]
    + ["PE-MZ-01"]
    + ["PE-ES-%02d" % i for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
                                  13, 14, 15, 16, 17)]
    + ["PE-EL-%02d" % i for i in (1, 2, 3, 4)]
    + ["PE-HI-%02d" % i for i in (1, 2, 3)]
    + ["PE-IN-%02d" % i for i in (1, 2, 3)]
    + ["PE-CL-01", "PE-CD-01", "PE-CD-02"])

# Sem emissor ligado: entrada declarada, sempre pulada com motivo.
# G138: PE-IN-02 ganha emissor (desenho_incendio adaptado do calculo).
# G140: PE-CO-04 ganha emissor (desenho_fundacao_edificio adaptado do
# calculo do galpao, sem redimensionar).
# G141: PE-MZ-01 segue sem emissor (mezanino calculado, sem prancha
# dedicada - ausencia declarada por codigo).
DECLARADOS_SEM_EMISSOR = {"PE-IN-03", "PE-MZ-01"}

# Motivo sem o dado nomeado e silencio, nao triagem (mesmo molde do G92).
AUSENCIA_NOMEADA = ("nao declarado", "nao declarada", "nao calculada",
                    "sem emissor", "nao gravou", "not_available")

GENERicos = {"nao disponivel", "não disponível", "not available",
             "not_available", "indisponivel", "indisponível", "n/a",
             "sem dados", "ausente", "nao emitido", "nao emitida"}


def _norm(texto):
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", str(texto or ""))
        if not unicodedata.combining(c))
    return " ".join(sem_acento.replace("_", " ").strip().casefold().split())


def _prometidos_vivos():
    import galpao_turnkey as tk
    import pacote_legal as pl

    discos = [d for d in tk.DISCIPLINAS if d in pl._PRANCHAS]
    return sorted([f["codigo"] for f in pl.indice_de_pranchas(
        discos + ["coordenacao"])] + [pl.PE_CD_02_GALPAO["codigo"]])


def _paginas_techdraw():
    """Nomes de pagina que os emissores realmente criam (AST, sem FreeCAD).

    G137: as 5 paginas de ligacao/detalhe variavel (PE10_DET_CUMEEIRA,
    PE11_DET_GUSSET_COB, PE12_DET_GUSSET_PAR, PE13_DET_CLIPE_GIRT,
    PE14_DET_CONSOLE) nao tem literal em `_nova_prancha` (page_name
    variavel em `_pr_ligacoes`) — o nome valido vem de
    `techdraw_exec.LIGACOES` (fonte viva, mesma do harness G105), nunca
    suposto.
    """
    arquivos = ("techdraw_concreto.py", "techdraw_exec.py",
                "techdraw_eletrico.py", "techdraw_hidraulica.py",
                "techdraw_incendio.py", "techdraw_climatizacao.py",
                "techdraw_coordenacao.py")
    paginas = set()
    for nome in arquivos:
        arvore = ast.parse(open(os.path.join(GALPAO, nome),
                                encoding="utf-8").read())
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call):
                continue
            fn = no.func
            if getattr(fn, "id", "") != "_nova_prancha" or len(no.args) < 2:
                continue
            segundo = no.args[1]
            if isinstance(segundo, ast.Constant) and segundo.value:
                paginas.add(segundo.value)
    # Paginas variaveis das ligacoes (1:1 com o mapa PE-ES-10..13,16).
    try:
        import techdraw_exec as _td

        for i, (_pref, _tit, _base, _kw, _el, _ch, _ca, _sn) in enumerate(
                _td.LIGACOES):
            paginas.add("PE%02d_DET_%s" % (10 + i, _base))
    except Exception:
        pass
    return paginas


def test_01_mapa_cobre_os_19_prometidos_caso_bom_verde():
    """O mapa fecha os 35 prometidos quando o disco tem tudo (G137: 19+14;
    G139: +PE-CD-02; G141: +PE-MZ-01)."""
    import galpao_adapter as ga
    import varredura_indice_disco as lente

    prometidos = _prometidos_vivos()
    gaps = []
    if prometidos != sorted(PROMETIDOS_ESPERADOS):
        gaps.append("prometidos vivos mudaram: %r" % (prometidos,))
    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    if sorted(mapa) != sorted(PROMETIDOS_ESPERADOS):
        gaps.append("mapa != 35 prometidos: sobrando=%r sem_mapa=%r" % (
            sorted(set(mapa) - set(PROMETIDOS_ESPERADOS)),
            sorted(set(PROMETIDOS_ESPERADOS) - set(mapa))))
    disco = sorted(set(mapa.values()))
    res = lente.conferir_indice_disco(prometidos, mapa, disco, {})
    if not res["OK"]:
        gaps.append("caso bom devia fechar 35/35: %r" % (res,))
    assert not gaps, (
        "G93 mapa:\n%s" % "\n".join("  - " + g for g in gaps))


def test_02_hidraulica_n_1_reusa_o_contrato_g82(tmp_path):
    """Um arquivo cobre PE-HI-01/02/03 sem virar faltando nem sobrando."""
    import desenho_hidraulica as dh
    import galpao_adapter as ga
    import varredura_indice_disco as lente

    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    gaps = []
    if set(mapa) & {"PE-HI-01", "PE-HI-02", "PE-HI-03"} != set(
            dh.COBERTURA_GALPAO):
        gaps.append("chaves HI do mapa divergem do contrato G82: %r vs %r"
                    % (sorted(k for k in mapa if k.startswith("PE-HI-")),
                       sorted(dh.COBERTURA_GALPAO)))
    valores = {mapa[c] for c in ("PE-HI-01", "PE-HI-02", "PE-HI-03")}
    if len(valores) != 1:
        gaps.append("HI devia apontar para UM arquivo (N:1): %r" % (valores,))
    prom = ["PE-HI-01", "PE-HI-02", "PE-HI-03"]
    sub = {c: mapa[c] for c in prom}
    cheio = lente.conferir_indice_disco(prom, sub, ["HID01_ESQUEMA.pdf"], {})
    if not cheio["OK"]:
        gaps.append("com o esquema no disco os 3 deviam cobrir: %r" % (cheio,))
    vazio = lente.conferir_indice_disco(prom, sub, [], {})
    if vazio["OK"] or vazio["faltando"] != prom:
        gaps.append("sem o esquema os 3 deviam faltar: %r" % (vazio,))
    assert tmp_path.is_dir()
    assert not gaps, (
        "G93 N:1:\n%s" % "\n".join("  - " + g for g in gaps))


def test_03_mapa_medido_nos_emissores_nao_suposto():
    """Cada entrada com emissor e pagina TechDraw real (+ .pdf).

    Fonte independente (convencao 5): os nomes de pagina vao do AST dos
    techdraw_*, nunca do proprio mapa. As 3 declaradas sem emissor tem de
    NAO estar entre as paginas — sao ausencia declarada, nao cobertura.
    """
    import galpao_adapter as ga

    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    paginas = _paginas_techdraw()
    gaps = []
    if not paginas:
        gaps.append("nenhuma pagina TechDraw encontrada via AST")
    for codigo, arquivo in sorted(mapa.items()):
        if codigo in DECLARADOS_SEM_EMISSOR:
            if arquivo[:-4] in paginas:
                gaps.append("%s declarado sem emissor mas %r e pagina real"
                            % (codigo, arquivo))
            continue
        if not arquivo.endswith(".pdf"):
            gaps.append("%s sem sufixo .pdf: %r" % (codigo, arquivo))
        elif arquivo[:-4] not in paginas:
            gaps.append("%s aponta para %r, que nenhum emissor cria"
                        % (codigo, arquivo))
    assert not gaps, (
        "G93 medida:\n%s" % "\n".join("  - " + g for g in gaps))


def test_04_nenhum_motivo_generico():
    """Motivo sem o dado nomeado e silencio, nao triagem."""
    import galpao_adapter as ga
    import pacote_legal as pl

    indice = {f["codigo"]: f["titulo"]
              for f in pl.indice_de_pranchas(
                  ["concreto", "mezanino", "aco", "eletrico", "hidraulica", "incendio",
                   "climatizacao", "coordenacao"])}
    gaps = []
    for codigo in sorted(PROMETIDOS_ESPERADOS):
        motivo = ga._motivo_folha_galpao_nao_emitida(
            codigo, indice.get(codigo, ""))
        texto = _norm(motivo)
        if not texto:
            gaps.append("%s com motivo vazio (silencio)" % codigo)
        elif texto in GENERicos:
            gaps.append("%s com motivo generico %r" % (codigo, motivo))
        elif codigo.lower().replace("_", "-") not in texto:
            gaps.append("%s sem o proprio codigo no motivo: %r"
                        % (codigo, motivo))
        elif not any(m in texto for m in AUSENCIA_NOMEADA):
            gaps.append("%s sem o dado nomeado: %r" % (codigo, motivo))
    assert not gaps, (
        "G93 motivos:\n%s" % "\n".join("  - " + g for g in gaps))


def test_05_vermelho_por_injecao_via_tmp_path(tmp_path):
    """Apagar entrada/motivo/arquivo ou plantar nome morto acusa.

    O defeito mora numa copia em `tmp_path` (convencao 2: o repo vivo
    nunca e mutado). Nos dois sentidos (convencao 1): o caso bom fecha, o
    injetado reprova.
    """
    import galpao_adapter as ga
    import varredura_indice_disco as lente

    prometidos = _prometidos_vivos()
    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    disco = sorted(set(mapa.values()))
    caminho = tmp_path / "mapa_galpao.json"
    caminho.write_text(json.dumps(mapa), encoding="utf-8")
    gaps = []
    bom = lente.conferir_indice_disco(
        prometidos, dict(json.loads(caminho.read_text(encoding="utf-8"))),
        list(disco), {})
    if not bom["OK"]:
        gaps.append("caso bom devia fechar: %r" % (bom,))
    sem_entrada = dict(json.loads(caminho.read_text(encoding="utf-8")))
    del sem_entrada["PE-ES-01"]
    quebrado = lente.conferir_indice_disco(prometidos, sem_entrada,
                                           list(disco), {})
    if quebrado["OK"] or quebrado["sem_mapa"] != ["PE-ES-01"]:
        gaps.append("sem a entrada PE-ES-01 devia acusar sem_mapa: %r"
                    % (quebrado,))
    morto = dict(json.loads(caminho.read_text(encoding="utf-8")))
    morto["PE-XX-99"] = "folha-morta.pdf"
    sobrando = lente.conferir_indice_disco(prometidos, morto, list(disco),
                                           {})
    if sobrando["OK"] or sobrando["sobrando"] != ["PE-XX-99"]:
        gaps.append("nome morto devia acusar sobrando: %r" % (sobrando,))
    furado = [n for n in disco if n != "HID01_ESQUEMA.pdf"]
    sem_pdf = lente.conferir_indice_disco(prometidos, mapa, furado, {})
    if sem_pdf["OK"] or sem_pdf["faltando"] != ["PE-HI-01", "PE-HI-02",
                                                "PE-HI-03"]:
        gaps.append("sem o HID01 os 3 HI deviam faltar: %r" % (sem_pdf,))
    assert not gaps, (
        "G93 injecao:\n%s" % "\n".join("  - " + g for g in gaps))


def _rodada_stub(tmp_path, monkeypatch, executadas, pdfs_por_disco,
                 turnkey_executadas=None):
    """Roda `_emit_drawings` de verdade com o caderno stubado (sem FreeCAD).

    O stub escreve os PDFs nomeados em drawings/ e devolve o status; o
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
                   "project_id": "g93", "adapter": "galpao"}
    opcoes = type("O", (), {"generate_2d": True, "generate_caderno": False,
                            "timeout_seconds": 10, "freecad_exe": None,
                            "folga_mm": 0.0, "vol_min_mm3": 0.0,
                            "executivo_aco": True})()
    turnkey = {"executadas": (executadas if turnkey_executadas is None
                              else turnkey_executadas)}
    ga._emit_drawings(manifesto, str(run_dir), normalizado, opcoes, turnkey)
    return manifesto, str(run_dir)


def test_06_aceite_duplo_na_rodada_stub(tmp_path, monkeypatch):
    """(1) codigo com arquivo mapeado; (2) o arquivo sai e vai ao manifesto.

    Aceite duplo (sexta regra): nao basta o mapa dizer — o PDF tem de
    existir no disco E estar nos artifacts. O que nao sai, sai pulado com
    o motivo, um por um (a lente fecha faltando/sem_mapa).
    """
    import galpao_adapter as ga
    import pacote_legal as pl
    import varredura_indice_disco as lente

    pdfs = ["aco/pranchas/PE04_PORTICO.pdf",
            "aco/pranchas/PE07_DET_JOELHO.pdf",
            "aco/pranchas/PE01_COBERTURA.pdf",
            "hidraulica/pranchas/HID01_ESQUEMA.pdf"]
    manifesto, destino = _rodada_stub(tmp_path, monkeypatch,
                                      ["aco", "hidraulica"], pdfs)
    desenhos = manifesto["deliverables"]["drawings"]
    gaps = []
    if desenhos.get("status") != "generated":
        gaps.append("status devia ser generated: %r" % (desenhos.get("status"),))
    artefatos = list(desenhos.get("artifacts") or [])
    no_disco = {a.split("/")[-1] for a in artefatos}
    for rel in pdfs:
        base = rel.split("/")[-1]
        if base not in no_disco:
            gaps.append("manifesto sem %s" % rel)
        if not os.path.isfile(os.path.join(destino, "drawings", rel)):
            gaps.append("disco sem %s (manifesto mentiria)" % rel)
    for codigo in ("PE-ES-01", "PE-ES-02", "PE-ES-03",
                   "PE-HI-01", "PE-HI-02", "PE-HI-03"):
        esperado = ga._PRANCHA_ARQUIVO_GALPAO[codigo]
        if esperado not in no_disco:
            gaps.append("%s sem arquivo mapeado no disco" % codigo)
    pulados = list(desenhos.get("skipped") or [])
    por_prancha = {}
    for item in pulados:
        por_prancha.setdefault(item.get("prancha"), []).append(
            item.get("motivo", ""))
    if "COORD01_PLANTA.pdf" not in por_prancha:
        gaps.append("PE-CD-01 devia sair pulada nomeada: %r" % (pulados,))
    if "COORD02_CLASH.pdf" not in por_prancha:
        gaps.append("PE-CD-02 devia sair pulada nomeada: %r" % (pulados,))
    for nome, motivos in sorted(por_prancha.items()):
        for motivo in motivos:
            if not any(m in _norm(motivo) for m in AUSENCIA_NOMEADA):
                gaps.append("%s sem o dado nomeado: %r" % (nome, motivo))
    prometidos = sorted(
        f["codigo"] for f in ga._indice_galpao_com_fronteira(
            ["aco", "hidraulica"], {})[0])
    res = lente.conferir_indice_disco(prometidos, ga._PRANCHA_ARQUIVO_GALPAO,
                                      artefatos, pulados)
    if res["faltando"] or res["sem_mapa"]:
        gaps.append("lente G91 acusa na rodada: %r" % (res,))
    assert not gaps, (
        "G93 rodada:\n%s" % "\n".join("  - " + g for g in gaps))


def test_07_laco_quebrado_e_nomeado_nao_cai_em_silencio(tmp_path, monkeypatch):
    """Se a propria conferencia falha, o manifesto diz — com o erro nomeado."""
    manifesto, _destino = _rodada_stub(
        tmp_path, monkeypatch, ["aco"], ["aco/pranchas/PE04_PORTICO.pdf"],
        turnkey_executadas=123)
    pulados = list(manifesto["deliverables"]["drawings"].get("skipped") or [])
    assert [p.get("prancha") for p in pulados] == ["(indice)"], pulados
    assert "TypeError" in pulados[0].get("motivo", ""), pulados
