# ============================================================================
# estaca_parametros_g143.py - G143: OS PARAMETROS DA FUNDACAO DO GALPAO SEM
# DEFAULT SILENCIOSO (D102: default que decide veredito — declarar ou recusar).
#
# Medido (2026-09-15, antes de mudar, galpao 10x40x6, tipo_fundacao="estaca",
# perfil SPT de tests/test_build_concreto.py:114):
# - sem D_estaca/L_estaca a conta usava D=0,30 m / L=8,0 m calados
#   (galpao_concreto.py:351) e a PE-CO-04 desenhava "D30 L8" como projeto;
# - L 8->10 m: util 0,116->0,103 e geometria "L8"->"L10"; D 0,30->0,40 m:
#   util 0,116->0,071; L=0: n 1->5 em silencio; D=0: TypeError cru;
# - tipo_estaca pre_moldada->escavada: util 0,116->0,198; com Q_roof=0,25 e
#   L=6 no perfil fraco a pre_moldada ATENDE (n=2) e a escavada REPROVA
#   (n=4) — o tipo INVERTE o veredito; com Q_roof=2,0 inverte de novo;
# - cota_apoio/B_max_sapata nao mudam o caminho com tipo explicito, mas com
#   tipo ausente (auto) B_max 0,5->estaca e >=1,0->sapata em carga alta;
# - mu_solo/sigma_solo_adm ignorados no caminho estaca (0,9/500 -> identico).
#
# Regra por item (motivo escrito, sem valor novo arbitrado):
# - D_estaca, L_estaca, tipo_estaca: RECUSA NOMEADA quando tipo_fundacao e
#   "estaca" (como a estaca sem SPT ja faz). Motivo: geometria comercial
#   sem piso universal — o default 0,30/8,0/"pre_moldada" decidia
#   geometria, capacidade e veredito sem ninguem declarar.
# - cota_apoio, B_max_sapata: DECLARACAO (defaults 0,5/2,5 mantidos para a
#   recomendacao SPT, com a origem dita no resultado, no memorial, na folha
#   e nos sinais de revisao). Motivo: parametro de modelo da recomendacao
#   geotecnica, nao geometria final; recusar quebraria o caminho
#   automatico legitimo (sapata que fecha sozinha).
# - mu_solo, sigma_solo_adm: TERCEIRO VALOR no caminho estaca ("nao se
#   aplica", declarado no memorial); no caminho sapata seguem com a origem
#   dita (a folha PE-CO-04 do G140 ja declarava; o memorial e os sinais
#   passam a declarar). Motivo: medido que a conta da estaca nao os le.
#
# Portas de entrada (convencao 11): o spec direto de galpao_concreto.rodar
# e o sub-spec "concreto" do galpao_turnkey (via project-spec.json ->
# turnkey.concreto) passam pelo mesmo `spec` — uma fonte so aqui. O
# wizard (wizard.py/PERGUNTAS_ESTACA) alimenta o ProjetoSpec METALICO
# (rodar_galpao), nunca o galpao_concreto: terceiro valor declarado
# (nao se aplica ao concreto), dito no verbete.
# ============================================================================
"""Parametros da fundacao do galpao de concreto sem default silencioso.

Fonte unica das recusas nomeadas (D/L/tipo da estaca) e das proveniencias
declaradas (cota/B_max/mu/sigma). O memorial e a folha leem daqui.
STATELESS: funcoes puras.
"""

from __future__ import annotations

# Defaults NUMERICOS mantidos onde a recusa quebraria caminho legitimo —
# agora com a origem dita (nunca calados). Nenhum numero novo arbitrado:
# sao os mesmos que o codigo ja usava.
COTA_APOIO_DEFAULT = 0.5
B_MAX_SAPATA_DEFAULT = 2.5
MU_SOLO_DEFAULT = 0.5
SIGMA_SOLO_DEFAULT = 200.0

ORIGEM_DECLARADO = "declarado_no_spec"
ORIGEM_DEFAULT = "default"
ORIGEM_NAO_SE_APLICA = "nao_se_aplica"


def _e_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def resolver_estaca_de_spec(spec):
    """Exige D/L/tipo da estaca declarados quando tipo_fundacao="estaca".

    Ausente/invalido -> ValueError NOMEADO (d_estaca_nao_declarada,
    l_estaca_nao_declarada, tipo_estaca_nao_declarada, *_invalida) — nunca
    0,30/8,0/"pre_moldada" calados. Declarado -> o numero do spec, com a
    origem declarada.
    """
    if not isinstance(spec, dict):
        raise ValueError("d_estaca_nao_declarada: spec nao e dict "
                         "(sem geometria de estaca declarada)")
    if "D_estaca" not in spec or spec["D_estaca"] is None:
        raise ValueError(
            "d_estaca_nao_declarada: tipo_fundacao='estaca' exige 'D_estaca' "
            "(diametro da estaca, m) declarado no spec — sem default")
    if "L_estaca" not in spec or spec["L_estaca"] is None:
        raise ValueError(
            "l_estaca_nao_declarada: tipo_fundacao='estaca' exige 'L_estaca' "
            "(comprimento da estaca, m) declarado no spec — sem default")
    if "tipo_estaca" not in spec or spec["tipo_estaca"] is None:
        raise ValueError(
            "tipo_estaca_nao_declarada: tipo_fundacao='estaca' exige "
            "'tipo_estaca' declarado no spec (pre_moldada/metalica/escavada/"
            "helice/raiz/franki/omega) — sem default")
    D_e = spec["D_estaca"]
    L_e = spec["L_estaca"]
    tipo = spec["tipo_estaca"]
    if not _e_numero(D_e) or not D_e > 0:
        raise ValueError(
            "d_estaca_invalida: D_estaca deve ser numero > 0 (m, recebido %r)"
            % (D_e,))
    if not _e_numero(L_e) or not L_e > 0:
        raise ValueError(
            "l_estaca_invalida: L_estaca deve ser numero > 0 (m, recebido %r)"
            % (L_e,))
    try:
        import estaca_profunda as _ep
        validos = sorted(_ep._F1_F2)
    except ImportError:
        validos = ["pre_moldada", "metalica", "escavada", "helice", "raiz",
                   "franki", "omega"]
    if not isinstance(tipo, str) or tipo not in validos:
        raise ValueError(
            "tipo_estaca_invalida: %r (use um de: %s)"
            % (tipo, ", ".join(validos)))
    return {"D": float(D_e), "L": float(L_e), "tipo_estaca": tipo,
            "origem": ORIGEM_DECLARADO, "explicito": True}


def resolver_recomendacao_de_spec(spec):
    """cota_apoio/B_max com a origem dita (declarado ou default mantido).

    Os numeros sao os que a recomendacao SPT sempre usou (0,5/2,5); a
    novidade e a proveniencia viajar no resultado (memorial, folha e
    sinais leem daqui). Nao numerico -> ValueError nomeado.
    """
    spec = spec if isinstance(spec, dict) else {}
    if spec.get("cota_apoio") is None:
        cota, cota_origem = COTA_APOIO_DEFAULT, ORIGEM_DEFAULT
    else:
        cota = spec["cota_apoio"]
        if not _e_numero(cota) or not cota >= 0:
            raise ValueError(
                "cota_apoio_invalida: cota_apoio deve ser numero >= 0 (m, "
                "recebido %r)" % (cota,))
        cota, cota_origem = float(cota), ORIGEM_DECLARADO
    if spec.get("B_max_sapata") is None:
        bmax, bmax_origem = B_MAX_SAPATA_DEFAULT, ORIGEM_DEFAULT
    else:
        bmax = spec["B_max_sapata"]
        if not _e_numero(bmax) or not bmax > 0:
            raise ValueError(
                "b_max_sapata_invalida: B_max_sapata deve ser numero > 0 (m, "
                "recebido %r)" % (bmax,))
        bmax, bmax_origem = float(bmax), ORIGEM_DECLARADO
    return {"cota_apoio": cota, "cota_origem": cota_origem,
            "B_max_sapata": bmax, "B_max_origem": bmax_origem}


def resolver_solo_sapata_de_spec(spec, tem_spt_ou_geo):
    """sigma/mu com a origem dita (declarado, derivado da sondagem, default).

    Os numeros sao os que o ramo sapata sempre usou (explicito > SPT >
    200; mu 0,5). Nao numerico -> ValueError nomeado.
    """
    spec = spec if isinstance(spec, dict) else {}
    if spec.get("sigma_solo_adm") is not None:
        sig = spec["sigma_solo_adm"]
        if not _e_numero(sig) or not sig > 0:
            raise ValueError(
                "sigma_solo_adm_invalida: deve ser numero > 0 (kN/m2, "
                "recebido %r)" % (sig,))
        sigma, sigma_origem = float(sig), ORIGEM_DECLARADO
    elif tem_spt_ou_geo:
        sigma, sigma_origem = None, "derivada_sondagem"
    else:
        sigma, sigma_origem = SIGMA_SOLO_DEFAULT, ORIGEM_DEFAULT
    if spec.get("mu_solo") is None:
        mu, mu_origem = MU_SOLO_DEFAULT, ORIGEM_DEFAULT
    else:
        mu = spec["mu_solo"]
        if not _e_numero(mu) or not mu > 0:
            raise ValueError(
                "mu_solo_invalido: deve ser numero > 0 (recebido %r)" % (mu,))
        mu, mu_origem = float(mu), ORIGEM_DECLARADO
    return {"sigma_solo_adm": sigma, "sigma_origem": sigma_origem,
            "mu_solo": mu, "mu_origem": mu_origem}


def parametros_de_spec(spec, tipo_fund, tem_spt_ou_geo):
    """Proveniencia completa dos 7 valores do bloco de fundacao (G143).

    No caminho estaca exige D/L/tipo (recusa nomeada) e marca mu/sigma
    como nao-se-aplica. Fora dele, D/L/tipo sao nao-se-aplica. Os
    dicionarios aninhados com {"default": True} sao lidos pelo
    _review_signals do adaptador (codigo assumed_default) — a declaracao
    chega aos sinais sem reinterpretar gate nenhum.
    """
    spec = spec if isinstance(spec, dict) else {}
    rec = resolver_recomendacao_de_spec(spec)
    if tipo_fund == "estaca":
        est = resolver_estaca_de_spec(spec)
        bloco = {
            "D_estaca": {"valor": est["D"], "origem": ORIGEM_DECLARADO},
            "L_estaca": {"valor": est["L"], "origem": ORIGEM_DECLARADO},
            "tipo_estaca": {"valor": est["tipo_estaca"],
                            "origem": ORIGEM_DECLARADO},
            "mu_solo": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                        "nota": "fundacao profunda: atrito solo-sapata nao "
                                "usado na conta da estaca"},
            "sigma_solo_adm": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                               "nota": "fundacao profunda: tensao de sapata "
                                       "nao usada na conta da estaca"},
        }
    else:
        solo = resolver_solo_sapata_de_spec(spec, tem_spt_ou_geo)
        bloco = {
            "D_estaca": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                         "nota": "fundacao rasa: sem estaca"},
            "L_estaca": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                         "nota": "fundacao rasa: sem estaca"},
            "tipo_estaca": {"valor": None, "origem": ORIGEM_NAO_SE_APLICA,
                            "nota": "fundacao rasa: sem estaca"},
            "mu_solo": {"valor": solo["mu_solo"],
                        "origem": solo["mu_origem"]},
            "sigma_solo_adm": {"valor": solo["sigma_solo_adm"],
                               "origem": solo["sigma_origem"]},
        }
        if solo["mu_origem"] == ORIGEM_DEFAULT:
            bloco["mu_solo"]["default"] = True
        if solo["sigma_origem"] == ORIGEM_DEFAULT:
            bloco["sigma_solo_adm"]["default"] = True
    bloco["cota_apoio"] = {"valor": rec["cota_apoio"],
                           "origem": rec["cota_origem"]}
    bloco["B_max_sapata"] = {"valor": rec["B_max_sapata"],
                             "origem": rec["B_max_origem"]}
    if rec["cota_origem"] == ORIGEM_DEFAULT:
        bloco["cota_apoio"]["default"] = True
    if rec["B_max_origem"] == ORIGEM_DEFAULT:
        bloco["B_max_sapata"]["default"] = True
    return {"tipo_fundacao": tipo_fund, "parametros": bloco,
            "estaca": ({"D": est["D"], "L": est["L"],
                        "tipo_estaca": est["tipo_estaca"],
                        "origem": ORIGEM_DECLARADO}
                       if tipo_fund == "estaca" else None)}


def _fmt_origem(origem):
    return {"declarado_no_spec": "declarado no spec",
            "default": "default (confirmar com sondagem/projeto)",
            "nao_se_aplica": "nao se aplica",
            "derivada_sondagem": "derivada da sondagem SPT"}.get(
                origem, str(origem))


def linha_memorial(parametros):
    """Linha que o memorial carimba (vem desta fonte so)."""
    if not isinstance(parametros, dict):
        raise ValueError("resultado sem fundacao_parametros (G143): a "
                         "entrega nao declara o que a conta nao registrou")
    bloco = parametros.get("parametros") or {}
    tipo = parametros.get("tipo_fundacao")
    partes = []
    if tipo == "estaca":
        est = parametros.get("estaca") or {}
        partes.append("estaca D=%.2f m L=%.1f m tipo=%s (%s)"
                      % (est.get("D", 0.0), est.get("L", 0.0),
                         est.get("tipo_estaca", "?"),
                         _fmt_origem((est.get("origem")))))
        partes.append("mu_solo/sigma_solo_adm nao se aplicam "
                      "(fundacao profunda)")
    else:
        for chave, rot in (("mu_solo", "mu_solo"),
                           ("sigma_solo_adm", "sigma_solo_adm")):
            item = bloco.get(chave) or {}
            val = item.get("valor")
            txt = ("%.3g" % val) if val is not None else "derivada"
            partes.append("%s=%s (%s)" % (rot, txt,
                                          _fmt_origem(item.get("origem"))))
    for chave, rot in (("cota_apoio", "cota_apoio"),
                       ("B_max_sapata", "B_max_sapata")):
        item = bloco.get(chave) or {}
        val = item.get("valor")
        txt = ("%.3g m" % val) if val is not None else "?"
        partes.append("%s=%s (%s)" % (rot, txt,
                                      _fmt_origem(item.get("origem"))))
    return ("PARAMETROS DA FUNDACAO (G143): " + " ; ".join(partes))


def linha_folha(parametros):
    """Linha curta que a PE-CO-04 carimba no quadro (vem desta fonte so)."""
    if not isinstance(parametros, dict):
        return None
    bloco = parametros.get("parametros") or {}
    tipo = parametros.get("tipo_fundacao")
    if tipo == "estaca":
        est = parametros.get("estaca") or {}
        base = ("estaca D%.0f L%.0f %s (declarado no spec)"
                % (float(est.get("D", 0.0)) * 100,
                   float(est.get("L", 0.0)),
                   est.get("tipo_estaca", "?")))
        c = bloco.get("cota_apoio") or {}
        if c.get("origem") == ORIGEM_DEFAULT:
            base += " ; cota_apoio default (confirmar)"
        b = bloco.get("B_max_sapata") or {}
        if b.get("origem") == ORIGEM_DEFAULT:
            base += " ; B_max default (confirmar)"
        return base + " ; mu/sigma N/A (profunda)"
    c = bloco.get("cota_apoio") or {}
    b = bloco.get("B_max_sapata") or {}
    m = bloco.get("mu_solo") or {}
    s = bloco.get("sigma_solo_adm") or {}
    marc = []
    if c.get("origem") == ORIGEM_DEFAULT:
        marc.append("cota_apoio default (confirmar)")
    if b.get("origem") == ORIGEM_DEFAULT:
        marc.append("B_max default (confirmar)")
    if m.get("origem") == ORIGEM_DEFAULT:
        marc.append("mu default (confirmar)")
    if s.get("origem") == ORIGEM_DEFAULT:
        marc.append("sigma default (confirmar)")
    if not marc:
        return None
    return "parametros: " + " ; ".join(marc)


def _selftest():
    perfil = [{"tipo": "argila", "N": 5, "dz": 3.0}]
    # recusa nomeada, uma por uma
    for spec, marca in [
            ({"tipo_fundacao": "estaca", "perfil_spt": perfil},
             "d_estaca_nao_declarada"),
            ({"tipo_fundacao": "estaca", "perfil_spt": perfil,
              "D_estaca": 0.30}, "l_estaca_nao_declarada"),
            ({"tipo_fundacao": "estaca", "perfil_spt": perfil,
              "D_estaca": 0.30, "L_estaca": 8.0},
             "tipo_estaca_nao_declarada"),
            ({"tipo_fundacao": "estaca", "D_estaca": 0, "L_estaca": 8.0,
              "tipo_estaca": "pre_moldada"}, "d_estaca_invalida"),
            ({"tipo_fundacao": "estaca", "D_estaca": 0.30, "L_estaca": 0,
              "tipo_estaca": "pre_moldada"}, "l_estaca_invalida"),
            ({"tipo_fundacao": "estaca", "D_estaca": 0.30, "L_estaca": 8.0,
              "tipo_estaca": "tubarole"}, "tipo_estaca_invalida")]:
        try:
            resolver_estaca_de_spec(spec)
            raise AssertionError("devia recusar: %s" % marca)
        except ValueError as exc:
            assert marca in str(exc), (marca, exc)
    ok = resolver_estaca_de_spec({"tipo_fundacao": "estaca",
                                  "D_estaca": 0.30, "L_estaca": 10.0,
                                  "tipo_estaca": "escavada"})
    assert ok["D"] == 0.30 and ok["L"] == 10.0
    assert ok["tipo_estaca"] == "escavada"
    # recomendacao: mesmos numeros, origem dita
    rec = resolver_recomendacao_de_spec({})
    assert rec["cota_apoio"] == 0.5 and rec["cota_origem"] == "default"
    assert rec["B_max_sapata"] == 2.5 and rec["B_max_origem"] == "default"
    rec2 = resolver_recomendacao_de_spec({"cota_apoio": 1.5,
                                          "B_max_sapata": 4.0})
    assert rec2["cota_origem"] == "declarado_no_spec"
    # bloco completo: estaca marca mu/sigma N/A; sapata marca defaults
    p_est = parametros_de_spec({"tipo_fundacao": "estaca", "D_estaca": 0.30,
                                "L_estaca": 8.0,
                                "tipo_estaca": "pre_moldada"}, "estaca",
                               True)
    assert p_est["parametros"]["mu_solo"]["origem"] == "nao_se_aplica"
    assert p_est["parametros"]["cota_apoio"]["default"] is True
    p_sap = parametros_de_spec({}, "sapata", False)
    assert p_sap["parametros"]["sigma_solo_adm"]["default"] is True
    assert p_sap["parametros"]["D_estaca"]["origem"] == "nao_se_aplica"
    assert "PARAMETROS DA FUNDACAO (G143)" in linha_memorial(p_est)
    assert "declarado no spec" in (linha_folha(p_est) or "")
    print("estaca_parametros_g143 self-test PASSED")


if __name__ == "__main__":
    _selftest()
