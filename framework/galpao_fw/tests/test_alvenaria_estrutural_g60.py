"""Vertical de alvenaria estrutural (G60): guardas + nucleo.

O que cada teste prova, e contra que defeito:
  fpk ausente -> recusa nomeada, e a assinatura prova que nenhum default
    entra (regra do SPT no G9). Nao recria aritmetica em variavel local:
    chama o modulo sem fpk e exige a recusa (licao do D86/D88: prova a
    CONTA em variavel local fica verde com o defeito de volta).
  lambda acima do teto -> REPROVA com motivo, e o resultado nem traz NRd
    (prova que nao saturou no teto nem virou razao que devolve OK: regra
    do G51 e do D82).
  peso proprio -> soma zero por dentro; a igualdade com a via da carga
    (cargas_nbr6120) e relacao no molde do test_fronteira_carga_laje_g52,
    com revestimento fora do default para a chave morta acusar.
  errata -> afirmada como RELACAO (o calculo usa fyd = fyk/1,15 e
    Es/Ea com Ea da Tab.1), nunca numero congelado: numero congelado
    cristaliza o erro se ele existir.
"""
import inspect
import sys
from pathlib import Path

import pytest

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import alvenaria_estrutural as alv          # noqa: E402
import cargas_nbr6120 as cg                 # noqa: E402
import edificio_multipavimento as em        # noqa: E402
import estrutura_casa as ec                 # noqa: E402


FPK = 4000.0       # prisma declarado (kN/m2)
FYK = 500e3
HE = 2.70
TE = 0.14
A_M2 = TE * 1.0


def test_gamma_m_tab2_combinacoes():
    assert alv.gamma_m("normal")["alvenaria"] == 2.0
    assert alv.gamma_m("especial")["alvenaria"] == 1.5
    assert alv.gamma_m("excepcional")["alvenaria"] == 1.5
    assert alv.gamma_m("els")["alvenaria"] == 1.0
    assert alv.gamma_m("excepcional")["aco"] == 1.0
    with pytest.raises(alv.EntradaAlvenaria):
        alv.gamma_m("rara")


def test_fpk_ausente_recusa_e_sem_default_na_assinatura():
    for fun in (alv.fk_de_fpk, alv.modulo_deformacao,
                alv.verifica_parede_compressao, alv.verifica_pilar_compressao,
                alv.verifica_pilar_armado):
        sig = inspect.signature(fun)
        assert "fpk" in sig.parameters, fun.__name__
        assert sig.parameters["fpk"].default is inspect.Parameter.empty, (
            "%s: fpk com default e bloco tipico em silencio" % fun.__name__)
    with pytest.raises(alv.EntradaAlvenaria, match="fpk_nao_declarado"):
        alv.fk_de_fpk(None, "bloco")
    with pytest.raises(alv.EntradaAlvenaria, match="fpk_nao_declarado"):
        alv.verifica_parede_compressao(100.0, None, HE, TE, A_M2)
    with pytest.raises(alv.EntradaAlvenaria, match="fpk_nao_declarado"):
        alv.verifica_pilar_armado(100.0, None, HE, TE, A_M2, 4e-4, FYK, 12.0)


def test_nucleo_compressao_1121_parede_e_pilar():
    r = alv.verifica_parede_compressao(100.0, FPK, HE, TE, A_M2)
    lam = HE / TE
    R = 1.0 - (lam / 40.0) ** 3
    fd = 0.70 * FPK / 2.0
    assert r["lambda_"] == pytest.approx(lam)
    assert r["R_redutor"] == pytest.approx(R, abs=1e-4)
    assert r["fd_kN_m2"] == pytest.approx(fd)
    assert r["NRd_kN"] == pytest.approx(fd * A_M2 * R, abs=1e-3)
    assert r["OK"] is True
    assert r["peso_proprio_interno_kN"] == 0.0
    rp = alv.verifica_pilar_compressao(100.0, FPK, HE, TE, A_M2)
    assert rp["NRd_kN"] == pytest.approx(0.9 * r["NRd_kN"], abs=1e-3)
    # fail-closed nos dois lados do numero: Nd acima reprova, abaixo aprova
    nrd = r["NRd_kN"]
    assert alv.verifica_parede_compressao(
        nrd * 1.001, FPK, HE, TE, A_M2)["OK"] is False
    assert alv.verifica_parede_compressao(
        nrd * 0.999, FPK, HE, TE, A_M2)["OK"] is True


def test_lambda_acima_do_teto_reprova_sem_saturar():
    # parede esbelta injetada: he/te = 32,1, teto 24 sem armadura
    r = alv.verifica_parede_compressao(1.0, FPK, 4.50, TE, A_M2)
    assert r["OK"] is False
    assert r["veredito"] == "reprovado"
    assert "esbeltez_acima_do_teto" in r["motivo"]
    assert "NRd_kN" not in r, (
        "NRd calculado com lambda acima do teto e saturacao no teto")
    # pilar armado acima de 30 reprova (11.2.2 cobre ate 30, sem Anexo C)
    rp = alv.verifica_pilar_armado(1.0, FPK, 4.50, TE, A_M2, 4e-4, FYK, 12.0)
    assert rp["OK"] is False and "esbeltez_acima_do_teto" in rp["motivo"]
    # parede armada acima de 30: Anexo C (G63, P-Delta com Md,total).
    # O alias sem esforcos indica o endereco novo; com esforcos calcula.
    with pytest.raises(alv.EntradaAlvenaria, match="anexo_C_pede_esforcos"):
        alv.verifica_parede_armada_anexo_C()
    c = alv.verifica_parede_esbelta_anexo_C(50.0, 2.0, FPK, 4.50, TE, 2.0,
                                            4e-4, FYK)
    assert c["Md_total_kNm"] > 2.0 and c["Ncr_kN"] > 0


def test_pilar_armado_1122_nucleo_com_Ea_da_errata():
    As = 4e-4
    r = alv.verifica_pilar_armado(120.0, FPK, HE, TE, A_M2, As, FYK, 12.0,
                                  tipo_bloco="bloco_concreto")
    Ea = alv.modulo_deformacao(FPK, "bloco_concreto")
    fs_prisma = FPK * alv.ES_ACO_KNM2 / Ea
    fs_esperado = min(fs_prisma, FYK, 500.0 * 1000.0)
    assert r["fs_kN_m2"] == pytest.approx(fs_esperado, rel=1e-9)
    lam = HE / TE
    R = 1.0 - (lam / 40.0) ** 3
    fd = 0.70 * FPK / 2.0
    assert r["NRd_kN"] == pytest.approx(
        (fd * A_M2 + fs_esperado * As / 1.15) * R, abs=1e-2)


def test_errata_fyd_como_relacao_1133():
    # 11.3.3 com a Er1:2021: fs corta em fyd = fyk/1,15, nao em fyk.
    # phi 12,5 mm, bloco ceramico liso -> 0,75 x fyd.
    fd = 0.70 * FPK / 2.0
    r = alv.verifica_flexao_simples_1133(
        5.0, 2e-4, 0.14, 0.30, fd, FYK, 12.5, bloco="ceramico")
    fyd = FYK / 1.15
    assert r["fyd_kN_m2"] == pytest.approx(fyd, rel=1e-6)
    assert r["fs_kN_m2"] == pytest.approx(0.75 * fyd, rel=1e-6)
    assert r["fs_kN_m2"] != pytest.approx(0.75 * FYK, rel=1e-3), (
        "fs em fyk e a formula pre-errata: erro de um gamma inteiro")
    assert r["errata_fyd_aplicada"] is True
    # bloco de concreto usa fyd cheio
    r2 = alv.verifica_flexao_simples_1133(
        5.0, 2e-4, 0.14, 0.30, fd, FYK, 10.0, bloco="concreto")
    assert r2["fs_kN_m2"] == pytest.approx(fyd, rel=1e-6)


def test_peso_proprio_zero_e_fronteira_com_a_via_da_carga():
    # revestimento fora do default 1,0: se a chave morrer no caminho e o
    # modulo cair no default, a relacao quebra (filtro de nome morto).
    tipo, esp, rev = "bloco_concreto_estrutural", 14.0, 2.0
    g_parede = cg.carga_linear_parede(tipo, esp, HE, rev)
    L = 3.30
    Nd = g_parede * L
    r = alv.verifica_parede_compressao(Nd, FPK, HE, TE, A_M2,
                                       comprimento_m=L)
    assert r["peso_proprio_interno_kN"] == 0.0
    junta = alv.confere_fronteira_peso(Nd, g_parede * L)
    assert junta["OK"] is True, junta["motivo"]
    # e nao e coincidencia: a decomposicao bate com o revestimento declarado
    assert g_parede == pytest.approx(
        cg.peso_alvenaria(tipo, esp, rev) * HE)
    # 10 % a mais num lado acusa a junta, nao o elemento
    junta2 = alv.confere_fronteira_peso(Nd * 1.10, g_parede * L)
    assert junta2["OK"] is False
    assert "fronteira_peso_diverge" in junta2["motivo"]


def test_vento_declarado_recusa_com_motivo_nunca_some():
    r = alv.verifica_parede_compressao(10.0, FPK, HE, TE, A_M2,
                                       acao_horizontal_kN=5.0)
    assert r["OK"] is False
    assert r["veredito"] == "recusado"
    assert "acao_horizontal_exige_contraventamento" in r["motivo"]
    # zero ou ausente segue o caminho gravitacional
    assert alv.verifica_parede_compressao(
        10.0, FPK, HE, TE, A_M2,
        acao_horizontal_kN=0.0)["OK"] is True
    assert alv.verifica_parede_compressao(
        10.0, FPK, HE, TE, A_M2)["OK"] is True


def test_espessura_minima_10_1_1():
    r = alv.verifica_parede_compressao(1.0, FPK, 2.40, 0.10, 0.10,
                                       n_pavimentos=3)
    assert r["OK"] is False and "espessura_minima_14cm" in r["motivo"]
    r2 = alv.verifica_parede_compressao(1.0, FPK, 2.40, TE, A_M2,
                                        n_pavimentos=3)
    assert "espessura_minima_14cm" not in r2.get("motivo", "")


def test_escopo_publica_o_fora_com_motivo():
    esc = alv.escopo()
    assert esc["compressao_parede_11_2_1"] == "implemented"
    # G62: BIM e pranchas deixaram de ser not_available (parede vira folha
    # e membro). G63: horizontal 9.6.2, 11.5 e Anexo C implemented; o fora
    # restante (cisalhamento 11.4) segue com motivo escrito.
    assert esc["bim_alvenaria"] == "implemented"
    assert esc["pranchas_alvenaria"] == "implemented"
    for chave in ("flexo_compressao_11_5", "parede_muito_esbelta_anexo_C",
                  "acao_horizontal_contraventamento"):
        assert esc[chave] == "implemented", chave
        assert alv.motivos_escopo()[chave], chave
    assert esc["cisalhamento_11_4"] == "not_available"
    assert alv.motivos_escopo()["cisalhamento_11_4"]


def test_selftest_do_modulo():
    assert alv._selftest() is True


def test_memorial_das_cadeias_cita_o_vertical_sem_fonte_ausente():
    # As cadeias gravitacionais consomem o modulo de verdade: a linha do
    # memorial vem da fonte unica (se o import/cair, este teste acusa).
    import copy
    spec_e = {
        "geometria": {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5],
                      "pe_direito": 2.90},
        "pavimentos": ([{"nome": "Cobertura", "uso": "cobertura_manutencao"}]
                       + [{"nome": "Tipo %d" % i, "uso": "residencial_dormitorio"}
                          for i in range(4, 0, -1)]),
        "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
        "viga": {"b": 0.20, "h": 0.50},
        "materiais": {"fck": 30e3, "fyk": 500e3},
    }
    txt_e = em.relatorio_pt(em.rodar(copy.deepcopy(spec_e)))
    spec_c = {
        "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                      "pe_direito": 2.7},
        "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
    }
    txt_c = ec.relatorio_pt(ec.rodar(copy.deepcopy(spec_c)))
    linha = alv.linha_memorial_cadeia_gravitacional()
    assert "ausente" not in txt_e and "ausente" not in txt_c, (
        "memorial ainda diz que a NBR 16868 esta ausente do acervo")
    assert linha in txt_e and linha in txt_c
