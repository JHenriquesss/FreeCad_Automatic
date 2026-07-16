# ============================================================================
# wizard.py - ENTRADA GUIADA (formulario) -> ProjetoSpec validado
# "Eu digo o que preciso e as condicoes do local" -> um ProjetoSpec completo,
# pronto para o rodar_projeto.rodar_tudo (calculo + 3D + pranchas). Pergunta
# GATE A GATE, na mesma ordem do projeto_spec.REQUERIDOS. Ask-Do-Not-Invent: os
# campos de SITIO (solo/sondagem) e de FABRICANTE (ponte) NAO tem default -
# o wizard exige; os demais aceitam Enter (default entre colchetes).
#
# Arquitetura testavel: o SCHEMA de perguntas e dados; construir_spec(respostas)
# monta o spec a partir de um dict de respostas (unit-testavel, sem stdin);
# perguntar() e so o laco de I/O. Salva/carrega o spec em JSON (reprodutivel).
#
# Uso:  python wizard.py            # interativo -> salva spec + oferece rodar
#       python wizard.py spec.json  # carrega um spec salvo e roda o pipeline
# ============================================================================
"""Wizard de entrada guiada -> ProjetoSpec. Testavel (construir_spec) + CLI."""

from __future__ import annotations

import json
import os
import sys

import projeto_spec as PS


# ---- parsers -----------------------------------------------------------------
def _f(v):
    return float(str(v).replace(",", "."))


def _i(v):
    return int(float(str(v).replace(",", ".")))


def _b(v):
    s = str(v).strip().lower()
    if s in ("s", "sim", "y", "yes", "true", "1", "engastada", "engastado"):
        return True
    if s in ("n", "nao", "não", "no", "false", "0", "rotulada", "rotulado"):
        return False
    raise ValueError("responda sim/nao")


def _dim(v):
    """'4000x4500' ou '4000,4500' -> (4000.0, 4500.0) em mm."""
    s = str(v).lower().replace("x", ",").replace(" ", "")
    a, b = s.split(",")[:2]
    return (_f(a), _f(b))


# ---- schema de perguntas (dados) --------------------------------------------
# (chave, prompt, parser, default, obrigatorio). default=None + obrigatorio=True
# => Ask-Do-Not-Invent (sem Enter). Ordem = ordem do formulario.
PERGUNTAS = [
    # terreno / legislacao
    ("area_lote_m2", "Area do lote (m2)", _f, None, True),
    ("to_max", "Taxa de ocupacao maxima (0-1)", _f, 0.6, False),
    ("ca_max", "Coeficiente de aproveitamento maximo", _f, 1.0, False),
    ("tp_min", "Taxa de permeabilidade minima (0-1)", _f, 0.2, False),
    ("recuo_frente", "Recuo de frente (m)", _f, 5.0, False),
    ("recuo_lateral", "Recuo lateral (m)", _f, 1.5, False),
    ("recuo_fundos", "Recuo de fundos (m)", _f, 3.0, False),
    # geometria
    ("span", "Vao transversal do galpao (m)", _f, None, True),
    ("comprimento", "Comprimento (m)", _f, None, True),
    ("eave", "Pe-direito / altura do beiral (m)", _f, None, True),
    ("bay", "Espacamento entre porticos (m)", _f, 5.0, False),
    ("base_fixed", "Base engastada? (sim=engastada / nao=rotulada)", _b, False, False),
    # cobertura
    ("aguas", "Numero de aguas da cobertura (1 ou 2)", _i, 2, False),
    ("slope", "Inclinacao da cobertura (fracao, ex 0.10 = 10%)", _f, 0.10, False),
    ("telha_tipo", "Tipo de telha (trapezoidal/ondulada/sanduiche)", str, "trapezoidal", False),
    ("telha_peso", "Peso da telha (kN/m2)", _f, 0.10, False),
    ("calha", "Tem calha de agua pluvial? (sim/nao)", _b, True, False),
    ("chuva_I_mm_h", "Intensidade pluviometrica local (mm/h, NBR 10844)", _f, 150.0, False),
    # fechamento
    ("fech_tipo", "Fechamento das paredes (telha/alvenaria/alvenaria_telha)", str, "telha", False),
    ("fech_peso", "Peso do fechamento (kN/m2)", _f, 0.10, False),
    ("mesa_travada", "Ha mao-francesa travando a mesa interna da viga? (sim/nao)", _b, False, False),
    ("n_maos_francesas", "Quantas maos-francesas por agua? (0 se nenhuma)", _i, 0, False),
    # aberturas (simplificado)
    ("ab_portao_frente", "Portao na frente LxH (mm, ex 4000x4500; vazio=nao)", _dim, "", False),
    ("ab_porta_fundo", "Porta nos fundos LxH (mm; vazio=nao)", _dim, "", False),
    ("ab_janelas_lat", "Janelas laterais LxH (mm; vazio=nao)", _dim, "", False),
    # vento
    ("v0", "Velocidade basica do vento V0 (m/s, NBR 6123 Fig.1)", _f, None, True),
    ("cat", "Categoria de rugosidade (I..V)", str, "II", False),
    ("classe", "Classe da edificacao (A/B/C)", str, "B", False),
    ("s3", "Fator estatistico S3", _f, 0.95, False),
    ("abertura_dominante", "Abertura dominante p/ Cpi (portao_oitao/portao_lateral/vedada)",
     str, "portao_oitao", False),
    # cargas
    ("G", "Carga permanente de cobertura G (kN/m2)", _f, 0.27, False),
    ("Q", "Sobrecarga Q (kN/m2)", _f, 0.25, False),
    ("self_peso", "Peso proprio estrutural estimado (kN/m2)", _f, 0.35, False),
    ("tapamento", "Carga de tapamento (kN/m2)", _f, 0.10, False),
    # fundacao (Ask-Do-Not-Invent no solo)
    ("sigma_solo", "Tensao admissivel do solo (kN/m2, DA SONDAGEM)", _f, None, True),
    ("fund_tipo", "Tipo de fundacao (sapata=rasa / estaca=profunda)", str, "sapata", False),
]

# perguntas da fundacao PROFUNDA (so quando fund_tipo == 'estaca')
PERGUNTAS_ESTACA = [
    ("est_tipo", "Tipo de estaca (pre_moldada/metalica/escavada/helice)", str, "pre_moldada", False),
    ("est_D", "Diametro da estaca (m)", _f, 0.30, False),
    ("est_L", "Comprimento da estaca (m)", _f, 10.0, False),
    ("est_FS", "Fator de seguranca global (NBR 6122; >=3,0 sem prova de carga)", _f, 3.0, False),
    ("spt_tipo", "Solo predominante da sondagem (ex areia_siltosa)", str, None, True),
    ("spt_N", "N-SPT medio ao longo do fuste", _f, None, True),
    ("spt_dz", "Espessura da camada resistente (m)", _f, None, True),
]


def _pergunta_map():
    return {k: (p, fn, d, obr) for k, p, fn, d, obr in (PERGUNTAS + PERGUNTAS_ESTACA)}


# ---- montagem do spec (testavel) --------------------------------------------
def construir_spec(r, slug="galpao"):
    """Monta um ProjetoSpec a partir do dict de respostas 'r' (ja com os tipos
    certos). Nao faz I/O. Retorna o spec (pode estar incompleto -> validar())."""
    s = PS.novo()
    s["slug"] = slug
    s["descricao"] = r.get("descricao", slug)
    s["terreno"].update(
        area_lote_m2=r["area_lote_m2"], to_max=r.get("to_max", 0.6),
        ca_max=r.get("ca_max", 1.0), tp_min=r.get("tp_min", 0.2),
        recuos={"frente": r.get("recuo_frente", 5.0),
                "lateral": r.get("recuo_lateral", 1.5),
                "fundos": r.get("recuo_fundos", 3.0)})
    span, eave, slope = r["span"], r["eave"], r.get("slope", 0.10)
    ridge = eave + slope * span / 2.0
    s["geometria"].update(span=span, comprimento=r["comprimento"], eave=eave,
                          ridge=ridge, bay=r.get("bay", 5.0),
                          base_fixed=bool(r.get("base_fixed", False)))
    s["cobertura"].update(aguas=r.get("aguas", 2), slope=slope,
                          telha_tipo=r.get("telha_tipo", "trapezoidal"),
                          telha_peso=r.get("telha_peso", 0.10),
                          calha=bool(r.get("calha", True)),
                          chuva_I_mm_h=r.get("chuva_I_mm_h", 150.0))
    nmf = r.get("n_maos_francesas", 0) or 0
    s["fechamento"].update(tipo=r.get("fech_tipo", "telha"),
                           altura_alvenaria=0, peso=r.get("fech_peso", 0.10),
                           mesa_interna_travada=bool(r.get("mesa_travada", False)),
                           n_maos_francesas=(nmf if nmf > 0 else None))
    ab = {}
    for chave, campo in (("ab_portao_frente", "portao_frente"),
                         ("ab_porta_fundo", "porta_fundo"),
                         ("ab_janelas_lat", "janelas_laterais")):
        v = r.get(chave)
        if v not in (None, "", ()):
            ab[campo] = v
    s["aberturas"] = ab if ab else {"vedada": True}
    s["vento"].update(v0=r["v0"], cat=r.get("cat", "II"), classe=r.get("classe", "B"),
                      s3=r.get("s3", 0.95), z=ridge,
                      abertura_dominante=r.get("abertura_dominante", "portao_oitao"))
    s["ponte"] = None            # ponte via bloco avancado (nao no wizard base)
    s["cargas"].update(G=r["G"] if "G" in r else 0.27, Q=r.get("Q", 0.25),
                       self=r.get("self_peso", 0.35), tapamento=r.get("tapamento", 0.10))
    s["fundacao"]["sigma_solo_adm"] = r["sigma_solo"]
    tipo = r.get("fund_tipo", "sapata")
    s["fundacao"]["tipo"] = tipo
    if tipo == "estaca":
        # sem os dados da sondagem, perfil_spt fica vazio -> validar() bloqueia
        # (Ask-Do-Not-Invent). Com eles, monta a camada resistente.
        tem_spt = all(r.get(k) not in (None, "") for k in ("spt_tipo", "spt_N", "spt_dz"))
        s["fundacao"]["estaca"] = {
            "perfil_spt": ([{"tipo": r["spt_tipo"], "N": r["spt_N"], "dz": r["spt_dz"]}]
                           if tem_spt else []),
            "tipo_estaca": r.get("est_tipo", "pre_moldada"),
            "D": r.get("est_D", 0.30), "L": r.get("est_L", 10.0),
            "FS": r.get("est_FS", 3.0)}
    return s


# ---- laco interativo ---------------------------------------------------------
def _ask_one(chave, prompt, parser, default, obrigatorio, entrada, saida):
    dflt = "" if default is None else (
        "sim" if default is True else "nao" if default is False else str(default))
    sufixo = "" if default is None else f" [{dflt}]"
    marca = "  (obrigatorio)" if obrigatorio and default is None else ""
    while True:
        saida(f"{prompt}{sufixo}{marca}")
        raw = entrada("> ").strip()
        if raw == "":
            if obrigatorio and default is None:
                saida("  -> campo obrigatorio (dado de sitio/projeto). Informe um valor.")
                continue
            if parser in (_dim,) and default in ("", None):
                return None
            return default
        try:
            return parser(raw)
        except Exception as ex:
            saida(f"  -> valor invalido ({ex}). Tente de novo.")


def perguntar(entrada=input, saida=print, slug=None):
    """Roda o formulario interativo e retorna um ProjetoSpec. entrada/saida
    injetaveis (testes)."""
    saida("=" * 64)
    saida("WIZARD DE PROJETO DE GALPAO - responda gate a gate (Enter=default)")
    saida("Campos 'obrigatorio' sao dados de SITIO/FABRICANTE (Ask-Do-Not-Invent).")
    saida("=" * 64)
    if slug is None:
        slug = entrada("Nome/slug do projeto [galpao]: ").strip() or "galpao"
    r = {}
    for chave, prompt, parser, default, obr in PERGUNTAS:
        r[chave] = _ask_one(chave, prompt, parser, default, obr, entrada, saida)
    if r.get("fund_tipo") == "estaca":
        saida("-- Fundacao PROFUNDA (estaca): dados da SONDAGEM --")
        for chave, prompt, parser, default, obr in PERGUNTAS_ESTACA:
            r[chave] = _ask_one(chave, prompt, parser, default, obr, entrada, saida)
    spec = construir_spec(r, slug=slug)
    return spec


def salvar_spec(spec, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    return path


def carregar_spec(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _cli():
    aqui = os.path.dirname(os.path.abspath(__file__))
    if aqui not in sys.path:
        sys.path.insert(0, aqui)
    # modo 2: carregar spec salvo e rodar
    if len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
        spec = carregar_spec(sys.argv[1])
        print(PS.resumo_pt(spec))
    else:
        spec = perguntar()
        print(PS.resumo_pt(spec))
        destino = input("\nSalvar spec em (Enter=spec_<slug>.json): ").strip() \
            or f"spec_{spec['slug']}.json"
        salvar_spec(spec, destino)
        print(f"Spec salvo em: {destino}")
    val = PS.validar(spec)
    if not val["ok"]:
        print("\nSpec INCOMPLETO - decida os campos pendentes antes de rodar:")
        for p, d in val["faltando"]:
            print(f"  - {p}: {d}")
        return
    if input("\nRodar o pipeline completo agora (calc+3D+pranchas)? [nao]: ").strip().lower() \
            in ("s", "sim", "y"):
        import rodar_projeto as RP
        res = RP.rodar_tudo(spec)
        print("\nATENDE (global):", res["atende"], "->", res["out_dir"])
    else:
        print("Spec pronto. Para rodar depois:  python wizard.py", "<spec.json>")


def _selftest():
    # respostas minimas (sapata) -> spec completo/valido
    r_sapata = dict(area_lote_m2=1200, span=10, comprimento=20, eave=6, v0=40,
                    sigma_solo=200, fund_tipo="sapata")
    s = construir_spec(r_sapata, slug="t_sapata")
    v = PS.validar(s)
    assert v["ok"], v["faltando"]
    # round-trip JSON preserva a validade
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "t_wiz.json")
    salvar_spec(s, p)
    assert PS.validar(carregar_spec(p))["ok"]
    # estaca sem os dados da sondagem -> bloqueia; com eles -> valido
    r_est = dict(r_sapata, fund_tipo="estaca")
    assert PS.validar(construir_spec(r_est))["ok"] is False
    r_est.update(spt_tipo="areia_siltosa", spt_N=20, spt_dz=8.0)
    assert PS.validar(construir_spec(r_est, slug="t_estaca"))["ok"]
    # laco interativo simulado: Enter em tudo menos os obrigatorios
    respostas = iter(["meu_galpao"] + _roteiro_min())
    saidas = []
    spec = perguntar(entrada=lambda _="": next(respostas), saida=saidas.append,
                     slug=None)
    assert PS.validar(spec)["ok"], PS.validar(spec)["faltando"]
    assert spec["slug"] == "meu_galpao"
    print("wizard self-test PASSED")
    print(f"  perguntas base: {len(PERGUNTAS)} ; estaca: {len(PERGUNTAS_ESTACA)}")
    print(f"  spec sapata valido={PS.validar(construir_spec(r_sapata))['ok']} ; "
          f"estaca valido={PS.validar(construir_spec(r_est))['ok']}")


def _roteiro_min():
    """Sequencia de respostas p/ o laco: obrigatorios preenchidos, resto Enter."""
    seq = []
    for chave, _p, _fn, default, obr in PERGUNTAS:
        if obr and default is None:
            seq.append({"area_lote_m2": "1200", "span": "10", "comprimento": "20",
                        "eave": "6", "v0": "40", "sigma_solo": "200"}[chave])
        else:
            seq.append("")          # Enter = default
    return seq


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        _cli()
