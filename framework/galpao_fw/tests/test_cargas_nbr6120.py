"""Testes das tabelas de acoes da NBR 6120:2019 (cargas_nbr6120).

Os valores conferidos aqui vieram do texto da norma (NotebookLM, notebook "04
Acoes e Equipamentos"), com as citacoes do texto bruto verificadas. O que estes
testes protegem nao e "o codigo roda", e sim:
  - que a transcricao da Tabela 2 e internamente coerente com a NOTA da propria
    tabela (conferencia independente, estilo rotulo x geometria);
  - que as consultas NAO tem fallback silencioso (ambiente/espessura inexistente
    levanta, em vez de cair no vizinho mais proximo);
  - que os gates que nao aparecem como razao solicitante/resistente reprovam
    (Tab.11 acima de 3,0 kN/m; reducao aplicada a viga/laje);
  - que a mecanica do item 6.12 reproduz as Figuras 12 a 14 da norma.
"""

import pytest

import cargas_nbr6120 as cg


# ---------------------------------------------------------------------------
# Tabela 2 - alvenarias
# ---------------------------------------------------------------------------
def test_tabela2_coerente_com_a_propria_nota():
    """A NOTA da Tabela 2 declara revestimento de 19 kN/m3, logo cada cm por face
    soma 0,19 kN/m2. As tres colunas de cada linha tem de ser arredondamentos de um
    MESMO peso-base. As unicas linhas sem base compativel sao as duas conhecidas,
    conferidas no texto bruto da norma (o proprio arredondamento da ABNT)."""
    fora = cg._coerencia_tab2()
    achadas = {(t, e) for (t, e, _p, _lo, _hi) in fora}
    conhecidas = {(t, e) for (t, e, _rev) in cg.DIVERGENCIAS_TAB2_CONHECIDAS}
    assert achadas == conhecidas, (
        "divergencia NOVA na Tabela 2 (possivel erro de transcricao): %s" % fora)


def test_peso_alvenaria_e_por_m2_de_parede_nao_por_m3():
    """ROTULO x GEOMETRIA: o valor da Tabela 2 e kN/m2 DE PAINEL. Uma parede de bloco
    ceramico de vedacao de 14 cm com 1 cm de revestimento por face pesa 1,5 kN/m2 de
    parede. Se alguem tratasse esse numero como kN/m3 e multiplicasse pela espessura,
    daria 0,21 kN/m2 - uma parede 7x mais leve, em silencio."""
    p = cg.peso_alvenaria("bloco_ceramico_furo_horizontal", 14.0, 1.0)
    assert p == 1.5
    # a grandeza tem ordem de kN/m2 de parede, nao de peso especifico x espessura
    assert p / 0.14 > 5.0


def test_carga_linear_parede_multiplica_pela_altura():
    """Carga linear sobre a viga = peso do painel x ALTURA da parede."""
    q = cg.carga_linear_parede("bloco_ceramico_furo_horizontal", 14.0, 2.80, 1.0)
    assert q == pytest.approx(1.5 * 2.80, rel=1e-12)


def test_alvenaria_estrutural_e_vedacao_sao_linhas_distintas():
    """A norma separa os dois blocos e os pesos diferem: usar a linha de vedacao no
    lugar da estrutural subestima a carga."""
    estrut = cg.peso_alvenaria("bloco_concreto_estrutural", 14.0, 1.0)
    vedac = cg.peso_alvenaria("bloco_concreto_vedacao", 14.0, 1.0)
    assert cg.ALVENARIAS["bloco_concreto_estrutural"]["estrutural"] is True
    assert cg.ALVENARIAS["bloco_concreto_vedacao"]["estrutural"] is False
    assert estrut > vedac


def test_espessura_nao_tabelada_levanta_em_vez_de_arredondar():
    """A tabela e discreta. Cair na espessura mais proxima subestimaria (ou inventaria)
    o peso sem nunca avisar - o padrao do 'filtro de nome morto'."""
    with pytest.raises(ValueError, match="nao tabelada"):
        cg.peso_alvenaria("bloco_ceramico_furo_horizontal", 12.0, 1.0)


def test_revestimento_nao_tabelado_levanta():
    with pytest.raises(ValueError, match="revestimento"):
        cg.peso_alvenaria("bloco_ceramico_furo_horizontal", 14.0, 1.5)


def test_bloco_de_vidro_so_tem_coluna_sem_revestimento():
    assert cg.peso_alvenaria("bloco_vidro", 8.0, 0.0) == 0.8
    with pytest.raises(ValueError):
        cg.peso_alvenaria("bloco_vidro", 8.0, 1.0)


# ---------------------------------------------------------------------------
# Tabela 10 - cargas de uso
# ---------------------------------------------------------------------------
def test_cargas_de_uso_conferidas_na_norma():
    esperado = {
        "residencial_dormitorio": 1.5,
        "residencial_servico": 2.0,
        "residencial_corredor_comum": 3.0,
        "escritorio_sala_uso_geral": 2.5,
        "escada_residencial_comum": 3.0,
        "escada_sem_acesso_publico": 2.5,
        "sacada_residencial": 2.5,
        "loja": 4.0,
        "loja_deposito": 5.0,
        "escola_sala_aula": 3.0,
        "biblioteca_leitura_com_estantes": 4.0,
        "cobertura_manutencao": 1.0,
        "garagem_ate_30kN": 3.0,
        "forro_manutencao": 0.1,
    }
    for chave, q in esperado.items():
        assert cg.carga_uso(chave)["q"] == q, chave


def test_ambiente_inexistente_levanta_sem_default():
    """Sem fallback: uma 'loja' que caisse num default de 1,5 kN/m2 seria dimensionada
    com 37% da carga da norma, e nada reprovaria."""
    with pytest.raises(KeyError, match="nao consta na Tabela 10"):
        cg.carga_uso("sala_de_estar")


def test_garagem_traz_concentrada_e_impacto_da_tabela13():
    g = cg.carga_uso("garagem_ate_30kN")
    assert g["q"] == 3.0 and g["Q"] == 12.0
    assert g["redutivel"] is False
    assert cg.GARAGEM_CAT_I["Fx"] == 100.0 and cg.GARAGEM_CAT_I["Fy"] == 50.0
    assert cg.GARAGEM_CAT_I["H_aplicacao_m"] == 0.5


def test_usos_nao_redutiveis_marcados():
    """A nota 'a' da Tabela 10 e a lista de 6.12 marcam quem nao pode ser reduzido."""
    for chave in ("garagem_ate_30kN", "cobertura_manutencao", "loja_deposito",
                  "escola_sala_aula", "restaurante_salao", "loja"):
        assert cg.carga_uso(chave)["redutivel"] is False, chave
    for chave in ("residencial_dormitorio", "escritorio_sala_uso_geral"):
        assert cg.carga_uso(chave)["redutivel"] is True, chave


# ---------------------------------------------------------------------------
# Tabela 11 - paredes divisorias sem posicao definida
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("pp,adicional", [(0.8, 0.5), (1.0, 0.5), (1.5, 0.75),
                                          (2.0, 0.75), (2.5, 1.0), (3.0, 1.0)])
def test_tabela11_faixas(pp, adicional):
    r = cg.parede_sem_posicao_definida(pp, q_pavimento_kN_m2=1.5)
    assert r["ok"] and r["adicional_kN_m2"] == adicional


def test_tabela11_acima_de_3kNm_reprova_em_vez_de_saturar():
    """SATURACAO SILENCIOSA: acima de 3,0 kN/m a norma diz NAO PERMITIDO. Uma
    implementacao que saturasse na ultima faixa devolveria 1,0 kN/m2 e OK, deixando a
    parede pesada fora da posicao de projeto sem nenhum gate reprovar."""
    r = cg.parede_sem_posicao_definida(3.6, q_pavimento_kN_m2=1.5)
    assert r["ok"] is False
    assert r["adicional_kN_m2"] is None
    assert "NAO PERMITIDO" in r["motivo"]
    assert "PERMANENTE" in r["motivo"]


def test_tabela11_dispensa_para_q_maior_igual_4():
    r = cg.parede_sem_posicao_definida(2.0, q_pavimento_kN_m2=4.0)
    assert r["ok"] and r["dispensada"] is True and r["adicional_kN_m2"] == 0.0


def test_dispensa_nao_vale_para_parede_acima_de_3kNm():
    """A excecao explicita do texto de 6.2: a dispensa por q >= 4,0 kN/m2 NAO se
    aplica a alvenaria com p.p. > 3,0 kN/m."""
    r = cg.parede_sem_posicao_definida(3.5, q_pavimento_kN_m2=5.0)
    assert r["ok"] is False and r["dispensada"] is False


# ---------------------------------------------------------------------------
# Tabela 12 - guarda-corpos
# ---------------------------------------------------------------------------
def test_guarda_corpo_valores_e_altura():
    assert cg.forca_guarda_corpo("passarela_inspecao")["F_kN_m"] == 0.4
    assert cg.forca_guarda_corpo("privativa_residencial")["F_kN_m"] == 1.0
    assert cg.forca_guarda_corpo("fluxo_paralelo")["F_kN_m"] == 2.0
    assert cg.forca_guarda_corpo("fluxo_perpendicular")["F_kN_m"] == 3.0
    assert cg.forca_guarda_corpo("escada_panoramica")["F_kN_m"] == 2.0
    r = cg.forca_guarda_corpo("acesso_publico")
    assert r["h_aplicacao_m"] == 1.10


def test_evento_extremo_so_nas_linhas_com_a_nota_b():
    r = cg.forca_guarda_corpo("fluxo_perpendicular", evento_extremo=True)
    assert r["F_kN_m"] == 5.0 and r["avisos"]
    with pytest.raises(ValueError, match="nota b"):
        cg.forca_guarda_corpo("passarela_inspecao", evento_extremo=True)


def test_ancoragem_de_balancim():
    assert cg.FD_ANCORAGEM_BALANCIM == 15.0


# ---------------------------------------------------------------------------
# Tabela 19 / item 6.12 - reducao de cargas variaveis
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n,a", [(1, 1.0), (2, 1.0), (3, 1.0), (4, 0.8), (5, 0.6),
                                 (6, 0.4), (7, 0.4), (20, 0.4)])
def test_alpha_n_tabela19(n, a):
    assert cg.alpha_n(n) == a


def test_figura12_esquema1_um_unico_uso():
    """Reproduz a Figura 12 (esquema 1) da norma: cobertura e atico a 1,0; o grupo de
    uso conta 1,0/1,0/1,0/0,8/0,6/0,4/0,4/...; terreo e garagem a 1,0."""
    pav = ([{"nome": "Cobertura", "uso": "cobertura_manutencao"},
            {"nome": "Atico", "uso": "sotao"}]
           + [{"nome": "Tipo %d" % i, "uso": "residencial_dormitorio"}
              for i in range(1, 10)]
           + [{"nome": "Terreo", "uso": "loja"},
              {"nome": "Garagem", "uso": "garagem_ate_30kN"}])
    alphas = [r["alpha"] for r in cg.multiplicadores_pavimentos(pav)]
    assert alphas == [1.0, 1.0,
                      1.0, 1.0, 1.0, 0.8, 0.6, 0.4, 0.4, 0.4, 0.4,
                      1.0, 1.0]


def test_figura12_esquema2_cvnr_nao_interrompe_a_sequencia():
    """"A presenca de pavimentos inteiramente ocupados por carga variavel nao
    redutivel, entre pavimentos com carga variavel redutivel, NAO interrompe a
    sequencia dos multiplicadores do grupo": o 4o piso de Uso1 esta em 0,8; passados
    dois c.v.n.r. (que recebem 1,0), o proximo Uso1 e o 5o do grupo -> 0,6."""
    pav = ([{"nome": "Uso1 %d" % i, "uso": "residencial_dormitorio"} for i in range(1, 5)]
           + [{"nome": "cvnr A", "uso": "garagem_ate_30kN"},
              {"nome": "cvnr B", "uso": "garagem_ate_30kN"}]
           + [{"nome": "Uso1 %d" % i, "uso": "residencial_dormitorio"} for i in range(5, 10)])
    r = cg.multiplicadores_pavimentos(pav)
    assert [x["alpha"] for x in r] == [1.0, 1.0, 1.0, 0.8,
                                       1.0, 1.0,
                                       0.6, 0.4, 0.4, 0.4, 0.4]
    # a contagem foi PAUSADA, nao reiniciada nem avancada pelos c.v.n.r.
    assert r[4]["n_grupo"] is None and r[5]["n_grupo"] is None
    assert r[6]["n_grupo"] == 5


def test_figura13_troca_de_uso_reinicia_a_contagem():
    pav = ([{"nome": "U1 %d" % i, "uso": "residencial_dormitorio"} for i in range(1, 7)]
           + [{"nome": "U2 %d" % i, "uso": "escritorio_sala_uso_geral"} for i in range(1, 5)])
    alphas = [r["alpha"] for r in cg.multiplicadores_pavimentos(pav)]
    assert alphas == [1.0, 1.0, 1.0, 0.8, 0.6, 0.4,
                      1.0, 1.0, 1.0, 0.8]


def test_figura14_mesma_ocupacao_areas_diferentes_sao_grupos_distintos():
    """"grupos de pavimentos com diferentes areas devem ser considerados como grupos
    distintos" - sem isso, a torre escalonada acumularia a contagem e reduziria demais."""
    pav = ([{"nome": "Torre %d" % i, "uso": "residencial_dormitorio", "area": 300.0}
            for i in range(1, 6)]
           + [{"nome": "Base %d" % i, "uso": "residencial_dormitorio", "area": 800.0}
              for i in range(1, 5)])
    r = cg.multiplicadores_pavimentos(pav)
    assert [x["alpha"] for x in r] == [1.0, 1.0, 1.0, 0.8, 0.6,
                                       1.0, 1.0, 1.0, 0.8]
    assert "area em planta diferente" in r[5]["motivo"]


def test_acumulado_soma_os_qk_ja_reduzidos_piso_a_piso():
    """Leitura B do item 6.12 (a das Figuras 12 a 14): a carga que chega ao pilar e a
    SOMA dos qk ja multiplicados piso a piso, nao a soma bruta vezes um unico alpha."""
    pav = [{"nome": "P%d" % i, "uso": "residencial_dormitorio"} for i in range(1, 7)]
    r = cg.multiplicadores_pavimentos(pav)
    esperado = 1.5 * (1.0 + 1.0 + 1.0 + 0.8 + 0.6 + 0.4)
    assert r[-1]["acumulado_kN_m2"] == pytest.approx(esperado, rel=1e-9)
    # a leitura A (um unico alpha sobre a soma) daria bem menos - nao e a da norma
    assert esperado > 6 * 1.5 * cg.alpha_n(6)


def test_reducao_nao_se_aplica_a_viga_nem_a_laje():
    """O item 6.12 e explicito: "para a determinacao de esforcos solicitantes em
    PILARES E FUNDACOES". Reduzir a carga de uma viga seria subdimensiona-la."""
    pav = [{"nome": "P%d" % i, "uso": "residencial_dormitorio"} for i in range(1, 9)]
    for elemento in ("viga", "laje"):
        r = cg.multiplicadores_pavimentos(pav, elemento=elemento)
        assert all(x["alpha"] == 1.0 for x in r)
        assert "PILARES E FUNDACOES" in r[0]["motivo"]


def test_fundacao_recebe_a_reducao_como_o_pilar():
    pav = [{"nome": "P%d" % i, "uso": "residencial_dormitorio"} for i in range(1, 7)]
    a_pilar = [x["alpha"] for x in cg.multiplicadores_pavimentos(pav, "pilar")]
    a_fund = [x["alpha"] for x in cg.multiplicadores_pavimentos(pav, "fundacao")]
    assert a_pilar == a_fund


def test_qk_explicito_sem_chave_da_tabela10():
    pav = [{"nome": "Especial", "uso": "uso_proprio", "qk": 2.2} for _ in range(4)]
    r = cg.multiplicadores_pavimentos(pav)
    assert [x["alpha"] for x in r] == [1.0, 1.0, 1.0, 0.8]
    assert r[0]["qk"] == 2.2


def test_pavimento_sem_qk_e_sem_uso_conhecido_levanta():
    with pytest.raises(KeyError, match="informe 'qk'"):
        cg.multiplicadores_pavimentos([{"nome": "X", "uso": "inexistente"}])


def test_registro_das_reducoes_exigido_por_612():
    """"As reducoes adotadas devem ser registradas nos documentos do projeto" - o
    registro e uma exigencia normativa, nao um conforto de depuracao."""
    pav = ([{"nome": "Cobertura", "uso": "cobertura_manutencao"}]
           + [{"nome": "Tipo %d" % i, "uso": "residencial_dormitorio"} for i in range(1, 7)])
    txt = cg.registro_reducoes(cg.multiplicadores_pavimentos(pav))
    assert "6.12" in txt and "Tabela 19" in txt
    assert "Cobertura" in txt and "Tipo 6" in txt
    assert "NAO REDUTIVEL" in txt
    assert "NAO se aplica a vigas nem a lajes" in txt
