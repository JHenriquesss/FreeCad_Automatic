"""G137 - cada prancha de aco emitida tem codigo no indice.

Medido (2026-09-14, antes de mudar):
- prazo do aco no caderno: 459 s de 1200 s (stage/2; D164/D165);
- tempo por prancha (tools_harness_aco_por_prancha.MEDIDOS_G109, G109+G118):
  16 pranchas 578,3 s + PE05 209,4 s = 787,7 s; 3D ~210 s (D164);
  D165: 1038,9 s total, 15 PDFs (PE01-PE14 e PE16, sem PE15);
- 15 pranchas contra o mapa: 3 com codigo, 12 sem (SEM_CODIGO_ACO no D165).

Entregue:
- PE-ES-04..15 para as 12 (1:1 medido contra o techdraw_exec, titulos em
  pacote_legal._PRANCHAS); PE-ES-16/17 para as condicionais (console so com
  ponte, bloco so com fundacao profunda);
- prazo do aco derivado do medido (_T_MEDIDO_SEG["aco"]=787,7, split 3D/exec
  proporcional 210/787,7) e global 1200 -> 2100 s com motivo escrito;
- SEM_CODIGO_ACO vazia (portao D165 nos dois sentidos).

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em tmp_path (nunca mutando o repo), substring ->
parse -> renderizar (olhe a imagem: os tres aceites de PE02/PE03 incluem o
PNG da rodada de auditoria, registrado no verbete D166), fonte
independente (techdraw_exec via AST + LIGACOES, nunca o proprio mapa).
"""
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

# 1:1 medido contra o techdraw_exec (pagina -> codigo esperado). As 5
# variaveis das ligacoes (PE10-13 + console) vem de LIGACOES (fonte viva,
# mesma do harness G105); as demais sao literais em _nova_prancha.
# PE15_DET_BLOCO e literal em _pr_bloco (carimba "-"); PE14_CROQUIS e
# PE16_MONTAGEM sao literais.
MAPA_ESPERADO_1A1 = {
    "PE01_COBERTURA.pdf": "PE-ES-03",
    "PE02_FUNDACOES.pdf": "PE-ES-04",
    "PE03_ELEVACOES.pdf": "PE-ES-05",
    "PE04_PORTICO.pdf": "PE-ES-01",
    "PE05_CONTRAVENTAMENTO.pdf": "PE-ES-06",
    "PE06_DET_BASE.pdf": "PE-ES-07",
    "PE07_DET_JOELHO.pdf": "PE-ES-02",
    "PE08_FECHAMENTO.pdf": "PE-ES-08",
    "PE09_QUADROS.pdf": "PE-ES-09",
    "PE10_DET_CUMEEIRA.pdf": "PE-ES-10",
    "PE11_DET_GUSSET_COB.pdf": "PE-ES-11",
    "PE12_DET_GUSSET_PAR.pdf": "PE-ES-12",
    "PE13_DET_CLIPE_GIRT.pdf": "PE-ES-13",
    "PE14_CROQUIS.pdf": "PE-ES-14",
    "PE14_DET_CONSOLE.pdf": "PE-ES-16",
    "PE15_DET_BLOCO.pdf": "PE-ES-17",
    "PE16_MONTAGEM.pdf": "PE-ES-15",
}


def _paginas_emitidas():
    """Paginas que o techdraw_exec realmente cria (AST + LIGACOES)."""
    caminho = os.path.join(GALPAO, "techdraw_exec.py")
    with open(caminho, encoding="utf-8") as fh:
        arvore = ast.parse(fh.read())
    paginas = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        fn = getattr(no.func, "attr", None) or getattr(no.func, "id", None)
        if fn != "_nova_prancha" or len(no.args) < 2:
            continue
        pagina = no.args[1]
        if isinstance(pagina, ast.Constant) and isinstance(pagina.value, str) \
                and pagina.value.strip():
            paginas.add(pagina.value.strip() + ".pdf")
    import techdraw_exec as _td

    for i, (_pref, _tit, _base, _kw, _el, _ch, _ca, _sn) in enumerate(
            _td.LIGACOES):
        paginas.add("PE%02d_DET_%s.pdf" % (10 + i, _base))
    return paginas


def test_01_mapa_1a1_medido_contra_o_emissor():
    """Cada PDF emitido tem um codigo; cada codigo do aco tem um PDF emitido.

    Nos dois sentidos: PDF novo sem codigo reprova; codigo sem PDF emitido
    (nome morto) reprova. Fonte independente: paginas do AST+LIGACOES,
    nunca o proprio mapa.
    """
    import galpao_adapter as ga

    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    paginas = _paginas_emitidas()
    lados = []
    # 1:1 esperado (medido, nao suposto).
    for pdf, codigo in sorted(MAPA_ESPERADO_1A1.items()):
        if pdf not in paginas:
            lados.append("%s esperado sem pagina no emissor" % pdf)
        if mapa.get(codigo) != pdf:
            lados.append("%s devia mapear %s, mapeia %r"
                         % (codigo, pdf, mapa.get(codigo)))
    # Nenhum PDF emitido fora do 1:1 (novo sem codigo).
    for pdf in sorted(paginas):
        if pdf not in MAPA_ESPERADO_1A1:
            lados.append("%s emitido sem codigo no 1:1" % pdf)
    # Nenhum codigo do aco fora do 1:1 (nome morto).
    for codigo, pdf in sorted(mapa.items()):
        if not codigo.startswith("PE-ES-"):
            continue
        if codigo not in MAPA_ESPERADO_1A1.values():
            lados.append("%s no mapa fora do 1:1 (-> %s)" % (codigo, pdf))
        elif pdf not in paginas:
            lados.append("%s aponta %s que o emissor nao cria"
                         % (codigo, pdf))
    assert not lados, "G137 1:1 reprova:\n" + "\n".join(lados)


def test_02_vermelho_por_injecao_via_tmp_path(tmp_path):
    """Prancha nova sem codigo e codigo sem prancha acusam; o caso bom fecha.

    Tudo em tmp_path (convencao 2: o repo vivo nunca e mutado).
    """
    import galpao_adapter as ga
    from tests.test_executivo_aco_completo_d165 import conferir_pranchas_aco

    mapa_vals = set(ga._PRANCHA_ARQUIVO_GALPAO.values())
    caminho = tmp_path / "mapa_aco.json"
    caminho.write_text(json.dumps(sorted(mapa_vals)), encoding="utf-8")
    copia_vals = set(json.loads(caminho.read_text(encoding="utf-8")))
    lados = []
    # Caso bom: as 15 do D165 (sem as 2 condicionais ausentes no spec) fecham
    # com a baseline vazia.
    emitidas_15 = [p for p in MAPA_ESPERADO_1A1
                   if p not in ("PE14_DET_CONSOLE.pdf", "PE15_DET_BLOCO.pdf")]
    bom = conferir_pranchas_aco(emitidas_15, copia_vals, {})
    if bom:
        lados.append("caso bom devia fechar vazio: %r" % (bom,))
    # Injecao 1 (um sentido): prancha nova sem codigo nem triagem.
    nova = list(emitidas_15) + ["PE99_FANTASMA.pdf"]
    quebrado = conferir_pranchas_aco(nova, copia_vals, {})
    if not any("PE99_FANTASMA" in q for q in quebrado):
        lados.append("prancha nova sem codigo devia acusar: %r" % (quebrado,))
    # Injecao 2 (outro sentido): baseline com nome morto (ganhou codigo).
    com_nome_morto = {"PE02_FUNDACOES.pdf": "triagem morta"}
    morto = conferir_pranchas_aco(emitidas_15, copia_vals, com_nome_morto)
    if not any("nome morto" in q for q in morto):
        lados.append("nome morto devia acusar: %r" % (morto,))
    assert not lados, "G137 injecao reprova:\n" + "\n".join(lados)


def test_03_tres_aceites_pe02_pe03_dizem_o_que_desenham():
    """Tres aceites por folha (convencao 6) para PE02 e PE03, sem freecad.

    1. esta certa: a pagina existe no emissor (AST) e o carimbo diz o que
       desenha (PLANTA DE FUNDACOES / ELEVACOES);
    2. sai no manifesto: o codigo esta no mapa (sai no disco e nos artifacts
       pela mesma via do G93/G102);
    3. diz o que desenha: o titulo no indice (fonte unica _PRANCHAS) nomeia
       a folha. O PNG da rodada de auditoria e olhado no verbete D166
       (substring -> parse -> renderizar: olhe a imagem).
    """
    import galpao_adapter as ga
    import pacote_legal as pl

    indice = {f["codigo"]: f["titulo"]
              for f in pl.indice_de_pranchas(["aco"])}
    # Carimbos literais medidos no fonte (AST, nunca substring).
    with open(os.path.join(GALPAO, "techdraw_exec.py"),
              encoding="utf-8") as fh:
        fonte = fh.read()
    lados = []
    for codigo, pdf, titulo_esperado, carimbo in (
            ("PE-ES-04", "PE02_FUNDACOES.pdf", "Planta de fundacoes",
             "PLANTA DE FUNDACOES"),
            ("PE-ES-05", "PE03_ELEVACOES.pdf", "Elevacoes", "ELEVACOES")):
        # 1. pagina no emissor + carimbo.
        if '"%s"' % pdf[:-4] not in fonte:
            lados.append("%s sem pagina no emissor" % pdf)
        if '"%s"' % carimbo not in fonte:
            lados.append("%s sem carimbo %r no fonte" % (pdf, carimbo))
        # 2. codigo no mapa.
        if ga._PRANCHA_ARQUIVO_GALPAO.get(codigo) != pdf:
            lados.append("%s fora do mapa (-> %r)" % (codigo, pdf))
        # 3. titulo no indice diz o que desenha.
        titulo = indice.get(codigo, "")
        if titulo_esperado.lower() not in titulo.lower():
            lados.append("%s com titulo que nao diz o que desenha: %r"
                         % (codigo, titulo))
    assert not lados, "G137 aceites reprova:\n" + "\n".join(lados)


def test_04_prazo_deriva_do_medido():
    """O prazo sai do tempo cronometrado por prancha, nunca de palpite.

    _T_MEDIDO_SEG["aco"] = 787,7 (578,3 G109 + 209,4 G118); o peso deriva
    via peso_medido (convencao 8: constante que a producao nao le e
    comentario); o split 3D/exec e proporcional ao medido (210/787,7);
    o global 1200 -> 2100 s com motivo escrito (D166).
    """
    import caderno_turnkey as ct

    lados = []
    if abs(ct._T_MEDIDO_SEG["aco"] - 787.7) > 1e-6:
        lados.append("t_medido do aco fora do cronometrado: %r"
                     % (ct._T_MEDIDO_SEG["aco"],))
    if abs(ct._STAGE_WEIGHTS["aco"]
           - ct.peso_medido(ct._T_MEDIDO_SEG["aco"])) > 1e-9:
        lados.append("peso do aco nao deriva do medido (G119): %r"
                     % (ct._STAGE_WEIGHTS["aco"],))
    if abs(ct._T_MEDIDO_3D_ACO_SEG - 210.0) > 1e-6:
        lados.append("t_3d do aco fora do medido D164: %r"
                     % (ct._T_MEDIDO_3D_ACO_SEG,))
    import inspect

    src = inspect.getsource(ct._dispatch_pranchas)
    if "_T_MEDIDO_3D_ACO_SEG" not in src or "_T_MEDIDO_SEG" not in src:
        lados.append("dispatch do aco nao le o medido (palpite): sem "
                     "_T_MEDIDO_* no fonte")
    if "stage_timeout / 2" in src.replace(" ", "") or \
            "stage_timeout/2" in src.replace(" ", ""):
        lados.append("split meio a meio ainda no fonte (D164/D165)")
    import project_loop as _pl

    if _pl.ProjectLoopOptions().timeout_seconds != 2100:
        lados.append("global nao mudou com motivo: %r"
                     % (_pl.ProjectLoopOptions().timeout_seconds,))
    assert not lados, "G137 prazo reprova:\n" + "\n".join(lados)
