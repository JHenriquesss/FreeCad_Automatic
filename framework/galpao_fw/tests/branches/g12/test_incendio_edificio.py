"""G12 - saidas de emergencia do edificio multipavimento (NBR 9077:2025).

O adaptador do edificio declarava DISCIPLINES = ("estrutura",): o predio saia
calculado, desenhado e modelado, e legalmente INOCUPAVEL. Estes testes fixam o
contrato da fronteira `incendio_edificio` e, sobretudo, a regra que impede o
projeto de se partir em dois: A ESCADA E' UMA SO. A largura vem de UMA
declaracao (estrutura.escada.largura); a estrutura dimensiona com ela e a 9077
verifica o fluxo de pessoas contra ela. Se o vertical de incendio propusesse a
sua propria largura, o predio teria duas escadas - o defeito que o G8 achou na
ancoragem viga-pilar.
"""

import ast
import copy
import json
from pathlib import Path

import pytest

import edificio_adapter as ea
import incendio_edificio as ie
import populacao_nbr9077 as pop
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


# --- Tabela 4: a densidade da atividade, nao uma area generica -------------

def test_habitacao_multifamiliar_e_medida_em_dormitorios():
    """Tab.4: "Duas pessoas por dormitorio". Area nao substitui o dado."""
    r = pop.populacao("habitacao_multifamiliar", dormitorios=4)
    assert r["populacao"] == 8
    with pytest.raises(ValueError, match="DORMITORIOS"):
        pop.populacao("habitacao_multifamiliar", area_computavel_m2=120.0)


def test_escritorio_sai_por_sete_metros_quadrados():
    """Tab.4, servicos profissionais: uma pessoa por 7 m2 de area computavel."""
    r = pop.populacao("servico_profissional", area_computavel_m2=105.0)
    assert r["populacao_exata"] == pytest.approx(15.0)
    assert r["populacao"] == 15


def test_arredondamento_e_decisao_declarada_e_conservadora():
    """A norma nao declara a politica; 'cima' e' decisao de projeto REGISTRADA."""
    r = pop.populacao("servico_profissional", area_computavel_m2=100.0)
    assert r["populacao_exata"] == pytest.approx(100.0 / 7.0)
    assert r["populacao"] == 15                      # ceil, nunca 14
    assert r["politica_arredondamento"] == "cima"
    assert r["arredondamento_normativo"] == "não declarado pela NBR 9077:2025"


def test_atividade_fora_da_tabela4_e_erro():
    with pytest.raises(ValueError, match="Tabela 4"):
        pop.populacao("coworking_com_pet", area_computavel_m2=100.0)


# --- Tabela 3: combinacoes que a norma NAO admite --------------------------

def test_perfil_de_risco_sai_da_tabela3():
    assert ie.perfil_risco("Ci", 1) == "C1"
    assert ie.perfil_risco("A", 4) == "A4"


def test_tabela3_recusa_crescimento_rapido_para_perfil_d():
    """Nota da Tab.3: nao se aceita crescimento 'rapido' (3) para o perfil D."""
    with pytest.raises(ValueError, match="NAO admite"):
        ie.perfil_risco("D", 3)


def test_tabela3_recusa_ultrarrapido_fora_do_perfil_a():
    with pytest.raises(ValueError, match="NAO admite"):
        ie.perfil_risco("Ci", 4)


# --- A ESCADA E' UMA SO ----------------------------------------------------

def test_a_largura_da_escada_e_uma_so_declaracao(spec):
    """ACEITE DO G12: estrutura e NBR 9077 leem a MESMA largura.

    Nao ha uma largura "da estrutura" e outra "do incendio": o valor que o gate
    da 9077 confere e' literalmente o que o spec declarou em
    estrutura.escada.largura, transportado pelo resultado de escada_concreto.
    """
    declarada = spec["turnkey"]["estrutura"]["escada"]["largura"]
    resultado, registros = _rodar(spec)

    estrutural = resultado["estrutura"]["escada"]["largura_m"]
    do_incendio = registros["incendio"]["gates"]["escada_largura"]

    assert estrutural == declarada
    assert do_incendio["largura_declarada_m"] == declarada
    assert do_incendio["fonte_da_largura"] == "estrutura.escada.largura (declaracao unica)"


def test_mudar_a_declaracao_move_os_dois_lados(spec):
    """Uma so declaracao: mexer nela move estrutura E incendio juntos."""
    outro = copy.deepcopy(spec)
    outro["turnkey"]["estrutura"]["escada"]["largura"] = 2.45
    resultado, registros = _rodar(outro)

    assert resultado["estrutura"]["escada"]["largura_m"] == 2.45
    assert (registros["incendio"]["gates"]["escada_largura"]["largura_declarada_m"]
            == 2.45)


def test_escada_estreita_REPROVA_em_vez_de_ser_alargada(spec):
    """A largura calculada e' EXIGENCIA, nunca adocao.

    O vertical de incendio nao "corrige" a escada: ele reprova. Alargar por
    conta propria criaria a segunda escada que este modulo existe para impedir.
    """
    estreito = copy.deepcopy(spec)
    estreito["turnkey"]["estrutura"]["escada"]["largura"] = 0.90
    resultado, registros = _rodar(estreito)

    gate = registros["incendio"]["gates"]["escada_largura"]
    assert gate["OK"] is False
    assert gate["largura_declarada_m"] == 0.90
    assert gate["largura_exigida_m"] >= ie.ESCADA_LARGURA_MIN_M
    # a estrutura continua com a largura DECLARADA - ninguem a reescreveu
    assert resultado["estrutura"]["escada"]["largura_m"] == 0.90
    assert "escada_largura" in registros["incendio"]["reprovados"]


def test_sem_escada_declarada_o_gate_nao_inventa_uma(spec):
    """Escada ausente vira erro nomeado, nunca largura arbitrada."""
    sem = copy.deepcopy(spec)
    sem["turnkey"]["estrutura"].pop("escada")
    _resultado, registros = _rodar(sem)

    gate = registros["incendio"]["gates"]["escada_largura"]
    assert gate["OK"] is False
    assert gate["largura_declarada_m"] is None
    assert "segunda escada" in gate["erro"]


def test_o_modulo_de_incendio_nao_tem_largura_de_escada_default():
    """Guarda estrutural: nenhuma constante deste modulo adota uma largura.

    A unica largura que ele conhece e' o PISO da NBR 9050 (1,20 m), que e'
    minimo de verificacao - nao um valor adotado para a escada do projeto.
    """
    permitidas = {"ESCADA_LARGURA_MIN_M", "PATAMAR_MIN_M",
                  "CORREDOR_USO_PUBLICO_MIN_M", "DESNIVEL_MAX_SEM_PATAMAR_M"}
    suspeitas = {
        nome: valor
        for nome, valor in vars(ie).items()
        if nome.isupper() and nome not in permitidas
        and isinstance(valor, float) and 0.80 <= valor <= 5.0
    }
    assert not suspeitas, (
        "constante de incendio_edificio com valor de largura de escada plausivel "
        "(m): %s - a largura da escada e' DECLARADA, nunca adotada aqui"
        % suspeitas)


# --- geometria da escada: a 9050 e' mais estreita que o gate estrutural -----

def test_geometria_da_escada_e_conferida_contra_a_nbr9050(execucao):
    _resultado, registros = execucao
    gate = registros["incendio"]["gates"]["escada_geometria"]
    assert gate["referencia"] == "NBR 9050:2020 6.8.2"
    assert gate["piso_faixa_m"] == [0.28, 0.32]
    assert gate["espelho_faixa_m"] == [0.16, 0.18]
    assert gate["OK"] is True


def test_escada_que_passa_na_estrutura_pode_reprovar_na_9050():
    """PISO_MIN de escada_concreto e' 0,25 m; a 9050 6.8.2 exige 0,28 m."""
    import escada_concreto as ec

    assert ec.PISO_MIN < ie.PISO_9050_M[0]
    gate = ie._geometria_9050({"geometria": {"piso": 0.26, "espelho": 0.185,
                                             "blondel": 0.63}})
    assert gate["OK"] is False
    assert gate["ok_piso"] is False
    assert gate["ok_espelho"] is False


# --- altura da edificacao (3.3) --------------------------------------------

def test_a_cobertura_sem_ocupacao_nao_entra_na_altura(execucao, spec):
    """3.3 NOTA 2: areas tecnicas acima do ultimo pavimento ocupado nao contam."""
    resultado, registros = execucao
    fire = registros["incendio"]["fire"]
    pe = spec["turnkey"]["estrutura"]["geometria"]["pe_direito"]
    n_pav = len(spec["turnkey"]["estrutura"]["pavimentos"])

    # a estrutura conta os 9 pavimentos; a 9077 conta os 8 OCUPADOS
    assert resultado["estrutura"]["H_total_m"] == pytest.approx(n_pav * pe)
    assert fire["altura_edificacao_m"] == pytest.approx((n_pav - 1) * pe)


def test_ocupar_a_cobertura_muda_a_altura_e_pode_mudar_a_escada(spec):
    ocupada = copy.deepcopy(spec)
    ocupada["turnkey"]["incendio"]["pavimentos"]["Cobertura"] = {
        "atividade": "habitacao_multifamiliar", "dormitorios": 2}
    _resultado, registros = _rodar(ocupada)
    pe = spec["turnkey"]["estrutura"]["geometria"]["pe_direito"]
    assert registros["incendio"]["fire"]["altura_edificacao_m"] == pytest.approx(9 * pe)


# --- silencio proibido: pavimento omitido ----------------------------------

def test_pavimento_omitido_do_projeto_de_incendio_bloqueia(spec):
    """Populacao que some do calculo da escada em silencio e' o defeito-classe."""
    faltando = copy.deepcopy(spec)
    faltando["turnkey"]["incendio"]["pavimentos"].pop("Tipo 5")
    _resultado, registros = _rodar(faltando)

    assert registros["incendio"]["status"] == "blocked"
    detalhe = registros["incendio"]["errors"][0]["detail"]
    assert "Tipo 5" in detalhe
    assert "sem_ocupacao" in detalhe


def test_pavimento_inexistente_declarado_tambem_bloqueia(spec):
    sobrando = copy.deepcopy(spec)
    sobrando["turnkey"]["incendio"]["pavimentos"]["Subsolo"] = {
        "atividade": "garagem_com_publico", "vagas": 20}
    _resultado, registros = _rodar(sobrando)
    assert registros["incendio"]["status"] == "blocked"
    assert "Subsolo" in registros["incendio"]["errors"][0]["detail"]


def test_velocidade_de_incendio_nao_tem_default(spec):
    sem = copy.deepcopy(spec)
    sem["turnkey"]["incendio"].pop("velocidade_incendio")
    _resultado, registros = _rodar(sem)
    assert registros["incendio"]["status"] == "blocked"
    assert registros["incendio"]["errors"][0]["code"] == "fire_input_not_declared"


# --- Tabela 10 / 9.4.3: a largura exigida ----------------------------------

def test_largura_vertical_pela_tabela10(execucao):
    """9.4.3: largura por pessoa do piso mais elevado x populacao total."""
    _resultado, registros = execucao
    gate = registros["incendio"]["gates"]["escada_largura"]
    # perfil C1, oitavo andar -> 2,30 mm/pessoa (Tab.10, linha "B1, C1, E1")
    assert gate["largura_por_pessoa_mm"] == 2.30
    assert gate["populacao_de_calculo"] == 64        # 8 pavimentos x 8 pessoas
    assert gate["largura_calculada_m"] == pytest.approx(64 * 2.30 / 1000.0,
                                                        abs=5e-4)
    # com populacao pequena quem governa e' o minimo da 9050
    assert gate["largura_exigida_m"] == ie.ESCADA_LARGURA_MIN_M
    assert gate["governa"] == "NBR 9050 6.8.3"


def test_predio_cheio_faz_a_tabela10_governar(spec):
    """Com populacao grande a Tab.10 passa a mandar, e nao mais a 9050."""
    cheio = copy.deepcopy(spec)
    for nome, dados in cheio["turnkey"]["incendio"]["pavimentos"].items():
        if not dados.get("sem_ocupacao"):
            dados["dormitorios"] = 200
    _resultado, registros = _rodar(cheio)
    gate = registros["incendio"]["gates"]["escada_largura"]
    assert gate["populacao_de_calculo"] == 8 * 400
    assert gate["largura_exigida_m"] == pytest.approx(3200 * 2.30 / 1000.0)
    assert gate["governa"] == "NBR 9077 Tab.10"
    assert gate["OK"] is False                       # 1,30 m declarados nao bastam


def test_abandono_faseado_usa_a_coluna_do_segundo_andar(spec):
    """9.4.4 + nota (F) da Tab.10: dois pavimentos de maior lotacao."""
    faseado = copy.deepcopy(spec)
    faseado["turnkey"]["incendio"]["estrategia_abandono"] = "faseado"
    _resultado, registros = _rodar(faseado)
    gate = registros["incendio"]["gates"]["escada_largura"]
    assert gate["largura_por_pessoa_mm"] == 3.80     # C1, coluna "Segundo andar"
    assert gate["populacao_de_calculo"] == 16        # os DOIS maiores (8 + 8)
    avisos = {a["code"] for a in registros["incendio"]["warnings"]}
    assert "abandono_faseado_exige_gestao" in avisos


# --- Tabela 11: tipo de escada ---------------------------------------------

def test_tabela11_por_ocupante_e_altura():
    assert ie.tipo_escada_exigido("Ci", 11.0) == "aberta"      # ate 12 m
    assert ie.tipo_escada_exigido("Ci", 23.2) == "protegida"   # 12 a 30 m
    assert ie.tipo_escada_exigido("Ci", 45.0) == "prova_de_fumaca"
    assert ie.tipo_escada_exigido("B", 11.0) == "protegida"    # B: EP de 6 a 12 m
    assert ie.tipo_escada_exigido("D", 8.0) == "prova_de_fumaca"  # D: EP nao aplicavel


def test_escada_mais_protegida_atende_a_menos_protegida():
    assert ie.atende_tipo_escada("pressurizada", "protegida") is True
    assert ie.atende_tipo_escada("aberta", "protegida") is False


def test_predio_alto_exige_prova_de_fumaca_e_diz_o_que_nao_dimensiona(spec):
    alto = copy.deepcopy(spec)
    alto["turnkey"]["incendio"]["altura_edificacao_m"] = 42.0
    _resultado, registros = _rodar(alto)
    gate = registros["incendio"]["gates"]["escada_tipo"]
    assert gate["tipo_exigido"] == "prova_de_fumaca"
    assert gate["OK"] is False                       # 'protegida' declarada
    scope = registros["incendio"]["scope"]
    assert scope["ventilacao_da_escada"] == "not_available"
    assert scope["antecamara_pressurizacao_nbr14880"] == "not_available"


def test_escada_externa_e_limitada_a_45_m(spec):
    alto = copy.deepcopy(spec)
    alto["turnkey"]["incendio"]["altura_edificacao_m"] = 60.0
    alto["turnkey"]["incendio"]["escada"]["tipo"] = "externa"
    _resultado, registros = _rodar(alto)
    gate = registros["incendio"]["gates"]["escada_tipo"]
    assert gate["OK"] is False
    assert "45" in gate["erro"]


# --- Tabela 5 / 7.4: numero de rotas ---------------------------------------

def test_tabela5_numero_minimo_de_rotas():
    assert ie.rotas_minimas(100) == 1
    assert ie.rotas_minimas(101) == 2
    assert ie.rotas_minimas(500) == 2
    assert ie.rotas_minimas(1001) == 4


def test_rota_unica_vedada_pela_altura_para_ocupante_nao_ci(spec):
    """7.4.3: acima de 30 m os demais ocupantes precisam de mais de uma rota."""
    escritorio = copy.deepcopy(spec)
    escritorio["turnkey"]["incendio"]["ocupante"] = "A"
    escritorio["turnkey"]["incendio"]["altura_edificacao_m"] = 35.0
    _resultado, registros = _rodar(escritorio)
    gate = registros["incendio"]["gates"]["rotas_verticais"]
    assert gate["n_minimo"] == 2
    assert gate["OK"] is False                        # 1 declarada
    avisos = {a["code"] for a in registros["incendio"]["warnings"]}
    assert "rota_unica_vedada_pela_altura" in avisos


def test_ci_ate_80_m_pode_ter_rota_unica(execucao):
    """7.4.2: Ci ate 80 m pode ter uma unica rota, com pop <= 100 (Tab.5)."""
    _resultado, registros = execucao
    gate = registros["incendio"]["gates"]["rotas_verticais"]
    assert gate["n_minimo"] == 1
    assert gate["OK"] is True


# --- Tabela 6 e 7: distancia a percorrer -----------------------------------

def test_ganho_de_caminhamento_satura_em_36_por_cento():
    """7.5.5.2: o efeito acumulativo nao pode ultrapassar 36 %."""
    r = ie.distancia_maxima("A1", pe_direito_rota_m=12.0, deteccao=True,
                            controle_fumaca=True)
    assert r["ganho_bruto_pct"] == pytest.approx(15 + 20 + 30)
    assert r["ganho_pct"] == 36.0
    assert r["ganho_saturou"] is True


def test_caminhamento_em_uma_direcao_tem_teto_de_30_m():
    """7.5.5.2: o caminhamento em uma so direcao nao pode ultrapassar 30 m."""
    r = ie.distancia_maxima("A1", pe_direito_rota_m=12.0, deteccao=True,
                            controle_fumaca=True)
    assert r["base_unica_m"] == 30.0
    assert r["unica_direcao_m"] == 30.0              # 30 x 1,36 truncado no teto
    assert r["unica_direcao_teto_aplicado"] is True


def test_leiaute_indefinido_reduz_30_por_cento():
    """7.5.4.1: rota nao definida no projeto arquitetonico perde 30 %."""
    definido = ie.distancia_maxima("A1")
    aberto = ie.distancia_maxima("A1", leiaute_definido=False)
    assert aberto["alternativas_m"] == pytest.approx(definido["alternativas_m"] * 0.7)


def test_ganho_de_deteccao_nao_e_de_graca(spec):
    """O ganho de 15 % e' da DETECCAO (17240), nao do alarme manual de 4.4.2 c)."""
    _resultado, registros = _rodar(spec)
    gate = registros["incendio"]["gates"]["caminhamento"]
    assert gate["ganho_pct"] == 0.0                  # deteccao_automatica: false

    com = copy.deepcopy(spec)
    com["turnkey"]["incendio"]["caminhamento"]["deteccao_automatica"] = True
    _r2, reg2 = _rodar(com)
    assert reg2["incendio"]["gates"]["caminhamento"]["ganho_pct"] == 15.0


def test_perfil_b_so_ganha_deteccao_com_comunicacao_por_voz(spec):
    """NOTA 2 da Tab.7."""
    loja = copy.deepcopy(spec)
    loja["turnkey"]["incendio"]["ocupante"] = "B"
    loja["turnkey"]["incendio"]["caminhamento"]["deteccao_automatica"] = True
    _resultado, registros = _rodar(loja)
    assert registros["incendio"]["gates"]["caminhamento"]["ganho_pct"] == 0.0
    avisos = {a["code"] for a in registros["incendio"]["warnings"]}
    assert "ganho_de_deteccao_negado_perfil_b" in avisos


def test_sem_distancia_declarada_o_gate_reprova(spec):
    """As distancias sao MEDIDAS na planta; ausencia nao vira estimativa."""
    sem = copy.deepcopy(spec)
    sem["turnkey"]["incendio"]["caminhamento"] = {"leiaute_definido": True}
    _resultado, registros = _rodar(sem)
    gate = registros["incendio"]["gates"]["caminhamento"]
    assert gate["OK"] is False
    assert "planta de arquitetura" in gate["erro"]


# --- Tabela 8: rotas horizontais -------------------------------------------

def test_largura_horizontal_pela_tabela8_com_piso_da_9050(execucao):
    _resultado, registros = execucao
    gate = registros["incendio"]["gates"]["rotas_horizontais"]
    assert gate["largura_por_pessoa_mm"] == 3.6      # C1
    assert gate["largura_exigida_m"] == 1.20         # corredor ate 10 m (9050)
    assert gate["governa"] == "NBR 9050 6.11.1"
    assert gate["OK"] is True


# --- os sistemas de 4.4.2 --------------------------------------------------

def test_os_quatro_sistemas_minimos_saem_dimensionados(execucao):
    """4.4.2: sinalizacao (16820), iluminacao (10898) e alarme (17240)."""
    _resultado, registros = execucao
    gates = registros["incendio"]["gates"]
    for nome in ("iluminacao_emergencia", "sinalizacao", "deteccao_alarme"):
        assert gates[nome]["OK"] is True
        assert gates[nome]["referencia"]


def test_a_reserva_de_incendio_nao_se_multiplica_por_pavimento(execucao):
    """Blocos e detectores sao por pavimento; a reserva e' UMA para o predio."""
    resultado, _registros = execucao
    sistemas = resultado["instalacoes"]["incendio"]["sistemas"]
    por_pav = sistemas["por_pavimento"]
    totais = sistemas["totais_edificio"]
    assert totais["blocos_autonomos"] == por_pav["blocos_autonomos"] * 9
    assert totais["detectores"] == por_pav["detectores"] * 9
    assert (totais["reserva_incendio_m3"]
            == sistemas["hidrantes"]["reserva_incendio_m3"])


def test_ocupacao_de_hidrante_inexistente_nao_passa_sob_o_tipo_declarado(spec):
    """`dimensiona_hidrantes` so consulta a Tab.D.1 sem 'tipo'; a fronteira
    confere a ocupacao de qualquer jeito - rotulo errado nao passa calado."""
    errado = copy.deepcopy(spec)
    errado["turnkey"]["incendio"]["hidrantes"] = {"ocupacao": "residencial_A2",
                                                  "tipo": 1}
    _resultado, registros = _rodar(errado)
    assert registros["incendio"]["status"] == "failed"
    assert "residencial_A2" in registros["incendio"]["errors"][0]["detail"]


def test_a_vazao_do_anexo_d_nao_se_perde(execucao):
    """D.2 residencial: 80 L/min por saida -> reserva 2 x 80 x 60 = 9,6 m3."""
    _resultado, registros = execucao
    assert registros["incendio"]["gates"]["hidrantes"]["reserva_incendio_m3"] == 9.6


# --- contrato do adaptador -------------------------------------------------

def test_a_disciplina_incendio_saiu_de_ausente(execucao):
    resultado, registros = execucao
    assert "incendio" in ea.DISCIPLINES
    assert resultado["scope"]["incendio"] == "implemented"
    assert resultado["disciplines"]["incendio"]["engine"] == "incendio_edificio"
    assert registros["incendio"]["status"] == "needs_review"


def test_o_manifesto_publica_os_gates_do_incendio(execucao):
    _resultado, registros = execucao
    gates = registros["incendio"]["gates"]
    esperados = {"populacao", "rotas_verticais", "escada_largura", "escada_tipo",
                 "caminhamento", "rotas_horizontais", "iluminacao_emergencia",
                 "sinalizacao", "deteccao_alarme"}
    assert esperados <= set(gates)
    assert registros["incendio"]["native_atende"] is True


def test_incendio_nao_declarado_nao_vira_projeto_inventado(spec):
    """Sem a declaracao, a disciplina some do resultado - nao vira default.

    A hidraulica LE a populacao do incendio, entao tirar o incendio sem mais
    nada bloquearia a hidraulica junto (ver o teste seguinte). Aqui a populacao
    e' declarada para ISOLAR o que este teste mede: a ausencia da disciplina.
    """
    sem = copy.deepcopy(spec)
    sem["turnkey"].pop("incendio")
    sem["turnkey"]["hidraulica"]["populacao"] = 64
    resultado, registros = _rodar(sem)
    assert "incendio" not in registros
    assert resultado["scope"]["incendio"] == "not_available"
    assert resultado["status"] == "needs_review"


def test_sem_incendio_a_hidraulica_cobra_a_populacao_em_vez_de_estimar(spec):
    """O acoplamento e' deliberado, e ele FALA.

    A populacao do predio e' uma so. Sem o vertical de incendio (de onde ela
    sai) e sem `hidraulica.populacao`, o consumo de agua nao e' estimavel pela
    area do envelope - e a hidraulica bloqueia dizendo as duas saidas, em vez de
    arbitrar um numero de moradores.
    """
    sem = copy.deepcopy(spec)
    sem["turnkey"].pop("incendio")
    _resultado, registros = _rodar(sem)
    assert registros["hidraulica"]["status"] == "blocked"
    detalhe = registros["hidraulica"]["errors"][0]["detail"]
    assert "hidraulica.populacao" in detalhe
    assert "turnkey.incendio.pavimentos" in detalhe
    # a estrutura e a eletrica seguem calculando: falha isolada por disciplina
    assert registros["estrutura"]["status"] == "needs_review"
    assert registros["eletrico"]["status"] == "needs_review"


def test_incendio_sem_estrutura_calculada_bloqueia(spec):
    sem = copy.deepcopy(spec)
    sem["turnkey"]["estrutura"]["materiais"] = {"fck": 0.0, "fyk": 0.0}
    _resultado, registros = _rodar(sem)
    assert registros["incendio"]["status"] == "blocked"
    assert registros["incendio"]["errors"][0]["code"] == "structure_result_required"


def test_a_disciplina_publica_o_seu_proprio_escopo(execucao):
    """O escopo do registro eletrico/incendio nao pode ser o da estrutura."""
    _resultado, registros = execucao
    escopo = registros["incendio"]["scope"]
    assert "fundacao" not in escopo
    assert escopo["populacao_nbr9077"] == "implemented"
    assert escopo["avcb"] == "not_claimed"
    assert escopo["leiaute_arquitetonico"] == "not_available"
