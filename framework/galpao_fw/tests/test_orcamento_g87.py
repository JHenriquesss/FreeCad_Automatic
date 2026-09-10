# ============================================================================
# test_orcamento_g87.py - G87: ORCAMENTO, OS SISTEMAS QUE NUNCA ENTRARAM NA TABELA.
#
# A guarda do G14 nomeava insumo que ESTA na tabela e ficou sem quantidade
# (fechamento_lateral); os sistemas que NUNCA entraram na tabela (alvenaria,
# revestimento, esquadria, impermeabilizacao, elevador, incendio) passavam em
# silencio — R$ 790 mil / 1134 m2 ~= R$ 700/m2 com cara de obra (CUB 2500-3000).
# A regra: quantificar a partir do MODELO, nunca do preco; insumo sem preco
# sai nomeado, nao chutado. A guarda distingue tres estados — "a obra nao
# tem" (nao_aplicaveis), "ninguem quantificou" (sem_quantidade / fora_tabela
# sem quantidade) e "quantificado sem preco" (sem_preco / fora_tabela com
# quantidade) — e o parcial nunca se diz fechado.
#
# Convencoes do repo exercidas aqui:
#  1. baseline nos dois sentidos (cada guarda tem o caso bom e o injetado);
#  2. vermelho por injecao em tmp_path, nunca mutando a arvore viva;
#  5. fonte independente (a area e' refeita a mao a partir dos vaos, nao lendo
#     o numero que a derivacao publicou).
# ============================================================================
"""Guarda G87 do orcamento: tres estados + quantificacao pelo modelo."""

import copy
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import gestao_casa as gc
import gestao_edificio as ge
import orcamento as orc


# --- ajuda: resultado minimo do edificio com parede + incendio --------------

def _resultado_edificio_minimo():
    """Estrutura retangular 2x1 vaos com parede declarada + incendio com totais.

    O suficiente para a derivacao medir fachada, cobertura e sistemas sem
    precisar rodar o adaptador inteiro.
    """
    pav = {"area_m2": 120.0, "b_viga": 0.20, "h_viga": 0.50,
           "vaos_x": [6.0, 6.0], "vaos_y": [8.0],
           "vigas_x": [{"vaos": [6.0, 6.0]}], "vigas_y": [{"vaos": [8.0]}],
           "g_parede_kN_m": 5.0}
    pilares = {"P1": {"lances": [{"b": 0.30, "h": 0.30, "pe_direito": 3.0,
                                  "h_viga": 0.50, "As_cm2": 8.0}]}}
    return {
        "estrutura": {
            "pavimento": pav, "pilares": pilares, "n_pavimentos": 2,
            "h_laje_adotada": 0.12, "h_laje_declarada": 0.10,
            "laje": {},
            "vigas_verificacao": {"por_linha": []},
            "fundacao": {"por_pilar": {}},
            "escada": None,
        },
        "instalacoes": {
            "eletrico": None, "hidraulica": None,
            "incendio": {"sistemas": {
                "por_pavimento": {"hidrantes": 2, "blocos_autonomos": 8,
                                  "placas": 6, "detectores": 4},
                "totais_edificio": {"n_pavimentos": 2,
                                    "hidrantes": 4, "blocos_autonomos": 16,
                                    "placas": 12, "detectores": 8,
                                    "acionadores": 4,
                                    "reserva_incendio_m3": 9.6}}},
        },
    }


# --- 1. a guarda distingue os tres estados -----------------------------------

def test_tres_estados_distintos_no_mesmo_orcamento():
    """Obra-nao-tem x ninguem-quantificou x quantificado-sem-preco."""
    precos = dict(orc.preco_ref())
    # codigo quantificado que a tabela nao conhece -> sem_preco
    res = orc.compor_orcamento(
        {"concreto_estrut": 10.0, "codigo_inexistente": 7.0},
        precos, 25.0,
        aplicaveis=["concreto_estrut", "forma", "codigo_inexistente"],
        fora_da_tabela=[
            {"codigo": "revestimento_fachada", "descricao": "Revestimento",
             "unidade": "m2", "quantidade": 100.0, "motivo": ""},
            {"codigo": "esquadrias", "descricao": "Esquadrias",
             "unidade": "un", "quantidade": None,
             "motivo": "arquitetura nao modelada"},
        ])
    # 1. a obra nao tem: na tabela mas fora do escopo
    assert "aco_estrutural" not in res["sem_quantidade"]
    # 2. ninguem quantificou (dentro da tabela)
    assert "forma" in res["sem_quantidade"]
    # 3. quantificado sem preco (dentro da tabela)
    assert "codigo_inexistente" in res["sem_preco"]
    # fora da tabela, os dois sub-estados
    por_codigo = {item["codigo"]: item for item in res["fora_tabela"]}
    assert por_codigo["revestimento_fachada"]["estado"] == "quantificado_sem_preco"
    assert por_codigo["revestimento_fachada"]["quantidade"] == 100.0
    assert por_codigo["esquadrias"]["estado"] == "sem_quantitativo"
    assert "modelada" in por_codigo["esquadrias"]["motivo"]
    # e o parcial nao se diz fechado
    estado = orc.estado_orcamento(res)
    assert estado["fechado"] is False
    assert res["orcamento_fechado"] is False
    assert any("forma" in motivo for motivo in estado["motivos"])
    assert any("codigo_inexistente" in motivo for motivo in estado["motivos"])
    assert any("revestimento_fachada" in motivo for motivo in estado["motivos"])
    assert any("esquadrias" in motivo for motivo in estado["motivos"])


def test_orcamento_fechado_exige_tabela_e_fora_da_tabela():
    """O caso bom: tudo quantificado com preco e nada fora da tabela."""
    res = orc.compor_orcamento(
        {"concreto_estrut": 10.0, "forma": 50.0}, None, 25.0,
        aplicaveis=["concreto_estrut", "forma"], fora_da_tabela=[])
    assert res["sem_quantidade"] == []
    assert res["sem_preco"] == []
    assert res["fora_tabela"] == []
    assert orc.estado_orcamento(res)["fechado"] is True
    assert res["orcamento_fechado"] is True
    texto = orc.relatorio_pt(res)
    assert "ORCAMENTO PARCIAL" not in texto


def test_tabela_fechada_com_fora_da_tabela_pendente_continua_parcial():
    """O defeito G87: cobertura 100% com sistema inteiro fora do preco.

    Antes do G87 a cobertura contava so a tabela interna, entao este caso
    saia com cara de orcamento fechado. A guarda nova acusa.
    """
    res = orc.compor_orcamento(
        {"concreto_estrut": 10.0, "forma": 50.0}, None, 25.0,
        aplicaveis=["concreto_estrut", "forma"],
        fora_da_tabela=[{"codigo": "elevador", "descricao": "Elevador",
                          "unidade": "un", "quantidade": None,
                          "motivo": "nenhum modulo dimensiona"}])
    assert res["cobertura_pct"] == 100.0  # a tabela interna fechou...
    assert res["orcamento_fechado"] is False  # ...mas a obra nao esta coberta
    texto = orc.relatorio_pt(res)
    assert "ORCAMENTO PARCIAL" in texto
    assert "elevador" in texto


# --- 2. quantificacao pelo modelo (edificio) ----------------------------------

def test_parede_e_revestimento_saem_da_mesma_geometria_do_fechamento():
    """Area refeita A MAO (fonte independente): perimetro x altura livre."""
    resultado = _resultado_edificio_minimo()
    dados = ge.derivacao(resultado)
    # perimetro = 2*(12+8) = 40 m; altura livre = 3.0-0.5 = 2.5 m; 2 pav
    esperada = 40.0 * 2.5 * 2
    assert dados["quantitativos"]["fechamento_lateral"] == pytest.approx(
        esperada, rel=1e-6)
    fora = {item["codigo"]: item for item in dados["fora_da_tabela"]}
    assert fora["alvenaria_fachada"]["quantidade"] == pytest.approx(
        esperada, rel=1e-6)
    # o estado (quantificado sem preco) e' dado pelo compor_orcamento
    composto = orc.compor_orcamento(
        dados["quantitativos"], dict(ge.PRECOS_EDIFICIO), 25.0,
        aplicaveis=dados["aplicaveis"], fora_da_tabela=dados["fora_da_tabela"])
    estados = {item["codigo"]: item for item in composto["fora_tabela"]}
    assert estados["alvenaria_fachada"]["estado"] == "quantificado_sem_preco"
    # revestimento: as duas faces, convencao declarada
    assert fora["revestimento_fachada"]["quantidade"] == pytest.approx(
        2.0 * esperada, rel=1e-6)
    # impermeabilizacao: a projecao de um pavimento (cobertura)
    assert fora["impermeabilizacao_cobertura"]["quantidade"] == pytest.approx(
        120.0, rel=1e-6)


def test_incendio_quantificado_pelos_totais_dimensionados():
    """drawing-vs-data: o que o desenho conta, o orcamento quantifica."""
    resultado = _resultado_edificio_minimo()
    dados = ge.derivacao(resultado)
    fora = {item["codigo"]: item for item in dados["fora_da_tabela"]}
    totais = resultado["instalacoes"]["incendio"]["sistemas"]["totais_edificio"]
    assert fora["hidrantes"]["quantidade"] == totais["hidrantes"] == 4
    assert fora["blocos_autonomos"]["quantidade"] == totais["blocos_autonomos"]
    assert fora["placas"]["quantidade"] == totais["placas"]
    assert fora["detectores"]["quantidade"] == totais["detectores"]
    assert fora["reserva_incendio_m3"]["quantidade"] == pytest.approx(9.6)
    composto = orc.compor_orcamento(
        dados["quantitativos"], dict(ge.PRECOS_EDIFICIO), 25.0,
        aplicaveis=dados["aplicaveis"], fora_da_tabela=dados["fora_da_tabela"])
    estados = {item["codigo"]: item for item in composto["fora_tabela"]}
    for codigo in ("hidrantes", "blocos_autonomos", "placas", "detectores",
                   "reserva_incendio_m3"):
        assert estados[codigo]["estado"] == "quantificado_sem_preco", codigo


def test_sem_parede_nem_incendio_tudo_e_falta_nomeada():
    """Sem dado de modelo: sem quantitativo com motivo, nunca zero."""
    resultado = _resultado_edificio_minimo()
    resultado["estrutura"]["pavimento"]["g_parede_kN_m"] = 0.0
    resultado["instalacoes"] = {}
    dados = ge.derivacao(resultado)
    assert "fechamento_lateral" not in dados["quantitativos"]
    fora = {item["codigo"]: item for item in dados["fora_da_tabela"]}
    assert fora["alvenaria_fachada"]["quantidade"] is None
    assert "parede_sobre_vigas" in fora["alvenaria_fachada"]["motivo"]
    assert fora["revestimento_fachada"]["quantidade"] is None
    assert fora["hidrantes"]["quantidade"] is None
    assert "incendio" in fora["hidrantes"]["motivo"].lower()
    assert fora["esquadrias"]["quantidade"] is None
    assert fora["elevador"]["quantidade"] is None
    composto = orc.compor_orcamento(
        dados["quantitativos"], dict(ge.PRECOS_EDIFICIO), 25.0,
        aplicaveis=dados["aplicaveis"], fora_da_tabela=dados["fora_da_tabela"])
    estados = {item["codigo"]: item for item in composto["fora_tabela"]}
    assert all(estados[codigo]["estado"] == "sem_quantitativo"
               for codigo in ("alvenaria_fachada", "revestimento_fachada",
                              "hidrantes", "esquadrias", "elevador"))


def test_vermelho_por_injecao_na_quantidade_fora_da_tabela():
    """A guarda acusa quando a quantidade do modelo e' adulterada."""
    resultado = _resultado_edificio_minimo()
    dados = ge.derivacao(resultado)
    fora = {item["codigo"]: item for item in dados["fora_da_tabela"]}
    base = fora["hidrantes"]["quantidade"]
    adulterado = copy.deepcopy(resultado)
    adulterado["instalacoes"]["incendio"]["sistemas"]["totais_edificio"][
        "hidrantes"] = base + 5
    dados2 = ge.derivacao(adulterado)
    fora2 = {item["codigo"]: item for item in dados2["fora_da_tabela"]}
    assert fora2["hidrantes"]["quantidade"] == base + 5
    assert fora2["hidrantes"]["quantidade"] != base


# --- 3. o manifesto carrega a guarda (tmp_path, sem mutar a arvore) -----------

def test_manifesto_publica_fora_da_tabela_e_nao_se_diz_fechado(tmp_path):
    """orcamento_no_manifesto em diretorio temporario (convencao 2)."""
    import project_loop  # primeiro: registra os adaptadores (evita import circular)
    import entregaveis_projeto as ep

    manifest = {"deliverables": {}, "artifacts": []}
    dados = ge.derivacao(_resultado_edificio_minimo())
    ep.orcamento_no_manifesto(
        manifest, str(tmp_path), {"raw_spec": {}},
        dados["quantitativos"], aplicaveis=dados["aplicaveis"],
        precos_extra=ge.PRECOS_EDIFICIO, notas=dados["a_confirmar"],
        fora_da_tabela=dados["fora_da_tabela"])
    orcado = manifest["deliverables"]["orcamento"]
    assert orcado["status"] == "generated"
    assert orcado["orcamento_fechado"] is False
    codigos = {item["codigo"] for item in orcado["fora_tabela"]}
    assert {"revestimento_fachada", "hidrantes", "esquadrias",
            "elevador"} <= codigos
    avisos = " ".join(orcado["a_confirmar"])
    assert "QUANTIFICADO SEM PRECO" in avisos
    assert "SEM QUANTITATIVO" in avisos
    texto = (tmp_path / "orcamento" / "relatorio.txt").read_text(
        encoding="utf-8")
    assert "ORCAMENTO PARCIAL" in texto
    assert "QUANTIFICADO SEM PRECO" in texto


def test_casa_tambem_quantifica_parede_e_cobertura_pelo_modelo():
    """A casa mede a sua parede (fechamento ou portante) e a projecao."""
    resultado = {"estrutura": None,
                 "eletrico": {"circuits": {"points": [{"kind": "lighting"}]}},
                 "hidraulica": {}, "arquitetura": {}}
    dados = gc.derivacao(
        resultado,
        {"aparelhos_agua": {"pia": 1}, "aparelhos_esgoto": {"bacia": 1},
         "cobertura": {"area_m2": 80.0}})
    fora = {item["codigo"]: item for item in dados["fora_da_tabela"]}
    # sem estrutura nao ha parede nem projecao: faltas nomeadas
    assert fora["alvenaria_vedacao"]["quantidade"] is None
    assert fora["revestimento_casa"]["quantidade"] is None
    assert fora["impermeabilizacao_casa"]["quantidade"] is None
    assert fora["esquadrias"]["quantidade"] is None
    assert "not_declared" in fora["esquadrias"]["motivo"]
