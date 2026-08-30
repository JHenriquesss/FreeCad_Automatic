"""Testes do orquestrador do edificio multipavimento (G3).

Trunk do G3: um `rodar(spec)` tem de encadear pavimento-tipo -> descida de cargas
-> pilares continuos -> laje -> vigas -> escada -> planta, e consolidar os gates.
Os testes verificam o ENCADEAMENTO (o que cada etapa entrega para a seguinte) e a
politica de adocao de secao, nao os calculos - esses ja tem os seus proprios
arquivos.
"""

import os
import xml.etree.ElementTree as ET

import pytest

import edificio_multipavimento as em


def _spec(n_tipo=8, uso="residencial_dormitorio", **kw):
    base = {
        "geometria": {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5],
                      "pe_direito": 2.90},
        "pavimentos": ([{"nome": "Cobertura", "uso": "cobertura_manutencao"}]
                       + [{"nome": "Tipo %d" % i, "uso": uso}
                          for i in range(n_tipo, 0, -1)]),
        "laje": {"h": 0.10}, "viga": {"b": 0.20, "h": 0.50},
        "materiais": {"fck": 30e3, "fyk": 500e3},
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# trunk: a cadeia inteira
# ---------------------------------------------------------------------------
def test_edificio_residencial_tipico_atende():
    r = em.rodar(_spec())
    assert r["ATENDE"] is True, r["reprovados"]
    for k in ("fechamento_carga", "reducao_6120", "pilares", "laje", "vigas"):
        assert r["gates"][k]["OK"], k


def test_todas_as_etapas_produzem_resultado():
    r = em.rodar(_spec())
    assert r["pavimento"]["n_pilares"] == 12
    assert r["descida"]["n_pavimentos"] == 9
    assert len(r["pilares"]) == 12
    assert len(r["vigas"]) == 7            # (ny+1) + (nx+1) = 3 + 4
    assert r["laje"] is not None


def test_carga_fecha_no_gate():
    r = em.rodar(_spec())
    g = r["gates"]["fechamento_carga"]
    assert g["OK"] and g["erro_rel"] < 1e-3


def test_registro_da_reducao_sai_no_resultado():
    """Exigencia normativa de 6.12, nao conforto de depuracao."""
    r = em.rodar(_spec())
    assert "6.12" in r["registro_6120"] and "Tabela 19" in r["registro_6120"]


# ---------------------------------------------------------------------------
# politica de adocao da secao dos pilares
# ---------------------------------------------------------------------------
def test_secao_do_pilar_nunca_encolhe_ao_descer():
    r = em.rodar(_spec(n_tipo=10))
    for nome, p in r["pilares"].items():
        b_ant = h_ant = 0.0
        for lc in p["lances"]:
            assert lc["b"] >= b_ant - 1e-9 and lc["h"] >= h_ant - 1e-9, (nome, lc["nome"])
            b_ant, h_ant = lc["b"], lc["h"]


def test_pilar_interno_recebe_secao_maior_que_o_de_canto():
    r = em.rodar(_spec())
    interno = r["pilares"]["P22"]["lances"][-1]
    canto = r["pilares"]["P11"]["lances"][-1]
    assert interno["b"] * interno["h"] >= canto["b"] * canto["h"]
    assert r["pilares"]["P22"]["N_base_k"] > r["pilares"]["P11"]["N_base_k"]


def test_predio_mais_alto_pede_secao_maior():
    baixo = em.rodar(_spec(n_tipo=4))
    alto = em.rodar(_spec(n_tipo=14))
    sb = baixo["pilares"]["P22"]["lances"][-1]
    sa = alto["pilares"]["P22"]["lances"][-1]
    assert sa["b"] * sa["h"] > sb["b"] * sb["h"]


def test_acumulacao_da_selecao_bate_com_a_verificacao_final():
    """A selecao de secao e a verificacao final tem de usar o MESMO N. Se a selecao
    esquecesse o peso proprio dos lances acima, poderia adotar uma secao que a
    verificacao final reprova, e o pilar sairia reprovado sem que nenhuma secao maior
    chegasse a ser tentada."""
    r = em.rodar(_spec(n_tipo=10))
    for p in r["pilares"].values():
        assert p["OK"], p.get("reprovados")
        Ns = [lc["N_base_k"] for lc in p["lances"]]
        assert Ns == sorted(Ns)


def test_lista_de_secoes_esgotada_reprova_nomeando_o_lance():
    """SATURACAO SILENCIOSA: se nenhuma secao da lista serve, o lance tem de sair
    REPROVADO e NOMEADO - nunca a maior secao tentada dada por boa. Exercitado direto
    no seletor, com a lista truncada numa secao so (equivale a esgota-la)."""
    lances = [{"nome": "Pav %d" % i, "b": 0.25, "h": 0.50, "pe_direito": 2.90,
               "h_viga": 0.50, "N_aplicado": 900.0} for i in range(3, 0, -1)]
    escolhidos, erros = em.dimensiona_pilar_continuo(
        lances, fck=30e3, fyk=500e3, secoes=((0.19, 0.30),))
    assert erros, "com uma unica secao minima e 2700 kN, a lista tem de esgotar"
    assert any("nenhuma secao da lista atende" in e for e in erros)
    assert any("Pav 1" in e for e in erros)
    # e a secao devolvida e a maior tentada, para o relatorio - nao um resultado bom
    assert escolhidos[-1]["b"] == 0.19 and escolhidos[-1]["h"] == 0.30


def test_pilar_reprovado_e_nomeado_no_gate_e_os_demais_seguem():
    """Falha ISOLADA: o projetista ve o quadro inteiro numa passada."""
    r = em.rodar(_spec(n_tipo=8,
                       geometria={"vaos_x": [11.0, 11.0], "vaos_y": [11.0, 11.0],
                                  "pe_direito": 2.90}))
    assert len(r["pilares"]) == 9           # todos foram processados
    if not r["gates"]["pilares"]["OK"]:
        assert r["gates"]["pilares"]["reprovados"]
        assert "pilares" in r["reprovados"]


# ---------------------------------------------------------------------------
# uso e cargas propagam da NBR 6120
# ---------------------------------------------------------------------------
def test_uso_mais_pesado_carrega_mais_os_pilares():
    leve = em.rodar(_spec(uso="residencial_dormitorio"))     # 1,5 kN/m2
    pesado = em.rodar(_spec(uso="escritorio_sala_uso_geral"))  # 2,5 kN/m2
    assert pesado["N_base_max_k"] > leve["N_base_max_k"]
    assert pesado["pavimento"]["q_kN_m2"] == 2.5


def test_uso_inexistente_propaga_o_erro_da_tabela10():
    with pytest.raises(KeyError, match="nao consta na Tabela 10"):
        em.rodar(_spec(uso="apartamento"))


def test_parede_sobre_vigas_carrega_o_contorno_e_nao_o_interno():
    """A parede de fachada fica sobre as vigas de CONTORNO, entao ela carrega os
    pilares de canto e de extremidade e NAO o pilar interno. Um teste que olhasse so
    o pilar mais carregado (que e o interno) nao veria diferenca nenhuma - e passaria
    igual se a parede fosse ignorada por completo."""
    sem = em.rodar(_spec())
    com = em.rodar(_spec(parede_sobre_vigas={
        "tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14.0}))
    # canto e extremidade sobem
    assert com["pilares"]["P11"]["N_base_k"] > sem["pilares"]["P11"]["N_base_k"]
    assert com["pilares"]["P12"]["N_base_k"] > sem["pilares"]["P12"]["N_base_k"]
    # o interno nao e tocado pela parede de contorno
    assert (com["descida"]["pilares"]["P22"]["N_base_k"]
            == pytest.approx(sem["descida"]["pilares"]["P22"]["N_base_k"], rel=1e-9))


def test_parede_pesada_sem_posicao_definida_reprova():
    """Tabela 11: acima de 3,0 kN/m e NAO PERMITIDO como carga distribuida."""
    with pytest.raises(ValueError, match="NAO PERMITIDO"):
        em.rodar(_spec(parede_sem_posicao_pp=3.5))


# ---------------------------------------------------------------------------
# escada e planta
# ---------------------------------------------------------------------------
def test_escada_entra_nos_gates_quando_pedida():
    r = em.rodar(_spec(escada={"desnivel": 1.45, "largura": 1.20,
                               "uso": "escada_residencial_comum",
                               "patamar": 1.20, "h_laje": 0.08}))
    assert "escada" in r["gates"]
    assert r["escada"] is not None and r["gates"]["escada"]["OK"]


def test_sem_escada_o_gate_nao_existe():
    r = em.rodar(_spec())
    assert "escada" not in r["gates"] and r["escada"] is None


def test_planta_de_formas_e_escrita_e_e_xml_valido(tmp_path):
    r = em.rodar(_spec(out_dir=str(tmp_path)))
    assert r["planta"] and os.path.exists(r["planta"])
    with open(r["planta"], encoding="utf-8") as f:
        root = ET.fromstring(f.read())
    assert root.tag.endswith("svg")


def test_sem_out_dir_nao_escreve_nada(tmp_path):
    r = em.rodar(_spec())
    assert r["planta"] is None
    assert not list(tmp_path.iterdir())


# ---------------------------------------------------------------------------
# relatorio
# ---------------------------------------------------------------------------
def test_relatorio_traz_o_quadro_e_as_limitacoes():
    txt = em.relatorio_pt(em.rodar(_spec()))
    assert "EDIFICIO MULTIPAVIMENTO" in txt
    assert "FECHAMENTO DE CARGA" in txt and "REDUCAO NBR 6120 6.12" in txt
    assert "P22" in txt
    assert "RESULTADO GLOBAL: ATENDE" in txt
    # a limitacao de fonte fica declarada no proprio relatorio
    assert "16868" in txt


def test_relatorio_nomeia_os_reprovados():
    r = em.rodar(_spec(n_tipo=8,
                       geometria={"vaos_x": [11.0, 11.0], "vaos_y": [11.0, 11.0],
                                  "pe_direito": 2.90}))
    txt = em.relatorio_pt(r)
    if not r["ATENDE"]:
        assert "REPROVA" in txt
    assert "EDIFICIO MULTIPAVIMENTO" in txt
