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
