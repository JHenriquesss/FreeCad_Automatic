"""G61: a alvenaria vira caminho de carga — da laje a sapata corrida.

O G60 entregou o calculo da parede e nenhuma tipologia o consumia. Este lote
fecha o caminho laje -> parede portante (11.2.1) -> baldrame -> sapata
corrida, com a regra do G9 intacta (SPT declarado, sem default de sigma) e
a F21 reescrita para o caso real (parcela, nunca numero).
"""
import copy
import sys
from pathlib import Path

import pytest

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import alvenaria_estrutural as alv
import cargas_nbr6120 as cg
import estrutura_casa as ec
import fundacao_edificio as fe
import fundacao_sapata_corrida as fsc
import projeto_spec as PS
from builtin_adapters import register_builtin_adapters

register_builtin_adapters()


BASE = {
    "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                  "pe_direito": 2.7},
    "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
    "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
    "viga": {"b": 0.20, "h": 0.45},
    "materiais": {"fck": 25e3, "fyk": 500e3},
    "alvenaria_portante": {
        "fpk": 4000.0, "material": "bloco", "te": 0.14,
        "combinacao": "normal", "habitacao_terrea": True,
        "parede_6120": {"tipo": "bloco_concreto_estrutural",
                        "espessura_cm": 14.0, "revestimento_cm": 2.0},
        "linhas": "todas"},
    "baldrame": {"b": 0.15, "h": 0.40,
                 "parede": {"tipo": "bloco_ceramico_furo_horizontal",
                            "espessura_cm": 14, "altura": 2.7,
                            "revestimento_cm": 1.0}},
    "fundacao": {"tipo": "sapata_corrida", "sigma_solo_adm": 150.0,
                 "cota_apoio_m": 1.0},
}


def _spec(**mud):
    s = copy.deepcopy(BASE)
    s.update(copy.deepcopy(mud))
    return s


@pytest.fixture(scope="module")
def rodada():
    return ec.rodar(copy.deepcopy(BASE))


# --- D89: o quarto tipo e fronteira de nome --------------------------------

def test_tipos_fundacao_ganha_a_corrida():
    assert "sapata_corrida" in PS.TIPOS_FUNDACAO
    assert "sapata_corrida" in fe.TIPOS


def test_fundacao_por_pilar_recusa_corrida_com_endereco():
    import copy as _cp
    ctx = {"pilares": [{"nome": "P11", "i": 0, "j": 0, "N_base_k": 100.0,
                        "secao": (0.19, 0.30), "posicao": "canto"}],
           "eixos_x": [0.0, 4.0], "eixos_y": [0.0, 4.0],
           "materiais": {"fck": 25e3, "fyk": 500e3}, "estabilidade": None}
    with pytest.raises(fe.EntradaFundacao, match="sapata_corrida"):
        fe.dimensiona({"tipo": "sapata_corrida", "sigma_solo_adm": 150.0},
                      _cp.deepcopy(ctx))


def test_galpao_recusa_corrida_sem_virar_sapata():
    # D89: a tupla nomeia o quarto tipo e cada consumidor decide em voz alta.
    # O galpao nao tem parede portante: a corrida e recusada com endereco,
    # nunca silenciosamente dimensionada como sapata isolada.
    import galpao_concreto as gc
    with pytest.raises(ValueError, match="sapata_corrida"):
        gc.rodar({"tipo_fundacao": "sapata_corrida"})
    import rodar_galpao as rg
    src = Path(rg.__file__).read_text(encoding="utf-8")
    assert "sapata_corrida" in src and "parede portante" in src
    assert "sapata_corrida" in PS.TIPOS_FUNDACAO


# --- sapata corrida: G9 intacto ---------------------------------------------

def test_corrida_sem_solo_recusa_em_vez_de_arbitrar():
    with pytest.raises(fsc.EntradaCorrida, match="perfil_spt"):
        fsc.dimensiona_corrida(60.0, {})


def test_corrida_spt_deriva_e_declarada_vence():
    spt = {"perfil_spt": [{"tipo": "areia", "N": 15, "dz": 6.0}],
           "cota_apoio_m": 1.0}
    r = fsc.dimensiona_corrida(40.0, spt)
    assert r["aprovado"] is not None
    sig_spt, _ = fsc.sigma_solo(spt, 0.6)
    sig_dec, prov = fsc.sigma_solo({"sigma_solo_adm": 200.0,
                                    "perfil_spt": spt["perfil_spt"]}, 0.6)
    assert sig_dec == 200.0 and "declarada" in prov
    assert sig_spt != 200.0


# --- caminho fechado: total + simetria (licao do G3) -------------------------

def test_fechamento_total_e_simetria_por_linha(rodada):
    fch = rodada["alvenaria"]["fechamento"]
    assert fch["ok"] is True
    assert fch["simetria_ok"] is True
    # gate que confere ZERO pares nao e gate: a malha da fixture e simetrica
    # em y, logo ha par espelhado para conferir.
    assert fch["simetria_pares"] >= 1
    assert fch["pior_erro_linha"] <= 1e-6


def test_fechamento_acusa_carga_no_apoio_errado():
    # O total fecha (140 = 140) e a SIMETRIA acusa: num plano simetrico as
    # duas linhas espelhadas tem de receber o mesmo quinhao. E' a licao do
    # G3 - o fechamento fecha com a carga indo para o apoio errado.
    por = [
        {"nome": "BX-0", "comprimento_m": 10.0, "N_laje_kN": 50.0,
         "Nd_parede_kN": 20.0},
        {"nome": "BX-1", "comprimento_m": 10.0, "N_laje_kN": 50.0,
         "Nd_parede_kN": 20.0},
    ]
    ok = ec.verifica_fechamento_alvenaria(por, 100.0, 2.0,
                                          vaos_x=[10.0], vaos_y=[10.0])
    assert ok["ok"] is True and ok["simetria_pares"] >= 1
    por2 = copy.deepcopy(por)
    por2[0]["N_laje_kN"] = 90.0
    por2[1]["N_laje_kN"] = 10.0
    r = ec.verifica_fechamento_alvenaria(por2, 100.0, 2.0,
                                         vaos_x=[10.0], vaos_y=[10.0])
    assert r["ok"] is False
    assert r["simetria_ok"] is False
    assert r["pior_linha"] in ("BX-0", "BX-1")


# --- o quinhao da laje e o da 14.7.6.1, nao a quota por comprimento ---------

def test_quinhao_da_laje_e_o_da_charneira_nao_o_proporcional_ao_comprimento():
    """Repartir a laje por COMPRIMENTO de parede tira carga da que governa.

    Num painel alongado a borda LONGA recebe mais por metro que a curta
    (charneiras a 45 graus, 14.7.6.1). A quota por comprimento da o mesmo
    kN/m as duas — 11 % a menos na parede longa, contra a seguranca.
    A assercao e RELACAO contra `laje_concreto.reacoes_apoios`, medido no
    mesmo instante, nunca um literal (a licao do AR300).
    """
    import laje_concreto as lj
    s = _spec()
    s["geometria"] = {"vaos_x": [4.0], "vaos_y": [9.0], "pe_direito": 2.7}
    r = ec.rodar(s)
    pav = r["pavimento"]
    p = pav["g_kN_m2"] + pav["q_kN_m2"]
    esperado = lj.reacoes_apoios(1, 4.0, 9.0, p)   # todas as bordas apoiadas
    v_longa = esperado["x0"]["v"]                  # borda de 9 m
    v_curta = esperado["y0"]["v"]                  # borda de 4 m
    assert v_longa > v_curta                       # premissa da medicao
    por = {reg["nome"]: reg["N_laje_kN"] / reg["comprimento_m"]
           for reg in r["alvenaria"]["por_linha"]}
    assert por["BY-0"] == pytest.approx(v_longa, rel=1e-6)
    assert por["BX-0"] == pytest.approx(v_curta, rel=1e-6)
    # e a proporcional ao comprimento (o defeito) seria a MESMA nas duas
    proporcional = pav["carga_laje_total_kN"] / (2 * 4.0 + 2 * 9.0)
    assert por["BY-0"] > proporcional * 1.05


def test_laje_nao_pode_apoiar_em_linha_sem_parede():
    """Apoio que ninguem vai construir sai NOMEADO, nao espalhado.

    Com malha interna e paredes so no contorno, a laje foi calculada em
    paineis apoiados nas linhas internas. Espalhar esse quinhao pelas
    paredes do contorno faria o total fechar sobre um apoio ficticio.
    """
    s = _spec()
    s["alvenaria_portante"] = copy.deepcopy(BASE["alvenaria_portante"])
    s["alvenaria_portante"]["linhas"] = "contorno"
    r = ec.rodar(s)
    erro = r["alvenaria_erro"] or ""
    assert "laje_apoia_em_linha_sem_parede" in erro
    for interna in ("BX-1", "BY-1", "BY-2"):
        assert interna in erro
    assert r["ATENDE"] is False
    assert "alvenaria_portante" in r["reprovados"]


# --- F21 caso real: parcela, relacao, revestimento fora do default -----------

def test_f21_parcela_e_relacao_com_revestimento_fora_do_default():
    tipo, esp, rev, HE, L = "bloco_concreto_estrutural", 14.0, 2.0, 2.7, 3.3
    g = cg.carga_linear_parede(tipo, esp, HE, rev)
    assert g == pytest.approx(cg.peso_alvenaria(tipo, esp, rev) * HE)
    assert alv.confere_fronteira_peso_parcela(
        g * L, tipo, esp, HE, L, rev)["OK"] is True
    assert alv.confere_fronteira_peso_parcela(
        g * L * 1.10, tipo, esp, HE, L, rev)["OK"] is False
    sem_parcela = alv.confere_fronteira_peso_parcela(
        None, tipo, esp, HE, L, rev)
    assert sem_parcela["OK"] is False and "parcela" in sem_parcela["motivo"]


def test_f21_isolada_quebra_com_laje_acima_mas_parcela_fecha(rodada):
    reg = rodada["alvenaria"]["por_linha"][0]
    total_d = reg["N_wall_d_kN"]
    via_total = reg["carga_linear_kN_m"] * reg["comprimento_m"]
    # Nd total (laje + parede, de calculo) nunca bate com o peso da parede:
    # a igualdade isolada do G60 quebra por construcao no caso real.
    assert alv.confere_fronteira_peso(total_d, via_total)["OK"] is False
    # a parcela (caracteristica) fecha: e essa a junta do G61.
    assert reg["junta_peso"]["OK"] is True


# --- gate de verdade + nao saturar (G60 por mutacao) --------------------------

def test_parede_fraca_reprova_a_tipologia():
    s = _spec()
    s["alvenaria_portante"]["fpk"] = 500.0
    r = ec.rodar(s)
    assert r["ATENDE"] is False
    assert "alvenaria_portante" in r["reprovados"]
    assert r["gates"]["alvenaria_portante"]["OK"] is False


def test_lambda_acima_do_teto_reprova_sem_nrdr_na_integracao():
    s = _spec()
    s["geometria"]["pe_direito"] = 4.5
    s["alvenaria_portante"]["habitacao_terrea"] = False
    r = ec.rodar(s)
    assert r["ATENDE"] is False
    v = r["alvenaria"]["por_linha"][0]["verificacao"]
    assert v["veredito"] == "reprovado"
    assert "esbeltez_acima_do_teto" in v["motivo"]
    assert "NRd_kN" not in v


# --- escopo honesto -----------------------------------------------------------

def test_sobrado_em_alvenaria_e_recusado():
    s = _spec(pavimentos=[{"nome": "Cob", "uso": "cobertura_manutencao"},
                          {"nome": "Ter", "uso": "residencial_dormitorio"}])
    with pytest.raises(ec.EntradaEstrutura, match="terrea"):
        ec.rodar(s)


def test_pontual_nao_recebe_carga_linear_e_corrida_exige_parede():
    s = _spec()
    s["fundacao"] = {"sigma_solo_adm": 150.0, "tipo": "sapata"}
    with pytest.raises(ec.EntradaEstrutura, match="LINEAR"):
        ec.rodar(s)
    s2 = _spec()
    del s2["alvenaria_portante"]
    s2["fundacao"] = {"tipo": "sapata_corrida", "sigma_solo_adm": 150.0}
    with pytest.raises(ec.EntradaEstrutura, match="sapata_corrida"):
        ec.rodar(s2)


def test_escopo_honesto(rodada):
    esc = rodada["escopo"]
    assert esc["alvenaria_estrutural"] == "implemented"
    assert esc["viga"] == esc["pilar"] == "not_available"
    r_conc = ec.rodar({
        "geometria": BASE["geometria"],
        "pavimentos": BASE["pavimentos"], "laje": BASE["laje"],
        "viga": BASE["viga"], "materiais": BASE["materiais"]})
    assert r_conc["escopo"]["alvenaria_estrutural"] == "not_available"


def test_casa_portante_roda_atende_com_memorial(rodada):
    assert rodada["ATENDE"], rodada["reprovados"]
    assert rodada["tipologia"] == "alvenaria_terrea"
    assert rodada["fundacao"]["tipo"] == "sapata_corrida"
    txt = ec.relatorio_pt(rodada)
    assert "ALVENARIA PORTANTE" in txt and "sapata_corrida" in txt


# --- ponta a ponta inventada (molde G52) --------------------------------------

def test_ponta_a_ponta_orcamento_cronograma_pacote(tmp_path):
    import gestao_casa as gc
    r = ec.rodar(copy.deepcopy(BASE))
    assert r["ATENDE"], r["reprovados"]
    hid = {"cobertura": {"area_m2": 95.0},
           "aparelhos_agua": {"chuveiro": 1, "lavatorio": 1},
           "aparelhos_esgoto": {"vaso": 1, "lavatorio": 1}}
    elt = {"circuits": {"points": [
        {"id": "L1", "kind": "lighting"}, {"id": "T1", "kind": "tug"}]}}
    result = {"estrutura": r, "hidraulica": {"redes": {"ok": True}},
              "eletrico": elt, "arquitetura": {"ambientes": []}}
    dados = gc.derivacao(result, hid)
    assert dados["quantitativos"]["alvenaria_estrutural"] > 0
    assert dados["quantitativos"]["fundacao_concreto"] > 0

    manifest = {"deliverables": {}, "artifacts": []}
    run_dir = tmp_path / "run-g61"
    run_dir.mkdir()
    normalized = {"turnkey_spec": {"estrutura": {"pavimentos": [1]},
                                  "hidraulica": hid}}
    gc.emitir_orcamento(manifest, str(run_dir), normalized, {}, result)
    orc = manifest["deliverables"]["orcamento"]
    assert orc["status"] in ("generated", "partial")
    planilha = run_dir / orc["artifacts"][0]
    texto = planilha.read_text(encoding="utf-8")
    assert "alvenaria_estrutural" in texto
    assert "fundacao_concreto" in texto

    gc.emitir_cronograma(manifest, str(run_dir), normalized, {}, result)
    cro = manifest["deliverables"]["cronograma"]
    assert cro["status"] == "generated"
    crono_txt = (run_dir / cro["artifacts"][0]).read_text(encoding="utf-8")
    assert "vedacao" in crono_txt or "fund" in crono_txt

    gc.emitir_caderno_encargos(manifest, str(run_dir), normalized, {}, result)
    cad = manifest["deliverables"]["caderno_encargos"]
    assert cad["status"] == "generated"

    gc.emitir_pacote_legal(manifest, str(run_dir), normalized, {}, result)
    pac = manifest["deliverables"]["pacote_legal"]
    assert pac["status"] == "generated"
    dados_pac = __import__("json").loads(
        (run_dir / pac["artifacts"][1]).read_text(encoding="utf-8"))
    texto_pac = (run_dir / pac["artifacts"][0]).read_text(encoding="utf-8")
    assert "Veredito global:** ATENDE" in texto_pac
    assert "alvenaria_terrea" in texto_pac


# --- a corrida: direcao da Parte B e o concreto no portao -------------------

def test_parte_b_arma_a_direcao_que_tem_balanco():
    """B e a largura TRANSVERSAL; o balanco ao longo do muro e ZERO.

    Trocar B por L quando B > 1 m (para manter "B = menor lado") troca as
    direcoes: o unico balanco real, (B - b_ped)/2, passaria a ser medido ao
    longo do muro. A assercao e geometrica — compara com a faixa montada a
    mao, no mesmo instante — e nao um numero congelado.
    """
    import fundacao_sapata as fsap
    q, spec = 300.0, {"sigma_solo_adm": 200.0}
    r = fsc.dimensiona_corrida(q, spec)
    B, h, _rA, _ = r["aprovado"]
    assert B > 1.0, "o caso escolhido tem de exercitar B > 1 m"
    pb = r["parte_B"]
    assert (pb["B"], pb["L"]) == (B, 1.0)
    assert pb["ap_L"] == 1.0          # pedestal cobre a faixa inteira
    assert pb["ap_B"] < B             # balanco transversal existe
    esperado = fsap.dimensiona_sapata_B(
        {"N": q, "V": 0.0, "M": 0.0, "fck": 25e3, "fyk": 500e3,
         "cobrimento": 0.05, "gamma_f": 1.4,
         "d_ped": 1.0, "b_ped": pb["ap_B"]},
        {"B": B, "L": 1.0, "h": h})
    assert pb["rigida"] == esperado["rigida"]
    assert pb["flexao_B"]["As_adot"] == pytest.approx(
        esperado["flexao_B"]["As_adot"], rel=1e-9)


def test_largura_adotada_passa_no_solo_E_no_concreto():
    """Parte B era calculada e nunca consultada (o irmao do G13)."""
    r = fsc.dimensiona_corrida(60.0, {"sigma_solo_adm": 150.0})
    B, h, rA, _ = r["aprovado"]
    assert rA["OK_A"] is True and rA["OK_B"] is True
    assert r["parte_B"]["OK_B"] is True
    # escada em que o concreto reprova: h ridiculo para a largura
    magra = fsc.dimensiona_corrida(
        300.0, {"sigma_solo_adm": 200.0}, escada=[(2.00, 0.10)])
    linha = magra["linhas"][0]
    assert linha["OK_A"] is True, "o solo passa; quem reprova e o concreto"
    assert linha["OK_B"] is False
    assert magra["aprovado"] is None, "largura reprovada no concreto nao e adotada"
    assert "concreto" in magra["tabela"]


def test_peca_flexivel_sai_nomeada_no_resultado():
    """h abaixo de (B - ap)/3: a peca e FLEXIVEL e isso e dito, nao omitido."""
    r = fsc.dimensiona_corrida(300.0, {"sigma_solo_adm": 200.0})
    if r["parte_B"]["rigida"]:
        pytest.skip("a escada adotou peca rigida neste caso")
    assert r["parte_B"]["flag_flexivel"]
    fund = ec.dimensiona_fundacao_corrida_por_linha(
        {"BX-0": 300.0}, {"sigma_solo_adm": 200.0, "cota_apoio_m": 1.0})
    codes = [a["code"] for a in fund["avisos"]]
    assert "corrida_flexivel" in codes
