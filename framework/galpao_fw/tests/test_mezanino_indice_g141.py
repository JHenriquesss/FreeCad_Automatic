"""G141 - O mezanino calculado que evapora do indice.

Medido (2026-09-14, antes de mudar):
- `galpao_turnkey.DISCIPLINAS` inclui `mezanino` (despachado por
  `_run_mezanino`, levado ao BIM); `pacote_legal._PRANCHAS` nao tem a
  disciplina, entao ela e executada e some no `continue` do indice (D89
  do lado da promessa, D121). Travado por assert em
  `tests/test_indice_disco_g91.py:304-305`, nao consertado.
- Nenhum `projects/*/project-spec.json` declara mezanino (0 ocorrencias):
  nao ha rodada real no repo que exercite o caminho. Remeça no test_01.

Entregue:
- `pacote_legal._PRANCHAS["mezanino"]` = ("PE-MZ", ["Mezanino de concreto
  (laje/vigas/pilares)"]) + entrada em `_ORDEM_DISC` (apos o concreto) e
  no grupo de LOD da estrutura; sem mezanino executado o indice/pacote
  saem byte-identicos (a disciplina so entra quando executada).
- `galpao_adapter._PRANCHA_ARQUIVO_GALPAO["PE-MZ-01"]` = "MZ01_MEZANINO.pdf"
  + motivo nomeado em `_motivo_folha_galpao_nao_emitida` (sem emissor
  TechDraw ligado; o dimensionamento sai no memorial/BIM com membros M-).
- `caderno_turnkey`: ROTULO/ORDEM com mezanino + dispatch declarado
  (ok None com MOTIVO_MEZANINO_SEM_PRANCHA, nunca erro).
- `varredura_disciplina_prancha.ISENCOES_DISCIPLINA_PRANCHA` vazia (a cura
  matou a isencao); o assert do G91 vira o portao do comportamento novo.
- Novo `tests/test_mezanino_indice_g141.py` (5): remeça, rodada com
  mezanino (indice x disco fecha via pulada nomeada), sem mezanino
  byte-identico, vermelho por injecao nos dois sentidos, calculo intacto.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em tmp_path (nunca mutando o repo), substring ->
parse -> renderizar (existencia, nao geometria - sem FreeCAD em CI),
fonte independente (o turnkey + o calculo, nunca o proprio mapa) e sem
valor normativo arbitrado. O spec de teste mora em tmp_path/fixture,
nunca num project-spec do repo (regra do goal).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

REPO = os.path.dirname(os.path.dirname(GALPAO))


def _spec_com_mezanino():
    """Spec minimo que exercita o caminho: galpao 40x20x6 + mezanino 6x5
    a 3 m (amostra que ATENDE no test_mezanino.py)."""
    return {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "concreto": {"vao": 10.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                      "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                      "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
                      "sigma_solo_adm": 250.0,
                      "travamento_longitudinal": "topo"},
        "mezanino": {"x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
                     "q_uso": 2.0},
    }


def test_01_medido_turnkey_executa_indice_nao_prometia_sem_spec_no_repo():
    """Remeça: o que o turnkey executa, o que o indice promete e o que o
    repo declara (fonte viva, nunca o proprio mapa)."""
    import glob

    import galpao_turnkey as tk
    import pacote_legal as pl

    gaps = []
    if "mezanino" not in tk.DISCIPLINAS:
        gaps.append("turnkey devia executar mezanino: %r" % (tk.DISCIPLINAS,))
    if "mezanino" not in pl._PRANCHAS:
        gaps.append("G141: _PRANCHAS devia ter mezanino (PE-MZ-01)")
    else:
        pref, titulos = pl._PRANCHAS["mezanino"]
        if pref != "PE-MZ" or len(titulos) != 1:
            gaps.append("entrada do mezanino fora do contrato: %r" % (
                pl._PRANCHAS["mezanino"],))
        if "mezanino" not in pl._ORDEM_DISC:
            gaps.append("_ORDEM_DISC sem mezanino: %r" % (pl._ORDEM_DISC,))
    # nenhum project-spec do repo declara mezanino (regra do goal: o spec
    # de teste mora em tmp_path, nunca no repo)
    specs = glob.glob(os.path.join(REPO, "projects", "*",
                                   "project-spec.json"))
    if not specs:
        gaps.append("nenhum project-spec encontrado em projects/")
    for caminho in specs:
        with open(caminho, encoding="utf-8") as fh:
            if "mezanino" in fh.read():
                gaps.append("%s declara mezanino (nao devia)" % caminho)
    # o calculo existe e ATENDE na amostra (fonte viva: o vertical)
    import galpao_mezanino as gmz

    r = gmz.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0,
                                 "pe_direito": 6.0},
                   "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
                   "q_uso": 2.0})
    if not r.get("ATENDE"):
        gaps.append("amostra do mezanino devia ATENDER: %r" % (r.get("reprovados"),))
    assert not gaps, "G141 medida:\n%s" % "\n".join("  - " + g for g in gaps)


def test_02_com_mezanino_indice_x_disco_fecha_no_pacote(tmp_path):
    """Rodada com mezanino: o codigo entra no indice e no pacote, e o laco
    fecha (pulada nomeada, sem emissor). O spec mora em tmp_path."""
    import galpao_adapter as ga
    import galpao_turnkey as tk
    import pacote_legal as pl
    import varredura_indice_disco as lente

    caminho = tmp_path / "spec_mezanino.json"
    caminho.write_text(json.dumps(_spec_com_mezanino()), encoding="utf-8")
    spec = json.loads(caminho.read_text(encoding="utf-8"))
    R = tk.rodar(spec)
    gaps = []
    if "mezanino" not in R.get("executadas", []):
        gaps.append("turnkey devia executar mezanino: %r" % (R.get("executadas"),))
    # indice da rodada (a mesma fonte do hook: executadas + coordenacao)
    indice, _disp = ga._indice_galpao_com_fronteira(
        list(R["executadas"]), {})
    codigos = sorted(f["codigo"] for f in indice)
    if "PE-MZ-01" not in codigos:
        gaps.append("indice da rodada sem PE-MZ-01: %r" % (codigos,))
    # pacote da rodada (a mesma fonte do emitir_pacote_legal: executadas)
    pac = pl.gerar_pacote(list(R["executadas"]))
    pac_cods = sorted(p["codigo"] for p in pac["indice_pranchas"]
                      if p["disciplina"] == "mezanino")
    if pac_cods != ["PE-MZ-01"]:
        gaps.append("pacote sem PE-MZ-01 do mezanino: %r" % (pac_cods,))
    # laco indice<->disco: sem o PDF no disco, a PE-MZ-01 sai pulada com
    # motivo (ausencia declarada), nunca faltando/sem_mapa
    disco = []  # nada emitido neste teste puro (sem FreeCAD)
    puladas = ga._conferir_indice_galpao(
        indice, ga._PRANCHA_ARQUIVO_GALPAO, disco)
    por_prancha = {p["prancha"]: p["motivo"] for p in puladas}
    motivo = por_prancha.get("MZ01_MEZANINO.pdf", "")
    if "PE-MZ-01" not in motivo or "MZ01_MEZANINO.pdf" not in motivo:
        gaps.append("PE-MZ-01 sem motivo nomeado: %r" % (puladas,))
    res = lente.conferir_indice_disco(codigos, ga._PRANCHA_ARQUIVO_GALPAO,
                                      disco, puladas)
    if res["sem_mapa"] or res["faltando"]:
        gaps.append("lente acusa com a pulada nomeada: %r" % (res,))
    # o BIM federa o mezanino (membros M-) - o calculo chega a entrega
    membros, disc = tk._membros_federados(R, spec)
    if "mezanino" not in disc:
        gaps.append("federado sem mezanino: %r" % (disc,))
    if not any(str(m.get("marca", "")).startswith("M-") for m in membros):
        gaps.append("sem membro M- no federado")
    assert tmp_path.is_dir()
    assert not gaps, "G141 rodada com mezanino:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_03_sem_mezanino_byte_identico(tmp_path):
    """Sem mezanino, byte-identico: o indice e o pacote nao citam o
    mezanino e o calculo das outras disciplinas nao muda."""
    import galpao_turnkey as tk
    import pacote_legal as pl

    spec = _spec_com_mezanino()
    sem = {k: v for k, v in spec.items() if k != "mezanino"}
    caminho = tmp_path / "spec_sem_mezanino.json"
    caminho.write_text(json.dumps(sem), encoding="utf-8")
    sem = json.loads(caminho.read_text(encoding="utf-8"))
    R_sem = tk.rodar(sem)
    R_com = tk.rodar(_spec_com_mezanino())
    gaps = []
    if "mezanino" in R_sem.get("executadas", []):
        gaps.append("sem mezanino no spec, nada a executar: %r"
                    % (R_sem["executadas"],))
    ind_sem = pl.indice_de_pranchas(list(R_sem["executadas"]) + ["coordenacao"])
    if any(f["disciplina"] == "mezanino" for f in ind_sem):
        gaps.append("indice sem mezanino cita mezanino: %r" % (ind_sem,))
    if any("PE-MZ" in f["codigo"] for f in ind_sem):
        gaps.append("indice sem mezanino tem PE-MZ: %r" % (ind_sem,))
    pac_sem = pl.gerar_pacote(list(R_sem["executadas"]))
    md_sem = pl.markdown(pac_sem)
    if "PE-MZ" in md_sem or "MZ01" in md_sem or "mezanino" in md_sem.lower():
        gaps.append("pacote sem mezanino cita mezanino")
    # o concreto calcula igual com e sem o vizinho (nao mude o calculo)
    c_sem = R_sem["disciplinas"]["concreto"]["raw"]
    c_com = R_com["disciplinas"]["concreto"]["raw"]
    if json.dumps(c_sem, sort_keys=True, default=str) != json.dumps(
            c_com, sort_keys=True, default=str):
        gaps.append("concreto mudou com o mezanino no spec (nao devia)")
    assert tmp_path.is_dir()
    assert not gaps, "G141 sem mezanino:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_04_vermelho_por_injecao_nos_dois_sentidos(tmp_path):
    """Sem a entrada em _PRANCHAS o mezanino volta a evaporar; sem a
    entrada no mapa vira sem_mapa; sem o motivo vira faltando. A copia
    mora em tmp_path (o repo vivo nunca e mutado)."""
    import copy

    import galpao_adapter as ga
    import galpao_turnkey as tk
    import pacote_legal as pl
    import varredura_disciplina_prancha as lente_g103
    import varredura_indice_disco as lente

    gaps = []
    # caso bom: executada tem prancha, mapa cobre, motivo nomeia
    res_bom = lente_g103.conferir_disciplina_prancha(
        list(tk.DISCIPLINAS), pl._PRANCHAS,
        lente_g103.ISENCOES_DISCIPLINA_PRANCHA)
    if not res_bom["OK"] or res_bom["sem_prancha"]:
        gaps.append("caso bom devia fechar: %r" % (res_bom,))
    # injecao 1: sem a entrada em _PRANCHAS, evapora de novo
    pranchas = dict(pl._PRANCHAS)
    caminho = tmp_path / "pranchas.json"
    caminho.write_text(json.dumps(sorted(pranchas)), encoding="utf-8")
    sem_entrada = {d: v for d, v in pranchas.items() if d != "mezanino"}
    quebrado = lente_g103.conferir_disciplina_prancha(
        list(tk.DISCIPLINAS), sem_entrada,
        lente_g103.ISENCOES_DISCIPLINA_PRANCHA)
    if quebrado["OK"] or quebrado["sem_prancha"] != ["mezanino"]:
        gaps.append("sem _PRANCHAS devia acusar sem_prancha: %r" % (quebrado,))
    # injecao 2 (outro sentido): sem a entrada no mapa, vira sem_mapa
    mapa = dict(json.loads(json.dumps(ga._PRANCHA_ARQUIVO_GALPAO)))
    del mapa["PE-MZ-01"]
    sem_mapa = lente.conferir_indice_disco(
        ["PE-MZ-01"], mapa, ["MZ01_MEZANINO.pdf"], [])
    if sem_mapa["OK"] or sem_mapa["sem_mapa"] != ["PE-MZ-01"]:
        gaps.append("sem mapa devia acusar sem_mapa: %r" % (sem_mapa,))
    # injecao 3 (outro sentido): sem motivo, o ausente vira faltando
    indice = [{"codigo": "PE-MZ-01", "titulo": "Mezanino de concreto"}]
    furado = ga._conferir_indice_galpao(
        indice, ga._PRANCHA_ARQUIVO_GALPAO, [], sem_freecad=())
    furado_sem_motivo = [p for p in furado
                         if p["prancha"] == "MZ01_MEZANINO.pdf"]
    if not furado_sem_motivo or "PE-MZ-01" not in furado_sem_motivo[0]["motivo"]:
        gaps.append("motivo vivo sem codigo: %r" % (furado,))
    vazio = lente.conferir_indice_disco(["PE-MZ-01"],
                                        ga._PRANCHA_ARQUIVO_GALPAO, [], [])
    if vazio["OK"] or vazio["faltando"] != ["PE-MZ-01"]:
        gaps.append("sem motivo devia faltar: %r" % (vazio,))
    # o dispatch declara ausencia, nunca erro (o caderno nao falha)
    import caderno_turnkey as ct

    st = ct._dispatch_pranchas("mezanino", {}, str(tmp_path), {}, None, 10)
    if st.get("ok") is not None or "erro" in st:
        gaps.append("dispatch do mezanino devia ser ok None: %r" % (st,))
    if "PE-MZ-01" not in ct.MOTIVO_MEZANINO_SEM_PRANCHA:
        gaps.append("motivo do caderno sem codigo: %r"
                    % (ct.MOTIVO_MEZANINO_SEM_PRANCHA,))
    assert copy is not None and tmp_path.is_dir()
    assert not gaps, "G141 injecao:\n%s" % "\n".join("  - " + g for g in gaps)


def test_05_fontes_independentes_e_calculo_intacto():
    """Assercao nao-tautologica: o codigo vem das fontes vivas (prefixo do
    indice, turnkey, calculo) e o calculo do mezanino nao mudou."""
    import galpao_adapter as ga
    import galpao_turnkey as tk
    import pacote_legal as pl

    lados = []
    if list(tk.DISCIPLINAS).count("mezanino") != 1:
        lados.append("DISCIPLINAS sem mezanino unico: %r" % (tk.DISCIPLINAS,))
    pref, titulos = pl._PRANCHAS.get("mezanino", (None, []))
    if pref != "PE-MZ" or titulos != ["Mezanino de concreto (laje/vigas/pilares)"]:
        lados.append("titulo do mezanino mudou: %r" % (pl._PRANCHAS.get("mezanino"),))
    if ga._PRANCHA_ARQUIVO_GALPAO.get("PE-MZ-01") != "MZ01_MEZANINO.pdf":
        lados.append("mapa do mezanino mudou: %r"
                     % (ga._PRANCHA_ARQUIVO_GALPAO.get("PE-MZ-01"),))
    if ga._disciplina_do_codigo_galpao("PE-MZ-01") != "mezanino":
        lados.append("dona do PE-MZ-01 devia ser mezanino")
    # o calculo nao mudou: a amostra ATENDE com os mesmos membros
    import galpao_mezanino as gmz

    r = gmz.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0,
                                 "pe_direito": 6.0},
                   "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
                   "q_uso": 2.0})
    ms = gmz.membros_bim(r)
    tipos = sorted(m["tipo"] for m in ms)
    if tipos != ["Beam"] * 4 + ["Column"] * 4 + ["Footing"] * 4 + ["Slab"]:
        lados.append("membros do mezanino mudaram: %r" % (tipos,))
    if not r.get("ATENDE"):
        lados.append("amostra devia ATENDER sem mudar o calculo")
    assert not lados, "fontes independentes reprovam:\n" + "\n".join(lados)
