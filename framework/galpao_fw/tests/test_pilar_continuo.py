"""Testes do pilar continuo de edificio multipavimento (NBR 6118:2014).

O dimensionamento de cada lance vem de `pilar_concreto`, ja aferido contra Bastos;
o que se verifica aqui e o que e NOVO: o comprimento equivalente de 15.6 por
direcao, a descida da forca normal, a mudanca de secao e os gates de continuidade e
de faixa de validade do metodo.
"""

import pytest

import pilar_concreto as pc
import pilar_continuo as pcn


def _lances(n=8, b=0.25, h=0.60, N=180.0, pe=2.90, h_viga=0.50):
    return [{"nome": "Pav %d" % (n - i), "b": b, "h": h, "pe_direito": pe,
             "h_viga": h_viga, "N_aplicado": N} for i in range(n)]


def _cfg(**kw):
    base = {"lances": _lances(), "fck": 30e3, "fyk": 500e3}
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# 15.6 - comprimento equivalente
# ---------------------------------------------------------------------------
def test_le_e_o_menor_entre_l0_mais_h_e_l():
    """le = min(l0 + h ; l), com l0 = l - h_viga."""
    le, l0 = pcn.comprimento_equivalente(l_eixos=3.00, h_viga=0.60, h_secao=0.20)
    assert l0 == pytest.approx(2.40)
    assert le == pytest.approx(2.60)          # 2,40 + 0,20 < 3,00


def test_le_e_cortado_por_l_quando_a_viga_e_baixa():
    """Com viga baixa, l0 + h supera l e o minimo corta em l. Isso e a norma - nao um
    clamp arbitrario: le nunca passa da distancia entre eixos."""
    le, l0 = pcn.comprimento_equivalente(l_eixos=3.00, h_viga=0.30, h_secao=0.60)
    assert l0 == pytest.approx(2.70)
    assert le == pytest.approx(3.00)          # min(3,30 ; 3,00)


def test_le_difere_entre_as_duas_direcoes_da_mesma_barra():
    """h entra por DIRECAO: le_x usa hx e le_y usa hy. Sao dois le distintos na mesma
    barra - usar um so subestima a esbeltez da direcao mais fraca."""
    r = pcn.dimensiona(_cfg(lances=_lances(n=1, b=0.20, h=0.60)))
    lc = r["lances"][0]
    assert lc["le_x"] != lc["le_y"]
    assert lc["le_x"] > lc["le_y"]            # hx = 0,60 > hy = 0,20


def test_geometria_invalida_da_viga_levanta():
    with pytest.raises(ValueError):
        pcn.comprimento_equivalente(3.0, h_viga=3.0, h_secao=0.2)
    with pytest.raises(ValueError):
        pcn.comprimento_equivalente(0.0, h_viga=0.5, h_secao=0.2)


# ---------------------------------------------------------------------------
# descida da forca normal
# ---------------------------------------------------------------------------
def test_forca_normal_acumula_de_cima_para_baixo():
    r = pcn.dimensiona(_cfg(peso_proprio=False))
    N = [lc["N_base_k"] for lc in r["lances"]]
    assert N == sorted(N)                              # monotona crescente
    assert N[0] == pytest.approx(180.0)
    assert N[-1] == pytest.approx(8 * 180.0)
    assert r["N_base_k"] == pytest.approx(8 * 180.0)


def test_peso_proprio_do_lance_entra_na_descida():
    com = pcn.dimensiona(_cfg(peso_proprio=True))
    sem = pcn.dimensiona(_cfg(peso_proprio=False))
    n = 8
    peso_total = n * 25.0 * 0.25 * 0.60 * 2.90
    assert com["N_base_k"] - sem["N_base_k"] == pytest.approx(peso_total, rel=1e-6)


def test_armadura_cresce_para_a_base():
    r = pcn.dimensiona(_cfg())
    As = [lc["As_cm2"] for lc in r["lances"]]
    assert As[-1] >= As[0]


def test_um_unico_lance_reproduz_o_pilar_isolado():
    """Um lance so tem de dar exatamente o que `pilar_concreto` daria com o mesmo le -
    a continuidade nao pode introduzir diferenca escondida."""
    lc = {"nome": "unico", "b": 0.25, "h": 0.60, "pe_direito": 2.90, "h_viga": 0.50,
          "N_aplicado": 500.0}
    r = pcn.dimensiona({"lances": [lc], "fck": 30e3, "fyk": 500e3,
                        "peso_proprio": False})
    direto = pc.dimensiona_pilar({"b": 0.25, "h": 0.60, "Nk": 500.0,
                                  "le_x": r["lances"][0]["le_x"],
                                  "le_y": r["lances"][0]["le_y"],
                                  "fck": 30e3, "fyk": 500e3})
    assert r["lances"][0]["As_cm2"] == pytest.approx(direto["As_cm2"])


def test_pilar_sem_lances_levanta():
    with pytest.raises(ValueError, match="pelo menos um lance"):
        pcn.dimensiona({"lances": [], "fck": 30e3, "fyk": 500e3})


# ---------------------------------------------------------------------------
# mudanca de secao
# ---------------------------------------------------------------------------
def test_secao_pode_aumentar_ao_descer():
    lances = (_lances(n=4, b=0.20, h=0.50) + _lances(n=4, b=0.30, h=0.70))
    for i, lc in enumerate(lances):
        lc["nome"] = "Pav %d" % (8 - i)
    r = pcn.dimensiona(_cfg(lances=lances))
    assert not r["erros"]
    assert r["lances"][3]["b"] == 0.20 and r["lances"][4]["b"] == 0.30


def test_secao_que_encolhe_ao_descer_reprova():
    """Gate de continuidade: nenhum gate de flexo-compressao acusaria isso COMO TAL -
    o lance de baixo so ganharia armadura, ou reprovaria por taxa, sem dizer que o
    lancamento e que esta errado."""
    lances = (_lances(n=4, b=0.30, h=0.70) + _lances(n=4, b=0.20, h=0.50))
    for i, lc in enumerate(lances):
        lc["nome"] = "Pav %d" % (8 - i)
    r = pcn.dimensiona(_cfg(lances=lances))
    assert r["OK"] is False
    assert any("nao pode diminuir ao descer" in e for e in r["erros"])


def test_transicao_brusca_gera_aviso_sem_reprovar():
    lances = (_lances(n=2, b=0.20, h=0.50) + _lances(n=2, b=0.20, h=0.90))
    for i, lc in enumerate(lances):
        lc["nome"] = "Pav %d" % (4 - i)
    r = pcn.dimensiona(_cfg(lances=lances))
    assert not r["erros"]
    assert any("transicao brusca" in a for a in r["avisos"])


# ---------------------------------------------------------------------------
# faixa de validade do metodo (15.8.1 / 15.8.3.3.2 / 15.8.4)
# ---------------------------------------------------------------------------
def test_pilar_continuo_tipico_fica_dentro_da_faixa():
    """O ganho de ser continuo: le ~ H em vez de 2H do balanco, e a esbeltez cai para
    dentro da faixa em que o metodo do pilar-padrao pode ser empregado."""
    r = pcn.dimensiona(_cfg())
    for lc in r["lances"]:
        assert max(lc["lambda_x"], lc["lambda_y"]) <= 90.0
        assert lc["esbeltez_valida"] is True
    assert r["OK"] is True


def test_lance_de_pe_direito_duplo_com_secao_fina_reprova_por_esbeltez():
    """SATURACAO SILENCIOSA: o pilotis / pe-direito de loja tem lance muito mais alto.
    Com secao fina a esbeltez estoura os 90 de 15.8.3.3.2 e o metodo aplicado deixa de
    valer - mas nada disso aparece como razao solicitante/resistente. Sem gate proprio
    o modulo devolveria um As perfeitamente calculado e OK=True."""
    lances = _lances(n=2, b=0.20, h=0.50)
    lances.append({"nome": "Pilotis", "b": 0.20, "h": 0.50, "pe_direito": 6.00,
                   "h_viga": 0.50, "N_aplicado": 200.0})
    r = pcn.dimensiona(_cfg(lances=lances))
    pil = r["lances"][-1]
    assert pil["lambda_y"] > 90.0
    assert pil["esbeltez_valida"] is False
    assert any("15.8.3.3.2" in a for a in pil["avisos_esbeltez"])
    assert r["OK"] is False
    assert "Pilotis" in r["reprovados"]


def test_fluencia_obrigatoria_e_declarada_acima_de_90():
    lances = [{"nome": "Alto", "b": 0.20, "h": 0.50, "pe_direito": 6.00,
               "h_viga": 0.50, "N_aplicado": 200.0}]
    r = pcn.dimensiona(_cfg(lances=lances))
    avisos = r["lances"][0]["avisos_esbeltez"]
    assert any("15.8.4" in a and "FLUENCIA" in a for a in avisos)


# ---------------------------------------------------------------------------
# integracao com a viga continua (14.6.6.1-c)
# ---------------------------------------------------------------------------
def test_momento_do_engastamento_parcial_da_viga_chega_ao_lance():
    """A parcela que 14.6.6.1-c manda para o tramo do pilar e o momento de 1a ordem do
    lance. Com ela, a armadura tem de subir em relacao ao pilar so comprimido."""
    import viga_continua as vc
    v = vc.analisa({
        "tramos": [{"L": 5.0, "b": 0.20, "h": 0.50} for _ in range(2)],
        "g": 25.0, "q": 8.0,
        "apoios_extremos": {0: {"r_vig": 1.0e-3, "r_inf": 1.2e-3, "r_sup": 1.2e-3}},
    })
    M_sup = v["momentos_no_pilar"][0]["M_sup"]
    assert M_sup > 0.0

    base = {"nome": "Extremidade", "b": 0.25, "h": 0.60, "pe_direito": 2.90,
            "h_viga": 0.50, "N_aplicado": 600.0}
    sem = pcn.dimensiona(_cfg(lances=[dict(base)]))
    com = pcn.dimensiona(_cfg(lances=[dict(base, M1d_x={"tipo": "biapoiado",
                                                        "Ma": 1.4 * M_sup})]))
    assert com["lances"][0]["As_cm2"] >= sem["lances"][0]["As_cm2"]


def test_relatorio_traz_a_descida_e_os_itens_normativos():
    r = pcn.dimensiona(_cfg())
    txt = pcn.relatorio(r)
    assert "PILAR CONTINUO" in txt and "15.6" in txt
    assert "Pav 8" in txt and "Pav 1" in txt
    assert "N_base" in txt or "N_base(kN)" in txt
    assert "ATENDE" in txt
