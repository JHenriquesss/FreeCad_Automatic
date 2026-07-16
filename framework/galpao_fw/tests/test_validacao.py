# ============================================================================
# test_validacao.py - integra ao pytest os novos modulos de entrada/validacao:
#   - validacao.rodar(): benchmarks independentes do nucleo (forma fechada,
#     equilibrio V/H, MAES B1, formula de vento) -> todos PASS.
#   - escopo: envelope + deteccao de fora-de-escopo + carimbo ART.
#   - wizard: construir_spec (sapata/estaca) + laco simulado -> spec valido.
#   - rodar_projeto.rodar_tudo (calc-only): veredito global honesto.
# ============================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)


def test_validacao_nucleo_toda_verde():
    import validacao
    ok, resultados = validacao.rodar(verbose=False)
    assert ok, [r for r in resultados if not r[1]]
    assert len(resultados) == 5


def test_validacao_sistema_cbca():
    # reproduz o galpao do manual CBCA (NBR 8800) sob Fd1 -> reacoes e momento
    # batem com o publicado dentro da tolerancia (sub-1% na pratica).
    import validacao
    ok, det = validacao.validacao_referencia(verbose=False)
    assert ok, det


def test_bootstrap_executivo_sem_repr_numpy():
    # regressao do bug da tesoura: o cfg embutido no script do freecad.exe via
    # repr NAO pode vazar 'np.float64(...)' (numpy>=2), senao o freecad quebra
    # com 'name np is not defined'. _para_nativo deve limpar tudo.
    import numpy as np
    import techdraw_exec as TD
    cfg = {"resultados": {"Maxima": np.float64(0.91), "Coluna": np.float64(0.65)},
           "geo": {"span": np.float64(20000.0)}, "n": np.int64(8),
           "terca": (np.float64(150.0), np.float64(60.0)),
           "takeoff": [np.float64(1.5), np.float64(2.5)], "descricao": "x"}
    boot = TD.script_bootstrap(cfg)
    linha = boot.splitlines()[1]                 # _CFG_ = {...}
    for tok in ("np.float64(", "np.int", "np.float", "array(", "numpy."):
        assert tok not in linha, "vazou %r no bootstrap" % tok
    # e re-executa sem numpy no escopo (como no freecad.exe)
    ns = {}
    exec(linha, {"__builtins__": __builtins__}, ns)
    assert ns["_CFG_"]["resultados"]["Maxima"] == 0.91
    assert isinstance(ns["_CFG_"]["terca"], tuple)   # preserva tupla


def test_codigo_prancha_bate_com_nome_do_arquivo():
    # regressao do defeito de numeracao: o drawing_number do carimbo deve ser o
    # codigo de TIPO da prancha (PE-11 no arquivo PE11), nao a ordem sequencial.
    import techdraw_exec as TD
    assert TD._codigo_prancha("PE11_DET_GUSSET_COB", 9, 12) == ("PE-11", "09/12")
    assert TD._codigo_prancha("PE01_COBERTURA", 1, 12) == ("PE-01", "01/12")
    assert TD._codigo_prancha("PE09_QUADROS", 12, 12) == ("PE-09", "12/12")
    # sem prefixo reconhecivel -> usa a ordem (fallback, nao quebra)
    assert TD._codigo_prancha("estranho", 3, 5) == ("PE-03", "03/05")


def test_pos_notas_nunca_sobrepoe_a_tabela():
    # regressao do defeito de overlap na PE09: o bloco de NOTAS deve ficar SEMPRE
    # abaixo da tabela mais baixa, para qualquer contagem de linhas plausivel.
    import techdraw_exec as TD
    for n_verif in range(4, 18):
        for n_mat in (0, 6, 12, 17):
            y = TD._pos_notas(n_verif, n_mat, n_notas=11)
            bases = []
            if n_verif:
                bases.append((480 - n_verif * 7) - TD._meia_alt_view(n_verif + 1, 1.5))
            if n_mat:
                bases.append((480 - n_mat * 7) - TD._meia_alt_view(n_mat + 1, 1.5))
            base = min(bases)
            topo_notas = y + TD._meia_alt_view(11, 1.4)      # borda superior do bloco
            assert topo_notas <= base + 1e-6, (n_verif, n_mat, topo_notas, base)


def test_cap_titulo_nunca_estoura_a_celula():
    # regressao do overflow: todo titulo do carimbo deve caber (<=26) e sem o
    # prefixo redundante 'DETALHE - ' que empurrava o texto para o 'Created by'.
    import techdraw_exec as TD
    titulos = ["PLANTA DE COBERTURA", "PLANTA DE FUNDACOES", "ELEVACOES",
               "PORTICO TIPICO", "CONTRAVENTAMENTOS", "DETALHE - BASE DE COLUNA",
               "DETALHE - LIGACAO JOELHO (VIGA-COLUNA)",
               "FECHAMENTO / TERCAS / MAO-FRANCESA", "QUADROS E NOTAS TECNICAS",
               "DETALHE - GUSSET CONTRAV. COBERTURA",
               "DETALHE - GUSSET CONTRAV. PAREDE", "DETALHE - FIXACAO DE GIRT"]
    for t in titulos:
        c = TD._cap_titulo(t)
        assert len(c) <= 26, (t, c, len(c))
        assert "DETALHE - " not in c
    # abreviacoes legiveis (nao caem em reticencia)
    assert TD._cap_titulo("DETALHE - LIGACAO JOELHO (VIGA-COLUNA)") == "LIGACAO JOELHO"
    assert TD._cap_titulo("FECHAMENTO / TERCAS / MAO-FRANCESA") == "FECHAMENTO / TERCAS"


def test_fmt_terca_formatado_legivel():
    # regressao do callout cru: a terca sai formatada, nao como repr de lista.
    import techdraw_exec as TD
    assert TD._fmt_terca((300.0, 85.0, 25.0, 3.35)) == "Ue 300 x 85 x 25 x 3.35 mm"
    assert TD._fmt_terca([150.0, 60.0, 20.0, 2.0]) == "Ue 150 x 60 x 20 x 2.00 mm"
    assert isinstance(TD._fmt_terca(None), str)          # entrada invalida nao quebra


def test_quadro_fundacao_coerente_com_tipo():
    # regressao do Defeito 5: fundacao profunda NAO pode usar terminologia de
    # 'sapatas'. Deep -> ESTACAS/BLOCOS; rasa -> SAPATAS.
    import techdraw_exec as TD
    cfg_est = {"estaca": {"D": 0.30, "L": 10.0, "n": 2}, "bloco": {"a": 0.60, "h": 0.60},
               "sapata": {"B": 1.2, "L": 1.2, "h": 0.4}}   # sapata_adotada tb existe
    tit, hdr, rows, nota = TD._quadro_fundacao(cfg_est, tem_estaca=True)
    assert tit == "QUADRO DE ESTACAS / BLOCOS"
    assert "estacas/blocos" in nota and "sapatas" not in nota
    assert any(r[0] == "Estaca" for r in rows) and any(r[0] == "Bloco" for r in rows)
    # rasa -> sapatas
    tit2, _h, rows2, nota2 = TD._quadro_fundacao({"sapata": {"B": 1.2, "L": 1.2, "h": 0.4}},
                                                 tem_estaca=False)
    assert tit2 == "QUADRO DE SAPATAS" and "sapatas em cm" in nota2


def test_pos_corte_ligacao_fora_das_notas():
    # regressao do Defeito 6: no detalhe 'dupla' (cumeeira/joelho) o corte vai
    # para a direita, fora da faixa horizontal do bloco de notas (x=200, larg 360).
    import techdraw_exec as TD
    x, y = TD._pos_corte_ligacao(True, xpos=230.0)
    assert x >= 200.0 + 360.0, (x,)          # a direita do bloco de notas
    # caso simples mantem sob a elevacao (nunca colidiu)
    assert TD._pos_corte_ligacao(False, xpos=410.0)[0] == 410.0


def test_escopo_envelope_e_carimbo():
    import escopo
    # projeto regular: so a fronteira sempre-ativa da fundacao
    ids = {i for i, _ in escopo.avaliar({"cobertura": {"aguas": 2}})}
    assert ids == {"fundacao_detalhe"}
    # fogo+ponte+sismo acendem as fronteiras
    s = {"cobertura": {"aguas": 2}, "fogo": {"TRRF_min": 30}, "ponte": {"Q": 50}}
    ids = {i for i, _ in escopo.avaliar(s, {"sismo_theta": {"ok": True}})}
    assert {"fogo_global", "ponte_fadiga", "sismo_modal"} <= ids
    assert any("ART" in ln for ln in escopo.carimbo_art())


def test_wizard_constroi_spec_valido():
    import wizard
    import projeto_spec as PS
    r = dict(area_lote_m2=1200, span=10, comprimento=20, eave=6, v0=40,
             sigma_solo=200, fund_tipo="sapata")
    assert PS.validar(wizard.construir_spec(r))["ok"]
    # estaca sem sondagem bloqueia; com sondagem valida
    r_est = dict(r, fund_tipo="estaca")
    assert PS.validar(wizard.construir_spec(r_est))["ok"] is False
    r_est.update(spt_tipo="areia_siltosa", spt_N=20, spt_dz=8.0)
    assert PS.validar(wizard.construir_spec(r_est))["ok"]


def test_rodar_tudo_veredito_global(tmp_path):
    import wizard
    import rodar_projeto as RP
    # geometria que atende globalmente (12x30) -> veredito ATENDE
    r = dict(area_lote_m2=1500, span=12, comprimento=30, eave=7, bay=6,
             base_fixed=True, v0=42, sigma_solo=250, fund_tipo="sapata")
    spec = wizard.construir_spec(r, slug="t_veredito")
    out = RP.rodar_tudo(spec, str(tmp_path), com_3d=False, com_executivo=False,
                        gerar_pdf=False, verbose=False)
    assert "atende" in out
    assert os.path.exists(os.path.join(str(tmp_path), "RELATORIO-CONSOLIDADO.txt"))
    # o veredito global expoe atende_global + falhas_verificacao no res
    assert "atende_global" in out["res"]
