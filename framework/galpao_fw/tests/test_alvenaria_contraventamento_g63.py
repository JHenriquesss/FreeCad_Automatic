"""G63 (depois do G61): acao horizontal por contraventamento de rigidez.

O que cada teste prova, e contra que defeito:
  flange 6t (10.1.3) -> bf adotada capa em 6.te como RELACAO (nao numero
    congelado); flange acima do cap nao aumenta o I em silencio.
  distribuicao (9.6.2) -> Fi proporcional a k = Ea.I/he^3, provada como
    relacao entre funcoes do modulo (quota via rigidez_parede); he maior
    recebe menos (1/he^3).
  fechamento -> soma(Fi) bate com Qh (relacao, nunca numero); soma
    adulterada acusa, com a parede nomeada.
  sem rigidez -> parede sem dado declaravel aparece NOMEADA no motivo e
    na lista, e o resultado recusa (nao some em silencio, nao zera vento).
  Qh avulsa -> continua recusando na 11.2 (regressao: melhor recusar que
    zerar o vento).
  11.5 -> compressao pura coincide com a 11.2.1; fail-closed nos dois
    lados do Md de fronteira; tracao sem As reprova nomeando T; errata
    (Es/Ea + fyd) afirmada como relacao.
  Anexo C -> Md,total amplifica Md1 (P-Delta) como relacao; Nd >= Ncr
    reprova (flambagem); campo so acima de 30; sem As recusa.
  D84 -> estabilidade_b1b2 nao e importada nem aparentada: o modulo nao
    importa o reticulado de aco e o reticulado nao cita a 16868.
"""
import sys
from pathlib import Path

import pytest

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import alvenaria_estrutural as alv  # noqa: E402


FPK = 4000.0
FYK = 500e3
HE = 2.70
TE = 0.14


def _paredes_2():
    return [{"nome": "PX-1", "comprimento_m": 3.0, "te_m": TE, "he_m": HE},
            {"nome": "PX-2", "comprimento_m": 1.5, "te_m": TE, "he_m": HE}]


def test_flange_cap_6t_1013_como_relacao():
    sec = alv.secao_efetiva_contraventamento(3.0, TE, 2.0, 2.0)
    cap = 6.0 * TE
    assert sec["bf_esq_adotada_m"] == pytest.approx(cap)
    assert sec["bf_dir_adotada_m"] == pytest.approx(cap)
    assert sec["flange_capada"] is True
    # abaixo do cap nao capa e entra cheia na area
    sec2 = alv.secao_efetiva_contraventamento(3.0, TE, 0.50, 0.0)
    assert sec2["flange_capada"] is False
    assert sec2["A_eff_m2"] == pytest.approx(TE * 3.0 + 0.50 * TE)
    # flange acima do cap nao aumenta o I em silencio: 2 m == cap
    sec3 = alv.secao_efetiva_contraventamento(3.0, TE, cap, 0.0)
    assert sec["I_eff_m4"] != pytest.approx(
        alv.secao_efetiva_contraventamento(3.0, TE)["I_eff_m4"])
    sec_cap = alv.secao_efetiva_contraventamento(3.0, TE, cap, cap)
    sec_acima = alv.secao_efetiva_contraventamento(3.0, TE, 2.0, 2.0)
    assert sec_cap["I_eff_m4"] == pytest.approx(sec_acima["I_eff_m4"])
    # sem flange: retangulo puro
    sec0 = alv.secao_efetiva_contraventamento(3.0, TE)
    assert sec0["I_eff_m4"] == pytest.approx(TE * 3.0 ** 3 / 12.0)
    assert sec0["A_eff_m2"] == pytest.approx(TE * 3.0)


def test_distribuicao_proporcional_a_rigidez_962():
    qh = 30.0
    d = alv.distribuir_horizontal_por_rigidez(qh, _paredes_2())
    assert d["OK"] is True and d["veredito"] == "distribuida"
    # quotas via as funcoes do modulo (relacao, nunca numero congelado)
    ks = []
    for p in _paredes_2():
        sec = alv.secao_efetiva_contraventamento(p["comprimento_m"], TE)
        ks.append(alv.rigidez_parede(sec["I_eff_m4"], HE))
    k_tot = sum(ks)
    for r, k in zip(d["por_parede"], ks):
        assert r["quota"] == pytest.approx(k / k_tot)
        assert r["Fi_kN"] == pytest.approx(qh * k / k_tot, abs=1e-6)
    assert d["soma_Fi_kN"] == pytest.approx(qh, abs=1e-6)
    assert d["paredes_sem_rigidez"] == []
    # a parede longa (mais rigida) leva mais
    fis = {r["nome"]: r["Fi_kN"] for r in d["por_parede"]}
    assert fis["PX-1"] > fis["PX-2"]


def test_he_maior_recebe_menos():
    pars = [{"nome": "baixa", "comprimento_m": 2.0, "te_m": TE, "he_m": 2.7},
            {"nome": "alta", "comprimento_m": 2.0, "te_m": TE, "he_m": 5.4}]
    d = alv.distribuir_horizontal_por_rigidez(20.0, pars)
    assert d["OK"] is True
    fis = {r["nome"]: r["Fi_kN"] for r in d["por_parede"]}
    assert fis["baixa"] > fis["alta"]
    # k ~ 1/he^3: dobrando he, quota cai ~8x (relacao entre paredes iguais)
    assert fis["baixa"] / fis["alta"] == pytest.approx(8.0, rel=1e-6)


def test_fechamento_horizontal_acusa_soma_adulterada():
    d = alv.distribuir_horizontal_por_rigidez(30.0, _paredes_2())
    assert alv.confere_fechamento_horizontal(d, 30.0)["OK"] is True
    # adultera uma Fi: a guarda acusa em vez de fechar
    adulterada = [{"Fi_kN": r["Fi_kN"]} for r in d["por_parede"]]
    adulterada[0]["Fi_kN"] *= 1.10
    f = alv.confere_fechamento_horizontal(adulterada, 30.0)
    assert f["OK"] is False
    assert "fechamento_horizontal_diverge" in f["motivo"]
    # e nao e coincidencia: dobrando Qh a soma dobra (relacao)
    d2 = alv.distribuir_horizontal_por_rigidez(60.0, _paredes_2())
    assert d2["soma_Fi_kN"] == pytest.approx(2 * d["soma_Fi_kN"], abs=1e-6)


def test_parede_sem_rigidez_aparece_nomeada_e_recusa():
    pars = [{"nome": "PX-1", "comprimento_m": 3.0, "te_m": TE, "he_m": HE},
            {"nome": "PX-fantasma"}]
    d = alv.distribuir_horizontal_por_rigidez(10.0, pars)
    assert d["OK"] is False
    assert d["veredito"] == "recusado"
    assert "PX-fantasma" in d["paredes_sem_rigidez"]
    assert "PX-fantasma" in d["motivo"]
    assert "parede_sem_rigidez_declarada" in d["motivo"]
    # a valida continua repartindo sozinha e o fechamento entre validas fecha
    assert len(d["por_parede"]) == 1
    assert d["soma_Fi_kN"] == pytest.approx(10.0, abs=1e-6)


def test_entradas_malformadas_da_distribuicao_recusam_com_endereco():
    with pytest.raises(alv.EntradaAlvenaria, match="qh_nao_declarada"):
        alv.distribuir_horizontal_por_rigidez(None, _paredes_2())
    with pytest.raises(alv.EntradaAlvenaria, match="paredes_nao_declaradas"):
        alv.distribuir_horizontal_por_rigidez(10.0, [])
    with pytest.raises(alv.EntradaAlvenaria, match="nome_duplicado"):
        alv.distribuir_horizontal_por_rigidez(
            10.0, [_paredes_2()[0], dict(_paredes_2()[0])])
    # nenhuma parede com rigidez: recusa nomeada, sem soma fantasma
    d = alv.distribuir_horizontal_por_rigidez(10.0, [{"nome": "X"}])
    assert d["OK"] is False
    assert "nenhuma_parede_com_rigidez" in d["motivo"]


def test_qh_avulsa_continua_recusando_na_112_regressao():
    r = alv.verifica_parede_compressao(10.0, FPK, HE, TE, TE * 1.0,
                                       acao_horizontal_kN=5.0)
    assert r["OK"] is False and r["veredito"] == "recusado"
    assert "acao_horizontal_exige_contraventamento" in r["motivo"]
    assert "distribuir_horizontal_por_rigidez" in r["motivo"]


def test_flexo_115_compressao_pura_coincide_com_1121():
    Nd = 100.0
    r115 = alv.verifica_flexo_compressao_115(Nd, 0.0, FPK, HE, TE, 1.0)
    r112 = alv.verifica_parede_compressao(Nd, FPK, HE, TE, TE * 1.0)
    assert r115["OK"] is True and r112["OK"] is True
    assert r115["sigma_max_kN_m2"] == pytest.approx(Nd / (TE * 1.0), abs=1.0)
    # fail-closed nos dois lados do Md de fronteira (relacao, nao numero)
    cap = r115["cap_compressao_kN_m2"]
    W = TE * 1.0 ** 2 / 6.0
    md_fronteira = (cap - Nd / (TE * 1.0)) * W
    assert alv.verifica_flexo_compressao_115(
        Nd, md_fronteira * 0.999, FPK, HE, TE, 1.0)["OK"] is True
    assert alv.verifica_flexo_compressao_115(
        Nd, md_fronteira * 1.001, FPK, HE, TE, 1.0)["OK"] is False


def test_flexo_115_tracao_sem_armadura_reprova_nomeando_T():
    r = alv.verifica_flexo_compressao_115(20.0, 15.0, FPK, HE, TE, 3.0)
    assert r["OK"] is False
    assert "flexo_tracao_sem_armadura" in r["motivo"]
    assert r["tracao_kN"] > 0
    # com As + fyk a mesma parede passa (o aco leva T)
    r2 = alv.verifica_flexo_compressao_115(20.0, 15.0, FPK, HE, TE, 3.0,
                                           As=4e-4, fyk=FYK)
    assert r2["OK"] is True, r2["motivo"]
    assert r2["Ts_kN"] > r2["tracao_kN"]
    # armada sem fyk recusa: sem ensaio declarado nao ha fs
    with pytest.raises(alv.EntradaAlvenaria, match="fyk_nao_declarado"):
        alv.verifica_flexo_compressao_115(20.0, 15.0, FPK, HE, TE, 3.0,
                                          As=4e-4)


def test_flexo_115_errata_como_relacao():
    r = alv.verifica_flexo_compressao_115(20.0, 15.0, FPK, HE, TE, 3.0,
                                          As=4e-4, fyk=FYK)
    Ea = alv.modulo_deformacao(FPK, "bloco_concreto")
    fs_esperada = min(FPK * alv.ES_ACO_KNM2 / Ea, FYK) / 1.15
    assert r["fs_kN_m2"] == pytest.approx(fs_esperada, abs=1e-3)
    assert r["errata_Ea_fyd_aplicada"] is True
    # pre-errata usaria fyk cheio: valor diferente por um gamma
    assert r["fs_kN_m2"] != pytest.approx(FYK / 1.0, rel=1e-3)


def test_anexo_C_amplifica_PDelta_como_relacao():
    c = alv.verifica_parede_esbelta_anexo_C(50.0, 2.0, FPK, 5.0, TE, 2.0,
                                            4e-4, FYK)
    Ea = alv.modulo_deformacao(FPK, "bloco_concreto")
    ncr = (3.141592653589793 ** 2 * Ea * (2.0 * TE ** 3 / 12.0) / 5.0 ** 2)
    assert c["Ncr_kN"] == pytest.approx(ncr, abs=1e-3)
    assert c["amplificacao_PDelta"] == pytest.approx(1 / (1 - 50.0 / ncr),
                                                    abs=1e-4)
    assert c["Md_total_kNm"] == pytest.approx(
        2.0 / (1 - 50.0 / ncr), abs=1e-3)
    assert c["Md_total_kNm"] > 2.0
    assert c["errata_Ea_fyd_aplicada"] is True


def test_anexo_C_flambagem_reprova_e_campo_e_armado():
    c = alv.verifica_parede_esbelta_anexo_C(50.0, 2.0, FPK, 5.0, TE, 2.0,
                                            4e-4, FYK)
    ncr = c["Ncr_kN"]
    f = alv.verifica_parede_esbelta_anexo_C(ncr * 1.10, 2.0, FPK, 5.0, TE,
                                            2.0, 4e-4, FYK)
    assert f["OK"] is False and "flambagem_anexo_C" in f["motivo"]
    # campo: so acima de 30
    with pytest.raises(alv.EntradaAlvenaria, match="anexo_C_so_acima_30"):
        alv.verifica_parede_esbelta_anexo_C(50.0, 2.0, FPK, HE, TE, 2.0,
                                            4e-4, FYK)
    # sem armadura o Anexo C nao tem objeto
    with pytest.raises(alv.EntradaAlvenaria, match="parede_armada"):
        alv.verifica_parede_esbelta_anexo_C(50.0, 2.0, FPK, 5.0, TE, 2.0,
                                            0.0, FYK)
    # alias legado sem esforcos indica o endereco novo
    with pytest.raises(alv.EntradaAlvenaria, match="anexo_C_pede_esforcos"):
        alv.verifica_parede_armada_anexo_C()


def test_escopo_g63_implemented_e_cisalhamento_nomeado():
    esc = alv.escopo()
    for chave in ("flexo_compressao_11_5", "parede_muito_esbelta_anexo_C",
                  "acao_horizontal_contraventamento"):
        assert esc[chave] == "implemented", chave
        assert alv.motivos_escopo()[chave], chave
    assert esc["cisalhamento_11_4"] == "not_available"
    assert "11.4" in alv.motivos_escopo()["cisalhamento_11_4"]


def test_d84_b1b2_nao_e_parentesco():
    src_alv = Path(alv.__file__).read_text(encoding="utf-8")
    assert "import estabilidade_b1b2" not in src_alv
    assert "from estabilidade_b1b2" not in src_alv
    src_b1b2 = (Path(alv.__file__).parent / "estabilidade_b1b2.py").read_text(
        encoding="utf-8")
    assert "16868" not in src_b1b2


def test_cadeia_horizontal_ponta_a_ponta():
    # Qh reparte, cada parede leva Md = Fi.he e passa na 11.5 com o Nd
    # gravitacional; o fechamento confere. Carga leve de proposito: o que
    # se prova e a CADEIA, nao um numero.
    qh = 12.0
    d = alv.distribuir_horizontal_por_rigidez(qh, _paredes_2())
    assert d["OK"] is True
    assert alv.confere_fechamento_horizontal(d, qh)["OK"] is True
    for r in d["por_parede"]:
        md = r["Fi_kN"] * HE
        v = alv.verifica_flexo_compressao_115(
            60.0, md, FPK, HE, TE, r["comprimento_m"], Vd_kN=r["Fi_kN"])
        assert v["OK"] is True, (r["nome"], v["motivo"])
        assert v["Vd_kN"] == pytest.approx(r["Fi_kN"])
        assert v["peso_proprio_interno_kN"] == 0.0


def test_selftest_do_modulo():
    assert alv._selftest() is True
