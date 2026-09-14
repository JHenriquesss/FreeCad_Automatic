"""G139 - PE-CD-01 coordenacao: o hook nunca emitia.

Medido (2026-09-14, antes de mudar):
- caderno_turnkey.montar_caderno so emitia a prancha formal de coordenacao
  com disciplinas=None; o hook do galpao sempre passa o recorte
  normalized["requested_disciplines"] (galpao_adapter._emit_drawings) —
  PE-CD-01 pulada em toda rodada ("... montar_caderno so emite a prancha
  com disciplinas=None");
- remeça com mocks (sem freecad): recorte de 2 disciplinas -> render 1,
  prancha formal 0; disciplinas=None -> render 1, prancha 1.

Entregue:
- montar_caderno emite render + prancha formal quando o ALVO (o recorte)
  tem >= 2 disciplinas executadas, com peso medido; recorte de 1 segue sem,
  com motivo escrito (MOTIVO_COORDENACAO_RECORTE_1);
- pesos derivados do cronometrado (G139/D167, galpao-tp-g95, 6 disciplinas,
  3012 membros, freecad.exe nesta maquina): render 95,6 s -> 1,1578;
  prancha 69,8 s -> 0,8453 (regra peso_medido, ancora 578 s; maximos — a
  media estourou por construcao na 1a suite). Sem aco
  (5 disc, 767 membros): 20,0 + 15,2 s; 4 leves (155): 12,1 + 13,0 s.
- motivo do laco PE-CD-01 atualizado para a regra nova (>= 2; 1 segue sem).

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em tmp_path (nunca mutando o repo), substring ->
parse -> renderizar (o PNG da rodada de medicao e olhado no verbete D167),
fonte independente (techdraw_coordenacao via AST + _PRANCHAS, nunca o
proprio mapa).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

# Tempos cronometrados (G139/D167, galpao-tp-g95, lote cheio com aco):
# maximos das amostras (render 73,6 + 95,6; prancha 34,8 fora + 67,8 +
# 69,8 + 65,7) — a 1a suite com a media estourou por construcao.
T_RENDER_MEDIDO = 95.6
T_PRANCHA_MEDIDO = 69.8


def _R2():
    return {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "executadas": ["incendio", "hidraulica"],
        "reprovados": [], "ATENDE": True,
        "disciplinas": {
            "incendio": {"rodou": True, "ATENDE": True, "reprovados": [],
                         "raw": {}},
            "hidraulica": {"rodou": True, "ATENDE": True, "reprovados": [],
                           "raw": {}},
        },
    }


def test_01_recorte_com_2_emite_recorte_com_1_segue_sem_motivo(tmp_path, monkeypatch):
    """O alvo (recorte) decide: >= 2 emite render + prancha; 1 segue sem.

    Monta o caderno com fakes que escrevem PDFs VALIDOS (via _pdf_dummy) em
    tmp_path: o caso bom fecha com a coordenacao no disco; o recorte de 1
    registra o motivo e nao chama o emissor. Vermelho por injecao: trocar o
    recorte de 2 por 1 tem de apagar a prancha (e o teste 02 prova o motivo
    no laco).
    """
    import caderno_turnkey as ct
    import galpao_turnkey as tk

    chamadas = {"render": 0, "prancha": 0}

    def fake_render(R, out, **kw):
        chamadas["render"] += 1
        return {"vistas": []}

    def fake_prancha(R, out, **kw):
        chamadas["prancha"] += 1
        prd = os.path.join(str(out), "pranchas")
        os.makedirs(prd, exist_ok=True)
        for base in ("COORD01_PLANTA", "COORD02_CLASH"):
            ct._pdf_dummy(os.path.join(prd, base + ".pdf"), base)
        return {"ok": True, "pranchas": ["COORD01_PLANTA", "COORD02_CLASH"]}

    def fake_dispatch(nome, r_disc, disc_out, sub_spec, exe, timeout, **kw):
        prd = os.path.join(str(disc_out), "pranchas")
        os.makedirs(prd, exist_ok=True)
        ct._pdf_dummy(os.path.join(prd, nome.upper() + ".pdf"), nome)
        return {"ok": True}

    monkeypatch.setattr(tk, "render_federado", fake_render)
    monkeypatch.setattr(tk, "montar_prancha_coordenacao", fake_prancha)
    monkeypatch.setattr(ct, "_dispatch_pranchas", fake_dispatch)
    monkeypatch.setattr(tk, "checa_interferencia_federada",
                        lambda R, spec: {"n_clashes": 0})
    monkeypatch.setattr(tk, "rodar", lambda spec, out: _R2())

    lados = []
    # Caso bom: recorte de 2 -> render + prancha formal no disco e no status.
    res = ct.montar_caderno({"slug": "g139-2"}, str(tmp_path / "a"),
                            disciplinas=["incendio", "hidraulica"],
                            freecad_exe="x", timeout=60, R=_R2())
    if chamadas["render"] != 1 or chamadas["prancha"] != 1:
        lados.append("recorte de 2 devia emitir render+prancha: %r" % chamadas)
    if "coordenacao" not in (res.get("disciplinas") or {}):
        lados.append("coordenacao fora do caderno com 2 disciplinas: %r"
                     % (res.get("disciplinas"),))
    if not isinstance(res.get("status", {}).get("coordenacao"), dict) \
            or not res["status"]["coordenacao"].get("ok"):
        lados.append("status da coordenacao sem ok com 2: %r"
                     % (res.get("status", {}).get("coordenacao"),))
    # Recorte de 1 -> sem emissor, com motivo escrito (nunca silencio).
    chamadas.update({"render": 0, "prancha": 0})
    res1 = ct.montar_caderno({"slug": "g139-1"}, str(tmp_path / "b"),
                             disciplinas=["incendio"],
                             freecad_exe="x", timeout=60, R=_R2())
    if chamadas["render"] != 0 or chamadas["prancha"] != 0:
        lados.append("recorte de 1 nao devia chamar render/prancha: %r"
                     % chamadas)
    motivo = ((res1.get("status", {}).get("coordenacao") or {})
              .get("nao_solicitado") or "")
    if "1 disciplina" not in motivo or ">= 2" not in motivo:
        lados.append("recorte de 1 sem motivo que nomeia a regra: %r" % motivo)
    if "coordenacao" in (res1.get("disciplinas") or {}):
        lados.append("coordenacao no caderno com 1 disciplina: %r"
                     % (res1.get("disciplinas"),))
    assert not lados, "G139 recorte reprova:\n" + "\n".join(lados)


def test_02_vermelho_por_injecao_nos_dois_sentidos(tmp_path):
    """Emissor desligado volta a pular com motivo; motivo apagado reacende.

    Tudo em tmp_path (convencao 2). Um sentido: sem COORD01 no disco e sem
    motivo, PE-CD-01 e faltando; com motivo, fecha. Outro sentido: motivo
    em branco nao libera (silencio nao e triagem).
    """
    import varredura_indice_disco as lente

    mapa = {"PE-CD-01": "COORD01_PLANTA.pdf"}
    lados = []
    # Caso bom: sem arquivo mas com motivo escrito -> OK.
    bom = lente.conferir_indice_disco(
        ["PE-CD-01"], mapa, [],
        [{"prancha": "COORD01_PLANTA.pdf",
          "motivo": "not_available: recorte de 1 disciplina (G139)"}])
    if not bom["OK"] or bom["faltando"]:
        lados.append("caso bom com motivo devia fechar: %r" % (bom,))
    # Injecao 1: sem arquivo e sem motivo -> faltando acusa.
    sem_motivo = lente.conferir_indice_disco(["PE-CD-01"], mapa, [], [])
    if sem_motivo["faltando"] != ["PE-CD-01"]:
        lados.append("sem motivo devia acusar faltando: %r" % (sem_motivo,))
    # Injecao 2: motivo em branco nao libera.
    em_branco = lente.conferir_indice_disco(
        ["PE-CD-01"], mapa, [],
        [{"prancha": "COORD01_PLANTA.pdf", "motivo": "   "}])
    if em_branco["faltando"] != ["PE-CD-01"]:
        lados.append("motivo em branco nao devia liberar: %r" % (em_branco,))
    # O motivo vivo do laco nomeia a regra (>= 2) e nunca o texto antigo.
    import galpao_adapter as ga

    vivo = ga._motivo_folha_galpao_nao_emitida("PE-CD-01", "Modelo federado")
    if ">= 2" not in vivo or "1 disciplina" not in vivo:
        lados.append("motivo vivo sem a regra G139: %r" % vivo[:160])
    if "disciplinas=None" in vivo:
        lados.append("motivo vivo ainda com o texto do defeito: %r"
                     % vivo[:160])
    assert not lados, "G139 injecao reprova:\n" + "\n".join(lados)


def test_03_tres_aceites_pecd01_diz_o_que_desenha():
    """Tres aceites por folha (convencao 6) para PE-CD-01 e PE-CD-02.

    G139 (2a rodada): o emissor emite 2 folhas, cada uma com seu codigo
    (PE-CD-02 para o quadro de clash) — emissao parcial (só COORD01, como
    no timeout sob carga da 1a suíte) deixa PE-CD-02 pulada com motivo, sem
    virar extra nem buraco (test_05). Sem freecad:
    1. esta certa: as paginas existem no emissor (AST) e o carimbo diz o que
       desenha (COORDENACAO, sem vazar ACO);
    2. sai no manifesto: o codigo esta no mapa (sai no disco e nos artifacts
       pela mesma via do G93/G102);
    3. diz o que desenha: o titulo no indice (fonte unica _PRANCHAS) nomeia
       a folha. Os PNGs da rodada de medicao sao olhados no verbete D167
       (substring -> parse -> renderizar: olhe a imagem).
    """
    import ast as _ast

    import galpao_adapter as ga
    import pacote_legal as pl

    indice = {f["codigo"]: f["titulo"]
              for f in pl.indice_de_pranchas(["coordenacao"])}
    # PE-CD-02 mora no verbete de fronteira do galpao (vocabulario
    # partilhado com o predio de folha unica nao pode prometer).
    indice[pl.PE_CD_02_GALPAO["codigo"]] = pl.PE_CD_02_GALPAO["titulo"]
    with open(os.path.join(GALPAO, "techdraw_coordenacao.py"),
              encoding="utf-8") as fh:
        fonte = fh.read()
    arvore = _ast.parse(fonte)
    paginas = set()
    for no in _ast.walk(arvore):
        if not isinstance(no, _ast.Call):
            continue
        fn = getattr(no.func, "id", "") or getattr(no.func, "attr", "")
        if fn != "_nova_prancha" or len(no.args) < 2:
            continue
        segundo = no.args[1]
        if isinstance(segundo, _ast.Constant) and segundo.value:
            paginas.add(segundo.value)
    lados = []
    # 1. paginas no emissor + carimbo de coordenacao.
    for pagina in ("COORD01_PLANTA", "COORD02_CLASH"):
        if pagina not in paginas:
            lados.append("%s sem pagina no emissor" % pagina)
    # O carimbo GERADO nao vaza material/norma de aco (o nome do generico
    # aparece no comentario de _carimbo_coord, nao no carimbo emitido).
    import galpao_turnkey as _tk
    import techdraw_coordenacao as _tc

    _spec = {"geometria": {"comprimento": 40.0, "vao": 20.0,
                           "pe_direito": 6.0},
             "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                          "deteccao": {"viga_m": 0.0}},
             "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2,
                                               "lavatorio": 2},
                            "aparelhos_esgoto": {"bacia": 2,
                                                 "lavatorio": 2}}}
    _R = _tk.rodar(_spec)
    _cfg = _tc.config_de_spec(_R, "/tmp/x", spec=_spec)
    if _cfg.get("carimbo_material") != "COORDENACAO":
        lados.append("carimbo gerado vazando material de aco: %r"
                     % (_cfg.get("carimbo_material"),))
    # 2. codigos no mapa; 3. titulos no indice dizem o que desenham.
    for codigo, pdf, termos in (
            ("PE-CD-01", "COORD01_PLANTA.pdf", ("federado", "compatibilizacao")),
            ("PE-CD-02", "COORD02_CLASH.pdf", ("clash",))):
        if ga._PRANCHA_ARQUIVO_GALPAO.get(codigo) != pdf:
            lados.append("%s fora do mapa (-> %r)"
                         % (codigo, ga._PRANCHA_ARQUIVO_GALPAO.get(codigo),))
        titulo = indice.get(codigo, "")
        if not any(t in titulo.lower() for t in termos):
            lados.append("%s com titulo que nao diz o que desenha: %r"
                         % (codigo, titulo))
    assert not lados, "G139 aceites reprova:\n" + "\n".join(lados)


def test_04_prazo_deriva_do_medido():
    """O prazo da coordenacao sai do cronometrado, nunca de palpite.

    _T_MEDIDO_SEG["coordenacao_render"]=95,6 e ["coordenacao"]=69,8
    (galpao-tp-g95, 6 disciplinas, freecad.exe; maximos das amostras D167)
    os pesos derivam via
    peso_medido (convencao 8: constante que a producao nao le e comentario);
    os literais 0,5/0,75 somem do fonte.
    """
    import inspect

    import caderno_turnkey as ct

    lados = []
    if abs(ct._T_MEDIDO_SEG.get("coordenacao_render", -1) - T_RENDER_MEDIDO) > 1e-6:
        lados.append("t_medido do render fora do cronometrado: %r"
                     % (ct._T_MEDIDO_SEG.get("coordenacao_render"),))
    if abs(ct._T_MEDIDO_SEG.get("coordenacao", -1) - T_PRANCHA_MEDIDO) > 1e-6:
        lados.append("t_medido da prancha fora do cronometrado: %r"
                     % (ct._T_MEDIDO_SEG.get("coordenacao"),))
    for chave in ("coordenacao_render", "coordenacao"):
        if abs(ct._STAGE_WEIGHTS.get(chave, -1)
               - ct.peso_medido(ct._T_MEDIDO_SEG[chave])) > 1e-9:
            lados.append("peso de %s nao deriva do medido (G119): %r"
                         % (chave, ct._STAGE_WEIGHTS.get(chave),))
    src = open(os.path.join(GALPAO, "caderno_turnkey.py"),
               encoding="utf-8").read()
    for literal in ('"coordenacao_render": 0.5', '"coordenacao": 0.75',
                    "'coordenacao_render': 0.5", "'coordenacao': 0.75"):
        if literal in src:
            lados.append("literal antigo ainda no fonte: %s" % literal)
    if "_T_MEDIDO_SEG[\"coordenacao" not in src \
            and "_T_MEDIDO_SEG['coordenacao" not in src:
        lados.append("peso da coordenacao nao le o medido (palpite)")
    # A reserva real usa os dois estagios quando o alvo tem >= 2.
    pendentes = ["coordenacao_render", "coordenacao", "incendio", "hidraulica"]
    total = ct._total_peso(pendentes)
    esperado = sum(ct._STAGE_WEIGHTS[k] for k in pendentes)
    if abs(total - esperado) > 1e-9:
        lados.append("reserva nao soma os pesos medidos: %r" % total)
    f_render = ct._fracao_reserva("coordenacao_render", pendentes)
    f_prancha = ct._fracao_reserva("coordenacao", pendentes)
    if not (0.0 < f_prancha < f_render < 1.0):
        lados.append("fracoes fora da ordem medida "
                     "(render %.4f <= prancha %.4f)" % (f_render, f_prancha))
    _ = inspect.getsource(ct.montar_caderno)
    assert not lados, "G139 prazo reprova:\n" + "\n".join(lados)


def test_05_emissao_parcial_nao_vira_extra_nem_buraco():
    """Emissao parcial (só COORD01, como no timeout sob carga da 1a suíte)
    fecha a lente: PE-CD-01 reivindicado, PE-CD-02 pulada com o motivo vivo.

    Reproduz o estado medido na 1a suíte (COORD01 no disco, COORD02 ausente
    após `timeout 62,4 s na prancha de coordenacao`): sem codigo novo, sem
    isencao e sem buraco — o motivo de producao libera, nos dois sentidos
    (motivo em branco nao libera).
    """
    import galpao_adapter as ga
    import varredura_indice_disco as lente

    prometidos = ["PE-CD-01", "PE-CD-02"]
    mapa = {c: ga._PRANCHA_ARQUIVO_GALPAO[c] for c in prometidos}
    motivo_vivo = ga._motivo_folha_galpao_nao_emitida(
        "PE-CD-02", "Quadro de clash e notas")
    lados = []
    # Caso bom parcial: COORD01 no disco + motivo vivo da COORD02 -> OK.
    parcial = lente.conferir_indice_disco(
        prometidos, mapa, ["drawings/coordenacao/pranchas/COORD01_PLANTA.pdf"],
        [{"prancha": "COORD02_CLASH.pdf", "motivo": motivo_vivo}])
    if not parcial["OK"] or parcial["faltando"] or parcial["extra_no_disco"]:
        lados.append("parcial devia fechar: %r" % (parcial,))
    # Completo: as 2 no disco, sem motivo -> OK.
    cheio = lente.conferir_indice_disco(
        prometidos, mapa,
        ["COORD01_PLANTA.pdf", "COORD02_CLASH.pdf"], [])
    if not cheio["OK"]:
        lados.append("completo devia fechar: %r" % (cheio,))
    # Vermelho: sem a COORD02 e sem motivo, PE-CD-02 falta.
    sem_motivo = lente.conferir_indice_disco(
        prometidos, mapa, ["COORD01_PLANTA.pdf"], [])
    if sem_motivo["faltando"] != ["PE-CD-02"]:
        lados.append("sem motivo PE-CD-02 devia faltar: %r" % (sem_motivo,))
    # Motivo em branco nao libera (silencio nao e triagem).
    em_branco = lente.conferir_indice_disco(
        prometidos, mapa, ["COORD01_PLANTA.pdf"],
        [{"prancha": "COORD02_CLASH.pdf", "motivo": "   "}])
    if em_branco["faltando"] != ["PE-CD-02"]:
        lados.append("motivo em branco nao devia liberar: %r" % (em_branco,))
    assert not lados, "G139 parcial reprova:\n" + "\n".join(lados)
