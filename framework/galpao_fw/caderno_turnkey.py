# ============================================================================
# caderno_turnkey.py - O QUE ESTE SCRIPT FAZ / MONTA
# CADERNO EXECUTIVO UNICO (PDF) do galpao TURNKEY: junta, num so PDF entregavel, as
# pranchas A1 de TODAS as disciplinas (concreto/aco/eletrico/incendio) que o
# orquestrador-mestre [[galpao-turnkey-orquestrador]] rodou, na ordem de um caderno:
#   1. CAPA CONSOLIDADA (projeto + veredito GLOBAL + geometria).
#   2. INDICE DE PRANCHAS (todas as folhas, por disciplina).
#   3. Por disciplina: uma folha DIVISORIA + as PE*.pdf daquela disciplina.
# Reusa o motor de mesclagem do dossie.py (PyMuPDF/fitz) - as pranchas vem do FreeCAD
# (cada vertical tem seu montar_pranchas); AQUI nada e' recalculado, so agregado.
#
# DUAS CAMADAS: `montar_caderno_de_pdfs` e' PURA (so fitz; testavel em CI com PDFs
# sinteticos); `montar_caderno` e' a orquestracao VIVA (dispara os montar_pranchas de
# cada disciplina no freecad.exe e depois mescla). O incendio nao tem 3D; eletrico e
# concreto precisam do montar_3d antes das pranchas.
# ============================================================================
"""Caderno executivo unico (PDF) do galpao turnkey: capa + indice + pranchas A1 de
todas as disciplinas, mescladas com PyMuPDF. Camada pura (merge) testavel em CI."""

from __future__ import annotations

import datetime
import glob
import os
import time


ROTULO = {"concreto": "ESTRUTURA DE CONCRETO (NBR 6118/6122)",
          "mezanino": "MEZANINO DE CONCRETO (NBR 6118, G20)",
          "aco": "ESTRUTURA DE ACO (NBR 8800/6123)",
          "eletrico": "INSTALACOES ELETRICAS (NBR 5410/14039/5419)",
          "incendio": "SEGURANCA CONTRA INCENDIO (NBR 10898/16820/17240/10897)",
          "climatizacao": "CLIMATIZACAO / HVAC (NBR 16401)",
          "hidraulica": "HIDRAULICA PREDIAL (NBR 5626:2020/8160/10844)",
          "coordenacao": "COORDENACAO - MODELO FEDERADO (BIM/IFC4)"}
ORDEM = ("concreto", "mezanino", "aco", "eletrico", "incendio", "climatizacao", "hidraulica",
         "coordenacao")


def _monotonic():
    """Relogio isolado para permitir testes deterministas do prazo global."""
    return time.monotonic()


def _remaining_timeout(deadline):
    """Retorna o tempo restante ou zero quando o prazo global terminou."""
    return max(0.0, deadline - _monotonic())


_ANCORA_ACO_SEG = 578.0
# D133/G109 (2026-09-11, galpao-ufpe 44x90 2 vaos, maquina 8 GB): executivo de
# aco ~578 s nas 16 pranchas medidas (PE01 187,7; PE02 58,8; PE03 211,9;
# PE04 15,4; PE06 6,4; PE07 7,5; PE08 28,6; PE09 7,6; PE10 12,8; PE11 8,6;
# PE12 10,7; PE13 12,0; PE14_CROQUIS 4,9; PE16 5,4; PE05 sem numero entao
# (+ PE05 ≈ 209 s medidos no G118; a ancora segue 578 ate o G114 decidir).
# G137 (D166, 2026-09-14): re-medido antes de mudar — soma do harness
# (tools_harness_aco_por_prancha.MEDIDOS_G109: 16 pranchas 578,3 s +
# PE05 209,4 s = 787,7 s) + modelo 3D ~210 s (D164, ~3,5 min) = ~998 s;
# D165 mediu 1038,9 s (3D+executivo, freecad sozinho) e 1186,4 s no pytest.
# A ancora segue 578 (referencia do peso 7,0); o _T_MEDIDO_SEG["aco"] passa
# a 787,7 (executivo) e o split 3D/executivo passa a proporcional medido.
# Compativel com os ~15 min do executivo em rodada (06-open-threads T13, a
# estimativa antiga de 900 s que a ancora usava ate o G113).
#: piso do peso: peso 0 daria share 0 e timeout 0 (reserva simbolica).
_PISO_PESO = 0.01


def peso_medido(t_seg):
    """Peso da etapa a partir do tempo MEDIDO, pela regra do G108 (G119).

    peso = 7,0 x t_seg / `_ANCORA_ACO_SEG`, com piso `_PISO_PESO`.

    G119 (auditoria do G114): `_ANCORA_ACO_SEG` era decorativa - escrita,
    documentada no comentario e lida por NINGUEM. Os pesos eram literais, e
    trocar a ancora nao mudava peso nenhum; o teste do G108 so conferia que
    a constante valia 578 (o literal contra ele mesmo) e procurava "900" no
    texto do arquivo. Agora a ancora sustenta os pesos de verdade: mude 578
    e os pesos derivados mudam junto.
    """
    return max(_PISO_PESO, round(7.0 * float(t_seg) / _ANCORA_ACO_SEG, 4))


#: tempos MEDIDOS por disciplina (s). So entra aqui o que foi cronometrado,
#: com a origem escrita. Disciplina sem medicao NAO ganha tempo inventado:
#: fica com peso literal e o motivo dito na entrada de `_STAGE_WEIGHTS`.
#: G137: o aco passa de 578 (16 pranchas sem PE05) a 787,7 (16 + PE05 209,4,
#: MEDIDOS_G109 G109+G118) — o peso deriva sozinho via peso_medido.
_T_MEDIDO_SEG = {
    "aco": 787.7,        # G137/D166: 578,3 (G109, 16 pranchas) + 209,4 (G118, PE05)
    "hidraulica": 0.56,  # D125/G104, rota SVG
    "incendio": 0.62,    # D125/G104
    "climatizacao": 0.57,  # D125/G104
    # G139/D167 (2026-09-14, galpao-tp-g95, 6 disciplinas, 3012 membros,
    # freecad.exe nesta maquina, processo reiniciado a cada amostra):
    # render federado 73,6 + 95,6 s; prancha formal 34,8 (1a, freecad morno
    # apos o render — fora) + 67,8 + 69,8 + 65,7 s (frias, ok=True, 2 PDFs).
    # O peso usa o MAXIMO (95,6 e 69,8): a 1a suite com a media estourou por
    # construcao (`timeout 62,4 s na prancha`, G102 sob carga) — a licao do
    # G137 vale para a coordenacao (prazo que nao cobre o medido estoura
    # sempre). Sem aco (5 disc, 767 membros): render 20,0 + prancha 15,2 s;
    # 4 leves (155 membros): 12,1 + 13,0 s. O lote cheio com aco e o que a
    # producao federada carrega.
    "coordenacao_render": 95.6,
    "coordenacao": 69.8,
}

#: 3D do aco medido (D164, modelo ~3,5 min = 210 s) — o dispatch divide o
#: stage proporcional ao medido (3D 210 / executivo 787,7), nunca meio a meio.
_T_MEDIDO_3D_ACO_SEG = 210.0

_STAGE_WEIGHTS = {
    # Aco executa calculo, modelo 3D e executivo no mesmo dispatch.
    "aco": peso_medido(_T_MEDIDO_SEG["aco"]),
    # G119: concreto e eletrico NUNCA foram cronometrados. O peso segue
    # literal, herdado do G108, e o motivo esta dito aqui em vez de um
    # t_medido inventado so para caber na formula (ausencia se declara).
    "concreto": 2.0,   # SEM MEDICAO: literal do G108
    "eletrico": 1.5,   # SEM MEDICAO: literal do G108
    # G108: pesos medidos, nunca palpite. Regra: peso = 7,0 x t_medido / 578 s
    # (ancora: executivo de aco ~578 s medidos, D133/G109; antes 900 s,
    # estimativa do 06-open-threads T13, corrigida no G114),
    # com piso 0,01 (reserva simbolica; peso 0 daria share 0 e timeout 0).
    # D125/G104 (galpao 40x20x6, rota SVG, processo novo): HID 0,56 s,
    # INC 0,62 s, CLI 0,57 s (era 15,25/21,09/13,52 s via freecad.exe);
    # corroborado em 2026-09-11 nesta maquina: 0,99/0,37/0,28 s.
    "hidraulica": peso_medido(_T_MEDIDO_SEG["hidraulica"]),    # 0,0068 -> piso
    "incendio": peso_medido(_T_MEDIDO_SEG["incendio"]),        # 0,0075 -> piso
    "climatizacao": peso_medido(_T_MEDIDO_SEG["climatizacao"]),  # 0,0069 -> piso
    # Mezanino: disciplina calculada sem emissor de prancha (G141: ok None
    # com MOTIVO_MEZANINO_SEM_PRANCHA, PE-MZ-01 pulada com motivo no laco;
    # antes "sem dispatch", isenta com motivo no G103); medido 2026-09-11:
    # 0,0003 s. Peso proporcional seria ~2e-6.
    "mezanino": 0.01,        # piso 0,01: reserva para nada vira quase nada
    # G139: pesos medidos, nunca palpite (convencao 8). Render 95,6 s ->
    # 1,1578; prancha 69,8 s -> 0,8453 (regra peso_medido, ancora 578 s;
    # maximos das amostras D167). Antes 0,5/0,75 literais (G108) que a
    # producao lia sem cronometro.
    "coordenacao_render": peso_medido(_T_MEDIDO_SEG["coordenacao_render"]),
    "coordenacao": peso_medido(_T_MEDIDO_SEG["coordenacao"]),
}


def _stage_timeout(deadline, cap, stages_remaining=1, *, weight=1.0,
                   total_weight=None):
    """Reserva prazo ponderado para a etapa e as etapas restantes.

    ``total_weight`` opcional preserva o comportamento linear de chamadas
    antigas; o caderno vivo usa pesos para acomodar dispatches de custo
    diferente sem alterar o prazo global.
    """
    remaining = _remaining_timeout(deadline)
    if remaining <= 0.0:
        return None
    denominator = (float(total_weight) if total_weight is not None
                   else float(max(1, int(stages_remaining))))
    denominator = max(denominator, 1e-9)
    share = remaining * float(weight) / denominator
    return min(float(cap), share)


def _total_peso(pendentes):
    """Soma dos pesos ainda pendentes (fonte unica da reserva; G114).

    O caderno vivo e o teste do G108 importam daqui — peso sem entrada cai
    no default 1,0, a mesma regra do `reserve_stage` interno.
    """
    return sum(_STAGE_WEIGHTS.get(etapa, 1.0) for etapa in pendentes)


def _fracao_reserva(nome, pendentes):
    """Fracao do prazo restante reservada a `nome` (peso/total; G114).

    Caminho real da reserva: `reserve_stage` interno reserva
    `_stage_timeout(deadline, cap, ..., weight, total_weight=_total_peso(...))`,
    logo a fracao e `weight/total`. O teste do G108 chama daqui, nunca
    recalcula a soma com formula propria (regra anti-tautologia do lote).
    """
    total = _total_peso(pendentes)
    if total <= 0.0:
        return 0.0
    return float(_STAGE_WEIGHTS.get(nome, 1.0)) / float(total)


def _timeout_status(timeout):
    return {
        "erro": "timeout global do caderno (%.3gs)" % float(timeout),
        "timeout": True,
    }


def _contains_timeout(value):
    if not isinstance(value, dict):
        return False
    if value.get("timeout") is True:
        return True
    return str(value.get("erro", "")).lower().startswith("timeout")


def _coletar_pdfs(out_dir, nome):
    """PDFs de pranchas de uma disciplina (out_dir/<nome>/pranchas/*.pdf), ordenados."""
    d = os.path.join(out_dir, nome, "pranchas")
    return sorted(glob.glob(os.path.join(d, "*.pdf")))


def _linhas_capa(R, spec):
    """Texto monoespacado da CAPA consolidada do caderno turnkey."""
    geo = R["geometria"]
    veredito = "ATENDE" if R["ATENDE"] else ("REPROVA -> " + ", ".join(R["reprovados"]))
    L = ["", "=" * 68, "",
         "        CADERNO EXECUTIVO - GALPAO INDUSTRIAL (TURNKEY)",
         "",
         "        %s" % spec.get("descricao", spec.get("slug", "galpao")),
         "        Galpao %.0f x %.0f m ; pe-direito %.1f m" % (
             geo["comprimento"], geo["vao"], geo["pe_direito"]),
         "", "=" * 68, "",
         "  Projeto:      %s" % spec.get("slug", "galpao"),
         "  Emissao:      %s" % datetime.date.today().strftime("%d/%m/%Y"),
         "  Disciplinas:  %s" % ", ".join(R["executadas"]),
         "  VEREDITO GLOBAL: %s" % veredito,
         "", "-" * 68, "  DISCIPLINAS:"]
    for nome in ORDEM:
        d = R["disciplinas"].get(nome)
        if d is None:
            continue
        if not d.get("rodou"):
            st = "PULADA (%s)" % (d.get("erro") or d.get("nota") or "nao executada")
        else:
            st = "ATENDE" if d["ATENDE"] else ("REPROVA -> " + ", ".join(d["reprovados"]))
        L.append("    - %-52s %s" % (ROTULO[nome], st))
    L.append("")
    return _virgula(L)


def _linhas_indice(pdfs_por_disciplina):
    """Texto do INDICE DE PRANCHAS (todas as folhas, por disciplina)."""
    L = ["", "=" * 68, "  INDICE DE PRANCHAS", "=" * 68, ""]
    n = 0
    for nome in ORDEM:
        pdfs = pdfs_por_disciplina.get(nome)
        if not pdfs:
            continue
        L.append("  %s" % ROTULO[nome])
        for pp in pdfs:
            n += 1
            L.append("    %02d.  %s" % (n, os.path.basename(pp)))
        L.append("")
    if n == 0:
        L.append("  (nenhuma prancha)")
    return L


def _linhas_clash(rep):
    """Texto do APENDICE DE COORDENACAO: interferencia ENTRE disciplinas (clash federado
    de galpao_turnkey.checa_interferencia_federada). Lista completa (o _add_paginas_texto
    pagina sozinho). Os conflitos sao CANDIDATOS a triagem, nao reprovacao de calculo."""
    n_rev = rep.get("n_revisar")
    n_esp = rep.get("n_esperado")
    clashes = rep.get("clashes") or []
    if n_rev is None:                                    # rep antigo sem triagem
        rev = [c for c in clashes if not c.get("esperado")]
        esp = [c for c in clashes if c.get("esperado")]
        n_rev, n_esp = len(rev), len(esp)
    else:
        rev = rep.get("revisar") or [c for c in clashes if not c.get("esperado")]
        esp = rep.get("esperados") or [c for c in clashes if c.get("esperado")]
    L = ["", "=" * 68,
         "  COORDENACAO - INTERFERENCIA ENTRE DISCIPLINAS (CLASH FEDERADO)",
         "=" * 68, "",
         "  %d elementos analisados ; %d conflitos entre disciplinas" %
         (rep.get("n_membros", 0), rep.get("n_clashes", 0)),
         "     -> %d A REVISAR (coordenacao real) + %d esperados (montagem)" %
         (n_rev, n_esp), ""]
    por = rep.get("por_par") or {}
    if por:
        L.append("  Por par de disciplinas:")
        for k, v in sorted(por.items()):
            L.append("    - %-30s %d" % (k, v))
        L.append("")

    def _tab(itens):
        out = ["  %-16s %-16s %-24s %11s" %
               ("PECA A", "PECA B", "DISCIPLINAS / TIPOS", "VOL (mm3)"),
               "  " + "-" * 66]
        for c in itens:
            rot = ("%s %s" % (c.get("disciplinas", ""), c.get("tipos", "")))[:24]
            out.append("  %-16s %-16s %-24s %11.0f" %
                       (str(c.get("a", ""))[:16], str(c.get("b", ""))[:16], rot,
                        c.get("vol_mm3", 0.0)))
        return out

    L.append("  [A REVISAR] conflitos de coordenacao real (eletrocalha/equipamento x")
    L.append("  estrutura). Verificar o leiaute e reposicionar:")
    L += _tab(rev) if rev else ["    (nenhum - nada a revisar)"]
    L.append("")
    L.append("  [ESPERADOS] montagem INTENCIONAL: aterramento/SPDA fixado a estrutura")
    L.append("  (NBR 5419 - descidas nas colunas, malha/hastes junto as fundacoes):")
    L += _tab(esp) if esp else ["    (nenhum)"]
    L.append("")
    return _virgula(L)


def _virgula(linhas):
    import re
    return [re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", str(x)) for x in linhas]


def _add_pagina_imagem(doc, png_path, titulo, subtitulo=""):
    """Adiciona uma pagina LANDSCAPE (A3) com um titulo no topo e a imagem PNG escalada
    p/ caber, preservando a proporcao. Best-effort: PNG ausente/invalido -> nao faz nada
    e retorna False. Usa PyMuPDF (fitz.insert_image)."""
    import fitz
    if not png_path or not os.path.exists(png_path):
        return False
    W, H = 1191.0, 842.0                                   # A3 paisagem (pt)
    margem, topo = 36.0, 90.0
    try:
        page = doc.new_page(width=W, height=H)
        page.insert_text((margem, 42), titulo, fontname="helv", fontsize=16)
        if subtitulo:
            page.insert_text((margem, 66), subtitulo, fontname="helv", fontsize=10)
        pix = fitz.Pixmap(png_path)
        iw, ih = float(pix.width), float(pix.height)
        aw, ah = W - 2 * margem, H - topo - margem
        esc = min(aw / iw, ah / ih) if iw and ih else 1.0
        w, h = iw * esc, ih * esc
        x0 = margem + (aw - w) / 2.0
        y0 = topo + (ah - h) / 2.0
        page.insert_image(fitz.Rect(x0, y0, x0 + w, y0 + h), filename=png_path)
        return True
    except Exception:
        return False


def montar_caderno_de_pdfs(pdfs_por_disciplina, out_pdf, R, spec, clash=None,
                           render_png=None):
    """PURO (so fitz): monta o caderno unico a partir de PDFs de pranchas JA gerados.
    capa + indice + [PRANCHA DE COORDENACAO: render do federado + apendice de clash] +
    (por disciplina: divisoria + pranchas). `clash` (opc) = dict de
    galpao_turnkey.checa_interferencia_federada; `render_png` (opc) = PNG isometrico do
    modelo federado (render_federado). Retorna {path, n_paginas, n_pranchas, disciplinas,
    faltando, n_clashes, render}."""
    import fitz
    from dossie import _add_paginas_texto

    faltando = []
    doc = fitz.open()
    _add_paginas_texto(doc, _linhas_capa(R, spec))
    _add_paginas_texto(doc, _linhas_indice(pdfs_por_disciplina))
    # PRANCHA DE COORDENACAO: a imagem do modelo federado (se houver) + a tabela de clash
    tem_render = False
    if render_png is not None:
        nrev = (clash or {}).get("n_revisar")
        sub = ("Modelo federado das disciplinas ; %s conflitos a revisar"
               % nrev if nrev is not None else "Modelo federado das disciplinas")
        tem_render = _add_pagina_imagem(
            doc, render_png, "PRANCHA DE COORDENACAO - MODELO FEDERADO", sub)
    if clash is not None:
        _add_paginas_texto(doc, _linhas_clash(clash))

    total = 0
    por_disc = {}
    for nome in ORDEM:
        pdfs = pdfs_por_disciplina.get(nome)
        if not pdfs:
            continue
        _add_paginas_texto(doc, ["", "=" * 70, "  " + ROTULO[nome], "=" * 70, ""])
        cont = 0
        for pp in pdfs:
            try:
                with fitz.open(pp) as pr:
                    doc.insert_pdf(pr)
                cont += 1
                total += 1
            except Exception as ex:
                faltando.append("%s (%s)" % (os.path.basename(pp), ex))
        por_disc[nome] = cont
    if total == 0:
        faltando.append("pranchas (nenhum PDF de disciplina)")

    n_pag = doc.page_count
    doc.save(out_pdf, garbage=3, deflate=True)
    doc.close()
    return {"path": out_pdf, "n_paginas": n_pag, "n_pranchas": total,
            "disciplinas": por_disc, "faltando": faltando,
            "n_clashes": (clash or {}).get("n_clashes"), "render": tem_render}


# ------------------------------------------------------------- orquestracao VIVA
MOTIVO_EXECUTIVO_ACO_FORA = (
    "executivo de aco nao solicitado nesta rodada (opcao executivo_aco=False, "
    "D165): calculo, memorial e modelo 3D do aco rodam; as pranchas TechDraw "
    "do aco nao sao geradas")

MOTIVO_COORDENACAO_RECORTE_1 = (
    "coordenacao nao emitida nesta rodada: recorte de 1 disciplina "
    "(G139) — a prancha formal PE-CD-01 requer >= 2 disciplinas executadas; "
    "a coordenacao sai como matriz (coordination-matrix) + pagina do caderno")

MOTIVO_MEZANINO_SEM_PRANCHA = (
    "mezanino calculado sem prancha dedicada nesta rodada (G141): "
    "laje+vigas+pilares dimensionados no memorial e federados no BIM "
    "(membros M-); sem emissor TechDraw ligado ao hook, a PE-MZ-01 sai "
    "pulada com motivo no laco do galpao")


def _dispatch_pranchas(nome, r_disc, disc_out, sub_spec, freecad_exe, timeout,
                       executivo_aco=True):
    """Dispara o montar_pranchas da disciplina (freecad.exe). eletrico/concreto
    precisam do montar_3d antes (a prancha e' vista do 3D); incendio nao (esquema);
    aco vai pelo pipeline proprio (rodar_projeto.rodar_tudo: calc + 3D + executivo)
    que escreve as PE*.pdf em disc_out/pranchas. Retorna o dict de status.
    D165: executivo_aco=False roda o aco sem o executivo e devolve o status
    "nao solicitado" (ok None, sem erro): ausencia declarada, nao falha."""
    if nome == "aco":
        import rodar_projeto as RP
        stage_timeout = max(0.01, float(timeout))
        # G137: split proporcional ao MEDIDO (3D 210 s / executivo 787,7 s),
        # nunca meio a meio — meio a meio dava 459 s ao executivo dentro de
        # 1200 s e estourava por construcao (D164/D165).
        _t3d = float(_T_MEDIDO_3D_ACO_SEG)
        _tex = float(_T_MEDIDO_SEG["aco"])
        _frac3d = _t3d / (_t3d + _tex) if (_t3d + _tex) > 0 else 0.5
        timeout_3d = stage_timeout * _frac3d
        timeout_exec = stage_timeout - timeout_3d
        r = RP.rodar_tudo(dict(sub_spec or {}), out_dir=disc_out, com_3d=True,
                          com_executivo=bool(executivo_aco), gerar_pdf=True,
                          gerar_dossie=False, verbose=False,
                          timeout_3d=timeout_3d, timeout_exec=timeout_exec)
        atende = r.get("atende") if isinstance(r, dict) else None
        if not executivo_aco:
            return {"ok": None, "nao_solicitado": True,
                    "executivo": {"nao_solicitado": MOTIVO_EXECUTIVO_ACO_FORA},
                    "atende": atende}
        ex = (r.get("executivo") if isinstance(r, dict) else None) or {}
        return {"ok": bool(ex.get("ok")), "executivo": ex, "atende": atende}
    if nome == "incendio":
        import galpao_seguranca_incendio as gsi
        return gsi.montar_pranchas(r_disc, disc_out, spec=sub_spec,
                                   freecad_exe=freecad_exe, timeout=timeout)
    if nome == "hidraulica":
        import galpao_hidraulica as ghi
        return ghi.montar_pranchas(r_disc, disc_out, spec=sub_spec,
                                   freecad_exe=freecad_exe, timeout=timeout)
    if nome == "climatizacao":
        import galpao_climatizacao as gcl
        return gcl.montar_pranchas(r_disc, disc_out, spec=sub_spec,
                                   freecad_exe=freecad_exe, timeout=timeout)
    if nome == "eletrico":
        import galpao_eletrico as ge
        m = ge.montar_3d(r_disc, disc_out, headless=True, timeout=min(timeout, 600))
        fcstd = (m.get("result") or {}).get("fcstd") or m.get("fcstd")
        if not fcstd or not os.path.exists(fcstd):
            return {"erro": "montar_3d eletrico nao gerou FCStd", "detalhe": m}
        return ge.montar_pranchas(r_disc, disc_out, fcstd, spec=sub_spec,
                                  freecad_exe=freecad_exe, timeout=timeout)
    if nome == "concreto":
        import galpao_concreto as gc
        m = gc.montar_3d(r_disc, disc_out, headless=True, timeout=min(timeout, 600))
        fcstd = (m.get("result") or {}).get("fcstd") or m.get("fcstd")
        if not fcstd or not os.path.exists(fcstd):
            return {"erro": "montar_3d concreto nao gerou FCStd", "detalhe": m}
        return gc.montar_pranchas(r_disc, disc_out, fcstd, spec=sub_spec,
                                  freecad_exe=freecad_exe, timeout=timeout)
    if nome == "mezanino":
        # G141: disciplina calculada sem dispatch de pranchas - ausencia
        # declarada (ok None, sem erro), nunca falha; o laco do galpao
        # nomeia a PE-MZ-01 pulada com o motivo.
        return {"ok": None, "nao_solicitado": MOTIVO_MEZANINO_SEM_PRANCHA}
    return {"erro": "disciplina sem dispatch de pranchas: %s" % nome}


def montar_caderno(spec, out_dir, disciplinas=None, freecad_exe=None, timeout=2100,
                   R=None, turnkey_result=None, executivo_aco=True):
    """VIVO: roda o turnkey (ou reusa o ja calculado), dispara as pranchas de
    cada disciplina executada (freecad) e mescla tudo num CADERNO unico.
    `disciplinas` (opc) restringe o subconjunto (ex. ['incendio']). O timeout
    e um prazo global da montagem: cada etapa recebe somente o tempo
    restante, e as etapas que nao couberem sao registradas como timeout
    antes da mesclagem do resultado parcial.

    G137 (D166): default 1200 -> 2100 s. Medido: aco 1038,9 s sozinho
    (D165, 3D+executivo) + resto 536,3 s sem aco (G102/D165) = 1575 s;
    2100 da folga ~33 % para variacao de maquina (D165 deu 1186 s no
    pytest contra 1038 na referencia). COMO-RODAR ja pedia >= 1800 para o
    lote cheio; sem aco o portao rapido segue em ~536 s (nao usa o teto).

    G114: `R` (alias `turnkey_result`) reusa o resultado que o adaptador do
    galpao ja tem do hook (`_run_turnkey` -> `tk.rodar`) e NAO recalcula.
    Sem ele, chama `tk.rodar(spec, out_dir)` uma vez (comportamento antigo).
    O resultado e identico (mesmas pranchas, mesmo caderno): o `R` so entra
    como leitura (`executadas`, `disciplinas[*].raw`, `geometria`, `ATENDE`).
    `res["turnkey_reuso"]` diz se reusou (portao G114 conta `tk.rodar` por
    injecao: com reuso, zero chamadas).
    """
    import galpao_turnkey as tk
    timeout = float(timeout)
    started = _monotonic()
    deadline = started + max(0.0, timeout)
    if R is None:
        R = turnkey_result
    turnkey_reuso = isinstance(R, dict) and all(
        k in R for k in ("executadas", "disciplinas", "geometria", "ATENDE"))
    if not turnkey_reuso:
        R = tk.rodar(spec, out_dir)
    else:
        turnkey_reuso = True
    alvo = [n for n in R["executadas"] if (disciplinas is None or n in disciplinas)]
    pending_stages = list(alvo)
    # G139: a coordenacao e de quem RODOU (o recorte), nao de quem existe no
    # R. Com >= 2 disciplinas no alvo, render + prancha formal entram na
    # reserva com peso medido; com 1, seguem fora com motivo escrito
    # (MOTIVO_COORDENACAO_RECORTE_1). Antes: o hook sempre passava o recorte
    # e a prancha so saia com disciplinas=None — PE-CD-01 nunca emitida.
    tem_coordenacao = len(alvo) >= 2
    if tem_coordenacao:
        pending_stages.insert(0, "coordenacao_render")
        pending_stages.insert(1, "coordenacao")

    def reserve_stage(name, cap):
        if name not in pending_stages:
            return None
        total_weight = _total_peso(pending_stages)
        value = _stage_timeout(
            deadline, cap, len(pending_stages),
            weight=_STAGE_WEIGHTS.get(name, 1.0),
            total_weight=total_weight)
        pending_stages.remove(name)
        return value

    status = {}
    pdfs_por_disciplina = {}

    # PRANCHA DE COORDENACAO: clash (interferencia entre disciplinas) + RENDER isometrico
    # do modelo federado + PRANCHA A1 TechDraw formal (planta/elevacao + quadro de clash).
    # G139: so com >= 2 disciplinas NO ALVO (o recorte); falha isolada nao
    # derruba o caderno; recorte de 1 segue sem, com motivo escrito.
    clash = None
    render_png = None
    if tem_coordenacao:
        try:
            clash = tk.checa_interferencia_federada(R, spec)
        except Exception:
            clash = None
        try:                                              # render 3D (freecad.exe grafico)
            render_timeout = reserve_stage("coordenacao_render", min(timeout, 600))
            if render_timeout is None:
                status["coordenacao_render"] = _timeout_status(timeout)
            else:
                rr = tk.render_federado(
                    R, out_dir, spec=spec, freecad_exe=freecad_exe,
                    timeout=render_timeout)
                vistas = (rr or {}).get("vistas") or []
                render_png = next((v for v in vistas if "isometrica" in v), None)
        except Exception:
            render_png = None
        try:                                              # prancha A1 formal de coordenacao
            coord_out = os.path.join(out_dir, "coordenacao")
            coord_timeout = reserve_stage("coordenacao", min(timeout, 600))
            if coord_timeout is None:
                status["coordenacao"] = _timeout_status(timeout)
            else:
                status["coordenacao"] = tk.montar_prancha_coordenacao(
                    R, coord_out, spec=spec, clash=clash,
                    freecad_exe=freecad_exe, timeout=coord_timeout)
                pdfs_coord = _coletar_pdfs(out_dir, "coordenacao")
                if pdfs_coord:
                    pdfs_por_disciplina["coordenacao"] = pdfs_coord
        except Exception as ex:
            status["coordenacao"] = {"erro": "%s: %s" % (type(ex).__name__, ex)}
    else:
        status["coordenacao"] = {"ok": None, "nao_solicitado": MOTIVO_COORDENACAO_RECORTE_1}

    for nome in alvo:
        disc_out = os.path.join(out_dir, nome)
        os.makedirs(disc_out, exist_ok=True)
        r_disc = R["disciplinas"][nome].get("raw")
        stage_timeout = reserve_stage(nome, timeout)
        if stage_timeout is None:
            status[nome] = _timeout_status(timeout)
        else:
            try:
                status[nome] = _dispatch_pranchas(
                    nome, r_disc, disc_out, spec.get(nome), freecad_exe,
                    stage_timeout, executivo_aco=executivo_aco)
            except Exception as ex:
                status[nome] = {"erro": "%s: %s" % (type(ex).__name__, ex)}
        pdfs_por_disciplina[nome] = _coletar_pdfs(out_dir, nome)

    out_pdf = os.path.join(out_dir, "CADERNO-EXECUTIVO-%s.pdf" % spec.get("slug", "galpao"))
    res = montar_caderno_de_pdfs(pdfs_por_disciplina, out_pdf, R, spec, clash=clash,
                                 render_png=render_png)
    res["status"] = status
    res["ATENDE"] = R["ATENDE"]
    res["timeout_seconds"] = timeout
    res["elapsed_seconds"] = max(0.0, _monotonic() - started)
    res["timed_out"] = any(_contains_timeout(item) for item in status.values())
    res["turnkey_reuso"] = bool(turnkey_reuso)
    res["executivo_aco"] = bool(executivo_aco)
    return res


def _pdf_dummy(path, texto):
    """Cria um PDF A1 minimo (1 pagina) - so p/ testar a mesclagem sem FreeCAD."""
    import fitz
    doc = fitz.open()
    pg = doc.new_page(width=2384.0, height=1684.0)          # A1 (pt)
    pg.insert_text((100, 100), texto, fontsize=40)
    doc.save(path)
    doc.close()
    return path


def _selftest():
    import tempfile
    out = tempfile.mkdtemp(prefix="caderno_")
    # 2 disciplinas com pranchas sinteticas
    for nome, folhas in (("eletrico", ["PE-EL-01", "PE-EL-02"]),
                         ("incendio", ["PE-INC-01", "PE-INC-02"])):
        prd = os.path.join(out, nome, "pranchas")
        os.makedirs(prd, exist_ok=True)
        for f in folhas:
            _pdf_dummy(os.path.join(prd, f + ".pdf"), f)
    pdfs = {"eletrico": _coletar_pdfs(out, "eletrico"),
            "incendio": _coletar_pdfs(out, "incendio")}
    R = {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
         "executadas": ["eletrico", "incendio"], "reprovados": [], "ATENDE": True,
         "disciplinas": {"eletrico": {"rodou": True, "ATENDE": True, "reprovados": []},
                         "incendio": {"rodou": True, "ATENDE": True, "reprovados": []}}}
    res = montar_caderno_de_pdfs(pdfs, os.path.join(out, "CADERNO.pdf"),
                                 R, {"slug": "t", "descricao": "teste"})
    assert os.path.exists(res["path"]) and res["n_pranchas"] == 4, res
    assert res["disciplinas"] == {"eletrico": 2, "incendio": 2}
    # capa (>=1 texto) + indice (>=1) + 2 divisorias + 4 pranchas -> varias paginas
    assert res["n_paginas"] >= 6, res["n_paginas"]
    import fitz
    with fitz.open(res["path"]) as d:
        capa = d[0].get_text()
    assert "CADERNO EXECUTIVO" in capa and "VEREDITO GLOBAL: ATENDE" in capa
    print("caderno_turnkey self-test PASSED")
    print("  paginas=%d ; pranchas=%d ; faltando=%s" % (
        res["n_paginas"], res["n_pranchas"], res["faltando"]))


if __name__ == "__main__":
    _selftest()
