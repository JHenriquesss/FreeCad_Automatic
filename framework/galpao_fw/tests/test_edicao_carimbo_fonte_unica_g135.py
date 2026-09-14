"""G135 - a declaracao da edicao escrita a mao vira fonte unica.

Medido (G131, remedido no G135 antes de mudar, 2026-09-13): o texto do
carimbo ("assumida 2014" / "Projeto calculado pela NBR 6118") fora de
edicao_nbr6118_g123 em 22 linhas de 6 arquivos (executivo_concreto,
caderno_encargos, pacote_legal, techdraw_concreto, rodar_galpao,
relatorio_calculo - quase tudo em fallback de except que dentro do pacote
nunca dispara) + "6118:2014" a mao em 46 linhas de 22 arquivos; o G131
removeu as mesmas copias da linha de cimento e o G127 fez isso para a
fct,m (fctm_nbr6118_g127.confere_copias e o molde).

Entregue:
  1. CENSO na fonte (edicao_nbr6118_g123, producao): copias_carimbo_fora_
     da_fonte/fonte_tem_carimbo/confere_copias (so a fonte contem o texto
     do carimbo, molde G127) + rotulos_6118_2014_fora_da_fonte/
     confere_rotulos (todo "6118:2014" fora daqui e citacao isenta em
     CITACOES_ISENTAS, com motivo; baseline nos dois sentidos).
  2. FIACAO: as 22 copias viram chamada a fonte (fallbacks literais
     removidos, como o G131 fez para o cimento); os rotulos de calculo
     (sufixo/rotulo/_FONTE_6118 + os 12 cabecalhos de memorial) passam a
     vir de rotulo_edicao()/carimbo_edicao()/sufixo_folha_edicao(); o que
     resta a mao e citacao historica isenta (14 arquivos, motivo escrito).
  3. USO: 19 + os 10 memoriais fiados = 29 leitores esperados.
  4. Sem a chave, a saida das tres tipologias declara 2014 em toda peca
     (e cada linha migrada rende o literal antigo byte a byte).

Nao fazer do goal: compor a declaracao por peca com a chave (isso e o
G132); virar a chave em projeto nenhum do repo.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

import edicao_nbr6118_g123 as fonte

# Remedicao do G135 antes de mudar (2026-09-13): 22 linhas do carimbo em
# 6 arquivos + "6118:2014" a mao em 22 arquivos (46 linhas). Depois da
# fiacao, o censo de copias e vazio e os rotulos sao so as 14 isencoes.
N_ISENCOES_ESPERADO = 14
N_USOS_ESPERADO = 29

# Os literais antigos, escritos a mao no teste (nao lidos da fonte: contra
# assercao tautologica, convencao 5 - a fonte tem de bater neles).
CARIMBO_SEM_CHAVE = ("Projeto calculado pela NBR 6118:2014 (comportamento "
                     "atual; edicao nao declarada no projeto \u2014 assumida "
                     "2014)")
ROTULO_2014 = "NBR 6118:2014"
SUFIXO_2014 = " (NBR 6118:2014)"


def test_01_censo_remedido_baseline_nos_dois_sentidos():
    """Um assert so: copias zeradas, rotulos so nas 14 isencoes triadas,
    29 usos fiados - cada lado nomeado (nada some nem nasce em silencio)."""
    quebras = []
    c = fonte.confere_copias()
    if not c["OK"] or c["copias"] or c["fonte_apagada"]:
        quebras.append("censo de copias fora do baseline: %r" % (c,))
    t = fonte.confere_rotulos()
    if not t["OK"]:
        quebras.append("rotulos fora da triagem: extras=%r faltando=%r"
                       % (t["extras"], t["faltando"]))
    if sorted(t["tem"]) != sorted(fonte.CITACOES_ISENTAS):
        quebras.append("rotulos=%r, isencoes=%r"
                       % (t["tem"], sorted(fonte.CITACOES_ISENTAS)))
    if len(t["tem"]) != N_ISENCOES_ESPERADO:
        quebras.append("isencoes=%d, esperado %d"
                       % (len(t["tem"]), N_ISENCOES_ESPERADO))
    u = fonte.confere_uso_edicao()
    if not u["OK"]:
        quebras.append("uso fora do baseline: extras=%r faltando=%r"
                       % (u["extras"], u["faltando"]))
    if sorted(u["tem"]) != sorted(fonte.USO_ESPERADO):
        quebras.append("leitores=%r, esperado=%r"
                       % (u["tem"], sorted(fonte.USO_ESPERADO)))
    if len(u["tem"]) != N_USOS_ESPERADO:
        quebras.append("usos=%d, esperado %d"
                       % (len(u["tem"]), N_USOS_ESPERADO))
    assert not quebras, "censo G135 reprova:\n" + "\n".join(quebras)


def test_02_sem_chave_cada_linha_migrada_rende_o_literal_antigo():
    """Um assert so: a fonte sem a chave devolve os literais antigos byte
    a byte (o que prova que cada cabecalho fiado sai identico); o memorial
    real do galpao carimba os cabecalhos migrados em 2014."""
    quebras = []
    if fonte.rotulo_edicao(None) != ROTULO_2014:
        quebras.append("rotulo sem chave=%r, esperado %r"
                       % (fonte.rotulo_edicao(None), ROTULO_2014))
    if fonte.carimbo_edicao(None) != CARIMBO_SEM_CHAVE:
        quebras.append("carimbo sem chave=%r" % (fonte.carimbo_edicao(None),))
    if fonte.sufixo_folha_edicao(None) != SUFIXO_2014:
        quebras.append("sufixo sem chave=%r"
                       % (fonte.sufixo_folha_edicao(None),))
    if fonte.DECLARACAO_2014 != ROTULO_2014:
        quebras.append("DECLARACAO_2014 mudou: %r" % (fonte.DECLARACAO_2014,))
    # Os 12 cabecalhos migrados, formatados pela fonte, contra os literais
    # antigos escritos a mao aqui (typo no formato acusaria).
    rot = fonte.rotulo_edicao()
    pares = [
        ("PARTE B - CONCRETO ARMADO (%s):" % rot,
         "PARTE B - CONCRETO ARMADO (NBR 6118:2014):"),
        ("SAPATA - PARTE B (CONCRETO ARMADO) - %s" % rot,
         "SAPATA - PARTE B (CONCRETO ARMADO) - NBR 6118:2014"),
        ("LAJE MACICA DE CONCRETO ARMADO (%s)" % rot,
         "LAJE MACICA DE CONCRETO ARMADO (NBR 6118:2014)"),
        ("PILAR DE CONCRETO ARMADO - FLEXAO COMPOSTA (ABNT %s)" % rot,
         "PILAR DE CONCRETO ARMADO - FLEXAO COMPOSTA (ABNT NBR 6118:2014)"),
        ("PILAR CONTINUO - ABNT %s (le de 15.6 ; 2a ordem local de 15.8)"
         % rot, "PILAR CONTINUO - ABNT NBR 6118:2014 (le de 15.6 ; 2a ordem "
                "local de 15.8)"),
        ("VIGA DE BALDRAME / AMARRACAO (ABNT %s)" % rot,
         "VIGA DE BALDRAME / AMARRACAO (ABNT NBR 6118:2014)"),
        ("VIGA BALDRAME DO EDIFICIO MULTIPAVIMENTO (ABNT %s)" % rot,
         "VIGA BALDRAME DO EDIFICIO MULTIPAVIMENTO (ABNT NBR 6118:2014)"),
        ("VIGA DE CONCRETO ARMADO (ABNT %s)" % rot,
         "VIGA DE CONCRETO ARMADO (ABNT NBR 6118:2014)"),
        ("VIGA CONTINUA - ABNT %s, item 14.6.6" % rot,
         "VIGA CONTINUA - ABNT NBR 6118:2014, item 14.6.6"),
        ("VIGA DE COBERTURA PRE-TRACIONADA (ABNT %s ; CP-190 RB)" % rot,
         "VIGA DE COBERTURA PRE-TRACIONADA (ABNT NBR 6118:2014 ; CP-190 RB)"),
        ("ESCADA DE CONCRETO ARMADO - ABNT %s (laje armada em uma direcao)"
         % rot, "ESCADA DE CONCRETO ARMADO - ABNT NBR 6118:2014 (laje armada "
                "em uma direcao)"),
    ]
    for agora, antes in pares:
        if agora != antes:
            quebras.append("cabecalho mudou: %r != %r" % (agora, antes))
    # Integracao: o memorial real do galpao (funcoes reais) carimba os
    # cabecalhos migrados + o carimbo, tudo em 2014 sem a chave.
    import galpao_concreto as gc
    import executivo_concreto as ex
    r = gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
                  "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
                  "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3,
                  "sigma_solo_adm": 250.0,
                  "travamento_longitudinal": "topo"})
    mem = ex.memorial(r)
    for esperado in ("PILAR DE CONCRETO ARMADO - FLEXAO COMPOSTA "
                     "(ABNT NBR 6118:2014)",
                     "VIGA DE CONCRETO ARMADO (ABNT NBR 6118:2014)",
                     CARIMBO_SEM_CHAVE):
        if esperado not in mem:
            quebras.append("memorial real sem %r" % (esperado,))
    if "2023" in mem:
        quebras.append("memorial sem chave citando 2023")
    # Fundacao (funcoes reais, caso real do modulo): os dois cabecalhos
    # migrados saem em 2014 sem a chave.
    import fundacao_sapata as fs
    caso_fs = dict(fs.CASO_EXEMPLO)
    dim_fs = fs.dimensiona_sapata(caso_fs)
    if "PARTE B - CONCRETO ARMADO (NBR 6118:2014):" not in dim_fs["tabela"]:
        quebras.append("tabela real da sapata sem o cabecalho em 2014")
    rA_fs = fs.verifica_sapata_A(caso_fs)
    rB_fs = fs.dimensiona_sapata_B(caso_fs, rA_fs)
    if "SAPATA - PARTE B (CONCRETO ARMADO) - NBR 6118:2014" not in \
            fs.relatorio_sapata_B(rB_fs, caso_fs):
        quebras.append("relatorio B real da sapata sem o cabecalho em 2014")
    if "2023" in mem:
        quebras.append("memorial sem chave citando 2023")
    assert not quebras, "byte-identico G135 reprova:\n" + "\n".join(quebras)


def test_03_vermelho_copia_ou_rotulo_novo_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo (molde G127 test_03): carimbo colado fora da
    fonte acusa; so em comentario nao e conta; fonte sem o carimbo acusa;
    rotulo novo sem triagem (extras) e isencao sem rotulo (faltando)
    acusam; o intacto fica verde."""
    quebras = []
    if not fonte.confere_copias()["OK"]:
        quebras.append("arvore real com copia: %r"
                       % (fonte.confere_copias(),))
    (tmp_path / "modulo_novo.py").write_text(
        "_x = 'Projeto calculado pela NBR 6118:2014 (copia)'" + chr(10),
        encoding="utf-8")
    (tmp_path / "edicao_nbr6118_g123.py").write_text(
        "x = 1" + chr(10), encoding="utf-8")
    copiado = fonte.confere_copias(str(tmp_path))
    if "modulo_novo" not in copiado["copias"] or copiado["OK"]:
        quebras.append("copia do carimbo nao acusou: %r" % (copiado,))
    (tmp_path / "modulo_novo.py").write_text(
        "# Projeto calculado pela NBR 6118:2014 (so comentario)" + chr(10),
        encoding="utf-8")
    if fonte.copias_carimbo_fora_da_fonte(str(tmp_path)):
        quebras.append("comentario contou como copia")
    if not fonte.confere_copias(str(tmp_path))["fonte_apagada"]:
        quebras.append("fonte sem o carimbo nao acusou")
    # Rotulos: arquivo novo com o literal = extras; isencao que perdeu o
    # literal = faltando; o bom passa.
    (tmp_path / "modulo_rotulo.py").write_text(
        "_y = 'NBR 6118:2014'" + chr(10), encoding="utf-8")
    rot = fonte.confere_rotulos(str(tmp_path))
    if "modulo_rotulo.py" not in rot["extras"] or rot["OK"]:
        quebras.append("rotulo novo sem triagem nao acusou: %r" % (rot,))
    (tmp_path / "modulo_limpo.py").write_text("x = 1" + chr(10),
                                              encoding="utf-8")
    morto = fonte.confere_rotulos(
        str(tmp_path), esperado={"modulo_limpo.py", "modulo_novo.py"})
    if morto["faltando"] != ["modulo_limpo.py", "modulo_novo.py"] \
            or morto["OK"]:
        quebras.append("isencao sem rotulo nao acusou: %r" % (morto,))
    if not fonte.confere_rotulos()["OK"]:
        quebras.append("arvore real com rotulo fora da triagem: %r"
                       % (fonte.confere_rotulos(),))
    assert not quebras, "G135:" + chr(10) + chr(10).join(quebras)


def test_04_uso_os_29_fiam_a_fonte(tmp_path):
    """Um assert so (molde G127 test_04): no repo real os 29 leitores
    chamam a fonte; em tmp_path, leitura nova sem triagem (extra) e nome
    morto (faltando) acusam."""
    quebras = []
    real = fonte.confere_uso_edicao()
    if not real["OK"]:
        quebras.append("arvore real: %r" % (real,))
    if sorted(real["tem"]) != sorted(fonte.USO_ESPERADO):
        quebras.append("leitores=%r, esperado=%r"
                       % (real["tem"], sorted(fonte.USO_ESPERADO)))
    (tmp_path / "edicao_nbr6118_g123.py").write_text("x = 1" + chr(10),
                                                    encoding="utf-8")
    (tmp_path / "modulo_novo.py").write_text(
        "import edicao_nbr6118_g123" + chr(10), encoding="utf-8")
    extra = fonte.confere_uso_edicao(str(tmp_path))
    if "modulo_novo.py" not in extra["extras"] or extra["OK"]:
        quebras.append("leitura por conta propria nao acusou: %r" % (extra,))
    (tmp_path / "modulo_morto.py").write_text("x = 1" + chr(10),
                                              encoding="utf-8")
    morto = fonte.confere_uso_edicao(
        str(tmp_path), esperado={"edicao_nbr6118_g123.py", "modulo_novo.py",
                                 "modulo_morto.py"})
    if morto["faltando"] != ["modulo_morto.py"] or morto["OK"]:
        quebras.append("nome morto nao acusou: %r" % (morto,))
    assert not quebras, "G135:" + chr(10) + chr(10).join(quebras)


def test_05_triagem_cada_rotulo_tem_motivo_e_nenhum_e_carimbo():
    """Um assert so: toda isencao tem motivo nao-vazio; nenhum arquivo com
    rotulo esta sem triagem; nenhuma isencao esconde o carimbo-sentenca
    (os dois portoes verdes juntos); a 2023 nao entrou nos memoriais."""
    quebras = []
    for arquivo, motivo in sorted(fonte.CITACOES_ISENTAS.items()):
        if not isinstance(motivo, str) or not motivo.strip():
            quebras.append("isencao sem motivo: %r" % (arquivo,))
    tem = fonte.rotulos_6118_2014_fora_da_fonte()
    sem_triagem = sorted(set(tem) - set(fonte.CITACOES_ISENTAS))
    if sem_triagem:
        quebras.append("rotulo sem triagem: %r" % (sem_triagem,))
    copias = fonte.copias_carimbo_fora_da_fonte()
    if copias:
        quebras.append("carimbo fora da fonte: %r" % (copias,))
    for arquivo in sorted(tem):
        caminho = os.path.join(GALPAO, arquivo)
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
        if "2023" in texto and arquivo in (
                "fundacao_sapata.py", "laje_concreto.py",
                "pilar_concreto.py", "pilar_continuo.py",
                "viga_baldrame.py", "viga_baldrame_edificio.py",
                "viga_concreto.py", "viga_continua.py",
                "viga_protendida.py", "escada_concreto.py"):
            quebras.append("%s com 2023 no memorial (G132 nao entrou)"
                           % (arquivo,))
    assert not quebras, "triagem G135 reprova:\n" + "\n".join(quebras)


def _rodada_sem_chave(nome, tmp_path):
    """Roda a tipologia de verdade sem a chave (spec persistido, Nail
    no repo) em tmp_path. Molde G128 _rodada com edicao=None; o galpao
    vai sem 2D (o emissor de desenho e do G123; aqui valem os SVG
    puro-Python + os documentos, molde G128 test_03)."""
    import test_indice_disco_rodada_g102 as g102
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    spec = g102._spec(nome)
    assert "norma_6118_edicao" not in spec, \
        "o repo nao declara a chave (Nao fazer do G135)"
    destino = str(tmp_path / ("run-g135-%s" % (nome,)))
    if nome == "galpao":
        opcoes = {"generate_ifc": False, "generate_2d": False}
    else:
        opcoes = dict(g102._OPCOES[nome])
    return run_project(spec, destino, opcoes), destino


def _pecas_concreto(nome, destino):
    if nome == "casa":
        import casa_residencial as adaptador
        mapa = dict(adaptador._PRANCHA_ARQUIVO_CASA)
    elif nome == "predio":
        import edificio_adapter as adaptador
        mapa = dict(adaptador._PRANCHA_ARQUIVO)
    else:
        mapa = {}
    pecas = {}
    faltando = []
    for codigo, arquivo in sorted(mapa.items()):
        if not codigo.startswith("PE-CO-"):
            continue
        caminho = os.path.join(destino, "drawings", arquivo)
        if not os.path.isfile(caminho):
            faltando.append("%s (%s) nao saiu" % (codigo, arquivo))
            continue
        with open(caminho, encoding="utf-8") as fh:
            pecas[arquivo] = fh.read()
    return pecas, faltando


def test_06_tres_tipologias_sem_chave_declaram_2014_em_toda_peca(tmp_path):
    """Um assert so (molde G128 test_01/02/03): rodada real das 3
    tipologias sem a chave - toda folha PE-CO / SVG de calculo + pacote
    + caderno declara 2014 pela fonte; nenhum "2023" sai."""
    quebras = []
    for nome in ("casa", "predio", "galpao"):
        _man, destino = _rodada_sem_chave(nome, tmp_path)
        pecas = {}
        if nome in ("casa", "predio"):
            folhas, faltando = _pecas_concreto(nome, destino)
            quebras.extend("%s: %s" % (nome, f) for f in faltando)
            if nome == "casa" and len(folhas) != 4:
                quebras.append("folhas PE-CO da casa=%d, esperado 4"
                               % len(folhas))
            if nome == "predio" and len(folhas) != 4:
                quebras.append("folhas PE-CO do predio=%d, esperado 4"
                               % len(folhas))
            pecas.update(folhas)
        else:
            for arquivo in ("concreto-armacao.svg", "concreto-formas.svg"):
                caminho = os.path.join(destino, "drawings-svg", arquivo)
                if not os.path.isfile(caminho):
                    quebras.append("galpao: %s nao saiu" % (arquivo,))
                    continue
                with open(caminho, encoding="utf-8") as fh:
                    pecas[arquivo] = fh.read()
        for doc in ("pacote-legal.md", "caderno-encargos.md"):
            caminho = os.path.join(destino, "documentos", doc)
            if not os.path.isfile(caminho):
                quebras.append("%s: %s nao saiu" % (nome, doc))
                continue
            with open(caminho, encoding="utf-8") as fh:
                pecas["%s:%s" % (nome, doc)] = fh.read()
        for arquivo, texto in sorted(pecas.items()):
            c = fonte.contem_declaracao(texto)
            if not c["tem"] or c["edicao"] != "2014":
                quebras.append("%s declara %r (esperado 2014)"
                               % (arquivo, c["edicao"]))
            if "2023" in texto:
                quebras.append("%s sem chave citando 2023" % (arquivo,))
    assert not quebras, "tipologias G135 reprovam:\n" + "\n".join(quebras)
