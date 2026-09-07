"""G57: SPDA + alimentacao de emergencia do predio + portao no pacote legal.

Guardas (vermelho por injecao):
  1. predio sem SPDA declarado -> o checklist PPCI/AVCB do pacote cita a
     ausencia (o portao que fecha o goal mesmo com os itens parciais);
  2. carga essencial do gerador e' menor que a total e DERIVADA (soma das
     parcelas declaradas), nao constante.
Extras: Ng nunca recebe default; recarga NBR 17019 segue not_available com o
motivo escrito (a norma ESTA no acervo - F056 - entao o motivo nunca e'
"fonte ausente").
"""
import copy
import json
import os
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import eletrica_edificio as ee
import gestao_edificio as ge
import pacote_legal as pl
import edificio_adapter as ea
from project_loop import normalize_spec

REPO = os.path.dirname(os.path.dirname(GALPAO))
SPEC_PERSISTIDO = os.path.join(REPO, "projects", "edificio-multipavimento",
                               "project-spec.json")


def _spec_base():
    return {
        "unidade": {"unidades_por_pavimento": 2, "carga_VA": 8000.0},
        "tensao": {"sistema": "trifasico", "V": 220.0},
    }


def _contexto():
    # envelope 14 x 9 m, H_total de predio alto (> 20 m -> descida 35 mm2)
    return {"pavimentos": [{"nome": "T1"}, {"nome": "T2"}],
            "C": 14.0, "L": 9.0, "H_total_m": 26.1, "pe_direito": 2.9}


# ===========================================================================
# PORTAO 1: sem SPDA declarado, o checklist cita a ausencia
# ===========================================================================
def test_sem_spda_o_checklist_cita_a_ausencia():
    """O buraco nao pode atravessar o pacote em silencio."""
    saida = ee.dimensiona(_spec_base(), _contexto())
    assert saida["escopo"]["spda_nbr5419"] == "not_available"
    assert saida["spda"] is None
    resultado = {"instalacoes": {"eletrico": {"escopo": saida["escopo"]}}}
    pendencias = ge._pendencias_aprovacao(resultado)
    assert any("SPDA" in p for p in pendencias), pendencias
    pac = pl.gerar_pacote(["eletrico"], memorial=None, pendencias=pendencias)
    citados = [s for s in pac["checklist_ppci_avcb"] if "PENDENTE" in s]
    assert any("SPDA" in s for s in citados), pac["checklist_ppci_avcb"]
    md = pl.markdown(pac)
    assert "SPDA" in md and "PENDENTE" in md


def test_sem_emergencia_o_checklist_cita_a_ausencia():
    saida = ee.dimensiona(_spec_base(), _contexto())
    assert saida["escopo"]["grupo_gerador_e_alimentacao_de_emergencia"] == "not_available"
    resultado = {"instalacoes": {"eletrico": {"escopo": saida["escopo"]}}}
    pendencias = ge._pendencias_aprovacao(resultado)
    assert any("emergencia" in p for p in pendencias), pendencias
    pac = pl.gerar_pacote(["eletrico"], memorial=None, pendencias=pendencias)
    assert any("PENDENTE" in s and "emergencia" in s
               for s in pac["checklist_ppci_avcb"])


def test_spda_sem_Cd_tambem_nao_avalia_risco():
    """Entorno (Cd, Tab.A.1) tambem e' dado de sitio: sem ele, sem Nd."""
    spec = _spec_base()
    spec["spda"] = {"NP": "III", "Ng": 5.0}
    saida = ee.dimensiona(spec, _contexto())
    assert saida["spda"]["Nd_ano"] is None
    aviso = [a for a in saida["avisos"]
             if a["code"] == "spda_sem_Ng_declarado"]
    assert len(aviso) == 1 and "Cd" in aviso[0]["detail"]


def test_com_spda_e_emergencia_o_checklist_limpa():
    """Declarados, os dois buracos somem do checklist (o portao abre)."""
    spec = _spec_base()
    spec["spda"] = {"NP": "III", "Ng": 5.0, "Cd": 1.0, "R1": 2e-5}
    spec["emergencia"] = {"elevador_VA": 8000.0, "bombas_incendio_VA": 3000.0,
                          "iluminacao_emergencia_VA": 1200.0}
    saida = ee.dimensiona(spec, _contexto())
    assert saida["escopo"]["spda_nbr5419"] == "implemented"
    assert saida["escopo"]["grupo_gerador_e_alimentacao_de_emergencia"] == "implemented"
    resultado = {"instalacoes": {"eletrico": saida}}
    assert ge._pendencias_aprovacao(resultado) == []
    pac = pl.gerar_pacote(["eletrico"], memorial=None, pendencias=[])
    assert not any("PENDENTE" in s for s in pac["checklist_ppci_avcb"])


def test_checklist_sem_pendencias_nao_muda():
    """Sem pendencias, a saida e' a de antes (compatibilidade com o galpao)."""
    antes = pl.checklist_ppci_avcb()
    assert not any("PENDENTE" in s for s in antes)
    assert any("AVCB" in s for s in antes)


# ===========================================================================
# PORTAO 2: carga essencial menor que a total e derivada, nao constante
# ===========================================================================
def test_carga_essencial_menor_que_a_total_e_derivada():
    spec = _spec_base()
    spec["emergencia"] = {"elevador_VA": 8000.0, "bombas_incendio_VA": 3000.0,
                          "iluminacao_emergencia_VA": 1200.0}
    saida = ee.dimensiona(spec, _contexto())
    em = saida["emergencia"]
    total = saida["entrada"]["carga_total_VA"]
    # derivada: e' a SOMA das parcelas, nao um numero redigitado
    assert em["carga_essencial_VA"] == 8000.0 + 3000.0 + 1200.0
    # menor que a total: a fonte sai pela essencial
    assert 0 < em["carga_essencial_VA"] < total
    assert saida["gates"]["carga_essencial"]["OK"] is True
    # nao constante: mudar uma parcela muda a essencial
    spec2 = copy.deepcopy(spec)
    spec2["emergencia"]["elevador_VA"] = 9500.0
    saida2 = ee.dimensiona(spec2, _contexto())
    assert saida2["emergencia"]["carga_essencial_VA"] == 9500.0 + 3000.0 + 1200.0
    assert saida2["emergencia"]["carga_essencial_VA"] != em["carga_essencial_VA"]


def test_emergencia_cobre_as_quatro_cargas_que_a_criam():
    """Elevador, pressurizacao, bombas e iluminacao: as chaves existem."""
    assert set(ee.PARCELAS_ESSENCIAIS) == {"elevador_VA", "pressurizacao_VA",
                                          "bombas_incendio_VA",
                                          "iluminacao_emergencia_VA"}
    spec = _spec_base()
    spec["emergencia"] = {"elevador_VA": 5000.0, "pressurizacao_VA": 4000.0,
                          "bombas_incendio_VA": 3000.0,
                          "iluminacao_emergencia_VA": 1000.0}
    saida = ee.dimensiona(spec, _contexto())
    assert (saida["emergencia"]["carga_essencial_VA"]
            == 5000.0 + 4000.0 + 3000.0 + 1000.0)


# ===========================================================================
# SPDA: reuso + Ng declarado, nunca default
# ===========================================================================
def _contexto_com_incendio():
    ctx = _contexto()
    ctx["incendio"] = {"tipo_escada_exigido": "prova_de_fumaca",
                       "blocos_por_pavimento": 6,
                       "blocos_total_edificio": 48,
                       "tem_hidrantes": True}
    return ctx


# ===========================================================================
# Essencial DERIVADA dos modulos: o conjunto vem do incendio, so a potencia
# e' declarada (nenhum modulo a calcula)
# ===========================================================================
def test_sem_bloco_o_aviso_nomeia_o_que_o_incendio_cria():
    """Nao e' motivo vazio: o aviso diz qual carga o incendio desta rodada cria."""
    saida = ee.dimensiona(_spec_base(), _contexto_com_incendio())
    aviso = [a for a in saida["avisos"]
             if a["code"] == "emergencia_nao_dimensionada"]
    assert len(aviso) == 1
    assert "prova de fumaca" in aviso[0]["detail"]
    assert "48 blocos" in aviso[0]["detail"]
    assert "hidrantes" in aviso[0]["detail"]


def test_parcela_faltante_que_o_incendio_exige_vira_aviso_nomeado():
    """Pressurizacao e bombas exigidas pelo incendio e ausentes: dito em voz alta."""
    spec = _spec_base()
    spec["emergencia"] = {"elevador_VA": 8000.0,
                          "iluminacao_emergencia_VA": 1200.0}
    saida = ee.dimensiona(spec, _contexto_com_incendio())
    codigos = {a["code"] for a in saida["avisos"]}
    assert "emergencia_pressurizacao_nao_declarada" in codigos
    assert "emergencia_bombas_nao_declaradas" in codigos
    # a essencial sai SEM elas - e continua menor que a total
    assert saida["emergencia"]["carga_essencial_VA"] == 9200.0
    assert saida["gates"]["carga_essencial"]["OK"] is True


def test_essencial_completa_nao_acusa_coerencia_e_traz_proveniencia():
    spec = _spec_base()
    spec["emergencia"] = {"elevador_VA": 8000.0, "pressurizacao_VA": 4000.0,
                          "bombas_incendio_VA": 3000.0,
                          "iluminacao_emergencia_VA": 1200.0}
    saida = ee.dimensiona(spec, _contexto_com_incendio())
    assert not [a for a in saida["avisos"] if a["code"].startswith("emergencia_")
                and a["code"] not in ("emergencia_nao_dimensionada",)]
    prov = saida["emergencia"]["proveniencia_parcelas"]
    assert "incendio" in prov["pressurizacao_VA"]
    assert "incendio" in prov["bombas_incendio_VA"]
    assert "10898" in prov["iluminacao_emergencia_VA"]
    # razao de sanidade: W por bloco implicito, sem juizo de valor
    assert saida["emergencia"]["w_por_bloco_implicito"] == 1200.0 / 48


def test_sem_incendio_no_contexto_nada_muda():
    """Sem o incendio na rodada, sem coerencia a cobrar (compatibilidade)."""
    spec = _spec_base()
    spec["emergencia"] = {"elevador_VA": 8000.0}
    saida = ee.dimensiona(spec, _contexto())
    assert not [a for a in saida["avisos"]
                if a["code"] in ("emergencia_pressurizacao_nao_declarada",
                                 "emergencia_bombas_nao_declaradas",
                                 "emergencia_iluminacao_nao_declarada")]


# ===========================================================================
# Fio adaptador: o resumo do incendio viaja no contexto ate a eletrica
# ===========================================================================
def _incendio_sintetico():
    return {
        "sistemas": {
            "iluminacao_emergencia": {"N_blocos_total": 6},
            "hidrantes": {"N_hidrantes": 2},
            "totais_edificio": {"blocos_autonomos": 48},
        },
        "gates": {"escada_tipo": {"tipo_exigido": "prova_de_fumaca"}},
    }


def _estrutura_sintetica():
    return {
        "geometria": {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5],
                      "pe_direito": 2.9},
        "pavimentos": [{"nome": "T1", "uso": "residencial_dormitorio"}],
    }


def test_resumo_do_incendio_viaja_no_contexto():
    """Sem recalculo: a eletrica le o que o incendio ja criou."""
    ctx = ea._contexto_predio(
        _estrutura_sintetica(), {"escada": None, "H_total_m": 26.1},
        {"incendio": _incendio_sintetico()})
    assert ctx["incendio"] == {"tipo_escada_exigido": "prova_de_fumaca",
                               "blocos_por_pavimento": 6,
                               "blocos_total_edificio": 48,
                               "tem_hidrantes": True}


def test_sem_incendio_o_resumo_e_none_e_nada_muda():
    ctx = ea._contexto_predio(_estrutura_sintetica(),
                              {"escada": None, "H_total_m": 26.1}, {})
    assert ctx["incendio"] is None
    assert ctx["populacao_por_pavimento"] is None


def test_spda_declarado_usa_envelope_e_tabela_do_galpao():
    spec = _spec_base()
    spec["spda"] = {"NP": "III", "Ng": 5.0, "Cd": 1.0, "R1": 2e-5}
    saida = ee.dimensiona(spec, _contexto())
    spda = saida["spda"]
    assert spda["NP"] == "III" and spda["n_descidas"] == 4  # 46 m / 15 m
    assert spda["Nd_ano"] is not None  # com Ng, o risco sai avaliado
    assert spda["secao_descida_mm2"] == 35  # H > 20 m
    assert spda["geometria"]["H_total_m"] == 26.1


def test_spda_sem_Ng_nao_inventa_risco():
    """Ng e' dado de sitio (regra G9): sem ele, Nd nao e' calculado."""
    spec = _spec_base()
    spec["spda"] = {"NP": "III", "Cd": 1.0}
    saida = ee.dimensiona(spec, _contexto())
    assert saida["spda"]["Nd_ano"] is None
    codigos = {a["code"] for a in saida["avisos"]}
    assert "spda_sem_Ng_declarado" in codigos


def test_spda_invalido_e_recusado():
    spec = _spec_base()
    spec["spda"] = {"NP": "VII"}
    try:
        ee.dimensiona(spec, _contexto())
    except ee.EntradaEletrica:
        pass
    else:
        raise AssertionError("NP inexistente tinha de ser recusado")


# ===========================================================================
# Recarga NBR 17019: motivo escrito, nunca "fonte ausente"
# ===========================================================================
def test_recarga_mantem_motivo_escrito_e_nao_fonte_ausente():
    """A norma ESTA no acervo (F056 catalogada): o motivo nao pode mentir."""
    saida = ee.dimensiona(_spec_base(), _contexto())
    assert saida["escopo"]["recarga_de_veiculos_nbr17019"] == "not_available"
    avisos = [a for a in saida["avisos"]
              if a["code"] == "recarga_veiculos_sem_projeto"]
    assert len(avisos) == 1
    detalhe = avisos[0]["detail"]
    assert "17019" in detalhe and "F056" in detalhe
    assert "ESTA no acervo" in detalhe
    assert "sem projeto dedicado" in detalhe


# ===========================================================================
# PONTA A PONTA: spec persistido -> adaptador -> pacote-legal.md (lento: uma
# rodada do predio por cenario, module-scoped)
# ===========================================================================
def _carrega_persistido():
    with open(SPEC_PERSISTIDO, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _pacote_no_disco(resultado, tmp_path_factory, nome):
    destino = str(tmp_path_factory.mktemp(nome))
    manifesto = {"artifacts": [], "deliverables": {}}
    ge.emitir_pacote_legal(manifesto, destino, None, None, resultado)
    md = Path(destino, "documentos", "pacote-legal.md").read_text(
        encoding="utf-8")
    return manifesto, md


@pytest.fixture(scope="module")
def rodada_persistida(tmp_path_factory):
    resultado, _registros = ea.run_edificio(
        normalize_spec(_carrega_persistido()), None)
    manifesto, md = _pacote_no_disco(resultado, tmp_path_factory, "g57e2e")
    return resultado, manifesto, md


def test_ponta_a_ponta_sem_spda_o_md_cita_a_ausencia(rodada_persistida):
    """O caminho real: o eletrico sai not_available e o .md nao se cala."""
    resultado, manifesto, md = rodada_persistida
    escopo = resultado["instalacoes"]["eletrico"]["escopo"]
    assert escopo["spda_nbr5419"] == "not_available"
    assert (escopo["grupo_gerador_e_alimentacao_de_emergencia"]
            == "not_available")
    pend = manifesto["deliverables"]["pacote_legal"]["pendencias_aprovacao"]
    assert any("SPDA" in p for p in pend)
    assert any("emergencia" in p for p in pend)
    assert "PENDENTE - SPDA" in md
    assert "PENDENTE" in md and "emergencia" in md


def test_ponta_a_ponta_declarados_o_md_limpa(tmp_path_factory):
    spec = _carrega_persistido()
    spec["turnkey"]["eletrico"]["spda"] = {"NP": "III", "Ng": 5.0, "Cd": 1.0}
    spec["turnkey"]["eletrico"]["emergencia"] = {
        "elevador_VA": 8000.0, "bombas_incendio_VA": 3000.0,
        "iluminacao_emergencia_VA": 1200.0}
    resultado, _registros = ea.run_edificio(normalize_spec(spec), None)
    escopo = resultado["instalacoes"]["eletrico"]["escopo"]
    assert escopo["spda_nbr5419"] == "implemented"
    assert (escopo["grupo_gerador_e_alimentacao_de_emergencia"]
            == "implemented")
    essencial = resultado["instalacoes"]["eletrico"]["emergencia"]
    total = resultado["instalacoes"]["eletrico"]["entrada"]["carga_total_VA"]
    assert 0 < essencial["carga_essencial_VA"] < total
    manifesto, md = _pacote_no_disco(resultado, tmp_path_factory, "g57e2eok")
    assert (manifesto["deliverables"]["pacote_legal"]["pendencias_aprovacao"]
            == [])
    assert "PENDENTE" not in md


# ===========================================================================
# NP sem declaracao: adotado por conservadorismo, nunca silencioso
# ===========================================================================
def test_spda_sem_np_adota_iii_e_diz_que_adotou():
    spec = _spec_base()
    spec["spda"] = {"Ng": 5.0, "Cd": 1.0}
    saida = ee.dimensiona(spec, _contexto())
    assert saida["spda"]["NP"] == "III"
    assert saida["spda"]["NP_declarado"] is False
    aviso = [a for a in saida["avisos"] if a["code"] == "spda_np_adotado"]
    assert len(aviso) == 1 and "ADOTADO" in aviso[0]["detail"]


def test_spda_com_np_nao_acusa_adocao():
    spec = _spec_base()
    spec["spda"] = {"NP": "II", "Ng": 5.0, "Cd": 1.0}
    saida = ee.dimensiona(spec, _contexto())
    assert saida["spda"]["NP"] == "II"
    assert not [a for a in saida["avisos"]
                if a["code"] == "spda_np_adotado"]


# ===========================================================================
# O PORTAO da parte 2: R1 declarado decide entre prescrever e dispensar
# ===========================================================================
def test_risco_dispensado_nao_prescreve_e_nao_trava_o_pacote():
    """R1 <= RT: avaliacao feita, resultado dispensa - sem NP, sem PENDENTE."""
    spec = _spec_base()
    spec["spda"] = {"Ng": 5.0, "Cd": 1.0, "R1": 5e-6}
    spec["emergencia"] = {"elevador_VA": 8000.0}
    saida = ee.dimensiona(spec, _contexto())
    assert saida["spda"]["dispensada_por_risco"] is True
    assert saida["escopo"]["spda_nbr5419"] == "implemented"
    assert saida["gates"]["spda"]["NP"] is None
    assert saida["gates"]["spda"]["dispensada_por_risco"] is True
    assert [a for a in saida["avisos"]
            if a["code"] == "spda_dispensada_por_risco"]
    resultado = {"instalacoes": {"eletrico": saida}}
    assert ge._pendencias_aprovacao(resultado) == []
    assert "DISPENSADA" in ee.relatorio_pt(saida)


def test_risco_necessario_prescreve_captacao():
    """R1 > RT: a protecao e' necessaria e a captacao sai prescrita."""
    spec = _spec_base()
    spec["spda"] = {"NP": "III", "Ng": 5.0, "Cd": 1.0, "R1": 2e-5}
    saida = ee.dimensiona(spec, _contexto())
    assert saida["spda"]["dispensada_por_risco"] is False
    assert saida["gates"]["spda"]["n_descidas"] == 4
    assert not [a for a in saida["avisos"]
                if a["code"] == "spda_dispensada_por_risco"]


def test_risco_nao_avaliado_vira_pendencia_nomeada():
    """Captacao sem Nd: o pacote nao trava como ausente, mas nao se cala."""
    spec = _spec_base()
    spec["spda"] = {"NP": "III", "Ng": 5.0}  # sem Cd: Nd nao sai
    saida = ee.dimensiona(spec, _contexto())
    assert saida["escopo"]["spda_nbr5419"] == "implemented"
    resultado = {"instalacoes": {"eletrico": saida}}
    pend = ge._pendencias_aprovacao(resultado)
    assert any("risco nao avaliado" in p for p in pend), pend
    pac = pl.gerar_pacote(["eletrico"], memorial=None, pendencias=pend)
    assert any("PENDENTE" in s and "risco nao avaliado" in s
               for s in pac["checklist_ppci_avcb"])
