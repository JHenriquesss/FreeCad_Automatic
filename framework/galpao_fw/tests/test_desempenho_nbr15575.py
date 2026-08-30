"""Testes do desempenho de edificacao habitacional (NBR 15575) - G11.

As Tabelas 1 e 2 da parte 2 foram transcritas da fonte e conferidas linha a
linha (o precedente "AR300": tabela decorada cristaliza erro). Estes testes
travam:

  1. os VALORES das duas tabelas, incluindo as linhas que a auditoria do G2
     tinha resumido de menos (paineis de juntas flexiveis, forros, viga calha);
  2. as notas a (balanco x 1,5) e c (rigidez pela metade na flecha final), que
     sao as duas unicas formas de AFROUXAR ou APERTAR um limite desta tabela;
  3. que um gate do qual nada foi verificado NAO devolve ATENDE.
"""

import pytest

import desempenho_nbr15575 as des


# ---------------------------------------------------------------------------
# 1. OS VALORES DA FONTE
# ---------------------------------------------------------------------------
def test_tabela_2_completa_da_15575_2():
    """Divisores de L nas colunas Sgk / Sqk / Sgk+0,7Sqk / final."""
    esperado = {
        "parede_rigida_com_aberturas": (1000.0, 2800.0, 800.0, 400.0),
        "parede_rigida_sem_aberturas": (750.0, 2100.0, 600.0, 340.0),
        "parede_flexivel_com_aberturas": (1050.0, 1700.0, 730.0, 330.0),
        "parede_flexivel_sem_aberturas": (850.0, 1400.0, 600.0, 300.0),
        "piso_rigido": (700.0, 1500.0, 530.0, 320.0),
        "piso_flexivel": (750.0, 1200.0, 520.0, 280.0),
        "forro_rigido": (600.0, 1700.0, 480.0, 300.0),
        "forro_flexivel": (560.0, 1600.0, 450.0, 260.0),
        "laje_cobertura_impermeabilizada": (850.0, 1400.0, 600.0, 320.0),
        "viga_calha": (750.0, None, None, 300.0),
    }
    assert des.TAB2_15575_2 == esperado
    assert des.COLUNAS_TAB2 == ("Sgk", "Sqk", "Sgk+0,7Sqk", "final")
    assert des.PSI_TAB2 == 0.7


def test_tabela_1_da_15575_2():
    t = des.TAB1_15575_2
    assert (t["visual"]["div_L"], t["visual"]["div_H"]) == (250.0, 300.0)
    assert t["caixilhos_instalacoes_acabamentos_rigidos"]["div_L"] == 800.0
    assert t["divisorias_leves_acabamentos_flexiveis"]["div_L"] == 600.0
    assert (t["vedacoes_rigidas"]["div_L"], t["vedacoes_rigidas"]["div_H"]) == (500.0, 500.0)
    assert (t["vedacoes_flexiveis"]["div_L"], t["vedacoes_flexiveis"]["div_H"]) == (400.0, 400.0)


def test_viga_calha_nao_tem_coluna_Sqk():
    """A norma traz travessao nessas duas celulas. Devolver um limite ali seria
    inventar criterio; o modulo recusa com o motivo."""
    assert des.limite_tab2("viga_calha", "Sgk", 6.0)["limite_m"] == pytest.approx(6.0 / 750)
    with pytest.raises(des.EntradaDesempenho):
        des.limite_tab2("viga_calha", "Sqk", 6.0)


# ---------------------------------------------------------------------------
# 2. AS NOTAS DA TABELA 2
# ---------------------------------------------------------------------------
def test_nota_a_balanco_multiplica_por_1_5():
    reto = des.limite_tab2("piso_rigido", "final", 4.0)
    bal = des.limite_tab2("piso_rigido", "final", 4.0, balanco=True)
    assert bal["limite_m"] == pytest.approx(1.5 * reto["limite_m"])
    assert des.FATOR_BALANCO == 1.5


def test_nota_a_so_liga_por_declaracao_explicita():
    """O balanco AFROUXA o limite. Ligar por default transformaria a nota a numa
    folga silenciosa de 50% em todo elemento."""
    assert des.limite_tab2("piso_rigido", "final", 4.0)["balanco"] is False


def test_nota_c_flecha_final_dobra_o_deslocamento():
    """"reduzir a rigidez dos elementos analisados pela metade": como a flecha e'
    inversamente proporcional a EI, meia rigidez dobra o deslocamento."""
    assert des.flecha_final(0.005) == pytest.approx(0.010)


def test_convencao_da_15575_nao_e_a_fluencia_da_6118():
    """A 15575 obtem a flecha final com EI/2; a NBR 6118 com (1+alpha_f). Sao
    convencoes distintas e nao se somam - este teste existe para que quem mexer
    aqui tropece na diferenca em vez de encadear as duas."""
    import laje_concreto as lj

    f = lj.flecha_laje(1, 4.0, 5.0, 6.0, 0.12, 30e3)
    assert des.flecha_final(f["f_imediata"]) == pytest.approx(2.0 * f["f_imediata"])
    assert f["f_total"] != pytest.approx(des.flecha_final(f["f_imediata"]))


# ---------------------------------------------------------------------------
# 3. TOPO, FISSURA, PISO E FACHADA
# ---------------------------------------------------------------------------
def test_topo_respeita_o_menor_entre_H_500_e_3cm():
    """Nota a da Tabela 1: "H_total/500 ou 3 cm, respeitando-se o MENOR"."""
    baixo = des.limite_topo(10.0)          # 10/500 = 20 mm < 30 mm
    assert baixo["limite_m"] == pytest.approx(0.020)
    assert baixo["governante"] == "H_total/500"
    alto = des.limite_topo(60.0)           # 60/500 = 120 mm > 30 mm
    assert alto["limite_m"] == pytest.approx(0.030)
    assert alto["governante"] == "3 cm"


def test_topo_adota_o_menor_entre_15575_e_a_norma_de_projeto():
    r = des.verifica_topo(0.018, 40.0, u_norma_m=0.0235)   # H/1700 da Tab 13.3
    assert r["limite_adotado_mm"] == pytest.approx(23.5)
    assert r["governante"] == "norma de projeto estrutural"
    assert r["OK"] is True
    # e reprova acima do teto absoluto de 3 cm
    assert des.verifica_topo(0.035, 40.0)["OK"] is False


def test_fissura_de_0_6mm_e_absoluta_mas_a_6118_pode_ser_mais_restritiva():
    assert des.WK_MAX_MM == 0.6
    assert des.verifica_fissura(0.55)["OK"] is True
    assert des.verifica_fissura(0.65)["OK"] is False
    r = des.verifica_fissura(0.35, wk_lim_norma_mm=0.3)     # CAA III
    assert r["OK"] is False and r["governante"].startswith("NBR 6118")


def test_piso_1kN_rigido_e_ductil_tem_limites_diferentes():
    """15575-3 7.5.1: L/500 (rigido) contra L/300 (ductil)."""
    assert des.Q_CONCENTRADA_PISO_kN == 1.0
    rig = des.verifica_piso_carga_concentrada(0.009, 5.0, "rigido")
    duc = des.verifica_piso_carga_concentrada(0.009, 5.0, "ductil")
    assert rig["limite_mm"] == pytest.approx(10.0)
    assert duc["limite_mm"] == pytest.approx(16.67, abs=0.01)
    assert rig["OK"] is True and duc["OK"] is True
    assert des.verifica_piso_carga_concentrada(0.012, 5.0, "rigido")["OK"] is False


def test_acabamento_de_piso_desconhecido_nao_tem_default():
    with pytest.raises(des.EntradaDesempenho):
        des.verifica_piso_carga_concentrada(0.005, 5.0, "qualquer")


def test_fachada_15575_4_dh_e_dhr():
    est = des.verifica_fachada(0.005, 2.9, "estrutural", d_hr_m=0.001)
    assert est["limite_dh_mm"] == pytest.approx(5.8)      # h/500
    assert est["limite_dhr_mm"] == pytest.approx(1.16)    # h/2500
    ved = des.verifica_fachada(0.005, 2.9, "vedacao", d_hr_m=0.001)
    assert ved["limite_dh_mm"] == pytest.approx(8.29, abs=0.01)   # h/350
    assert ved["limite_dhr_mm"] == pytest.approx(1.657, abs=0.01)  # h/1750


def test_nota_b_dobra_so_o_dh_e_so_em_parede_leve_de_vedacao():
    leve = des.verifica_fachada(0.005, 2.9, "vedacao", d_hr_m=0.001,
                                G_kgf_m2=50.0)
    normal = des.verifica_fachada(0.005, 2.9, "vedacao", d_hr_m=0.001)
    assert leve["parede_leve"] is True
    assert leve["limite_dh_mm"] == pytest.approx(2 * normal["limite_dh_mm"],
                                                 abs=0.02)
    # o residual NAO dobra
    assert leve["limite_dhr_mm"] == pytest.approx(normal["limite_dhr_mm"])
    # e a nota b nao vale para fachada com funcao ESTRUTURAL
    est = des.verifica_fachada(0.005, 2.9, "estrutural", d_hr_m=0.001,
                               G_kgf_m2=50.0)
    assert est["parede_leve"] is False


def test_fachada_sem_residual_declarado_nao_atende():
    """d_hr vem de ensaio. Sem ele a fachada nao esta verificada, e verificar so
    metade da Tabela 1 e apresentar como atendida e o bug de sempre."""
    r = des.verifica_fachada(0.001, 2.9, "vedacao")
    assert r["ok_dh"] is True
    assert r["OK"] is False
    assert "residual" in r["aviso"]


# ---------------------------------------------------------------------------
# 4. O GATE
# ---------------------------------------------------------------------------
def test_gate_nao_aplicavel_a_edificacao_nao_habitacional():
    r = des.verifica({"habitacional": False})
    assert r["aplicavel"] is False and r["OK"] is True


def test_gate_do_qual_nada_foi_verificado_nao_atende():
    """Passar por vacuidade e' a forma mais barata de um gate mentir."""
    r = des.verifica({"habitacional": True})
    assert r["nada_verificado"] is True
    assert r["OK"] is False
    assert set(r["nao_verificados"]) == {"topo", "fissura", "flechas",
                                         "piso_carga_concentrada", "fachada"}


def test_gate_separa_reprovado_de_nao_declarado():
    r = des.verifica({"habitacional": True,
                      "fissura": {"wk_mm": 0.2},
                      "topo": {"u_m": 0.010, "H_total_m": 30.0}})
    assert r["OK"] is True                # nada excedeu limite
    assert r["completo"] is False         # mas falta verificar
    assert "fachada" in r["nao_verificados"]

    ruim = des.verifica({"habitacional": True, "fissura": {"wk_mm": 0.9}})
    assert ruim["OK"] is False and ruim["reprovados"] == ["fissura"]


def test_relatorio_publica_o_que_nao_foi_verificado():
    txt = des.relatorio_pt(des.verifica({"habitacional": True,
                                         "fissura": {"wk_mm": 0.2}}))
    assert "NAO VERIFICADOS" in txt
    assert "fachada" in txt
