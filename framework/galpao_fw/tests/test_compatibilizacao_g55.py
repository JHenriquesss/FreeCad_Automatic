"""G55: a pendencia de compatibilizacao precisa poder fechar.

Terceira categoria (furo_previsto) + regra normativa (NBR 6118:2014
13.2.5/13.2.5.1/13.2.5.2/21.3.3) + classificador por geometria declarada +
resolucao registrada que sai do denominador do gate. Cada teste fica vermelho
ao injetar o defeito correspondente (regra frouxa, passe sem dado, aprovacao
sem justificativa, aprovacao de reprovado, reclassificacao do galpao).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import compatibilizacao as cp


def _clash(a="C-V1", b="P-TUBO", disc="estruturaxhidraulica",
           tipos="BeamxPipe", vol=6.0e5, esperado=False, **extra):
    c = {"a": a, "b": b, "disciplinas": disc, "tipos": tipos,
         "vol_mm3": vol, "esperado": esperado}
    c.update(extra)
    return c


def _rep(*clashes):
    return {"por_par": {}, "clashes": list(clashes)}


# ---------------------------------------------------------------------------
# 1. Regra do furo em viga (13.2.5.1 a-d + face minima "em qualquer caso")
# ---------------------------------------------------------------------------
def test_furo_viga_dispensa_atendida_e_admissivel():
    r = cp.avalia_furo_viga(d_furo_mm=50, h_viga_mm=500, dist_apoio_mm=1200,
                            zona_tracao=True, dist_face_mm=80, cobrimento_mm=30,
                            furo_unico=True, armadura_seccionada=False)
    assert r["veredito"] == cp.VER_ADMISSIVEL
    assert any("13.2.5.1" in c for c in r["clausulas"])


def test_furo_viga_face_minima_reprova():
    # dist a face 40 < max(50, 2x30=60): limite DURO, nao dispensa.
    r = cp.avalia_furo_viga(d_furo_mm=50, h_viga_mm=500, dist_apoio_mm=1200,
                            zona_tracao=True, dist_face_mm=40, cobrimento_mm=30,
                            furo_unico=True, armadura_seccionada=False)
    assert r["veredito"] == cp.VER_REPROVADO
    assert "face" in " ".join(r["motivos"])


def test_furo_viga_secciona_armadura_reprova():
    r = cp.avalia_furo_viga(d_furo_mm=50, h_viga_mm=500, dist_apoio_mm=1200,
                            zona_tracao=True, dist_face_mm=80, cobrimento_mm=30,
                            furo_unico=True, armadura_seccionada=True)
    assert r["veredito"] == cp.VER_REPROVADO


def test_furo_viga_sem_dado_nunca_e_passe():
    r = cp.avalia_furo_viga(d_furo_mm=50, h_viga_mm=None, dist_apoio_mm=1200,
                            zona_tracao=True, dist_face_mm=80, cobrimento_mm=30,
                            furo_unico=True, armadura_seccionada=False)
    assert r["veredito"] == cp.VER_ACONFIRMAR
    assert "h_viga_mm" in " ".join(r["motivos"])


def test_furo_viga_fora_da_dispensa_pede_verificacao():
    # d=150 > 120 (13.2.5.1(b)) mas <= h/3: nao dispensa, nao reprova.
    r = cp.avalia_furo_viga(d_furo_mm=150, h_viga_mm=600, dist_apoio_mm=1500,
                            zona_tracao=True, dist_face_mm=80, cobrimento_mm=30,
                            furo_unico=True, armadura_seccionada=False)
    assert r["veredito"] == cp.VER_ACONFIRMAR
    assert any("verificaca" in m for m in r["motivos"])


def test_furo_viga_perto_do_apoio_pede_verificacao():
    r = cp.avalia_furo_viga(d_furo_mm=50, h_viga_mm=500, dist_apoio_mm=300,
                            zona_tracao=True, dist_face_mm=80, cobrimento_mm=30,
                            furo_unico=True, armadura_seccionada=False)
    assert r["veredito"] == cp.VER_ACONFIRMAR


# ---------------------------------------------------------------------------
# 2. Regra da abertura em laje (13.2.5.2) + furo vertical (21.3.3)
# ---------------------------------------------------------------------------
def test_abertura_laje_dispensa_atendida():
    r = cp.avalia_abertura_laje(dim_abertura_mm=100, vao_menor_mm=4000,
                                dist_apoio_mm=1500, dist_adjacente_mm=2500,
                                laje_lisa=False, armadura_seccionada=False)
    assert r["veredito"] == cp.VER_ADMISSIVEL


def test_abertura_laje_sem_dado_e_a_confirmar():
    r = cp.avalia_abertura_laje(dim_abertura_mm=100, vao_menor_mm=None,
                                dist_apoio_mm=1500, dist_adjacente_mm=2500,
                                laje_lisa=False, armadura_seccionada=False)
    assert r["veredito"] == cp.VER_ACONFIRMAR
    assert "vao_menor_mm" in " ".join(r["motivos"])


def test_abertura_laje_lisa_sempre_verifica():
    r = cp.avalia_abertura_laje(dim_abertura_mm=100, vao_menor_mm=4000,
                                dist_apoio_mm=1500, dist_adjacente_mm=2500,
                                laje_lisa=True, armadura_seccionada=False)
    assert r["veredito"] == cp.VER_ACONFIRMAR


def test_furo_vertical_alem_de_b_terco_reprova():
    r = cp.avalia_furo_vertical_viga(d_furo_mm=100, b_viga_mm=200,
                                     dist_face_mm=80, cobrimento_mm=30)
    assert r["veredito"] == cp.VER_REPROVADO


# ---------------------------------------------------------------------------
# 3. Classificador: um par de cada categoria, geometria decide (nunca o tipo)
# ---------------------------------------------------------------------------
def test_classificador_montagem_conflito_e_furo():
    mont = cp.classifica_cruzamento(_clash(esperado=True))
    assert mont["categoria"] == cp.CAT_MONTAGEM and mont["veredito"] is None

    # BeamxPipe SEM geometria: conflito (o tipo nao classifica furo).
    sem_geo = cp.classifica_cruzamento(_clash())
    assert sem_geo["categoria"] == cp.CAT_CONFLITO

    # BeamxPipe COM passagem transversal: furo (sem dims -> a_confirmar).
    furo = cp.classifica_cruzamento(
        _clash(), {"direcao": "transversal"})
    assert furo["categoria"] == cp.CAT_FURO
    assert furo["veredito"] == cp.VER_ACONFIRMAR

    # Mesmo BeamxPipe, sobreposicao longitudinal: conflito (13.2.6).
    longi = cp.classifica_cruzamento(
        _clash(), {"direcao": "longitudinal"})
    assert longi["categoria"] == cp.CAT_CONFLITO

    # Slab x prumada vertical: furo pela regra da laje.
    laje = cp.classifica_cruzamento(
        _clash(a="C-L11", b="P-H-ESG-PRU", tipos="SlabxPipe"),
        {"direcao": "transversal"})
    assert laje["categoria"] == cp.CAT_FURO

    # Pilar x tubo, mesmo transversal: conflito (13.2.5.1 e' de vigas).
    pilar = cp.classifica_cruzamento(
        _clash(a="C-P1", b="P-TUBO", tipos="ColumnxPipe"),
        {"direcao": "transversal"})
    assert pilar["categoria"] == cp.CAT_CONFLITO


def test_pendencia_furo_tem_acao_de_prever_e_nao_remanejar():
    hint = {"direcao": "transversal"}
    pend = cp.gerar_pendencias(
        _rep(_clash(cruzamento=hint)))
    assert len(pend) == 1
    p = pend[0]
    assert p["categoria"] == cp.CAT_FURO
    assert p["status"] == cp.STATUS_ABERTO  # admissivel nao fecha sozinho
    assert "remanejar" not in p["acao_sugerida"].lower()
    assert "prever passagem" in p["acao_sugerida"].lower()
    assert p["responsavel"] == "hidraulica"


def test_furo_admissivel_continua_aberto_ate_decisao():
    hint = {"direcao": "transversal", "d_furo_mm": 50, "h_viga_mm": 500,
            "dist_apoio_mm": 1200, "zona_tracao": True, "dist_face_mm": 80,
            "cobrimento_mm": 30, "furo_unico": True,
            "armadura_seccionada": False}
    pend = cp.gerar_pendencias(_rep(_clash(cruzamento=hint)))
    assert pend[0]["veredito"] == cp.VER_ADMISSIVEL
    assert pend[0]["status"] == cp.STATUS_ABERTO
    assert cp.gate_ok(pend) is False


# ---------------------------------------------------------------------------
# 4. Fechar a pendencia: resolucao sai do denominador, com rastro
# ---------------------------------------------------------------------------
def test_resolucao_fecha_gate_com_rastro_no_relatorio_e_bcf():
    pend = cp.gerar_pendencias(
        _rep(_clash(cruzamento={"direcao": "transversal"})))
    assert cp.gate_ok(pend) is False
    reqs = [{"id": pend[0]["id"], "aprovador": "Eng. Resp. - CREA 123",
             "justificativa": "furo DN50 no terco medio, borda armada no executivo"}]
    fech = cp.aplicar_resolucoes(pend, reqs)
    assert fech[0]["status"] == cp.STATUS_RESOLVIDA
    assert cp.gate_ok(fech) is True
    assert cp.resumo(fech)["abertas"] == 0
    assert cp.resumo(fech)["resolvidas"] == 1
    bcf = cp.bcf_topics(fech)
    assert bcf["topics"][0]["topic_status"] == "Closed"
    assert "Eng. Resp." in bcf["topics"][0]["description"]
    assert "DN50" in bcf["topics"][0]["description"]
    txt = cp.relatorio_pt(fech)
    assert "Eng. Resp." in txt and "DN50" in txt


def test_resolucao_sem_justificativa_falha():
    pend = cp.gerar_pendencias(
        _rep(_clash(cruzamento={"direcao": "transversal"})))
    try:
        cp.aplicar_resolucoes(pend, [{"id": pend[0]["id"],
                                      "aprovador": "Eng. Resp."}])
    except ValueError as exc:
        assert "justificativa" in str(exc)
    else:
        raise AssertionError("aprovacao sem justificativa passou em silencio")


def test_resolucao_sem_aprovador_falha():
    pend = cp.gerar_pendencias(
        _rep(_clash(cruzamento={"direcao": "transversal"})))
    try:
        cp.aplicar_resolucoes(pend, [{"id": pend[0]["id"],
                                      "justificativa": "algum motivo"}])
    except ValueError as exc:
        assert "aprovador" in str(exc)
    else:
        raise AssertionError("aprovacao anonima passou em silencio")


def test_resolucao_de_reprovado_falha():
    hint = {"direcao": "transversal", "d_furo_mm": 50, "h_viga_mm": 500,
            "dist_apoio_mm": 1200, "zona_tracao": True, "dist_face_mm": 10,
            "cobrimento_mm": 30, "furo_unico": True,
            "armadura_seccionada": False}
    pend = cp.gerar_pendencias(_rep(_clash(cruzamento=hint)))
    assert pend[0]["veredito"] == cp.VER_REPROVADO
    try:
        cp.aplicar_resolucoes(pend, [{"id": pend[0]["id"],
                                      "aprovador": "Eng. Resp.",
                                      "justificativa": "tentando silenciar"}])
    except ValueError as exc:
        assert "reprovado" in str(exc)
    else:
        raise AssertionError("aprovacao de reprovado passou em silencio")


def test_resolucao_de_conflito_falha():
    pend = cp.gerar_pendencias(_rep(_clash()))  # sem hint: conflito
    assert pend[0]["categoria"] == cp.CAT_CONFLITO
    try:
        cp.aplicar_resolucoes(pend, [{"id": pend[0]["id"],
                                      "aprovador": "Eng. Resp.",
                                      "justificativa": "tentando silenciar"}])
    except ValueError as exc:
        assert "conflito" in str(exc) or "furo_previsto" in str(exc)
    else:
        raise AssertionError("aprovacao de conflito passou em silencio")


def test_nota_legada_nao_fecha_nem_falha():
    # issue_id + status + note e' o canal antigo de revisao: ecoa no manifesto,
    # nao fecha o gate e nao falha (texto nao fecha conflito).
    pend = cp.gerar_pendencias(
        _rep(_clash(cruzamento={"direcao": "transversal"})))
    notas = [{"issue_id": pend[0]["id"], "status": "reviewed",
              "note": "revisado pelo engenheiro"},
             {"issue_id": pend[0]["id"], "status": "approved",
              "note": "revisado pelo engenheiro"}]
    mantidas = cp.aplicar_resolucoes(pend, notas)
    assert mantidas[0]["status"] == cp.STATUS_ABERTO
    assert cp.gate_ok(mantidas) is False


def test_decisao_explicita_aprovar_sem_justificativa_falha():
    pend = cp.gerar_pendencias(
        _rep(_clash(cruzamento={"direcao": "transversal"})))
    try:
        cp.aplicar_resolucoes(pend, [{"id": pend[0]["id"],
                                      "decisao": "aprovar",
                                      "aprovador": "Eng. Resp."}])
    except ValueError as exc:
        assert "justificativa" in str(exc)
    else:
        raise AssertionError("decisao de aprovar sem justificativa passou")


def test_resolucao_alvo_inexistente_falha():
    pend = cp.gerar_pendencias(
        _rep(_clash(cruzamento={"direcao": "transversal"})))
    try:
        cp.aplicar_resolucoes(pend, [{"id": "CLH-999",
                                      "aprovador": "Eng. Resp.",
                                      "justificativa": "x"}])
    except ValueError as exc:
        assert "inexistente" in str(exc)
    else:
        raise AssertionError("resolucao de alvo inexistente passou em silencio")


# ---------------------------------------------------------------------------
# 5. Regressao do galpao: mesmos pares, mesma classificacao/acao/responsavel
# ---------------------------------------------------------------------------
def _par_galpao(a, b, disc, tipos, vol, esperado):
    return _clash(a=a, b=b, disc=disc, tipos=tipos, vol=vol, esperado=esperado)


def test_galpao_congelado_sem_hint():
    rep = _rep(
        _par_galpao("C-P1E", "E-CALHA", "concretoxeletrico",
                    "ColumnxCableCarrier", 8.0e6, False),
        _par_galpao("C-V1", "H-TUBO", "concretoxhidraulica",
                    "BeamxPipe", 6.0e5, False),
        _par_galpao("C-P2D", "E-DESC", "concretoxeletrico",
                    "ColumnxCable", 3.0e5, True),
    )
    pend = cp.gerar_pendencias(rep)
    por_tipos = {p["tipos"]: p for p in pend}
    calha = por_tipos["ColumnxCableCarrier"]
    assert calha["categoria"] == cp.CAT_CONFLITO
    assert calha["status"] == cp.STATUS_ABERTO
    assert calha["responsavel"] == "eletrico"
    assert "remanejar" in calha["acao_sugerida"].lower() or \
        "prever passagem" in calha["acao_sugerida"]
    tubo = por_tipos["BeamxPipe"]
    assert tubo["categoria"] == cp.CAT_CONFLITO
    assert tubo["status"] == cp.STATUS_ABERTO
    assert tubo["responsavel"] == "hidraulica"
    assert "prever passagem" in tubo["acao_sugerida"]
    desc = por_tipos["ColumnxCable"]
    assert desc["categoria"] == cp.CAT_MONTAGEM
    assert desc["status"] == cp.STATUS_APROVADO
    assert desc["severidade"] == "Informativa"


# ---------------------------------------------------------------------------
# 6. Geometria do federado do edificio: transversal x longitudinal
# ---------------------------------------------------------------------------
def test_cruzamentos_edificio_transversal_e_longitudinal():
    import bim_instalacoes_edificio as bie

    membros = [
        {"marca": "C-VY", "disciplina": "estrutura", "tipo": "Beam",
         "p1": [0.0, 0.0, 2700.0], "p2": [0.0, 4000.0, 2700.0]},
        {"marca": "C-L11", "disciplina": "estrutura", "tipo": "Slab",
         "dims": [4000.0, 4000.0, 100.0], "centro": [2000.0, 2000.0, 2950.0]},
        {"marca": "P-RAMAL", "disciplina": "hidraulica", "tipo": "Pipe",
         "p1": [0.0, 1000.0, 2700.0], "p2": [4000.0, 1000.0, 2700.0]},
        {"marca": "P-PRU", "disciplina": "hidraulica", "tipo": "Pipe",
         "p1": [1000.0, 1000.0, 0.0], "p2": [1000.0, 1000.0, 6000.0]},
        {"marca": "P-LONG", "disciplina": "hidraulica", "tipo": "Pipe",
         "p1": [0.0, 0.0, 2700.0], "p2": [0.0, 4000.0, 2700.0]},
    ]
    rep = {"clashes": [
        {"a": "C-VY", "b": "P-RAMAL", "disciplinas": "estruturaxhidraulica",
         "tipos": "BeamxPipe", "vol_mm3": 1e5, "esperado": False},
        {"a": "C-L11", "b": "P-PRU", "disciplinas": "estruturaxhidraulica",
         "tipos": "SlabxPipe", "vol_mm3": 2e5, "esperado": False},
        {"a": "C-VY", "b": "P-LONG", "disciplinas": "estruturaxhidraulica",
         "tipos": "BeamxPipe", "vol_mm3": 3e5, "esperado": False},
    ]}
    hints = bie.cruzamentos_edificio(membros, rep)
    assert hints[("C-VY", "P-RAMAL", "BeamxPipe")]["direcao"] == "transversal"
    assert hints[("C-L11", "P-PRU", "SlabxPipe")]["direcao"] == "transversal"
    assert hints[("C-VY", "P-LONG", "BeamxPipe")]["direcao"] == "longitudinal"
    pend = cp.gerar_pendencias(rep, cruzamentos=hints)
    por_par = {(p["elemento_a"], p["elemento_b"]): p for p in pend}
    assert por_par[("C-VY", "P-RAMAL")]["categoria"] == cp.CAT_FURO
    assert por_par[("C-L11", "P-PRU")]["categoria"] == cp.CAT_FURO
    assert por_par[("C-VY", "P-LONG")]["categoria"] == cp.CAT_CONFLITO
