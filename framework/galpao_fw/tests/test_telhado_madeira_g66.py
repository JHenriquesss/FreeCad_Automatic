"""G66: o telhado de madeira da casa (NBR 7190-1:2022, F136).

A casa tinha laje, viga, pilar, fundacao e parede portante - e nao tinha
telhado. Cada teste abre o numero (relacao, nunca congelado, molde G52) e
o vermelho-por-injecao garante que o defeito volta a reprovar.
"""

import copy
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import estrutura_casa as ec
import gestao_casa as gc
import madeira_nbr7190 as mad
import telhado_casa_madeira as tmad

ROOT = Path(__file__).resolve().parents[3]
SPEC_PERSISTIDO = ROOT / "projects" / "casa-residencial" / "project-spec.json"

REVEST = 1.6
PAREDE = {"tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14,
          "altura": 2.7, "revestimento_cm": 2.0}

TELHADO_VIGA = {
    "vao": 8.0, "inclinacao_graus": 25.0, "extensao": 10.4,
    "espacamento": 2.0, "n_paineis": 2,
    "telha": {"tipo": "ondulada", "peso": 0.55},
    "sobrecarga_kNm2": 0.25,
    "madeira": {"classe": "C24", "carregamento": "curta", "umidade": 2,
                "categoria": "serrada"},
    "secoes": {
        "banzo_sup": {"b": 0.08, "h": 0.16},
        "banzo_inf": {"b": 0.06, "h": 0.16},
        "diagonal": {"b": 0.06, "h": 0.12},
        "montante": {"b": 0.06, "h": 0.12},
        "terca": {"b": 0.06, "h": 0.16}},
    "apoio": "viga",
    "travamento_borda_comprimida_m": 2.0,
    "contraventamento_banzo_inf": True,
    "apoio_comprimento_m": 0.2,
    "ligacao": {
        "tipo_pino": "parafuso", "d_mm": 12.0, "fu_MPa": 415.0,
        "t_chapa_mm": 6.3,
        "n_pinos": 4, "config_73": "chapa_central_dupla",
        "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                         "a3c": 80, "a4t": 60, "a4c": 60},
        "he_mm": 90.0},
}

TELHADO_PAREDE = dict(copy.deepcopy(TELHADO_VIGA), apoio="parede")


def _casa_concreto(telhado=None):
    spec = {
        "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                      "pe_direito": 2.7},
        "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": REVEST},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
        "parede_sobre_vigas": dict(PAREDE),
        "baldrame": {"b": 0.15, "h": 0.40, "parede": dict(PAREDE)},
    }
    if telhado is not None:
        spec["telhado_madeira"] = telhado
    return spec


ALVENARIA = {
    "fpk": 4000.0, "material": "bloco", "te": 0.14,
    "combinacao": "normal", "habitacao_terrea": True,
    "parede_6120": {"tipo": "bloco_ceramico_furo_horizontal",
                    "espessura_cm": 14, "revestimento_cm": 2.0,
                    "altura_m": 2.7},
    "linhas": "contorno",
}


def _casa_portante(telhado=None):
    spec = {
        "geometria": {"vaos_x": [4.0], "vaos_y": [3.0],
                      "pe_direito": 2.7},
        "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": REVEST},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
        "alvenaria_portante": dict(ALVENARIA),
        "baldrame": {"b": 0.15, "h": 0.40, "parede": dict(PAREDE)},
        "fundacao": {"tipo": "sapata_corrida", "cota_apoio_m": 1.0,
                     "sigma_solo_adm": 150.0,
                     "sigma_solo_proveniencia": "ensaio declarada no teste"},
    }
    if telhado is not None:
        spec["telhado_madeira"] = telhado
    return spec


def _telhado_portante():
    tel = copy.deepcopy(TELHADO_PAREDE)
    tel.update(vao=3.0, extensao=4.0, espacamento=2.0, n_paineis=1)
    return tel


# --- NBR 7190-1: classes e kmod ----------------------------------------------

def test_tab3_transcrita_C24_e_D40():
    p = mad.propriedades_classe("C24")
    assert (p["fbk_MPa"], p["ft0k_MPa"], p["fc0k_MPa"],
            p["fvk_MPa"]) == (24, 14, 21, 4.0)
    assert (p["E0m_GPa"], p["E005_GPa"], p["rhok"]) == (11, 7.4, 350)
    assert p["conifera"] is True
    d = mad.propriedades_classe("D40")
    assert (d["fbk_MPa"], d["fc90k_MPa"], d["fvk_MPa"]) == (40, 8.3, 4.0)
    assert d["conifera"] is False


def test_classe_sem_default_recusa_e_tab2_tem_endereco():
    for ruim in (None, "", "C99"):
        with pytest.raises(mad.EntradaMadeira):
            mad.propriedades_classe(ruim)
    with pytest.raises(mad.EntradaMadeira, match="7190-3"):
        mad.propriedades_classe("D20")
    with pytest.raises(mad.EntradaMadeira, match="fora do lote"):
        mad.kmod("longa", 2, "MLC")


def test_kmod_e_tabelas():
    assert mad.kmod("longa", 2, "serrada")["kmod"] == pytest.approx(0.63)
    assert mad.kmod("media", 1, "recomposta")["kmod"] == pytest.approx(0.65)
    assert mad.kmod("curta", 2, "serrada")["kmod"] == pytest.approx(0.81)
    with pytest.raises(mad.EntradaMadeira):
        mad.kmod("eterna", 2, "serrada")
    with pytest.raises(mad.EntradaMadeira):
        mad.kmod("curta", 5, "serrada")


def test_resistencia_de_calculo_e_gamma_do_cisalhamento():
    r = mad.resistencias_calculo(mad.propriedades_classe("C24"), 0.90)
    assert r["fmd"] == pytest.approx(0.90 * 24000 / 1.4)
    assert r["fv0d"] == pytest.approx(0.90 * 4000 / 1.8)


def test_verificacoes_contra_a_mao():
    assert mad.verifica_tracao(20.0, 0.005, 9000.0)["OK"]
    assert mad.verifica_tracao(50.0, 0.005, 9000.0)["OK"] is False
    assert mad.verifica_cisalhamento(6.0, 0.012, 2000.0)["OK"]
    assert abs(mad.verifica_cisalhamento(6.0, 0.012, 2000.0)["tau_kNm2"]
               - 750.0) < 1e-9
    # 6.5.6: a dispensa e' CONFERIDA (Tab.8), nao declarada. Mesma viga,
    # mesma secao: com travamento a cada 2 m dispensa; a 6 m, nao.
    prop = mad.propriedades_classe("C24")
    perto = mad.dispensa_estabilidade_lateral_656(
        0.06, 0.16, 2.0, prop["E0m"], 20000.0, 0.81)
    longe = mad.dispensa_estabilidade_lateral_656(
        0.06, 0.16, 6.0, prop["E0m"], 20000.0, 0.81)
    assert perto["dispensada"] and not longe["dispensada"]
    assert perto["L1_limite_m"] == pytest.approx(longe["L1_limite_m"])
    assert 2.0 < perto["L1_limite_m"] < 6.0
    assert mad.verifica_flexao(5.0, 0.001, 20000.0, perto)["OK"]
    sem_trava = mad.verifica_flexao(5.0, 0.001, 20000.0, longe)
    assert sem_trava["OK"] is False and "6.5.6-b" in sem_trava["motivo"]
    # a flag booleana nao e' aceita como conferencia.
    with pytest.raises(mad.EntradaMadeira, match="6.5.6"):
        mad.verifica_flexao(5.0, 0.001, 20000.0, True)


def test_compressao_com_estabilidade_reprova_esbelta():
    prop = mad.propriedades_classe("C24")
    res = mad.resistencias_calculo(prop, 0.81)
    # peca curta: passa na resistencia e dispensa estabilidade.
    curta = mad.verifica_compressao(10.0, 0.01, res["fc0d"], 10.0,
                                    prop["fc0k_d0"], prop["E005"])
    assert curta["OK"] and curta["kc"] == 1.0
    # lambda > 140: reprova com o artigo, nao com numero mudo.
    alta = mad.verifica_compressao(1.0, 0.01, res["fc0d"], 150.0,
                                   prop["fc0k_d0"], prop["E005"])
    assert alta["OK"] is False and "140" in alta["motivo"]
    # intermediaria: kc < 1 aperta a utilizacao.
    media = mad.verifica_compressao(10.0, 0.01, res["fc0d"], 80.0,
                                    prop["fc0k_d0"], prop["E005"])
    assert media["kc"] < 1.0
    assert (media["util_estabilidade"]
            > media["util_resistencia"])


def test_embutimento_hankinson_e_pino():
    fe0 = mad.embutimento_fek(12.0, 350.0, True, True, 0.0)
    fe90 = mad.embutimento_fek(12.0, 350.0, True, True, 90.0)
    assert fe90["fe_k_Nmm2"] == pytest.approx(
        fe0["fe0_k_Nmm2"] / fe0["k90"])
    assert fe90["fe_k_Nmm2"] < fe0["fe_k_Nmm2"]
    assert mad.pino_Myk_Nmm(415.0, 12.0) == pytest.approx(
        0.3 * 415.0 * 12.0 ** 2.6)
    assert mad.n_efetivo(11) == pytest.approx(10.0)
    with pytest.raises(mad.EntradaMadeira):
        mad.n_efetivo(1)


def test_ligacao_73_teto_do_kmod1_e_geometria():
    fe = mad.embutimento_fek(12.0, 350.0, True, True, 0.0)["fe_k_Nmm2"]
    cfg = {"config_73": "chapa_central_dupla", "tipo_pino": "parafuso",
           "d_mm": 12.0, "fu_MPa": 415.0, "t1_mm": 160.0, "t2_mm": 160.0,
           "fe1_Nmm2": fe, "fe2_Nmm2": fe, "n_pinos": 4, "n_planos": 2,
           "kmod1": 1.10, "kmod2": 0.90,
           "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                            "a3c": 80, "a4t": 60, "a4c": 60},
           "alpha_graus": 0.0, "t_madeira_mm": 80.0,
           "penetracao_mm": 80.0, "t_chapa_mm": 6.3}
    r = mad.verifica_ligacao(10.0, cfg)
    assert r["kmod1_usado"] == 1.0  # 7.1.2: teto no aco
    assert r["Rd_kN"] == pytest.approx(
        1.0 * 0.90 * r["Rk_N"] / 1.4 / 1000.0)
    assert r["OK"] and r["falhas_geometria"] == []
    fina = dict(cfg, t_madeira_mm=20.0)
    r2 = mad.verifica_ligacao(1.0, fina)
    assert r2["OK"] is False and any("7.2-a" in m
                                    for m in r2["falhas_geometria"])


# --- tesoura ------------------------------------------------------------------

def test_geometria_cumeeira_simetria_e_contagem():
    g = tmad.geometria(8.0, 25.0, 2)
    assert g["h_cumeeira"] == pytest.approx(4.0 * math.tan(math.radians(25)))
    assert len(g["barras"]) == 2 * len(g["nos"]) - 3
    comp = tmad.comprimentos(g)
    for (n1, n2, _g), L in comp.items():
        assert L > 0, (n1, n2)
    # simetria: TL1-B2 espelha TR1-B2.
    assert comp[("TL1", "B2", "diagonal")] == pytest.approx(
        comp[("TR1", "B2", "diagonal")])
    assert g["nos"]["C"][1] == pytest.approx(g["h_cumeeira"])


def test_fechamento_reacoes_batem_com_o_lancado():
    r = tmad.rodar(copy.deepcopy(TELHADO_VIGA))
    f = r["gates"]["fechamento_carga"]
    assert f["OK"] and f["erro_rel"] <= 0.02
    assert r["descida"]["W_total_kN"] == pytest.approx(f["lancado_kN"] * 6,
                                                      rel=1e-3)


def test_tesoura_atende_e_nomeia_carga():
    r = tmad.rodar(copy.deepcopy(TELHADO_VIGA))
    assert r["ATENDE"] is True, r["reprovados"]
    assert r["n_tesouras"] == 6
    assert r["vol_madeira_m3"] > 0 and r["area_telha_m2"] > 0


def test_secao_insuficiente_reprova_com_nome():
    fraca = copy.deepcopy(TELHADO_VIGA)
    fraca["secoes"]["banzo_sup"] = {"b": 0.04, "h": 0.10}
    r = tmad.rodar(fraca)
    assert r["ATENDE"] is False
    assert any("banzo_sup" in m
               for m in r["gates"]["barras"]["reprovadas"])


def test_detalhe_inconsistente_recusa_com_endereco():
    ruim = copy.deepcopy(TELHADO_VIGA)
    ruim["secoes"]["banzo_sup"] = {"b": 0.04, "h": 0.06}
    with pytest.raises(tmad.EntradaTelhado, match="he_mm"):
        tmad.rodar(ruim)


def test_telhado_sem_peso_e_sem_classe_recusa():
    sem_peso = copy.deepcopy(TELHADO_VIGA)
    sem_peso["telha"] = {"tipo": "ondulada", "peso": None}
    with pytest.raises(tmad.EntradaTelhado):
        tmad.rodar(sem_peso)
    sem_classe = copy.deepcopy(TELHADO_VIGA)
    del sem_classe["madeira"]["classe"]
    with pytest.raises(tmad.EntradaTelhado):
        tmad.rodar(sem_classe)


# --- costura com a casa ---------------------------------------------------------

def test_sem_telhado_escopo_e_relatorio_dizem_a_verdade():
    r = ec.rodar(_casa_concreto())
    assert r["escopo"]["telhado_madeira"] == "not_available"
    assert "telhado_madeira" not in r["gates"]
    assert "[A CONFIRMAR: estrutura de telhado em madeira fora do escopo.]" \
        in ec.relatorio_pt(r)


def test_concreto_com_telhado_desce_e_fecha():
    r = ec.rodar(_casa_concreto(copy.deepcopy(TELHADO_VIGA)))
    assert r["escopo"]["telhado_madeira"] == "implemented"
    assert r["gates"]["telhado_madeira"]["OK"] is True
    f = r["gates"]["fechamento_carga"]
    assert f["OK"] is True, f
    assert f["telhado_total_kN"] == pytest.approx(
        r["telhado"]["descida"]["W_total_kN"])
    assert f["N_desc_total_k"] == pytest.approx(f["esperado_total_k"],
                                               rel=1e-3)
    texto = ec.relatorio_pt(r)
    assert "TELHADO DE MADEIRA (G66" in texto
    assert "[A CONFIRMAR: estrutura de telhado em madeira" not in texto


def test_telhado_que_nao_cobre_a_malha_recusa():
    errada = copy.deepcopy(TELHADO_VIGA)
    errada["vao"] = 5.0
    with pytest.raises(ec.EntradaEstrutura, match="nao cobre a malha"):
        ec.rodar(_casa_concreto(errada))
    trocada = copy.deepcopy(TELHADO_PAREDE)
    with pytest.raises(ec.EntradaEstrutura, match="cinta do topo"):
        ec.rodar(_casa_concreto(trocada))


def test_portante_com_telhado_sobe_a_parede_e_a_corrida():
    sem = ec.rodar(_casa_portante())
    com = ec.rodar(_casa_portante(_telhado_portante()))
    assert com["escopo"]["telhado_madeira"] == "implemented"
    assert com["gates"]["telhado_madeira"]["OK"] is True
    assert com["gates"]["fechamento_carga"]["OK"] is True
    q_sem = sem["q_fundacao_linear_kN_m"]
    q_com = com["q_fundacao_linear_kN_m"]
    assert set(q_com) == set(q_sem) and q_com
    nomes = [n for n in q_com if q_com[n] > q_sem[n]]
    assert nomes, "o telhado nao chegou a fundacao corrida"
    tel = com["telhado"]["descida"]["W_total_kN"]
    # exatidao na parede: a soma do N_telhado bate com o W do telhado.
    soma_parede = sum(reg["N_telhado_kN"]
                      for reg in com["alvenaria"]["por_linha"])
    assert soma_parede == pytest.approx(tel, rel=1e-3)
    # conservadorismo da secao unica: o que a corrida recebe (>= W).
    comp = {reg["nome"]: reg["comprimento_m"]
            for reg in com["alvenaria"]["por_linha"]}
    recebido = sum((q_com[n] - q_sem[n]) * comp[n] for n in nomes)
    assert recebido >= tel


# --- gestao: madeira por peca -----------------------------------------------------

def test_gestao_mede_madeira_por_peca_e_telha_inclinada():
    est = ec.rodar(_casa_concreto(copy.deepcopy(TELHADO_VIGA)))
    dados = gc.derivacao({"estrutura": est},
                         {"cobertura": {"area_m2": 83.2}})
    tel = est["telhado"]
    esperado = sum(p["b_m"] * p["h_m"] * p["L_por_tesoura_m"]
                   for p in tel["pecas"]) * tel["n_tesouras"]
    assert dados["quantitativos"]["madeira_telhado"] == pytest.approx(
        esperado, rel=1e-3)
    assert dados["quantitativos"]["telha_cobertura"] == pytest.approx(
        tel["area_telha_m2"])
    assert "madeira_telhado" in dados["aplicaveis"]
    assert not any(n["item"] == "madeira_telhado"
                   for n in dados["nao_derivados"])


def test_gestao_sem_telhado_nomeia_o_que_nao_mediu():
    import orcamento as orc

    dados = gc.derivacao({"estrutura": ec.rodar(_casa_concreto())},
                         {"cobertura": {"area_m2": 83.2}})
    assert "madeira_telhado" not in dados["quantitativos"]
    composto = orc.compor_orcamento(dados["quantitativos"],
                                   dict(gc.PRECOS_CASA), 25.0,
                                   aplicaveis=dados["aplicaveis"])
    assert "madeira_telhado" in composto["sem_quantidade"]
    # e a telha segue pela projecao, dita sem inclinacao.
    assert dados["quantitativos"]["telha_cobertura"] == pytest.approx(83.2)
    assert any("SEM fator de inclinacao" in n for n in dados["a_confirmar"])


# --- ponta a ponta (molde G52/G58) --------------------------------------------------

@pytest.fixture(scope="module")
def spec_persistido():
    return json.loads(SPEC_PERSISTIDO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def execucao(spec_persistido, tmp_path_factory):
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    destino = tmp_path_factory.mktemp("casa-g66") / "run"
    manifesto = run_project(
        spec_persistido, destino,
        {"generate_2d": True, "generate_ifc": True, "generate_3d": False})
    return manifesto, destino


def test_e2e_orcamento_cobre_a_madeira_e_nao_e_parcial(execucao):
    manifesto, destino = execucao
    orcamento = manifesto["deliverables"]["orcamento"]
    assert orcamento["status"] == "generated"
    assert "madeira_telhado" in orcamento["codigos"]
    assert "telha_cobertura" in orcamento["codigos"]
    assert orcamento["sem_quantidade"] == []
    assert orcamento["cobertura_pct"] == 100.0
    texto = (destino / "orcamento" / "relatorio.txt").read_text(
        encoding="utf-8")
    assert "madeira_telhado" in texto
    assert "ORCAMENTO PARCIAL" not in texto


def test_e2e_estrutura_e_memorial_trazem_o_telhado(execucao):
    manifesto, destino = execucao
    resultado = json.loads(
        (destino / "reports" / "adapter-result.json").read_text(
            encoding="utf-8"))
    tel = resultado["estrutura"]["telhado"]
    assert tel["ATENDE"] is True
    assert resultado["estrutura"]["escopo"]["telhado_madeira"] \
        == "implemented"
    assert resultado["scope"]["telhado_madeira"] == "implemented"
    # memorial: item proprio com numero, nao so o veredito da estrutura.
    pacote = json.loads(
        (destino / "documentos" / "pacote-legal.json").read_text(
            encoding="utf-8"))
    mem = pacote["memorial_consolidado"]
    por_disc = {it["disciplina"]: it for it in mem["disciplinas"]}
    assert por_disc["telhado_madeira"]["veredito"] == "ATENDE"
    assert "tesoura" in por_disc["telhado_madeira"]["detalhe"]
    assert mem["atende_global"] is True
    md = (destino / "documentos" / "pacote-legal.md").read_text(
        encoding="utf-8")
    assert "telhado_madeira" in md and "tesoura" in md
    assert any(p["codigo"] == "PE-MD-01"
               for p in pacote["indice_pranchas"])


def test_memorial_sem_telhado_nao_inventa_linha():
    mem = gc.memorial({"estrutura": ec.rodar(_casa_concreto())})
    assert "telhado_madeira" not in {it["disciplina"]
                                     for it in mem["disciplinas"]}
    assert "madeira" not in gc.disciplinas_pacote(
        {"estrutura": ec.rodar(_casa_concreto())})


def test_pacote_com_telhado_tem_pe_md_e_art_e_oem(execucao):
    _manifesto, destino = execucao
    pacote = json.loads(
        (destino / "documentos" / "pacote-legal.json").read_text(
            encoding="utf-8"))
    assert any(a["disciplina"] == "madeira" for a in pacote["lista_art"])
    assert any(o["disciplina"] == "madeira" for o in pacote["manual_oem"])
    assert "Cobertura/fechamento" in [c["grupo"]
                                      for c in pacote["checklist_lod_bim"]]


def test_e2e_cronograma_custeia_a_cobertura_com_madeira(execucao):
    manifesto, destino = execucao
    cronograma = manifesto["deliverables"]["cronograma"]
    assert cronograma["status"] == "generated"
    assert cronograma["custeado_pelo_orcamento"] is True
    cpm = json.loads((destino / "cronograma" / "cpm.json").read_text(
        encoding="utf-8"))
    assert "cob" in {a["id"] for a in cpm["atividades"]}


def test_e2e_prancha_da_tesoura_abre_no_disco(execucao):
    manifesto, destino = execucao
    assert "drawings/telhado-tesoura.svg" in manifesto["deliverables"][
        "drawings"]["artifacts"]
    svg = (destino / "drawings" / "telhado-tesoura.svg").read_text(
        encoding="utf-8")
    ET.fromstring(svg)  # XML valido
    assert "TESOURA" in svg and "ATENDE" in svg


# --- revisao do G66: os defeitos que a entrega trazia ------------------------
# Cada teste abaixo fica VERMELHO se o defeito voltar (injecao), e nenhum
# congela numero: todos comparam com a origem independente do outro lado.

def test_carga_lancada_e_a_do_telhado_que_a_tesoura_cobre():
    """O tributario do beiral valia painel INTEIRO (espelhava o vizinho) e
    a tesoura carregava N/(N-1) telhados - 25 % a mais com 4 paineis -,
    enquanto o quantitativo comprava um telhado so. O gate irmao
    (reacao x lancado) fechava com erro 0,0: ele nao pode ver isso."""
    r = tmad.rodar(copy.deepcopy(TELHADO_VIGA))
    fa = r["gates"]["fechamento_area"]
    assert fa["OK"] and fa["erro_rel"] <= 0.02
    # a origem do outro lado, recomposta aqui sem passar pelo modulo:
    cos_t = math.cos(math.radians(TELHADO_VIGA["inclinacao_graus"]))
    esp = TELHADO_VIGA["espacamento"]
    area_incl = TELHADO_VIGA["vao"] / cos_t * esp
    g_tot = r["telha_peso_kNm2"] + r["pp_madeira_kNm2"]
    assert fa["G_lancado_kN"] == pytest.approx(g_tot * area_incl, rel=1e-3)
    assert fa["Q_lancado_kN"] == pytest.approx(
        TELHADO_VIGA["sobrecarga_kNm2"] * TELHADO_VIGA["vao"] * esp,
        rel=1e-3)
    # e a area do quantitativo fala do MESMO telhado que a carga.
    assert r["area_telha_m2"] == pytest.approx(
        area_incl / esp * TELHADO_VIGA["extensao"], rel=1e-3)


def test_fechamento_de_area_reprova_o_painel_a_mais():
    """Vermelho por injecao: 25 % de carga a mais (o defeito medido) tem
    de reprovar a guarda nova."""
    cos25 = math.cos(math.radians(25.0))
    ok = tmad.confere_fechamento_area(11.076, 4.0, 0.6273, 0.25, 8.0, 2.0,
                                      cos25)
    assert ok["ok"]
    inflado = tmad.confere_fechamento_area(11.076 * 1.25, 4.0 * 1.25,
                                           0.6273, 0.25, 8.0, 2.0, cos25)
    assert inflado["ok"] is False
    assert inflado["erro_rel"] == pytest.approx(0.25, rel=1e-2)


def test_a2_de_prego_e_a_linha_da_tab14_nao_a_do_eurocode():
    """Tab.14: a2 de prego com pre-furo e' (3 + 6.|sen a|).d. Estava
    (3 + |sen a|).d - a 90 graus a norma pede 9d e o gate aceitava 4d."""
    d = 5.0
    assert mad.espacamentos_minimos("prego", d, 0.0)["a2"] == pytest.approx(
        3 * d)
    assert mad.espacamentos_minimos("prego", d, 90.0)["a2"] == pytest.approx(
        9 * d)
    assert mad.espacamentos_minimos("prego", d, 30.0)["a2"] == pytest.approx(
        (3 + 6 * 0.5) * d)
    # o parafuso segue 4d em qualquer angulo (coluna propria da Tab.14).
    assert mad.espacamentos_minimos("parafuso", d, 90.0)["a2"] == (
        pytest.approx(4 * d))


def test_espacamento_curto_reprova_a_ligacao_de_prego():
    """Vermelho por injecao: a2 = 5d a 90 graus passava antes (4d bastava)
    e agora reprova nomeando a Tab.14."""
    fe = mad.embutimento_fek(4.0, 350.0, True, True, 90.0)["fe_k_Nmm2"]
    base = {"config_73": "chapa_fina_simples", "tipo_pino": "prego",
            "d_mm": 4.0, "fu_MPa": 600.0, "t1_mm": 60.0,
            "fe1_Nmm2": fe, "n_pinos": 4, "n_planos": 1,
            "kmod1": 0.9, "kmod2": 0.9, "alpha_graus": 90.0,
            "t_madeira_mm": 60.0, "t_chapa_mm": 1.5,
            "espacamentos": {"a1": 999, "a2": 5 * 4.0, "a3t": 999,
                             "a3c": 999, "a4t": 999, "a4c": 999}}
    r = mad.verifica_ligacao(0.5, base)
    assert r["OK"] is False
    assert any("a2=" in m and "Tab.14" in m for m in r["falhas_geometria"])
    folgado = dict(base, espacamentos=dict(base["espacamentos"],
                                           a2=9 * 4.0))
    assert mad.verifica_ligacao(0.5, folgado)["OK"]


def test_apoio_na_ponta_da_peca_nao_ganha_o_alfa_n_da_tab6():
    """6.2.4 tem DUAS condicoes: a' >= 15 cm OU forca a menos de 7,5 cm da
    extremidade. So a primeira estava implementada, e o apoio da tesoura
    e' exatamente a ponta do banzo inferior."""
    assert mad.alfa_n(5.0, dist_extremidade_cm=50.0) == pytest.approx(1.30)
    assert mad.alfa_n(5.0, dist_extremidade_cm=3.0) == 1.00
    assert mad.alfa_n(5.0) == 1.00           # posicao nao declarada = piso
    assert mad.alfa_n(20.0, dist_extremidade_cm=50.0) == 1.00
    meio = mad.verifica_apoio(10.0, 0.01, 8000.0, 5.0,
                              dist_extremidade_cm=50.0)
    ponta = mad.verifica_apoio(10.0, 0.01, 8000.0, 5.0)
    assert ponta["fc90d_kNm2"] == pytest.approx(meio["fc90d_kNm2"] / 1.30)
    assert ponta["util"] > meio["util"]
    # no telhado, o apoio da tesoura cai na ponta do banzo inferior.
    r = tmad.rodar(copy.deepcopy(TELHADO_VIGA))
    assert r["apoio_verificacao"]["alfa_n"] == 1.00


def test_tab21_e_faixa_e_o_limite_sem_declaracao_e_o_estrito():
    """L/200 nao existe na Tab.21 (a faixa de delta_fin e' L/150 a L/300):
    era numero do meio da faixa vendido como tabela. E o delta_net,fin
    nao era verificado."""
    lim = mad.limites_tab21()
    assert lim == {"inst": 500.0, "fin": 300.0, "net_fin": 350.0}
    assert mad.limites_tab21({"fin": 200.0})["fin"] == 200.0
    with pytest.raises(mad.EntradaMadeira, match="Tab.21"):
        mad.limites_tab21({"fin": 100.0})     # mais folgado que L/150
    with pytest.raises(mad.EntradaMadeira, match="Tab.21"):
        mad.limites_tab21({"inst": 600.0})    # fora por cima
    r = tmad.rodar(copy.deepcopy(TELHADO_VIGA))
    e = r["terca"]["els"]
    assert e["d_net_fin_m"] <= e["lim_net_fin_m"]
    assert e["lim_inst_m"] == pytest.approx(r["espacamento_m"] / 500.0)


def test_contraflecha_acima_de_dois_tercos_recusa():
    """8.2: a contraflecha nao passa de 2/3 da flecha permanente
    instantanea - senao ela 'zera' no papel uma flecha que existe."""
    with pytest.raises(mad.EntradaMadeira, match="2/3"):
        mad.verifica_els_terca(2.0, 1.0, 3.0, 11e6, 2e-5, 2,
                               contraflecha_m=0.05)


def test_secao_abaixo_do_minimo_construtivo_reprova_com_o_artigo():
    """9.2.1 e 9.3 nao existiam - nem implementadas nem no escopo(). Uma
    peca podia sair legal na conta e proibida na norma."""
    assert mad.verifica_dimensoes_minimas_921(0.06, 0.16)["OK"]
    magra = mad.verifica_dimensoes_minimas_921(0.04, 0.10)
    assert magra["OK"] is False and any("espessura" in f
                                        for f in magra["falhas"])
    assert mad.verifica_dimensoes_minimas_921(0.04, 0.10,
                                              "secundaria_isolada")["OK"]
    assert mad.verifica_esbeltez_geometrica_93(2.0, 0.06)["OK"]
    esbelta = mad.verifica_esbeltez_geometrica_93(3.0, 0.06)
    assert esbelta["OK"] is False and "9.3" in esbelta["motivo"]
    # tracionada tem teto proprio (50x, nao 40x).
    assert mad.verifica_esbeltez_geometrica_93(3.0, 0.06,
                                               "tracionada")["OK"]
    magro = copy.deepcopy(TELHADO_VIGA)
    magro["secoes"]["banzo_inf"] = {"b": 0.04, "h": 0.10}
    r = tmad.rodar(magro)
    assert r["ATENDE"] is False
    assert "construtivas_9" in r["reprovados"]
    assert any("banzo_inf" in m
               for m in r["gates"]["construtivas_9"]["fora_do_minimo"])


def test_classe_da_chapa_e_medida_na_espessura_nao_declarada():
    """7.3 classifica a chapa por ts (fina <= 0,5d, grossa >= d) e manda
    interpolar entre as duas. A config era declaracao livre: chamar de
    'grossa' uma chapa fina dava os modos c/d/e, mais resistentes."""
    fe = mad.embutimento_fek(12.0, 350.0, True, True, 0.0)["fe_k_Nmm2"]
    cfg = {"config_73": "chapa_grossa_simples", "tipo_pino": "parafuso",
           "d_mm": 12.0, "fu_MPa": 415.0, "t1_mm": 160.0,
           "fe1_Nmm2": fe, "n_pinos": 4, "n_planos": 1,
           "kmod1": 0.9, "kmod2": 0.9, "alpha_graus": 0.0,
           "t_madeira_mm": 80.0, "t_chapa_mm": 12.0,
           "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                            "a3c": 80, "a4t": 60, "a4c": 60}}
    boa = mad.verifica_ligacao(5.0, cfg)
    assert boa["classe_chapa_73"] == "grossa" and boa["OK"]
    mentira = dict(cfg, t_chapa_mm=3.0)     # 3 mm <= 0,5d: e' fina
    r = mad.verifica_ligacao(5.0, mentira)
    assert r["classe_chapa_73"] == "fina" and r["OK"] is False
    assert any("declara grossa" in m for m in r["falhas_geometria"])
    meio = dict(cfg, t_chapa_mm=8.0)        # entre 0,5d e d
    r2 = mad.verifica_ligacao(5.0, meio)
    assert r2["classe_chapa_73"] == "intermediaria"
    assert any("INTERPOLAR" in m for m in r2["falhas_geometria"])
    # a chapa CENTRAL de dupla secao vale "de qualquer espessura" (7.3).
    central = dict(cfg, config_73="chapa_central_dupla", n_planos=2,
                   t2_mm=160.0, fe2_Nmm2=fe, t_chapa_mm=8.0)
    assert mad.verifica_ligacao(5.0, central)["OK"]


def test_contrato_antigo_do_travamento_recusa_com_endereco():
    """A flag booleana era carimbo: ninguem conferia. Quem ainda mandar a
    chave antiga recebe o endereco da 6.5.6, nao um telhado calculado."""
    velho = copy.deepcopy(TELHADO_VIGA)
    velho["travado_borda_comprimida"] = True
    with pytest.raises(tmad.EntradaTelhado, match="6.5.6"):
        tmad.rodar(velho)
    solto = copy.deepcopy(TELHADO_VIGA)
    solto["travamento_borda_comprimida_m"] = 6.0
    r = tmad.rodar(solto)
    assert r["ATENDE"] is False and "tercas" in r["reprovados"]
    assert "6.5.6-b" in r["terca"]["flexao"]["motivo"]


def test_apoio_interior_da_terca_recebe_os_dois_tramos():
    """A terca corre a extensao inteira sobre varias tesouras: a tesoura
    INTERIOR recebe as duas meias-cargas dos tramos vizinhos. O modulo
    usava R = w.esp/2 (meio tramo) com o alfa_n da Tab.6 - metade do
    apoio interior. Os dois casos passam a ser verificados e governa o
    pior; a ponta leva meio tramo, mas na extremidade da peca (alfa_n=1)."""
    r = tmad.rodar(copy.deepcopy(TELHADO_VIGA))
    a = r["terca"]["apoio"]
    assert a["apoio"] == "interior"
    # relacao, nao numero: o interior e' o dobro da carga da ponta.
    w = r["terca"]["w_g_kNm"] + r["terca"]["w_q_kNm"]
    assert a["R_kN"] == pytest.approx(w * r["espacamento_m"], rel=1e-3)
    # e a ponta, com meio tramo, nao ganha o alfa_n da Tab.6.
    ponta = mad.verifica_apoio(w * r["espacamento_m"] / 2.0,
                               TELHADO_VIGA["secoes"]["terca"]["b"]
                               * TELHADO_VIGA["secoes"]["banzo_sup"]["b"],
                               r["madeira"]["fc0d"],
                               TELHADO_VIGA["secoes"]["banzo_sup"]["b"] * 100.0)
    assert ponta["alfa_n"] == 1.00
    assert a["util"] > ponta["util"]
    # telhado de uma tesoura so nao tem apoio interior.
    unico = copy.deepcopy(TELHADO_VIGA)
    unico["extensao"] = unico["espacamento"]
    assert tmad.rodar(unico)["terca"]["apoio"]["apoio"] == "extremidade"


def test_prancha_da_tesoura_diz_a_situacao_de_CADA_peca():
    """Renderizar-e-olhar: a folha abria e o teste so via 'TESOURA' e
    'ATENDE' por substring. Olhando, a coluna 'Situacao' repetia o
    veredito GLOBAL nas cinco linhas - um telhado com uma barra reprovada
    carimbava REPROVA nas quatro que passam - e 'Volume (m3)' era o total
    do telhado ao lado de 'L/tesoura (m)', duas grandezas sem dizer qual
    e' qual."""
    import re
    import desenho_casa_residencial as dcr

    ruim = copy.deepcopy(TELHADO_VIGA)
    ruim["secoes"]["diagonal"] = {"b": 0.02, "h": 0.02}
    r = tmad.rodar(ruim)
    assert r["ATENDE"] is False
    svg = dcr.telhado_tesoura_svg(r)
    ET.fromstring(svg)
    txt = re.findall(r">([^<]+)</text>", svg)
    i = txt.index("Peca")
    cab = txt[i:i + 5]
    assert "Volume total (m3)" in cab and "L/tesoura (m)" in cab
    situacao = {}
    for k in range(i + 5, len(txt) - 4, 5):
        situacao[txt[k]] = txt[k + 4]
    assert situacao["diagonal"] == "REPROVA"
    # e as que passam continuam dizendo que passam.
    assert situacao["banzo_sup"] == situacao["terca"] == "ATENDE"
    # o volume da linha e' o do telhado inteiro, nao o de uma tesoura.
    peca = next(p for p in r["pecas"] if p["grupo"] == "banzo_sup")
    valor = float(dict(zip(txt[i + 5::5], txt[i + 8::5]))["banzo_sup"])
    assert valor == pytest.approx(
        peca["vol_por_tesoura_m3"] * r["n_tesouras"], rel=1e-3)
