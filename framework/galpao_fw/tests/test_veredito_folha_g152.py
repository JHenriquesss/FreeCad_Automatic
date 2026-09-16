"""G152 - a folha de disciplina reprovada que nao dizia que reprovou.

Medido (antes de mudar, com o resultado real na mao, sem mudar a conta):
  - `grep REPROVAD|NAO ATENDE` em `techdraw_*.py` e `prancha_svg_direta.py`: 0;
  - o carimbo generico saia com `document_status` "PARA APROVACAO"
    (`techdraw_exec._carimbo`) qualquer que fosse o veredito;
  - hidraulica/incendio/climatizacao/mezanino ATENDEM e a folha nao diz nada;
  - eletrico REPROVA de verdade (`reprovados=['cargas']`) e concreto REPROVA
    de verdade (`reprovados=['pilar']`) nos specs minimos - e a folha nao
    dizia nada, carimbo PARA APROVACAO (prova viva do defeito);
  - mezanino reprovado injetado (`viga_X/viga_Y/vigas`): so a pagina de
    armacao marcava por viga; formas e quadro nada;
  - o aco (`techdraw_exec.config_de_spec`) nem recebia o veredito.

Entregue (fonte unica `veredito_folha_g152.py`, lida do RESULTADO, nunca
decidida na folha):
  1. `aplicar_a_cfg` em todo `config_de_spec` (7 disciplinas); o aco viaja
     carimbado no spec pelo `calcular` (`estrutura.veredito_aco`, escrito do
     `res` - sem o carimbo, DESCONHECIDO e a folha sai como antes);
  2. carimbo declara (`REPROVADO - VER MEMORIAL` so na REPROVA; ATENDE e
     DESCONHECIDO mantem `PARA APROVACAO` - byte-identico);
  3. corpo declara nomeando os gates (`VEREDITO: REPROVADO em g1, g2 - ver
     memorial e memoria de calculo.`), nas notas do quadro, no titulo das
     vistas e no subtitulo + rodape STATUS de cada pagina da rota SVG.

Aceite: vermelho por injecao em cada disciplina com folha; ATENDE sem
nenhum REPROVAD (folha byte-identica); PNG olhado; `test_carimbo_mapa_g112`
verde (nenhum `drawing_number`/codigo de prancha muda aqui).
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import veredito_folha_g152 as V152


def _resultados_reais():
    """Resultados reais (a conta roda de verdade; a injecao copia em memoria,
    nunca muta o repo - convencao 2)."""
    import galpao_hidraulica as ghi
    import galpao_seguranca_incendio as gsi
    import galpao_climatizacao as gcl
    import galpao_mezanino as gmz
    import galpao_eletrico as ge
    import galpao_concreto as gc

    geo = {"L": 40.0, "W": 20.0, "H": 6.0}
    return {
        "hidraulica": ghi.rodar({
            "geometria": geo,
            "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                            "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}}),
        "incendio": gsi.rodar({
            "geometria": geo,
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0},
            "sprinklers": {"altura_estoque_m": 3.0}}),
        "climatizacao": gcl.rodar({"geometria": geo, "tipo": "galpao"}),
        "mezanino": gmz.rodar(
            {"geometria": {"comprimento": 40.0, "vao": 20.0,
                            "pe_direito": 6.0}}),
        "eletrico": ge.rodar({"geometria": geo}),
        "concreto": gc.rodar({"comprimento": 40.0, "vao": 20.0,
                               "pe_direito": 6.0}),
    }


def _cfgs(resultados, out="/tmp/g152"):
    """Cfgs a partir dos resultados (lado lancador, fora do FreeCAD)."""
    import techdraw_hidraulica as th
    import techdraw_incendio as ti
    import techdraw_climatizacao as tc
    import techdraw_mezanino as tm
    import techdraw_eletrico as te
    import techdraw_concreto as tco

    return {
        "hidraulica": (th.config_de_spec(resultados["hidraulica"], out, {}), th),
        "incendio": (ti.config_de_spec(resultados["incendio"], out, {}), ti),
        "climatizacao": (tc.config_de_spec(resultados["climatizacao"], out, {}), tc),
        "mezanino": (tm.config_de_spec(resultados["mezanino"], out, {}), tm),
        "eletrico": (te.config_de_spec(resultados["eletrico"], "/tmp/fc", out, {}), te),
        "concreto": (tco.config_de_spec(resultados["concreto"], "/tmp/fc", out, {}), tco),
    }


def _texto_cfg(cfg):
    """Todo texto que a folha imprime a partir do cfg (notas + quadros)."""
    partes = list(cfg.get("notas") or [])
    for chave in ("dim_rows", "resumo", "quadro_sap", "quadro_cargas",
                  "qdc_rows", "quadro_pilares", "quadro_vigas", "quadro_fund",
                  "quadro_linhas"):
        for linha in (cfg.get(chave) or []):
            partes.append(" | ".join(str(c) for c in
                                     (linha if isinstance(linha, (list, tuple))
                                      else [linha])))
    return "\n".join(partes)


def test_01_baseline_atende_sem_reprovad_e_carimbo_historico():
    """Baseline nos dois sentidos (convencao 1): com o veredito ATENDIDO (ou
    DESCONHECIDO no aco sem carimbo), nenhuma folha declara REPROVA e o
    carimbo e o historico - a cura muda este baseline junto."""
    import techdraw_exec as tex

    resultados = _resultados_reais()
    cfgs = _cfgs(resultados)
    lados = []
    for nome, (cfg, _td) in sorted(cfgs.items()):
        r = resultados[nome]
        if r["ATENDE"] is not True:
            # eletrico/concreto reprovam de verdade no spec minimo: a prova
            # viva de que a folha declara (test_02); aqui so registra.
            continue
        if cfg.get("veredito_atende") is not True:
            lados.append("%s: ATENDE real sem veredito_atende True" % nome)
        if cfg.get("veredito_linha") is not None:
            lados.append("%s: ATENDE com linha de veredito" % nome)
        if "REPROVAD" in _texto_cfg(cfg):
            lados.append("%s: ATENDE com REPROVAD no corpo" % nome)
        car = tex._carimbo(cfg, "TITULO", "PE-X-01", "S/ESC", "01/02")
        if car.get("document_status") != "PARA APROVACAO":
            lados.append("%s: ATENDE sem carimbo historico: %r"
                         % (nome, car.get("document_status")))
    # aco sem carimbo do calcular: DESCONHECIDO, folha como antes.
    spec = {"slug": "t", "descricao": "d", "autor": "a",
            "geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0,
                          "ridge": 6.6, "bay": 5.0}, "estrutura": {}}
    cfg_aco = tex.config_de_spec(spec, "/tmp/f.fcstd", "/tmp/x")
    if cfg_aco.get("veredito_atende") is not None:
        lados.append("aco sem carimbo devia ser DESCONHECIDO")
    if cfg_aco.get("veredito_linha") is not None:
        lados.append("aco sem carimbo devia sair sem linha")
    if tex._carimbo(cfg_aco, "T", "PE-01", "1:50", "01/09").get(
            "document_status") != "PARA APROVACAO":
        lados.append("aco sem carimbo devia manter PARA APROVACAO")
    assert not lados, "baseline G152 reprova:\n" + "\n".join(lados)


def test_02_vermelho_por_injecao_em_cada_disciplina_com_folha():
    """Injecao do veredito reprovado (copia em memoria, convencao 2): cada
    disciplina com folha declara no carimbo E no corpo, nomeando os gates -
    texto, nunca omissao (convencao 4)."""
    import techdraw_exec as tex

    resultados = _resultados_reais()
    lados = []
    pares = [("hidraulica", ["pressao_ponto", "calha"]),
             ("incendio", ["hidrantes_tipo", "reserva"]),
             ("climatizacao", ["duto_velocidade", "capacidade"]),
             ("mezanino", ["viga_X", "viga_Y", "vigas"]),
             ("eletrico", ["curto", "spda"]),
             ("concreto", ["pilar", "viga_cobertura"])]
    for nome, gates in pares:
        r2 = copy.deepcopy(resultados[nome])
        r2["ATENDE"] = False
        r2["reprovados"] = list(gates)
        solo = {nome: r2}
        base = _resultados_reais()
        base[nome] = r2
        cfgs = _cfgs(base)
        cfg, _td = cfgs[nome]
        if cfg.get("veredito_atende") is not False:
            lados.append("%s: injecao sem veredito_atende False" % nome)
        linha = cfg.get("veredito_linha") or ""
        for g in gates:
            if g not in linha:
                lados.append("%s: gate %r fora da linha %r" % (nome, g, linha))
        if "REPROVAD" not in linha:
            lados.append("%s: linha sem REPROVAD: %r" % (nome, linha))
        if (cfg.get("notas") or [""])[-1] != linha:
            lados.append("%s: linha fora das notas da folha" % nome)
        car = tex._carimbo(cfg, "TITULO", "PE-X-01", "S/ESC", "01/02")
        if car.get("document_status") != "REPROVADO - VER MEMORIAL":
            lados.append("%s: carimbo sem REPROVA: %r"
                         % (nome, car.get("document_status")))
        _ = solo
    # aco: injecao via carimbo no spec (copia em memoria).
    spec = {"slug": "t", "descricao": "d", "autor": "a",
            "geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0,
                          "ridge": 6.6, "bay": 5.0},
            "estrutura": {"veredito_aco": {
                "atende": False,
                "falhas_verificacao": ["portico_X", "terca"]}}}
    cfg_aco = tex.config_de_spec(copy.deepcopy(spec), "/tmp/f.fcstd", "/tmp/x")
    if tex._carimbo(cfg_aco, "T", "PE-01", "1:50", "01/09").get(
            "document_status") != "REPROVADO - VER MEMORIAL":
        lados.append("aco: carimbo sem REPROVA com veredito injetado")
    for g in ("portico_X", "terca"):
        if g not in (cfg_aco.get("veredito_linha") or ""):
            lados.append("aco: falha %r fora da linha" % g)
    assert not lados, "injecao G152 reprova:\n" + "\n".join(lados)


def test_03_fonte_unica_le_sem_decidir_gate():
    """A lente parte de onde o dado e PRODUZIDO (convencao 9): a fonte unica
    LE os dois dialetos de resultado e nunca decide gate - sem chave, sem
    veredito (o receptor declara a ausencia, nao um default). Literais
    escritos a mao (convencao 5: nada de conferir literal contra ele mesmo).
    """
    lados = []

    def _confere(fonte, at_esp, gates_esp):
        at, gates = V152.extrair_veredito(fonte)
        if at != at_esp or list(gates) != list(gates_esp):
            return ("extrair %r: esperado (%r, %r), saiu (%r, %r)"
                    % (fonte, at_esp, gates_esp, at, gates))
        return None

    for fonte, at_esp, gates_esp in [
            ({"ATENDE": True, "reprovados": []}, True, []),
            ({"ATENDE": False, "reprovados": ["a", "b"]}, False, ["a", "b"]),
            ({"ATENDE": False, "reprovados": []}, False, []),
            ({"ATENDE": None, "reprovados": []}, None, []),
            ({"atende_global": False, "falhas_verificacao": ["x"]}, False, ["x"]),
            ({"atende": True}, True, []),
            ({}, None, []),
            ({"rodou": True}, None, []),
            (None, None, []),
            ("texto", None, []),
    ]:
        erro = _confere(fonte, at_esp, gates_esp)
        if erro:
            lados.append(erro)
    if V152.linha_veredito(True, ["a"]) is not None:
        lados.append("ATENDE devia sair sem linha")
    if V152.linha_veredito(None, ["a"]) is not None:
        lados.append("DESCONHECIDO devia sair sem linha")
    linha = V152.linha_veredito(False, ["portico_X", "terca"])
    if linha != ("VEREDITO: REPROVADO em portico_X, terca - "
                 "ver memorial e memoria de calculo."):
        lados.append("linha com gates fora do contrato: %r" % (linha,))
    if V152.linha_veredito(False, []) != (
            "VEREDITO: REPROVADO - ver memorial e memoria de calculo."):
        lados.append("linha sem gates omite o veredito")
    if V152.status_carimbo(False) != "REPROVADO - VER MEMORIAL":
        lados.append("status da REPROVA fora do contrato")
    if V152.status_carimbo(True) != "PARA APROVACAO":
        lados.append("status do ATENDE mudou o historico")
    if V152.status_carimbo(None) != "PARA APROVACAO":
        lados.append("status DESCONHECIDO inventa veredito")
    # o aco sem carimbo nao inventa veredito (ausencia declarada, G149/D102).
    at, gates = V152.veredito_de_spec_aco({"estrutura": {}})
    if (at, gates) != (None, []):
        lados.append("aco sem carimbo devia ser (None, [])")
    assert not lados, "fonte unica G152 reprova:\n" + "\n".join(lados)


def test_04_rota_svg_declara_em_cada_pagina_e_atende_sem_reprovad(tmp_path):
    """A rota SVG (default, sem freecad.exe) exercita o caminho que falha
    (convencao 14): com a disciplina reprovada, CADA pagina declara o
    veredito e os gates; ATENDE sai sem nenhum REPROVAD."""
    import fitz
    import prancha_svg_direta as psd

    resultados = _resultados_reais()
    lados = []
    r2 = copy.deepcopy(resultados["hidraulica"])
    r2["ATENDE"] = False
    r2["reprovados"] = ["pressao_ponto", "calha"]
    out_rep = str(tmp_path / "rep")
    os.makedirs(out_rep, exist_ok=True)
    res = psd.montar_pranchas_rota_direta(r2, out_rep, "hidraulica", spec={})
    if not res.get("ok"):
        lados.append("rota SVG reprovada nao emite (ela deve emitir): %r" % (res,))
    else:
        for pdf in res["arquivos"]:
            with fitz.open(pdf) as d:
                for i, pag in enumerate(d):
                    txt = pag.get_text()
                    if "VEREDITO: REPROVADO em pressao_ponto, calha" not in txt:
                        lados.append("%s p%d sem o veredito com os gates"
                                     % (os.path.basename(pdf), i))
                    if "REPROVADO - VER MEMORIAL" not in txt:
                        lados.append("%s p%d sem o STATUS no rodape"
                                     % (os.path.basename(pdf), i))
    out_ok = str(tmp_path / "ok")
    os.makedirs(out_ok, exist_ok=True)
    res_ok = psd.montar_pranchas_rota_direta(resultados["hidraulica"], out_ok,
                                             "hidraulica", spec={})
    if not res_ok.get("ok"):
        lados.append("rota SVG ATENDE nao emite: %r" % (res_ok,))
    else:
        for pdf in res_ok["arquivos"]:
            with fitz.open(pdf) as d:
                for i, pag in enumerate(d):
                    if "REPROVAD" in pag.get_text():
                        lados.append("%s p%d ATENDE com REPROVAD" % (
                            os.path.basename(pdf), i))
    assert not lados, "rota SVG G152 reprova:\n" + "\n".join(lados)


def test_05_mezanino_tres_paginas_declaram_e_atende_sem_reprovad(tmp_path):
    """A MZ01 tem 3 paginas (G151): com o mezanino reprovado, formas, armacao
    e quadro declaram; ATENDE sai sem nenhum REPROVAD."""
    import fitz
    import galpao_mezanino as gmz

    resultados = _resultados_reais()
    lados = []
    r2 = copy.deepcopy(resultados["mezanino"])
    r2["ATENDE"] = False
    r2["reprovados"] = ["viga_X", "viga_Y", "vigas"]
    out_rep = str(tmp_path / "rep")
    os.makedirs(os.path.join(out_rep, "pranchas"), exist_ok=True)
    try:
        pdf = gmz.gerar_prancha_mezanino(r2, out_rep, spec={})
    except Exception as exc:  # noqa: BLE001
        lados.append("MZ01 reprovada nao emite (ela deve emitir): %r" % (exc,))
        pdf = None
    if pdf:
        with fitz.open(pdf) as d:
            if len(d) != 3:
                lados.append("MZ01 reprovada com %d paginas (esperado 3)"
                             % len(d))
            for i, pag in enumerate(d):
                txt = pag.get_text()
                if "VEREDITO: REPROVADO em viga_X, viga_Y, vigas" not in txt:
                    lados.append("MZ01 p%d sem o veredito com os gates" % i)
    out_ok = str(tmp_path / "ok")
    os.makedirs(os.path.join(out_ok, "pranchas"), exist_ok=True)
    try:
        pdf_ok = gmz.gerar_prancha_mezanino(resultados["mezanino"], out_ok,
                                            spec={})
    except Exception as exc:  # noqa: BLE001
        lados.append("MZ01 ATENDE nao emite: %r" % (exc,))
        pdf_ok = None
    if pdf_ok:
        with fitz.open(pdf_ok) as d:
            for i, pag in enumerate(d):
                if "REPROVAD" in pag.get_text():
                    lados.append("MZ01 ATENDE p%d com REPROVAD" % i)
    assert not lados, "MZ01 G152 reprova:\n" + "\n".join(lados)
