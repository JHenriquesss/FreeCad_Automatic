"""Testes da descida de cargas do edificio multipavimento.

O ponto sensivel: a reducao de cargas variaveis do item 6.12 da NBR 6120 e uma
BONIFICACAO - ela so alivia o pilar. Aplicada onde a norma nao permite, nada
reprova; o pilar simplesmente sai subdimensionado. Por isso os testes verificam
tanto que a reducao acontece onde deve, quanto que ela NAO acontece onde nao deve,
e que ela incide so sobre a parcela variavel.
"""

import pytest

import descida_cargas as dc
import pilar_continuo as pcn


def _tipo(**kw):
    base = {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5], "h_laje": 0.10,
            "uso": "residencial_dormitorio", "revestimento_kN_m2": 1.0,
            "b_viga": 0.20, "h_viga": 0.50, "fck": 30e3, "fyk": 500e3,
            "pe_direito": 2.90}
    base.update(kw)
    return base


def _predio(n_tipo=8, cobertura=True, tipo=None):
    tipo = tipo or _tipo()
    pavs = []
    if cobertura:
        pavs.append({"nome": "Cobertura", "pavimento": _tipo(uso="cobertura_manutencao"),
                     "pe_direito": 2.90, "secao": {"b": 0.25, "h": 0.60}})
    for i in range(n_tipo, 0, -1):
        pavs.append({"nome": "Tipo %d" % i, "pavimento": tipo, "pe_direito": 2.90,
                     "secao": {"b": 0.25, "h": 0.60}})
    return pavs


# ---------------------------------------------------------------------------
# empilhamento e acumulacao
# ---------------------------------------------------------------------------
def test_carga_acumula_do_topo_para_a_base():
    r = dc.descer({"pavimentos": _predio()})
    lances = r["pilares"]["P22"]["lances"]
    acum = [l["N_acum_k"] for l in lances]
    assert acum == sorted(acum)
    assert acum[-1] == pytest.approx(r["pilares"]["P22"]["N_base_k"], rel=1e-6)


def test_pavimentos_identicos_dao_parcelas_permanentes_identicas():
    """O permanente nao e reduzido por 6.12, entao cada pavimento-tipo entrega
    exatamente a mesma parcela g."""
    r = dc.descer({"pavimentos": _predio()})
    gs = [l["N_g_pav"] for l in r["pilares"]["P22"]["lances"][1:]]
    assert max(gs) == pytest.approx(min(gs), rel=1e-9)


def test_malhas_diferentes_entre_pavimentos_levantam():
    tipo_a = _tipo()
    tipo_b = _tipo(vaos_x=[5.0, 5.0])
    pavs = [{"nome": "A", "pavimento": tipo_a}, {"nome": "B", "pavimento": tipo_b}]
    with pytest.raises(ValueError, match="malhas de pilares diferentes"):
        dc.descer({"pavimentos": pavs})


def test_predio_sem_pavimentos_levanta():
    with pytest.raises(ValueError, match="pelo menos um pavimento"):
        dc.descer({"pavimentos": []})


# ---------------------------------------------------------------------------
# item 6.12 - a reducao incide SO sobre a parcela variavel
# ---------------------------------------------------------------------------
def test_reducao_nao_toca_no_permanente():
    """Aplicar alpha_n sobre a reacao TOTAL reduziria tambem o peso proprio - a norma
    reduz apenas 'o valor da carga variavel de uso'."""
    r = dc.descer({"pavimentos": _predio()})
    p = r["pilares"]["P22"]
    soma_g = sum(l["N_g_pav"] for l in p["lances"])
    assert p["N_base_g_k"] == pytest.approx(soma_g, rel=1e-6)
    # e a parcela variavel acumulada e menor que a bruta
    soma_q_bruta = sum(l["N_q_pav_bruto"] for l in p["lances"])
    assert p["N_base_q_k"] < soma_q_bruta


def test_multiplicador_por_pavimento_bate_com_a_tabela19():
    r = dc.descer({"pavimentos": _predio(n_tipo=8)})
    alphas = [pv["alpha_n"] for pv in r["pavimentos"]]
    # cobertura (nao redutivel) 1,0 e nao consome posicao; depois 1/1/1/0,8/0,6/0,4...
    assert alphas == [1.0, 1.0, 1.0, 1.0, 0.8, 0.6, 0.4, 0.4, 0.4]


def test_cobertura_nao_consome_posicao_do_grupo():
    """A cobertura e nao redutivel; ela nao interrompe nem avanca a contagem do grupo
    dos pavimentos-tipo abaixo dela (6.12)."""
    com = dc.descer({"pavimentos": _predio(n_tipo=6, cobertura=True)})
    sem = dc.descer({"pavimentos": _predio(n_tipo=6, cobertura=False)})
    alpha_com = [pv["alpha_n"] for pv in com["pavimentos"] if pv["nome"] != "Cobertura"]
    alpha_sem = [pv["alpha_n"] for pv in sem["pavimentos"]]
    assert alpha_com == alpha_sem


def test_reducao_alivia_a_base_mas_pouco_em_uso_residencial():
    """Sanidade de ordem de grandeza: em residencial a variavel e pequena diante da
    permanente, entao o alivio na base fica na casa de poucos por cento. Um alivio de
    dezenas de por cento seria sinal de que a reducao pegou o permanente junto."""
    r = dc.descer({"pavimentos": _predio()})
    v = dc.verifica_reducao(r)
    assert v["ok"]
    assert 0.0 < v["alivio_pct_max"] < 15.0


def test_predio_baixo_nao_recebe_reducao_nenhuma():
    r = dc.descer({"pavimentos": _predio(n_tipo=3, cobertura=False)})
    assert all(pv["alpha_n"] == 1.0 for pv in r["pavimentos"])
    p = r["pilares"]["P22"]
    assert p["N_base_k"] == pytest.approx(p["N_base_sem_reducao_k"], rel=1e-6)


# ---------------------------------------------------------------------------
# gates: onde a reducao NAO pode ser aplicada
# ---------------------------------------------------------------------------
def test_garagem_e_cobertura_nunca_sao_reduzidas():
    """A lista de 6.12 exclui garagens e coberturas. Elas entram com alpha = 1,0
    mesmo no meio de uma pilha alta."""
    tipo = _tipo()
    pavs = _predio(n_tipo=6, tipo=tipo)
    pavs.append({"nome": "Garagem", "pavimento": _tipo(uso="garagem_ate_30kN"),
                 "pe_direito": 2.90, "secao": {"b": 0.25, "h": 0.60}})
    r = dc.descer({"pavimentos": pavs})
    por_nome = {pv["nome"]: pv for pv in r["pavimentos"]}
    assert por_nome["Garagem"]["alpha_n"] == 1.0
    assert por_nome["Garagem"]["redutivel"] is False
    assert por_nome["Cobertura"]["alpha_n"] == 1.0
    assert dc.verifica_reducao(r)["ok"]


def test_reducao_desligada_para_viga_e_laje():
    """6.12 vale so para pilares e fundacoes. Pedindo o elemento 'viga', nenhum
    pavimento pode ser reduzido."""
    r = dc.descer({"pavimentos": _predio(), "elemento": "viga"})
    assert all(pv["alpha_n"] == 1.0 for pv in r["pavimentos"])
    p = r["pilares"]["P22"]
    assert p["N_base_k"] == pytest.approx(p["N_base_sem_reducao_k"], rel=1e-6)


def test_fundacao_recebe_a_mesma_reducao_do_pilar():
    a = dc.descer({"pavimentos": _predio(), "elemento": "pilar"})
    b = dc.descer({"pavimentos": _predio(), "elemento": "fundacao"})
    assert (a["pilares"]["P22"]["N_base_k"]
            == pytest.approx(b["pilares"]["P22"]["N_base_k"], rel=1e-9))


def test_verifica_reducao_acusa_alpha_indevido():
    """Guarda direta contra o subdimensionamento silencioso: se por qualquer caminho
    um pavimento nao redutivel sair com alpha < 1, o gate acusa."""
    r = dc.descer({"pavimentos": _predio()})
    # simula a regressao adulterando a linha da cobertura (nao redutivel)
    for lin in r["linhas_reducao"]:
        if not lin["redutivel"]:
            lin["alpha"] = 0.4
            break
    v = dc.verifica_reducao(r)
    assert v["ok"] is False
    assert any("NAO REDUTIVEL" in x for x in v["violacoes"])


def test_registro_das_reducoes_sai_no_relatorio():
    """6.12: 'as reducoes adotadas devem ser registradas nos documentos do projeto'."""
    r = dc.descer({"pavimentos": _predio()})
    txt = dc.relatorio(r)
    assert "6.12" in txt and "Tabela 19" in txt
    assert "DESCIDA DE CARGAS" in txt
    assert "P22" in txt


# ---------------------------------------------------------------------------
# integracao com o pilar continuo
# ---------------------------------------------------------------------------
def test_lances_alimentam_o_pilar_continuo():
    r = dc.descer({"pavimentos": _predio()})
    lances = dc.lances_para_pilar(r, "P22")
    assert len(lances) == r["n_pavimentos"]
    p = pcn.dimensiona({"lances": lances, "fck": 30e3, "fyk": 500e3})
    assert p["OK"] is True
    # a forca normal na base do pilar continuo = descida + peso proprio dos lances
    assert p["N_base_k"] > r["pilares"]["P22"]["N_base_k"]
    # e a armadura cresce para baixo
    As = [x["As_cm2"] for x in p["lances"]]
    assert As[-1] >= As[0]


def test_pilar_interno_puxa_mais_carga_que_o_de_canto_em_todo_o_predio():
    r = dc.descer({"pavimentos": _predio()})
    assert (r["pilares"]["P22"]["N_base_k"] > r["pilares"]["P11"]["N_base_k"] * 3)


def test_pilar_inexistente_levanta():
    r = dc.descer({"pavimentos": _predio()})
    with pytest.raises(KeyError, match="nao existe na descida"):
        dc.lances_para_pilar(r, "P99")
