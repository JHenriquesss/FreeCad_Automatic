"""G11 no edificio multipavimento: o ELS de vibracao do Anexo L e o desempenho
da NBR 15575 encadeados em `edificio_multipavimento.rodar`.

Os calculos em si estao em tests/test_vibracao_piso.py e
tests/test_desempenho_nbr15575.py. Aqui se verifica o ENCADEAMENTO: que a cadeia
entrega para os dois gates o dado CERTO (armadura real, carga por tramo,
combinacao propria de cada norma) e nao um proximo que passaria calado.
"""

import pytest

import desempenho_nbr15575 as des
import edificio_multipavimento as em
import vibracao_piso as vib


def _spec(uso="residencial_dormitorio", **kw):
    base = {
        "geometria": {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5],
                      "pe_direito": 2.90},
        "pavimentos": ([{"nome": "Cobertura", "uso": "cobertura_manutencao"}]
                       + [{"nome": "Tipo %d" % i, "uso": uso}
                          for i in range(6, 0, -1)]),
        "laje": {"h": 0.10}, "viga": {"b": 0.20, "h": 0.50},
        "materiais": {"fck": 30e3, "fyk": 500e3},
    }
    base.update(kw)
    return base


@pytest.fixture(scope="module")
def rodado():
    return em.rodar(_spec(desempenho={"linha_flecha": "parede_rigida_sem_aberturas"}))


# ---------------------------------------------------------------------------
# os dois gates existem e sao conjuncao do ATENDE
# ---------------------------------------------------------------------------
def test_os_dois_gates_do_g11_entram_no_atende(rodado):
    assert "vibracao_piso" in rodado["gates"]
    assert "desempenho_15575" in rodado["gates"]
    assert rodado["ATENDE"] is True, rodado["reprovados"]


def test_vibracao_classifica_pelo_uso_do_pavimento_tipo(rodado):
    v = rodado["vibracao"]
    assert v["classe"] == "caminhada"
    assert v["d_lim_mm"] == 20.0
    assert v["psi_1"] == 0.4                 # Tabela 2, linha 1 (residencial)


def test_o_deslocamento_soma_laje_e_viga(rodado):
    """"deslocamento vertical TOTAL do piso": o painel flecha em relacao as
    vigas e as vigas em relacao aos pilares. Ficar so com a laje ignoraria a
    parcela dominante num vao grande."""
    v = rodado["vibracao"]
    assert v["d_viga_mm"] > 0 and v["d_laje_mm"] > 0
    assert v["d_total_mm"] == pytest.approx(v["d_laje_mm"] + v["d_viga_mm"],
                                            abs=0.02)


def test_a_viga_da_vibracao_leva_a_armadura_REAL_do_tramo(rodado):
    """Sem As a flecha sairia de secao BRUTA, que subestima assim que a viga
    fissura - e o modulo, com razao, recusaria dar o piso por atendido."""
    v = rodado["vibracao"]
    assert v["viga_critica"]["As_cm2"] > 0
    assert v["viga"]["secao"].startswith("Branson")
    assert v["avaliavel"] is True


def test_a_viga_critica_e_a_de_maior_carga_vezes_L4_e_nao_a_de_maior_vao():
    """Com uma parede pesada so nas linhas de contorno, a viga que mais flecha
    pode ser uma de vao MENOR. Escolher pelo vao daria a viga errada e o gate
    olharia para um piso que nao e' o critico."""
    r = em.rodar(_spec(parede_sobre_vigas={"tipo": "bloco_ceramico_furo_horizontal",
                                           "espessura_cm": 14.0}))
    pav = r["pavimento"]
    p1 = vib.psi_1("restrito")
    def sev(v, k):
        return (v["g_tramos"][k] + p1 * v["q_tramos"][k]) * v["vaos"][k] ** 4

    todas = [(sev(v, k), v["nome"], k)
             for v in list(pav["vigas_x"]) + list(pav["vigas_y"])
             for k in range(len(v["vaos"]))]
    pior = max(s for s, _n, _k in todas)
    escolhida = r["vibracao"]["viga_critica"]
    # a malha e simetrica, entao o maximo empata entre tramos espelhados: o que
    # o gate NAO pode e' escolher um tramo que nao esta empatado no topo.
    assert any(nome == escolhida["linha"] and k + 1 == escolhida["tramo"]
               and s == pytest.approx(pior) for s, nome, k in todas)
    # e o vao escolhido nao e' necessariamente o maior da malha isoladamente:
    # o criterio e carga x L^4, nao L
    assert escolhida["L"] == pytest.approx(5.0)


def test_pavimento_tipo_publica_as_cargas_por_tramo():
    """A analise devolve ESFORCOS; sem g e q por tramo nao ha como montar
    nenhuma combinacao de servico por fora dela."""
    pav = em.rodar(_spec())["pavimento"]
    for v in list(pav["vigas_x"]) + list(pav["vigas_y"]):
        assert len(v["g_tramos"]) == len(v["vaos"])
        assert len(v["q_tramos"]) == len(v["vaos"])
        assert v["b"] > 0 and v["h"] > 0


# ---------------------------------------------------------------------------
# NBR 15575
# ---------------------------------------------------------------------------
def test_habitacional_e_deduzido_dos_usos_da_tabela_10(rodado):
    assert rodado["desempenho"]["aplicavel"] is True


def test_edificio_comercial_nao_dispara_a_15575():
    """A 15575 e' exigivel para edificacao HABITACIONAL. Dizer 'nao aplicavel'
    e' diferente de dizer que passou, e o gate diz qual dos dois."""
    r = em.rodar(_spec(uso="escritorio_sala_uso_geral"))
    assert r["desempenho"]["aplicavel"] is False
    assert r["gates"]["desempenho_15575"]["aplicavel"] is False
    # o Anexo L, esse, continua valendo - escritorio e' caminhada regular
    assert r["vibracao"]["classe"] == "caminhada"
    assert r["vibracao"]["psi_1"] == 0.6      # linha 2 da Tabela 2 (nota c)


def test_habitacional_pode_ser_declarado_no_spec():
    r = em.rodar(_spec(uso="escritorio_sala_uso_geral", habitacional=True))
    assert r["desempenho"]["aplicavel"] is True


def test_a_flecha_da_tabela_2_usa_a_combinacao_da_15575_e_nao_a_da_6118(rodado):
    """A Tabela 2 tem combinacao PROPRIA (Sgk + 0,7 Sqk) e convencao PROPRIA de
    flecha final (rigidez pela metade). A laje ja calculou a flecha da
    quase-permanente com fluencia para a Tabela 13.3 - comparar aquela com o
    limite desta seria cruzar combinacao de uma norma com limite de outra."""
    flechas = rodado["desempenho"]["verificacoes"]["flechas"]
    imediata = next(f for f in flechas if "imediata" in f["nome"])
    final = next(f for f in flechas if "final" in f["nome"])
    assert final["flecha_mm"] == pytest.approx(2.0 * imediata["flecha_mm"], abs=0.05)
    assert final["expressao"] == "L/340"
    assert imediata["expressao"] == "L/600"
    # e nao e' a flecha que a laje calculou para a 6118
    assert final["flecha_mm"] != pytest.approx(
        rodado["laje"]["flecha"]["f_total"] * 1000, abs=0.05)


def test_o_que_a_15575_exige_e_ninguem_calculou_fica_publicado(rodado):
    """A parte 3 (1 kN concentrado) e a parte 4 (fachada) se verificam por
    ENSAIO. Nao aparecem como reprovados - aparecem como nao verificados."""
    g = rodado["gates"]["desempenho_15575"]
    assert g["OK"] is True
    assert g["completo"] is False
    assert "piso_carga_concentrada" in g["nao_verificados"]
    assert "fachada" in g["nao_verificados"]
    assert g["reprovados"] == []


def test_com_vento_declarado_o_topo_entra_na_15575():
    r = em.rodar(_spec(vento={"v0": 40.0, "cat": "IV", "classe": "B",
                             "ca": {"x": 1.2, "y": 1.3}}))
    ver = r["desempenho"]["verificacoes"]
    assert "topo" in ver
    assert "topo" not in r["desempenho"]["nao_verificados"]
    # o limite adotado e o MENOR entre a 15575 e a norma de projeto
    assert ver["topo"]["limite_adotado_mm"] <= ver["topo"]["limite_15575_mm"] + 1e-9
    assert ver["topo"]["H_total_m"] == pytest.approx(7 * 2.90)


def test_a_fissura_da_laje_alimenta_o_gate_da_15575(rodado):
    f = rodado["desempenho"]["verificacoes"]["fissura"]
    assert f["limite_15575_mm"] == des.WK_MAX_MM
    assert f["wk_mm"] == pytest.approx(rodado["laje"]["fissuracao"]["wk_mm"])


def test_relatorio_do_edificio_nomeia_os_dois_gates(rodado):
    txt = em.relatorio_pt(rodado)
    assert "VIBRACAO DE PISO" in txt
    assert "DESEMPENHO NBR 15575" in txt
    assert "NAO verificados" in txt
    assert "ENSAIO" in txt
