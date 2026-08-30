# ============================================================================
# hidraulica_residencial.py - O QUE ESTE MODULO CALCULA
# VERTICAL HIDRAULICA DE UMA CASA (modulo de calculo stateless, CI). Nao contem
# nenhuma tabela propria: reusa as PRIMITIVAS ja aferidas de hidraulica_predial
# (NBR 5626:2020 agua fria / NBR 8160 esgoto e ventilacao / NBR 10844 pluvial),
# lidas literalmente dos PDFs no NotebookLM (regra AR300).
#
#   AGUA FRIA  - vazao pelo metodo escolhido (soma da Tab.B.4, default, ou pesos
#                da 5626:1998) -> DN por v <= 3 m/s (Sec.6.8.3) + verificacao de
#                pressao no ponto mais desfavoravel (Sec.6.9).
#   ESGOTO     - UHC (Tab.3) -> ramal (Tab.5), tubo de queda quando ha mais de um
#                pavimento (Tab.6), coletor predial (Tab.7, DN >= 100) e
#                ventilacao (Tab.8 + Tab.D.1).
#   PLUVIAL    - Q = i*A/60 (Sec.5.3.1) por PONTO DE DESCIDA -> condutor (Tab.4)
#                e calha semicircular (Tab.3).
#
# DIFERENCA DELIBERADA em relacao ao galpao: aqui NAO existe DN default. Uma casa
# sem aparelhos declarados fica BLOQUEADA, nunca com um diametro comercial
# plausivel que parece dimensionado. O unico dado com default e' a intensidade
# pluvial i (dado de sitio), sempre flagado [A CONFIRMAR].
#
# SATURACAO: toda tabela da NBR 8160 tem teto. Os gates leem a flag 'saturado'
# das primitivas *_sat e REPROVAM - a saturacao nunca sai silenciosa com OK=True.
# ============================================================================
"""Hidraulica residencial: agua fria, esgoto/ventilacao e pluvial de uma casa,
reusando hidraulica_predial (NBR 5626:2020 / 8160 / 10844). Stateless (CI)."""

from __future__ import annotations

import math
from numbers import Real

import hidraulica_predial as hp

# ambientes que, por destinacao, tem aparelho hidraulico. Serve so para a
# CONFERENCIA arquitetura x hidraulica (um banheiro sem aparelho declarado e'
# uma lacuna do projeto, nao um ambiente seco).
TIPOS_COM_APARELHO = frozenset({
    "banheiro", "lavabo", "cozinha", "copa", "copa_cozinha",
    "cozinha_area_servico", "area_servico", "lavanderia",
})
# ponto de utilizacao mais exigente do conjunto governa o minimo (NBR 5626 Sec.6.9.2)
TIPO_PONTO_POR_APARELHO = {"bacia_valvula": "valvula_descarga"}


def _finito_positivo(valor):
    return (isinstance(valor, Real) and not isinstance(valor, bool)
            and math.isfinite(float(valor)) and float(valor) > 0.0)


def _erro(code, detail, **ctx):
    registro = {"code": code, "detail": detail}
    if ctx:
        registro.update(ctx)
    return registro


def _agua_fria(spec, erros, avisos):
    aparelhos = spec.get("aparelhos_agua")
    if not aparelhos:
        erros.append(_erro("aparelhos_agua_ausentes",
                           "informe aparelhos_agua {tipo: qtd}; nao ha DN default "
                           "para uma casa"))
        return None
    metodo = spec.get("metodo_agua", "soma")
    try:
        calc = hp.diametro_agua(aparelhos, metodo=metodo)
    except ValueError as exc:
        erros.append(_erro("aparelhos_agua_invalidos", str(exc)))
        return None
    rede = {"DN_mm": float(calc["DN_mm"]), "Q_Ls": calc["Q_Ls"],
            "v_real_ms": calc["v_real_ms"], "v_max_ms": calc["v_max_ms"],
            "metodo": calc["metodo"], "velocidade_OK": bool(calc["OK"]),
            "fonte": ("NBR 5626:1998 (pesos)" if metodo == "pesos"
                      else "NBR 5626:2020 (soma)")}
    if "soma_P" in calc:
        rede["soma_P"] = calc["soma_P"]

    # --- pressao no ponto mais desfavoravel (Sec.6.9) ---
    agua_cfg = spec.get("agua") or {}
    p_alim = agua_cfg.get("p_alim_kPa")
    p_alim_default = p_alim is None
    if p_alim_default:
        p_alim = 100.0                      # [A CONFIRMAR] dado de sitio
        avisos.append(_erro("p_alim_assumida",
                            "pressao de alimentacao assumida em 100 kPa "
                            "[A CONFIRMAR]: informe agua.p_alim_kPa"))
    l_real = agua_cfg.get("L_real_m")
    if l_real is None:
        erros.append(_erro("comprimento_agua_ausente",
                           "informe agua.L_real_m (percurso ate o ponto mais "
                           "desfavoravel); o traçado nao e' inventado"))
        return rede
    if not _finito_positivo(l_real):
        erros.append(_erro("comprimento_agua_invalido",
                           "agua.L_real_m deve ser finito e maior que zero"))
        return rede
    tipo_ponto = "geral"
    for aparelho, tipo in TIPO_PONTO_POR_APARELHO.items():
        if aparelhos.get(aparelho):
            tipo_ponto = tipo
    pressao = hp.verifica_pressao(
        calc["Q_Ls"], calc["DN_mm"], float(l_real), float(p_alim),
        conexoes=agua_cfg.get("conexoes"),
        dcota_m=float(agua_cfg.get("dcota_m", 0.0)),
        tipo_ponto=tipo_ponto)
    pressao["p_alim_default"] = p_alim_default
    rede["pressao"] = pressao
    return rede


def _esgoto(spec, erros, avisos):
    aparelhos = spec.get("aparelhos_esgoto")
    if not aparelhos:
        erros.append(_erro("aparelhos_esgoto_ausentes",
                           "informe aparelhos_esgoto {tipo: qtd}; nao ha DN "
                           "default para uma casa"))
        return None
    try:
        uhc, dn_descarga = hp.uhc_de_aparelhos(aparelhos)
    except ValueError as exc:
        erros.append(_erro("aparelhos_esgoto_invalidos", str(exc)))
        return None
    declividade = float(spec.get("decl_esgoto_pct", 1.0))
    pavimentos = int(spec.get("pavimentos", 1))
    if pavimentos < 1:
        erros.append(_erro("pavimentos_invalidos",
                           "pavimentos deve ser >= 1"))
        return None
    ramal = hp.diametro_ramal_esgoto_sat(uhc, dn_descarga)
    try:
        coletor = hp.diametro_coletor_sat(uhc, declividade)
    except ValueError as exc:
        erros.append(_erro("declividade_esgoto_invalida", str(exc)))
        return None
    com_bacia = bool(aparelhos.get("bacia"))
    ventilacao = hp.diametro_ramal_ventilacao_sat(uhc, com_bacia=com_bacia)
    rede = {
        "uhc": uhc, "dn_ramal_descarga_min_mm": dn_descarga,
        "ramal_DN_mm": float(ramal["DN_mm"]),
        "ramal_saturado": bool(ramal["saturado"]),
        "coletor_DN_mm": float(coletor["DN_mm"]),
        "coletor_saturado": bool(coletor["saturado"]),
        "declividade_pct": coletor["declividade_pct"],
        "declividade_minima_pct": hp.declividade_minima_pct(coletor["DN_mm"]),
        "ventilacao_ramal_DN_mm": float(ventilacao["DN_mm"]),
        "ventilacao_saturada": bool(ventilacao["saturado"]),
        "ventilacao_coluna_DN_mm": float(
            hp.diametro_coluna_ventilacao(coletor["DN_mm"])),
        "com_bacia": com_bacia,
        "pavimentos": pavimentos,
        "fonte": "NBR 8160",
    }
    if pavimentos > 1:
        # so ha tubo de queda quando existe mais de um pavimento; numa casa
        # terrea o campo fica explicitamente ausente, nao zerado.
        queda = hp.diametro_tubo_queda_sat(uhc, pavimentos)
        rede["tubo_queda_DN_mm"] = float(queda["DN_mm"])
        rede["tubo_queda_saturado"] = bool(queda["saturado"])
    if not com_bacia:
        avisos.append(_erro("ventilacao_sem_bacia",
                            "nenhuma bacia sanitaria declarada: a ventilacao usou "
                            "a coluna 'sem bacias' da Tab.8 (menos exigente)"))
    return rede


def _pluvial(spec, erros, avisos):
    cobertura = spec.get("cobertura") or {}
    area = cobertura.get("area_m2")
    if area is None:
        erros.append(_erro("area_cobertura_ausente",
                           "informe cobertura.area_m2 (projecao horizontal)"))
        return None
    if not _finito_positivo(area):
        erros.append(_erro("area_cobertura_invalida",
                           "cobertura.area_m2 deve ser finita e maior que zero"))
        return None
    n_pontos = int(cobertura.get("n_condutores", 2))
    if n_pontos < 1:
        erros.append(_erro("n_condutores_invalido",
                           "cobertura.n_condutores deve ser >= 1"))
        return None
    # cada ponto de descida drena uma FRACAO da cobertura, nao o telhado inteiro
    area_ponto = float(area) / n_pontos
    # a intensidade de chuva e' DADO DE SITIO (Tab.5, por cidade). O flag de
    # "assumida" vem de o spec ter declarado ou nao - e nao de o valor coincidir
    # com o padrao (um projeto pode confirmar 150 mm/h e nao merece o aviso).
    i_declarada = cobertura.get("i_mm_h")
    i_assumida = i_declarada is None
    if not i_assumida and not _finito_positivo(i_declarada):
        erros.append(_erro("intensidade_pluvial_invalida",
                           "cobertura.i_mm_h deve ser finita e maior que zero"))
        return None
    i_mm_h = (hp.I_PLUVIAL_PADRAO_MM_H if i_assumida else float(i_declarada))
    condutor = hp.diametro_pluvial(area_ponto, i_mm_h,
                                   float(cobertura.get("decl_pluvial_pct", 1.0)))
    calha = hp.diametro_calha(area_ponto, condutor["i_mm_h"],
                              declividade_pct=float(
                                  cobertura.get("decl_calha_pct", 1.0)))
    if i_assumida:
        avisos.append(_erro("intensidade_pluvial_assumida",
                            "intensidade de chuva assumida em %.0f mm/h "
                            "[A CONFIRMAR]: informe cobertura.i_mm_h (NBR 10844 "
                            "Tab.5, por cidade)" % condutor["i_mm_h"]))
    return {
        "area_m2": float(area), "n_condutores": n_pontos,
        "area_por_ponto_m2": round(area_ponto, 2),
        "Q_Lmin": condutor["Q_Lmin"], "i_mm_h": condutor["i_mm_h"],
        "i_default": i_assumida,
        "condutor_DN_mm": float(condutor["DN_mm"]),
        "condutor_saturado": bool(condutor["saturado"]),
        "calha_DN_mm": float(calha["DN_mm"]),
        "calha_saturada": bool(calha["saturado"]),
        "fonte": "NBR 10844",
    }


def conferir_ambientes_molhados(ambientes, aparelhos_agua, aparelhos_esgoto):
    """Lacunas entre o programa de arquitetura e os aparelhos declarados.

    Um banheiro, cozinha ou area de servico no programa e nenhum aparelho no
    spec hidraulico e' uma LACUNA do projeto: sem esta conferencia a casa sai
    com a rede dimensionada para menos pontos do que a planta tem."""
    if not isinstance(ambientes, list):
        return []
    molhados = [a for a in ambientes
                if str((a or {}).get("tipo", "")).lower() in TIPOS_COM_APARELHO]
    if not molhados:
        return []
    total = sum((aparelhos_agua or {}).values()) + sum(
        (aparelhos_esgoto or {}).values())
    if total > 0:
        return []
    return [_erro("ambientes_molhados_sem_aparelho",
                  "o programa tem %d ambiente(s) molhado(s) e nenhum aparelho "
                  "hidraulico declarado" % len(molhados),
                  ambientes=[a.get("nome") for a in molhados])]


def rodar(spec):
    """Dimensiona agua fria, esgoto/ventilacao e pluvial de uma casa.

    spec: {aparelhos_agua{tipo:qtd}, aparelhos_esgoto{tipo:qtd},
           metodo_agua ('soma'|'pesos'), decl_esgoto_pct, pavimentos,
           agua{p_alim_kPa, L_real_m, dcota_m, conexoes},
           cobertura{area_m2, n_condutores, i_mm_h, decl_pluvial_pct,
           decl_calha_pct}, ambientes (opcional, do programa de arquitetura)}.
    Retorna {redes, gates, reprovados, erros, avisos, escopo, ATENDE}."""
    if not isinstance(spec, dict):
        raise TypeError("spec de hidraulica residencial deve ser um dicionario")
    erros = []
    avisos = []
    agua = _agua_fria(spec, erros, avisos)
    esgoto = _esgoto(spec, erros, avisos)
    pluvial = _pluvial(spec, erros, avisos)
    erros.extend(conferir_ambientes_molhados(
        spec.get("ambientes"), spec.get("aparelhos_agua"),
        spec.get("aparelhos_esgoto")))

    redes = {}
    if agua:
        redes["agua_fria"] = agua
    if esgoto:
        redes["esgoto"] = esgoto
    if pluvial:
        redes["pluvial"] = pluvial

    gates = {}
    if agua:
        gates["agua_velocidade"] = {
            "DN_mm": agua["DN_mm"], "v_real_ms": agua["v_real_ms"],
            "v_max_ms": agua["v_max_ms"], "OK": agua["velocidade_OK"]}
        if agua.get("pressao"):
            pressao = agua["pressao"]
            # gate INFORMATIVO enquanto p_alim for assumida (dado de sitio);
            # EFETIVO assim que o spec informar a pressao disponivel.
            gates["agua_pressao"] = {
                "p_residual_kPa": pressao["p_residual_kPa"],
                "p_min_kPa": pressao["p_min_kPa"],
                "perda_kPa": pressao["perda_kPa"],
                "p_alim_assumida": pressao["p_alim_default"],
                "OK": pressao["OK"] or pressao["p_alim_default"]}
    if esgoto:
        saturado = bool(esgoto["ramal_saturado"] or esgoto["coletor_saturado"]
                        or esgoto["ventilacao_saturada"]
                        or esgoto.get("tubo_queda_saturado"))
        gates["esgoto_saturacao"] = {
            "ramal_saturado": esgoto["ramal_saturado"],
            "coletor_saturado": esgoto["coletor_saturado"],
            "ventilacao_saturada": esgoto["ventilacao_saturada"],
            "tubo_queda_saturado": esgoto.get("tubo_queda_saturado", False),
            "uhc": esgoto["uhc"], "OK": not saturado}
        gates["esgoto_declividade"] = {
            "declividade_pct": esgoto["declividade_pct"],
            "declividade_minima_pct": esgoto["declividade_minima_pct"],
            "OK": esgoto["declividade_pct"] >= esgoto["declividade_minima_pct"]}
    if pluvial:
        saturado_pl = bool(pluvial["condutor_saturado"] or pluvial["calha_saturada"])
        gates["pluvial_saturacao"] = {
            "condutor_saturado": pluvial["condutor_saturado"],
            "calha_saturada": pluvial["calha_saturada"],
            "Q_Lmin": pluvial["Q_Lmin"], "OK": not saturado_pl}
    gates["entradas_declaradas"] = {
        "n_erros": len(erros), "OK": not erros}

    escopo = {
        "agua_fria": "implemented",
        "esgoto_ventilacao": "implemented",
        "pluvial": "implemented",
        "agua_quente": "not_requested",
        "reservatorio_e_recalque": "not_implemented",
        "aprovacao_concessionaria": "not_claimed",
        "construction_readiness": "not_claimed",
    }
    resultado = {
        "schema": "freecad-automatic/residential-hydraulics",
        "schema_version": 1,
        "redes": redes, "gates": gates, "erros": erros, "avisos": avisos,
        "escopo": escopo,
    }
    resultado["dimensionamento"] = relatorio_pt(resultado)
    resultado["reprovados"] = [k for k, g in gates.items() if not g["OK"]]
    resultado["ATENDE"] = not resultado["reprovados"]
    return resultado


def relatorio_pt(resultado):
    """Uma linha por rede, com o que foi calculado e o que ficou [A CONFIRMAR]."""
    redes = resultado["redes"]
    partes = []
    agua = redes.get("agua_fria")
    if agua:
        texto = ("agua fria DN%.0f calculado %s (Q=%.2f L/s; v=%.2f m/s)"
                 % (agua["DN_mm"], agua["fonte"], agua["Q_Ls"], agua["v_real_ms"]))
        if not agua["velocidade_OK"]:
            texto += " [VELOCIDADE ACIMA DE %.1f m/s]" % agua["v_max_ms"]
        if agua.get("pressao"):
            pressao = agua["pressao"]
            texto += (" ; pressao residual %.0f kPa (min %.0f, %s%s)"
                      % (pressao["p_residual_kPa"], pressao["p_min_kPa"],
                         "OK" if pressao["OK"] else "INSUF.",
                         " [A CONFIRMAR p_alim]" if pressao["p_alim_default"] else ""))
        partes.append(texto)
    esgoto = redes.get("esgoto")
    if esgoto:
        texto = ("esgoto ramal DN%.0f / coletor DN%.0f a %.1f%% (ventilacao ramal "
                 "DN%.0f, coluna DN%.0f) calculado NBR 8160 (UHC=%.1f)"
                 % (esgoto["ramal_DN_mm"], esgoto["coletor_DN_mm"],
                    esgoto["declividade_pct"], esgoto["ventilacao_ramal_DN_mm"],
                    esgoto["ventilacao_coluna_DN_mm"], esgoto["uhc"]))
        if "tubo_queda_DN_mm" in esgoto:
            texto += " ; tubo de queda DN%.0f (%d pav)" % (
                esgoto["tubo_queda_DN_mm"], esgoto["pavimentos"])
        if (esgoto["ramal_saturado"] or esgoto["coletor_saturado"]
                or esgoto["ventilacao_saturada"]
                or esgoto.get("tubo_queda_saturado")):
            texto += " [SATURADO - subdividir o trecho ou aumentar a declividade]"
        partes.append(texto)
    pluvial = redes.get("pluvial")
    if pluvial:
        texto = ("pluvial condutor DN%.0f + calha DN%.0f calculado NBR 10844 "
                 "(Q=%.0f L/min por ponto; i=%.0f mm/h%s; %d ponto(s) de descida "
                 "para %.1f m2)"
                 % (pluvial["condutor_DN_mm"], pluvial["calha_DN_mm"],
                    pluvial["Q_Lmin"], pluvial["i_mm_h"],
                    " [A CONFIRMAR i local]" if pluvial["i_default"] else "",
                    pluvial["n_condutores"], pluvial["area_m2"]))
        if pluvial["condutor_saturado"] or pluvial["calha_saturada"]:
            texto += " [SATURADO - aumentar a declividade ou os pontos de descida]"
        partes.append(texto)
    if not partes:
        return "nada dimensionado: entradas obrigatorias ausentes"
    return "; ".join(partes)


def _selftest():
    spec = {
        "aparelhos_agua": {"bacia_caixa": 1, "chuveiro": 1, "lavatorio": 1,
                           "pia": 1, "tanque": 1},
        "aparelhos_esgoto": {"bacia": 1, "chuveiro": 1, "lavatorio": 1,
                             "pia": 1, "tanque": 1},
        "agua": {"L_real_m": 18.0, "p_alim_kPa": 120.0,
                 "conexoes": {"cotovelo_90": 6, "te_direta": 2}},
        "cobertura": {"area_m2": 90.0, "n_condutores": 2, "i_mm_h": 150.0},
    }
    r = rodar(spec)
    # UHC = 6 + 2 + 1 + 3 + 3 = 15 -> ramal Tab.5 DN75, mas o DN minimo de descarga
    # da bacia (Tab.3) e' 100 -> o ramal nao pode ser menor que isso
    assert r["redes"]["esgoto"]["uhc"] == 15
    assert r["redes"]["esgoto"]["ramal_DN_mm"] == 100
    assert r["redes"]["esgoto"]["coletor_DN_mm"] == 100
    # 15 UHC com bacia -> Tab.8 coluna "com bacias": ate 17 -> DN50
    assert r["redes"]["esgoto"]["ventilacao_ramal_DN_mm"] == 50
    assert r["ATENDE"] is True, r["reprovados"]
    # sem aparelhos NAO ha diametro default: bloqueia
    vazio = rodar({"cobertura": {"area_m2": 90.0}})
    assert vazio["ATENDE"] is False
    assert "aparelhos_agua_ausentes" in [e["code"] for e in vazio["erros"]]
    # saturacao da ventilacao (Tab.8 termina em 60 UHC com bacias) nunca silenciosa
    grande = rodar({**spec, "aparelhos_esgoto": {"bacia": 20, "pia": 10}})
    assert grande["gates"]["esgoto_saturacao"]["ventilacao_saturada"] is True
    assert grande["ATENDE"] is False
    print("hidraulica_residencial self-test PASSED (NBR 5626:2020 / 8160 / 10844)")
    print("  " + r["dimensionamento"])


if __name__ == "__main__":
    _selftest()
