"""G12 - hidraulica e eletrica do edificio multipavimento.

As duas fronteiras que faltavam depois do incendio. O que muda num predio de
nove pavimentos, em relacao a casa que `hidraulica_residencial` e
`residencial_eletrica` ja cobriam, e' a VERTICAL: uma coluna d'agua que ganha
pressao a cada andar que desce e uma prumada eletrica cuja queda de tensao
ACUMULA a cada andar que sobe. Estes testes fixam o contrato dessas fronteiras -
e a regra que o G12 inteiro persegue: o predio tem UMA populacao, como tem UMA
escada.
"""

import copy
import json
from pathlib import Path

import pytest

import edificio_adapter as ea
import eletrica_edificio as ee
import hidraulica_edificio as he
import hidraulica_predial as hp
from builtin_adapters import register_builtin_adapters
from project_loop import normalize_spec


ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parents[1]
SPEC_PERSISTIDO = REPO_ROOT / "projects" / "edificio-multipavimento" / "project-spec.json"


@pytest.fixture(scope="module", autouse=True)
def _adaptadores():
    register_builtin_adapters()


@pytest.fixture(scope="module")
def spec():
    return json.loads(SPEC_PERSISTIDO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def execucao(spec):
    return ea.run_edificio(normalize_spec(spec), None)


def _rodar(spec):
    return ea.run_edificio(normalize_spec(spec), None)


# ===========================================================================
# HIDRAULICA
# ===========================================================================

def test_a_disciplina_hidraulica_saiu_de_ausente(execucao):
    resultado, registros = execucao
    assert "hidraulica" in ea.DISCIPLINES
    assert resultado["scope"]["hidraulica"] == "implemented"
    assert resultado["disciplines"]["hidraulica"]["engine"] == "hidraulica_edificio"
    assert registros["hidraulica"]["status"] == "needs_review"


def test_o_predio_tem_uma_populacao_so(execucao):
    """A hidraulica LE a populacao da NBR 9077 em vez de pedir uma segunda."""
    _resultado, registros = execucao
    hidr = registros["hidraulica"]["hydraulics"]
    incendio = registros["incendio"]["fire"]
    assert hidr["populacao"] == incendio["populacao_total"]
    assert "MESMA populacao da NBR 9077" in hidr["populacao_proveniencia"]


def test_populacao_divergente_e_erro_e_nao_escolha_silenciosa(spec):
    divergente = copy.deepcopy(spec)
    divergente["turnkey"]["hidraulica"]["populacao"] = 40
    _resultado, registros = _rodar(divergente)
    assert registros["hidraulica"]["status"] == "blocked"
    detalhe = registros["hidraulica"]["errors"][0]["detail"]
    assert "UMA populacao" in detalhe
    assert "40" in detalhe


def test_consumo_per_capita_nao_tem_default(spec):
    """6.5.4 NAO tabela consumo: sem o dado nao ha volume de reservacao."""
    sem = copy.deepcopy(spec)
    sem["turnkey"]["hidraulica"].pop("consumo_per_capita_L_dia")
    _resultado, registros = _rodar(sem)
    assert registros["hidraulica"]["status"] == "blocked"
    assert registros["hidraulica"]["errors"][0]["code"] == "hydraulic_input_not_declared"


def test_reservacao_atende_24h_de_consumo(execucao):
    """6.5.6.2: no minimo 24 h de consumo normal no edificio."""
    _resultado, registros = execucao
    gate = registros["hidraulica"]["gates"]["reservacao_24h"]
    hidr = registros["hidraulica"]["hydraulics"]
    assert gate["exigido_L"] == pytest.approx(hidr["consumo_diario_L"])
    assert gate["adotado_L"] >= gate["exigido_L"]
    assert gate["OK"] is True
    # 64 pessoas x 150 L/dia
    assert hidr["consumo_diario_L"] == pytest.approx(64 * 150.0)


def test_reservacao_insuficiente_reprova(spec):
    pequeno = copy.deepcopy(spec)
    pequeno["turnkey"]["hidraulica"]["reservacao"]["superior_L"] = 5000.0
    _resultado, registros = _rodar(pequeno)
    assert registros["hidraulica"]["gates"]["reservacao_24h"]["OK"] is False
    assert "reservacao_24h" in registros["hidraulica"]["reprovados"]


def test_reservatorio_elevado_exige_dois_compartimentos(spec):
    """6.5.6.5: "devem ser divididos em dois ou mais compartimentos"."""
    unico = copy.deepcopy(spec)
    unico["turnkey"]["hidraulica"]["reservacao"]["compartimentos_superior"] = 1
    _resultado, registros = _rodar(unico)
    gate = registros["hidraulica"]["gates"]["reservacao_compartimentos"]
    assert gate["OK"] is False
    assert gate["minimo"] == 2
    assert "6.5.6.5" in gate["referencia"]


def test_tres_dias_e_recomendacao_e_sai_como_aviso(spec):
    """6.5.6.3 NOTA diz "recomenda-se": aviso, nao gate."""
    grande = copy.deepcopy(spec)
    grande["turnkey"]["hidraulica"]["reservacao"]["superior_L"] = 60000.0
    _resultado, registros = _rodar(grande)
    assert "reservacao_24h" not in registros["hidraulica"]["reprovados"]
    avisos = {a["code"] for a in registros["hidraulica"]["warnings"]}
    assert "reservacao_acima_de_tres_dias" in avisos


def test_alimentador_repoe_o_consumo_diario_em_seis_horas(execucao):
    """6.7.2: reposicao total do volume de consumo diario em ate 6 h."""
    _resultado, registros = execucao
    gate = registros["hidraulica"]["gates"]["alimentador_predial"]
    esperado = 64 * 150.0 / (6.0 * 3600.0)
    assert gate["Q_Ls"] == pytest.approx(esperado, abs=1e-3)
    assert gate["OK"] is True


def test_tempo_de_reposicao_acima_de_seis_horas_e_recusado(spec):
    lento = copy.deepcopy(spec)
    lento["turnkey"]["hidraulica"]["tempo_reposicao_h"] = 12.0
    _resultado, registros = _rodar(lento)
    assert registros["hidraulica"]["status"] == "blocked"
    assert "6.7.2" in registros["hidraulica"]["errors"][0]["detail"]


def test_pressao_estatica_no_pe_da_coluna_tem_teto_de_400_kPa(execucao):
    """6.9.5 - o gate que um predio alto estoura e que obriga zona de pressao."""
    _resultado, registros = execucao
    gate = registros["hidraulica"]["gates"]["pressao_estatica"]
    # NA a 3,0 m sobre a cobertura + 7 pes-direitos de 2,90 m ate o 1o pavimento
    assert gate["desnivel_m"] == pytest.approx(3.0 + 7 * 2.9)
    assert gate["p_estatica_kPa"] == pytest.approx(gate["desnivel_m"] * 10.0, abs=0.1)
    assert gate["p_max_kPa"] == 400.0
    assert gate["OK"] is True


def test_predio_alto_estoura_os_400_kPa_e_pede_zona_de_pressao(spec):
    alto = copy.deepcopy(spec)
    alto["turnkey"]["hidraulica"]["coluna"]["altura_na_sobre_cobertura_m"] = 45.0
    _resultado, registros = _rodar(alto)
    gate = registros["hidraulica"]["gates"]["pressao_estatica"]
    assert gate["OK"] is False
    assert "ZONAS DE PRESSAO" in gate["erro"]
    escopo = registros["hidraulica"]["scope"]
    assert escopo["zonas_de_pressao_e_valvulas_redutoras"] == "not_available"


def test_o_ponto_critico_de_pressao_dinamica_e_o_mais_ALTO(execucao):
    """Sao dois pontos criticos diferentes, e ambos sao verificados.

    A dinamica critica esta no topo (menor desnivel); a estatica critica esta no
    pe (maior coluna d'agua). E o trecho ate o topo conduz so a demanda do
    ultimo pavimento, nao a do predio inteiro.
    """
    _resultado, registros = execucao
    din = registros["hidraulica"]["gates"]["pressao_dinamica"]
    est = registros["hidraulica"]["gates"]["pressao_estatica"]
    assert "mais ALTO" in din["ponto"]
    assert "mais BAIXO" in est["ponto"]
    assert din["desnivel_m"] < est["desnivel_m"]
    assert din["Q_do_trecho_Ls"] < registros["hidraulica"]["gates"][
        "coluna_distribuicao"]["Q_Ls"]
    assert din["p_residual_kPa"] >= din["p_min_kPa"]
    assert din["OK"] is True


def test_tubo_de_queda_usa_a_coluna_de_mais_de_tres_pavimentos(execucao):
    """NBR 8160 Tab.6 tem duas colunas; um predio de 8 pavimentos usa a segunda."""
    _resultado, registros = execucao
    gate = registros["hidraulica"]["gates"]["tubo_de_queda"]
    assert gate["coluna_da_tabela"] == "mais de 3 pavimentos"
    assert gate["saturado"] is False
    # 8 pavimentos x 2 unidades x (6+2+1+3+3+3) UHC = 288
    assert gate["uhc"] == pytest.approx(288.0)
    assert gate["DN_mm"] == hp.diametro_tubo_queda(288.0, pavimentos=8)


def test_saturacao_do_tubo_de_queda_reprova(spec):
    """Tabela saturada nunca sai com OK=True (o padrao que este framework caca)."""
    enorme = copy.deepcopy(spec)
    enorme["turnkey"]["hidraulica"]["unidade"]["unidades_por_pavimento"] = 400
    _resultado, registros = _rodar(enorme)
    gate = registros["hidraulica"]["gates"]["tubo_de_queda"]
    assert gate["saturado"] is True
    assert gate["OK"] is False


def test_a_reserva_de_incendio_nao_e_somada_em_silencio(execucao):
    """6.5.6.2 so soma o volume de incendio quando ele e' armazenado JUNTO."""
    _resultado, registros = execucao
    avisos = {a["code"] for a in registros["hidraulica"]["warnings"]}
    assert "reserva_de_incendio_nao_somada" in avisos
    hidr = registros["hidraulica"]["hydraulics"]
    reserva_incendio = registros["incendio"]["gates"]["hidrantes"]["reserva_incendio_m3"]
    assert hidr["reservacao_total_L"] < (hidr["consumo_diario_L"]
                                         + reserva_incendio * 1000.0)


def test_intensidade_pluvial_declarada_nao_e_rotulada_de_default(execucao):
    """Rotulo x dado: um i de sitio que valha 150 mm/h nao e' o default."""
    _resultado, registros = execucao
    gate = registros["hidraulica"]["gates"]["pluvial"]
    assert gate["i_mm_h"] == 150.0
    assert gate["i_declarado"] is True
    avisos = {a["code"] for a in registros["hidraulica"]["warnings"]}
    assert "intensidade_pluvial_default" not in avisos


def test_intensidade_pluvial_ausente_vira_aviso(spec):
    sem = copy.deepcopy(spec)
    sem["turnkey"]["hidraulica"]["pluvial"].pop("i_mm_h")
    _resultado, registros = _rodar(sem)
    avisos = {a["code"] for a in registros["hidraulica"]["warnings"]}
    assert "intensidade_pluvial_default" in avisos


def test_hidraulica_sem_estrutura_calculada_bloqueia(spec):
    sem = copy.deepcopy(spec)
    sem["turnkey"]["estrutura"]["materiais"] = {"fck": 0.0, "fyk": 0.0}
    _resultado, registros = _rodar(sem)
    assert registros["hidraulica"]["errors"][0]["code"] == "structure_result_required"


# ===========================================================================
# ELETRICA
# ===========================================================================

def test_a_disciplina_eletrica_saiu_de_ausente(execucao):
    resultado, registros = execucao
    assert "eletrico" in ea.DISCIPLINES
    assert resultado["scope"]["eletrico"] == "implemented"
    assert resultado["disciplines"]["eletrico"]["engine"] == "eletrica_edificio"
    assert registros["eletrico"]["status"] == "needs_review"


def test_carga_da_unidade_sai_da_nbr5410_9_5_2(execucao):
    """A previsao de carga reusa as primitivas ja aferidas da 9.5.2."""
    resultado, _registros = execucao
    carga = resultado["instalacoes"]["eletrico"]["carga_por_unidade"]
    assert "9.5.2" in carga["proveniencia"]
    assert carga["carga_VA"] == pytest.approx(carga["iluminacao_VA"]
                                              + carga["tomadas_VA"]
                                              + carga["especiais_VA"])
    # sala de 16 m2: 100 VA + 60 VA por bloco de 4 m2 inteiros excedentes = 220 VA
    sala = next(a for a in carga["ambientes"] if a["tipo"] == "sala")
    assert sala["iluminacao_VA"] == 220.0
    # banheiro: 9.5.2.2.1-a, um ponto de 600 VA
    banheiro = next(a for a in carga["ambientes"] if a["tipo"] == "banheiro")
    assert banheiro["n_tomadas"] == 1
    assert banheiro["tomadas_VA"] == 600.0


def test_a_carga_da_unidade_nao_e_estimada_pela_area_do_envelope(spec):
    sem = copy.deepcopy(spec)
    sem["turnkey"]["eletrico"]["unidade"].pop("ambientes")
    _resultado, registros = _rodar(sem)
    assert registros["eletrico"]["status"] == "blocked"
    detalhe = registros["eletrico"]["errors"][0]["detail"]
    assert "envelope estrutural" in detalhe


def test_a_queda_de_tensao_da_prumada_ACUMULA_trecho_a_trecho(execucao):
    """O trecho e' o ponto: verificar so o pe da coluna daria a queda errada."""
    resultado, registros = execucao
    prumada = resultado["instalacoes"]["eletrico"]["prumada"]
    trechos = prumada["trechos"]

    assert len(trechos) == resultado["instalacoes"]["eletrico"]["pavimentos_servidos"]
    # a corrente CAI a cada pavimento atendido...
    correntes = [t["IB_A"] for t in trechos]
    assert correntes == sorted(correntes, reverse=True)
    # ...e a queda acumulada so CRESCE
    acumuladas = [t["dv_acumulada_pct"] for t in trechos]
    assert acumuladas == sorted(acumuladas)
    # a acumulada e' a soma das parciais, nao a do trecho mais carregado
    assert acumuladas[-1] == pytest.approx(sum(t["dv_trecho_pct"] for t in trechos),
                                           abs=1e-3)
    assert acumuladas[-1] > trechos[0]["dv_trecho_pct"]
    assert prumada["dv_critica_pct"] == acumuladas[-1]
    assert registros["eletrico"]["gates"]["queda_de_tensao_prumada"]["OK"] is True


def test_o_ultimo_trecho_conduz_um_pavimento_so(execucao):
    resultado, _registros = execucao
    trechos = resultado["instalacoes"]["eletrico"]["prumada"]["trechos"]
    assert trechos[-1]["pavimentos_acima"] == 1
    assert trechos[0]["pavimentos_acima"] == len(trechos)


def test_prumada_muito_longa_reprova_por_queda(spec):
    longa = copy.deepcopy(spec)
    longa["turnkey"]["eletrico"]["prumada"]["comprimento_por_pavimento_m"] = 60.0
    longa["turnkey"]["eletrico"]["prumada"][
        "comprimento_ate_o_primeiro_quadro_m"] = 200.0
    _resultado, registros = _rodar(longa)
    gate = registros["eletrico"]["gates"]["queda_de_tensao_prumada"]
    assert gate["dv_acumulada_pct"] > gate["dv_max_pct"]
    assert gate["OK"] is False


def test_o_disjuntor_e_escolhido_ANTES_da_secao(execucao):
    """Coordenacao 5.3.4.1: IB <= IN <= IZ tem de ter solucao.

    Dimensionar o condutor so por IB devolvia 10 mm2 com Iz = 66 A para um
    IB de 65,5 A - e nao existe disjuntor entre 65,5 e 66 A. Escolhendo IN
    primeiro (70 A) e dimensionando a ampacidade para ele, a coordenacao fecha.
    """
    _resultado, registros = execucao
    gate = registros["eletrico"]["gates"]["quadro_de_pavimento"]
    assert gate["IB_A"] <= gate["disjuntor_A"]
    assert gate["secao_mm2"] == 16
    assert gate["disjuntor_A"] == 70
    assert gate["OK"] is True
    assert ee.corrente_de_protecao(65.5) == 70


def test_sem_fator_de_demanda_soma_todas_as_unidades(execucao):
    """Piso conservador: dado ausente vira o TETO, nomeado no escopo."""
    resultado, registros = execucao
    eletrico = resultado["instalacoes"]["eletrico"]
    assert eletrico["fator_demanda_entre_unidades"] is None
    esperado = (eletrico["quadro_de_pavimento"]["carga_VA"]
                * eletrico["pavimentos_servidos"]
                + eletrico["carga_areas_comuns_VA"])
    assert eletrico["prumada"]["carga_base_VA"] == pytest.approx(esperado)
    assert (registros["eletrico"]["scope"]["fator_de_demanda_entre_unidades"]
            == "not_available")
    avisos = {a["code"] for a in registros["eletrico"]["warnings"]}
    assert "sem_fator_de_demanda_entre_unidades" in avisos


def test_com_fator_declarado_a_demanda_cai_e_o_escopo_muda(spec):
    com = copy.deepcopy(spec)
    com["turnkey"]["eletrico"]["fator_demanda_entre_unidades"] = 0.5
    resultado, registros = _rodar(com)
    eletrico = resultado["instalacoes"]["eletrico"]
    assert eletrico["fator_demanda_entre_unidades"] == 0.5
    assert (registros["eletrico"]["scope"]["fator_de_demanda_entre_unidades"]
            == "implemented")
    avisos = {a["code"] for a in registros["eletrico"]["warnings"]}
    assert "sem_fator_de_demanda_entre_unidades" not in avisos


def test_o_limite_de_75_kW_da_conexao_BT_e_um_gate(execucao):
    """Achado real do G12: este predio NAO e' atendivel em baixa tensao.

    Somadas as unidades sem diversidade, a carga instalada passa de 200 kW. O
    modulo nao esconde isso numa bitola maior: reprova e nomeia a subestacao
    propria, que ele nao projeta.
    """
    _resultado, registros = execucao
    gate = registros["eletrico"]["gates"]["limite_de_baixa_tensao"]
    assert gate["OK"] is False
    assert gate["carga_instalada_kW"] > gate["limite_kW"]
    assert "subestacao propria" in gate["referencia"]
    assert registros["eletrico"]["scope"]["subestacao_propria"] == "not_available"
    assert "limite_de_baixa_tensao" in registros["eletrico"]["reprovados"]


def test_areas_comuns_entram_so_no_pe_da_coluna(execucao):
    """Elevador e bombas nao sobem com os pavimentos."""
    resultado, _registros = execucao
    eletrico = resultado["instalacoes"]["eletrico"]
    trechos = eletrico["prumada"]["trechos"]
    comum = eletrico["carga_areas_comuns_VA"]
    assert comum > 0
    por_pav = eletrico["quadro_de_pavimento"]["carga_VA"]
    assert trechos[0]["carga_VA"] == pytest.approx(por_pav * len(trechos) + comum)
    assert trechos[1]["carga_VA"] == pytest.approx(por_pav * (len(trechos) - 1))


def test_icc_nao_declarada_vira_aviso_e_nao_verificacao_falsa(execucao):
    _resultado, registros = execucao
    avisos = {a["code"] for a in registros["eletrico"]["warnings"]}
    assert "icc_nao_declarada" in avisos
    assert registros["eletrico"]["gates"]["protecao_geral"]["Icc_declarada_A"] is None
    assert registros["eletrico"]["scope"]["curto_circuito_calculado"] == "not_available"


def test_circuitos_terminais_ficam_nomeados_como_fora_do_escopo(execucao):
    _resultado, registros = execucao
    escopo = registros["eletrico"]["scope"]
    assert escopo["circuitos_terminais_da_unidade"] == "not_available"
    assert escopo["spda_nbr5419"] == "not_available"


def test_eletrico_nao_declarado_nao_vira_projeto_inventado(spec):
    sem = copy.deepcopy(spec)
    sem["turnkey"].pop("eletrico")
    resultado, registros = _rodar(sem)
    assert "eletrico" not in registros
    assert resultado["scope"]["eletrico"] == "not_available"


# ===========================================================================
# O CONJUNTO
# ===========================================================================

def test_as_tres_disciplinas_saem_de_ausentes(execucao):
    """ACEITE DO G12."""
    resultado, registros = execucao
    assert set(ea.DISCIPLINES) == {"estrutura", "incendio", "hidraulica",
                                   "eletrico"}
    for nome in ("incendio", "hidraulica", "eletrico"):
        assert resultado["scope"][nome] == "implemented"
        assert registros[nome]["status"] == "needs_review"
        assert registros[nome]["gates"], "%s sem gates publicados" % nome


def test_cada_disciplina_publica_o_seu_proprio_escopo(execucao):
    """O escopo do registro hidraulico nao pode ser o da estrutura."""
    _resultado, registros = execucao
    assert "fundacao" not in registros["hidraulica"]["scope"]
    assert "fundacao" not in registros["eletrico"]["scope"]
    assert "superestrutura" not in registros["eletrico"]["scope"]


def test_falha_de_uma_disciplina_nao_derruba_as_outras(spec):
    quebrado = copy.deepcopy(spec)
    quebrado["turnkey"]["hidraulica"].pop("consumo_per_capita_L_dia")
    _resultado, registros = _rodar(quebrado)
    assert registros["hidraulica"]["status"] == "blocked"
    assert registros["incendio"]["status"] == "needs_review"
    assert registros["eletrico"]["status"] == "needs_review"
    assert registros["estrutura"]["status"] == "needs_review"


def test_nenhuma_disciplina_e_marcada_passed(execucao):
    """Aprovacao para obra continua sendo decisao de responsavel tecnico."""
    _resultado, registros = execucao
    assert all(r["status"] != "passed" for r in registros.values())
    for nome in ("incendio", "hidraulica", "eletrico"):
        assert registros[nome]["scope"]["aprovacao_legal"] == "not_claimed"
        assert registros[nome]["scope"]["construction_readiness"] == "not_claimed"
