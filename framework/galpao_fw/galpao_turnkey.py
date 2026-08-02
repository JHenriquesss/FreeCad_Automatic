# ============================================================================
# galpao_turnkey.py - O QUE ESTE SCRIPT FAZ / CALCULA
# ORQUESTRADOR-MESTRE "turnkey" do galpao industrial: um unico rodar(spec)
# dispara TODOS os verticais do sistema e consolida os vereditos numa unica
# saida. Nao recalcula nada - apenas DESPACHA para os orquestradores de cada
# disciplina e AGREGA os gates/ATENDE:
#   - "concreto"  -> galpao_concreto.rodar(spec)          (NBR 6118/6123/6122)
#   - "aco"       -> rodar_projeto.calcular(spec, out_dir) (NBR 8800/6123) *
#   - "eletrico"  -> galpao_eletrico.rodar(spec)          (NBR 5410/14039/5419)
#   - "incendio"  -> galpao_seguranca_incendio.rodar(spec)(NBR 10898/16820/17240/10897)
#   * o vertical de aco usa spec de PROJETO proprio (geometria.spans / secoes /
#     cargas) e ESCREVE arquivos; so roda quando um out_dir e' fornecido; senao e'
#     pulado com nota (nunca inventa um veredito). O MESMO shape de spec alimenta o
#     caderno_turnkey (rodar_tudo -> pranchas A1).
# PRINCIPIOS (herdados dos verticais): STATELESS (spec explicito, sem estado
# global); imports PREGUICOSOS dentro de cada adaptador -> o modulo-mestre nao
# carrega FreeCAD nem nada pesado, e uma disciplina que quebre NAO derruba as
# outras (fica isolada com 'erro'). Geometria comum e propagada a cada disciplina
# no formato que ela espera (concreto usa comprimento/vao/pe_direito; eletrico e
# incendio usam geometria={L,W,H}). Dados de projeto ausentes seguem a regra dos
# verticais (A CONFIRMAR nos proprios modulos) - o mestre nao preenche premissa.
# Veredito GLOBAL = todas as disciplinas EXECUTADAS atendem.
# Unidades: as de cada vertical (sem conversao aqui).
# ============================================================================
"""Orquestrador-mestre turnkey do galpao: um rodar(spec) despacha todos os
verticais (concreto/aco/eletrico/incendio) e consolida gates + ATENDE global."""

from __future__ import annotations


# ordem canonica de apresentacao das disciplinas no relatorio consolidado
DISCIPLINAS = ("concreto", "aco", "eletrico", "incendio")


def _geometria(g):
    """Normaliza a geometria comum aceitando os dois dialetos de chave usados pelos
    verticais: {comprimento, vao, pe_direito} (concreto) ou {L, W, H} (eletrico/
    incendio). Devolve o formato canonico {comprimento, vao, pe_direito} em metros."""
    g = g or {}
    comp = g.get("comprimento", g.get("L", 40.0))
    vao = g.get("vao", g.get("W", g.get("largura", 20.0)))
    pd = g.get("pe_direito", g.get("H", 6.0))
    return {"comprimento": float(comp), "vao": float(vao), "pe_direito": float(pd)}


def _norm(r):
    """Normaliza a saida de um vertical de contrato moderno (rodar(spec) ->
    {gates, reprovados, ATENDE}) para o registro consolidado do mestre."""
    return {"rodou": True, "ATENDE": bool(r["ATENDE"]),
            "reprovados": list(r.get("reprovados", [])),
            "gates": r.get("gates", {}), "raw": r}


# ------------------------------------------------------------------ adaptadores
# Cada adaptador recebe (sub_spec, geo_canonica, out_dir) e devolve um registro
# {rodou, ATENDE, reprovados, gates, raw|erro|nota}. Import preguicoso.

def _run_concreto(sub, geo, out_dir):
    import galpao_concreto as gc
    s = dict(sub)
    s.setdefault("comprimento", geo["comprimento"])
    s.setdefault("vao", geo["vao"])
    s.setdefault("pe_direito", geo["pe_direito"])
    return _norm(gc.rodar(s))


def _run_eletrico(sub, geo, out_dir):
    import galpao_eletrico as ge
    s = dict(sub)
    return _norm(ge.rodar(_com_geometria_LWH(s, geo)))


def _run_incendio(sub, geo, out_dir):
    import galpao_seguranca_incendio as gi
    s = dict(sub)
    return _norm(gi.rodar(_com_geometria_LWH(s, geo)))


def _run_aco(sub, geo, out_dir):
    """Vertical de aco: usa spec de PROJETO proprio (geometria.spans/secoes/cargas) e
    ESCREVE arquivos -> so roda com out_dir. Sem out_dir, e' pulado com nota (nao
    inventa). Usa rodar_projeto.calcular (que valida via exigir_completo, converte com
    to_rodar_params e chama rodar_galpao) -> MESMO shape de spec que o caderno usa p/
    gerar as pranchas (rodar_tudo). O res traz atende_global/falhas_verificacao."""
    if not out_dir:
        return {"rodou": False, "ATENDE": None, "reprovados": [], "gates": {},
                "nota": "vertical de aco requer out_dir (gera arquivos) - nao executado"}
    import os
    import rodar_projeto as RP
    res = RP.calcular(dict(sub), os.path.join(out_dir, "aco"))
    falhas = res.get("falhas_verificacao", [])            # [(nome, util), ...]
    atende = res.get("atende_global", res.get("atende"))
    gates = {nome: {"util": float(u), "OK": float(u) <= 1.001} for nome, u in falhas}
    return {"rodou": True, "ATENDE": bool(atende) if atende is not None else None,
            "reprovados": [nome for nome, u in falhas if float(u) > 1.001],
            "gates": gates, "raw": res}


def _com_geometria_LWH(s, geo):
    """Preenche s['geometria'] = {L, W, H} a partir da geometria canonica, sem
    sobrescrever o que o usuario ja informou."""
    g = dict(s.get("geometria", {}))
    g.setdefault("L", geo["comprimento"])
    g.setdefault("W", geo["vao"])
    g.setdefault("H", geo["pe_direito"])
    s["geometria"] = g
    return s


_ADAPTADORES = {"concreto": _run_concreto, "aco": _run_aco,
                "eletrico": _run_eletrico, "incendio": _run_incendio}


# ------------------------------------------------------------------- mestre
def rodar(spec, out_dir=None):
    """Despacha todos os verticais presentes no spec e consolida os vereditos.
    spec: {
      'geometria': {comprimento/L, vao/W, pe_direito/H} (m) - comum a todas as
                   disciplinas; cada uma usa o que precisa,
      'concreto' : sub-spec de galpao_concreto.rodar   (opc),
      'aco'      : spec de PROJETO de aco (rodar_projeto)(opc; requer out_dir),
      'eletrico' : sub-spec de galpao_eletrico.rodar    (opc),
      'incendio' : sub-spec de galpao_seguranca_incendio.rodar (opc),
    }
    out_dir (opc): pasta de saida do vertical de aco (que escreve arquivos).
    Retorna R com R['disciplinas'][nome] = {rodou, ATENDE, reprovados, gates, ...},
    R['executadas'], R['reprovados'] (disciplinas que reprovam) e R['ATENDE']
    (todas as executadas atendem). Uma disciplina que lance excecao fica ISOLADA
    com 'erro' e reprova, sem derrubar as demais."""
    geo = _geometria(spec.get("geometria", {}))
    disciplinas = {}
    for nome in DISCIPLINAS:
        if nome not in spec:
            continue
        try:
            disciplinas[nome] = _ADAPTADORES[nome](spec[nome], geo, out_dir)
        except Exception as e:                            # isola a falha da disciplina
            disciplinas[nome] = {"rodou": False, "ATENDE": False, "reprovados": ["ERRO"],
                                 "gates": {}, "erro": "%s: %s" % (type(e).__name__, e)}

    executadas = [n for n in DISCIPLINAS if disciplinas.get(n, {}).get("rodou")]
    puladas = [n for n in disciplinas if not disciplinas[n].get("rodou")]
    reprovados = [n for n in disciplinas
                  if disciplinas[n].get("ATENDE") is False]
    R = {"geometria": geo, "disciplinas": disciplinas, "executadas": executadas,
         "puladas": puladas, "reprovados": reprovados,
         "ATENDE": len(executadas) > 0 and len(reprovados) == 0}
    return R


def relatorio_pt(R):
    """Quadro-resumo consolidado das disciplinas do galpao turnkey."""
    geo = R["geometria"]
    L = ["PROJETO TURNKEY - GALPAO INDUSTRIAL (quadro-resumo consolidado)",
         "  Geometria comum: %.0f x %.0f m ; pe-direito %.1f m"
         % (geo["comprimento"], geo["vao"], geo["pe_direito"]),
         "  Disciplinas:"]
    rotulo = {"concreto": "Estrutura de concreto (NBR 6118/6122)",
              "aco": "Estrutura de aco (NBR 8800/6123)",
              "eletrico": "Instalacoes eletricas (NBR 5410/14039/5419)",
              "incendio": "Seguranca contra incendio (NBR 10898/16820/17240/10897)"}
    for nome in DISCIPLINAS:
        d = R["disciplinas"].get(nome)
        if d is None:
            continue
        if not d.get("rodou"):
            motivo = d.get("erro") or d.get("nota") or "nao executada"
            L.append("   - %-45s PULADA (%s)" % (rotulo[nome], motivo))
            continue
        if d["ATENDE"]:
            L.append("   - %-45s ATENDE" % rotulo[nome])
        else:
            L.append("   - %-45s REPROVA -> %s"
                     % (rotulo[nome], ", ".join(d["reprovados"]) or "?"))
    if not R["executadas"]:
        L.append("  RESULTADO: nenhuma disciplina executada")
    elif R["ATENDE"]:
        L.append("  RESULTADO GLOBAL: ATENDE (todas as %d disciplinas executadas)"
                 % len(R["executadas"]))
    else:
        L.append("  RESULTADO GLOBAL: REPROVA -> %s" % ", ".join(R["reprovados"]))
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    """Afere a consolidacao com os tres verticais de contrato moderno (puro/CI).
    Nao invoca o vertical de aco (escreve arquivos) nem FreeCAD."""
    spec = {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        # concreto com seu proprio vao/vento/solo (galpao de concreto tipico que
        # ATENDE); a geometria comum so preenche o que a disciplina nao informar.
        "concreto": {"vao": 10.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                     "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                     "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3, "sigma_solo_adm": 250.0},
        "eletrico": {"tensao_V": 380.0,
                     "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2}],
                                "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
        "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                     "deteccao": {"viga_m": 0.0},
                     "sprinklers": {"altura_estoque_m": 3.0}},
    }
    R = rodar(spec)
    # as tres disciplinas modernas executaram
    assert set(R["executadas"]) == {"concreto", "eletrico", "incendio"}, R["executadas"]
    # geometria comum propagada ao incendio (galpao 40x20x6 -> 6 pontos de aclaramento)
    inc = R["disciplinas"]["incendio"]["raw"]
    assert inc["gates"]["iluminacao_emergencia"]["N_aclaramento"] == 6
    # geometria comum propagada ao eletrico via geometria={L,W,H}
    ele = R["disciplinas"]["eletrico"]["raw"]
    assert ele["gates"]["luminotecnica"]["OK"]
    # veredito global = AND dos verticais
    esperado = all(R["disciplinas"][n]["ATENDE"] for n in R["executadas"])
    assert R["ATENDE"] == esperado
    # aco sem out_dir -> pulado, com nota, NUNCA inventado
    R2 = rodar(dict(spec, aco={"qualquer": 1}))
    assert "aco" in R2["puladas"] and R2["disciplinas"]["aco"]["ATENDE"] is None
    assert "requer out_dir" in R2["disciplinas"]["aco"]["nota"]
    # uma disciplina que quebra fica ISOLADA e reprova, sem derrubar as outras
    R3 = rodar({"geometria": spec["geometria"], "incendio": spec["incendio"],
                "eletrico": "spec_invalido_de_proposito"})
    assert R3["disciplinas"]["eletrico"]["rodou"] is False
    assert "erro" in R3["disciplinas"]["eletrico"]
    assert R3["disciplinas"]["incendio"]["rodou"] is True    # a outra seguiu
    assert R3["ATENDE"] is False                             # a quebrada reprova
    print(relatorio_pt(R))
    print("galpao_turnkey self-test PASSED")


if __name__ == "__main__":
    _selftest()
