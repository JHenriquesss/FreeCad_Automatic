# ============================================================================
# veredito_folha_g152.py - FONTE UNICA do veredito que a FOLHA declara (G152)
# ----------------------------------------------------------------------------
# Medido (G152): `grep REPROVAD|NAO ATENDE` em `techdraw_*.py` e
# `prancha_svg_direta.py` dava 0, e o carimbo generico saia com
# `document_status` "PARA APROVACAO" qualquer que fosse o veredito. O veredito
# existia e era declarado FORA da folha (capa do caderno, adaptador com
# `native_atende`/`reprovados`). A folha de disciplina reprovada nao dizia
# que reprovou.
#
# Este modulo e a fonte unica da LEITURA do veredito para as folhas: todo
# `config_de_spec` (o lado lancador, fora do FreeCAD) chama `aplicar_a_cfg`
# com o RESULTADO da disciplina, e o cfg carrega `veredito_atende`,
# `veredito_reprovados`, `veredito_linha` e `veredito_status`. O lado de
# dentro do FreeCAD (carimbos, _anot, _bloco_texto) so LE essas chaves do
# cfg - nunca importa este modulo la dentro (o bootstrap do aco nem poe o
# galpao_fw no sys.path) e nunca decide gate: sem ATENDE no resultado, o
# veredito e DESCONHECIDO (None). G155 (folhas SVG do predio/casa): o
# parametro ausente (None) sai como antes, byte-identico; a fonte presente
# sem veredito declara a ausencia na folha, sem STATUS.
#
# Formas de resultado lidas (nunca decididas aqui):
#   - maiusculas: {"ATENDE": bool, "reprovados": [...]} (concreto, eletrico,
#     incendio, hidraulica, climatizacao, mezanino via galpao_turnkey._norm;
#     predio/casa: eletrica/hidraulica/incendio/estrutura via dimensiona);
#   - minusculas do aco: {"atende_global"|"atende": bool, "falhas_verificacao":
#     [...]} (rodar_projeto.calcular/rodar_tudo). O `calcular` carimba o
#     veredito no spec (`estrutura.veredito_aco`, lido por
#     `veredito_de_spec_aco`) - o carimbo viaja do resultado, nunca de conta
#     refeita na folha.
#   - G155 (predio/casa, sem copiar a semantica): {"gate": {"OK": bool,
#     "reprovados": [...]}} (fundacao_edificio.dimensiona: o veredito mora no
#     gate, nao em ATENDE); {"OK": bool, "reprovados"|"falhas"|"gates": [...]}
#     (piso, escada e pecas com OK direto); {"ok": bool, "errors":
#     [{"design_id": ...}], "designs": [{id, conductor.OK, protection.OK}]}
#     (circuits da eletrica residencial: o ok e os erros por design_id sao
#     produzidos pelo dimensionamento); {"ok": bool} (conferencia interna
#     da casa). Ordem fixa: ATENDE > atende_* > gate > OK > ok; fonte
#     presente sem nenhuma chave: a folha declara "VEREDITO NAO DISPONIVEL
#     NO RESULTADO" (decisao do backlog G155), sem STATUS; so o parametro
#     ausente (None) sai byte-identico.
# ============================================================================
"""Fonte unica do veredito declarado nas folhas (G152).

Le o veredito do RESULTADO (nunca decide gate) e entrega as quatro chaves
que o cfg carrega para dentro do FreeCAD. Puro e testavel sem FreeCAD.
"""

from __future__ import annotations


#: Carimbo de folha ATENDIDA (comportamento historico, mantido byte-identico).
STATUS_APROVADO = "PARA APROVACAO"

#: Carimbo de folha REPROVADA (G152: o carimbo declara o veredito).
STATUS_REPROVADO = "REPROVADO - VER MEMORIAL"

#: Linha da folha sem veredito no resultado (G155, decisao do backlog: a
#: disciplina sem veredito nao ganha veredito na folha - a folha declara a
#: ausencia; sem STATUS, carimbar seria decidir).
LINHA_SEM_VEREDITO = "VEREDITO NAO DISPONIVEL NO RESULTADO - VER MEMORIAL"


def _porta_recusa_demanda(erro):
    """Nome curto da recusa da demanda (G162), ou None.

    O modulo tem recusas nomeadas que partilham o codigo
    `motor_outside_table`: a variante sai da mensagem (bifasico, sem
    linha exata, quantidade acima de 10). Qualquer outra recusa do
    calculo vira `demanda:<code>`. Le, nunca decide.
    """
    if not isinstance(erro, dict):
        return None
    codigo = erro.get("code")
    import unicodedata as _ud162
    bruto = str(erro.get("message", erro.get("detail", "")) or "").lower()
    msg = "".join(c for c in _ud162.normalize("NFKD", bruto)
                  if not _ud162.combining(c))
    if codigo == "motor_outside_table":
        if "bifas" in msg:
            return "demanda-motor-bifasico"
        if "acima de 10" in msg:
            return "demanda-motor-qtd-acima-10"
        if "sem linha exata" in msg:
            return "demanda-motor-sem-linha"
        return "demanda-motor-outside-table"
    if codigo == "invalid_location_factor":
        return "demanda-fator-locacional"
    if isinstance(codigo, str) and codigo.strip():
        return "demanda-%s" % codigo.strip()
    return "demanda-recusa"


def gates_demanda(fonte):
    """Gates da demanda recusada lidos da fonte, sem decidir nada.

    Le `fonte["demand_errors"]` (a vertical eletrica grava ali as recusas
    de `calculate_residential_demand`, inclusive quando o numero falta)
    e, por robustez, `fonte["calculation"]["demand_errors"]` (o resultado
    eletrico inteiro passado direto). Sem a chave: [] (a folha sai como
    antes, byte-identica).
    """
    if not isinstance(fonte, dict):
        return []
    vistos = []

    def _colhe(lista):
        for erro in (lista or []):
            nome = _porta_recusa_demanda(erro)
            if nome and nome not in vistos:
                vistos.append(nome)

    derr = fonte.get("demand_errors")
    if isinstance(derr, list):
        _colhe(derr)
    calc = fonte.get("calculation")
    if isinstance(calc, dict):
        derr2 = calc.get("demand_errors")
        if isinstance(derr2, list):
            _colhe(derr2)
    return vistos


def extrair_veredito(fonte):
    """(atende, reprovados) lidos da fonte, sem decidir nada.

    Devolve `(True|False|None, [gates])`. `None` = a fonte nao declara
    veredito (chaves ausentes ou valor None): a folha nao inventa um, sai
    como antes. `reprovados` vazio com `False` declara a REPROVA sem nomear
    gates (nunca omite o veredito).

    G162 (eletrica residencial, sem copiar a semantica): a recusa da
    DEMANDA (erros de `calculate_residential_demand` gravados pela
    vertical em `demand_errors`, inclusive quando o numero falta) entra
    aqui como REPROVA nomeada (`demanda-motor-bifasico`,
    `demanda-motor-sem-linha`, `demanda-motor-qtd-acima-10`,
    `demanda-fator-locacional`, `demanda-<code>`). Sem a chave, a folha
    sai como antes (ATENDE byte-identico). A folha nunca decide gate.
    """
    def _completa(at, gates):
        dem = gates_demanda(fonte)
        if not dem:
            return at, gates
        todos = list(gates or [])
        for nome in dem:
            if nome not in todos:
                todos.append(nome)
        return False, todos

    if not isinstance(fonte, dict):
        return None, []
    if "ATENDE" in fonte:
        at = fonte.get("ATENDE")
        rep = fonte.get("reprovados") or []
        if isinstance(rep, (list, tuple)):
            gates = [str(x) for x in rep]
        else:
            gates = [str(rep)]
        return _completa(None if at is None else bool(at), gates)
    if "atende_global" in fonte or "atende" in fonte:
        at = fonte.get("atende_global", fonte.get("atende"))
        falhas = fonte.get("falhas_verificacao",
                           fonte.get("falhas", fonte.get("reprovados", []))) or []
        if isinstance(falhas, (list, tuple)):
            gates = [str(x) for x in falhas]
        else:
            gates = [str(falhas)]
        return _completa(None if at is None else bool(at), gates)
    # G155: fundacao do predio/casa - o veredito mora em fonte["gate"].
    gate = fonte.get("gate")
    if isinstance(gate, dict) and ("OK" in gate or "reprovados" in gate):
        ok = gate.get("OK")
        rep = gate.get("reprovados") or []
        if isinstance(rep, (list, tuple)):
            gates = [str(x) for x in rep]
        else:
            gates = [str(rep)]
        return _completa(None if ok is None else bool(ok), gates)
    # G155: piso/escada/peca com OK direto (sem ATENDE). So le quando ha
    # chave de gates ao lado ou valor booleano explícito; sem OK, desconhecido.
    if "OK" in fonte and isinstance(fonte.get("OK"), bool):
        rep = (fonte.get("reprovados", fonte.get("falhas",
               fonte.get("gates", []))) or [])
        if isinstance(rep, (list, tuple)):
            gates = [str(x) for x in rep]
        else:
            gates = [str(rep)]
        return _completa(bool(fonte.get("OK")), gates)
    # G155 (casa): conferencia interna com "ok" minusculo (conferencia_nbr5410,
    # esquema hidraulico com pressao OK por rede). Mesma semantica, sem decidir.
    # G155 (casa eletrica): o `circuits` do dimensionamento declara "ok" e os
    # erros por design_id (produzidos pelo calculo); os designs reprovados
    # trazem conductor/protection com OK False. Os gates nomeados sao os
    # design_id - lidos, nunca decididos aqui.
    if "ok" in fonte and isinstance(fonte.get("ok"), bool):
        rep = (fonte.get("reprovados", fonte.get("falhas",
               fonte.get("gates", []))) or [])
        if isinstance(rep, (list, tuple)):
            gates = [str(x) for x in rep]
        else:
            gates = [str(rep)]
        for erro in (fonte.get("errors") or []):
            if not isinstance(erro, dict):
                continue
            did = erro.get("design_id")
            if isinstance(did, str) and did.strip() and did not in gates:
                gates.append(did)
        for desenho in (fonte.get("designs") or []):
            if not isinstance(desenho, dict):
                continue
            cond = desenho.get("conductor")
            prot = desenho.get("protection")
            cok = cond.get("OK") if isinstance(cond, dict) else None
            pok = prot.get("OK") if isinstance(prot, dict) else None
            did = desenho.get("id")
            if ((cok is False or pok is False) and isinstance(did, str)
                    and did.strip() and did not in gates):
                gates.append(did)
        return _completa(bool(fonte.get("ok")), gates)
    return _completa(None, [])


def veredito_de_spec_aco(spec):
    """Veredito do aco lido do spec (carimbado pelo `calcular` a partir do
    resultado de `rodar_projeto.calcular`). Sem o carimbo, (None, []) - a
    folha nao inventa veredito para spec que nao passou pelo calculo."""
    try:
        est = (spec or {}).get("estrutura") or {}
        carimbo = est.get("veredito_aco")
    except AttributeError:
        return None, []
    if not isinstance(carimbo, dict):
        return None, []
    return extrair_veredito(carimbo)


def linha_veredito(atende, reprovados):
    """Linha de corpo da folha com o veredito, ou None.

    So a REPROVA gera linha (o ATENDE sai byte-identico, sem linha nova; o
    DESCONHECIDO nao inventa linha). Os gates reprovados sao nomeados - texto,
    nunca omissao.
    """
    if atende is not False:
        return None
    gates = [str(g) for g in (reprovados or []) if str(g).strip()]
    if gates:
        return ("VEREDITO: REPROVADO em %s - "
                "ver memorial e memoria de calculo." % (", ".join(gates)))
    return "VEREDITO: REPROVADO - ver memorial e memoria de calculo."


def status_carimbo(atende):
    """`document_status` do carimbo a partir do veredito lido."""
    if atende is False:
        return STATUS_REPROVADO
    return STATUS_APROVADO


def aplicar_a_cfg(cfg, fonte):
    """Carrega o veredito lido da fonte no cfg (lado lancador, fora do
    FreeCAD). Seta SEMPRE as quatro chaves (`veredito_atende`,
    `veredito_reprovados`, `veredito_linha`, `veredito_status`); anexa a
    linha ao `cfg["notas"]` SOMENTE quando ha REPROVA (o ATENDE e o
    DESCONHECIDO mantem as notas intactas - folha byte-identica). Devolve o
    proprio cfg."""
    atende, gates = extrair_veredito(fonte)
    linha = linha_veredito(atende, gates)
    cfg["veredito_atende"] = atende
    cfg["veredito_reprovados"] = list(gates)
    cfg["veredito_linha"] = linha
    cfg["veredito_status"] = status_carimbo(atende)
    if linha is not None and isinstance(cfg.get("notas"), list):
        cfg["notas"] = list(cfg["notas"]) + [linha]
    return cfg


def veredito_para_folha_svg(fonte):
    """(linha, status) para as folhas SVG puras do predio/casa (G155).

    Le da MESMA fonte (extrair_veredito) e devolve o MESMO texto
    (linha_veredito) e o MESMO status (status_carimbo): a folha nao decide
    nada, so posiciona as duas strings. ATENDE: (None, "PARA APROVACAO") -
    a folha sai byte-identica (nenhum texto novo). Fonte None (parametro
    ausente, caminho historico): idem. Fonte presente SEM veredito
    (decisao do backlog G155): (LINHA_SEM_VEREDITO, None) - a folha
    declara a ausencia, sem carimbar STATUS; o chamador so anexa o
    STATUS quando nao e None."""

    if fonte is None:
        return None, STATUS_APROVADO
    atende, gates = extrair_veredito(fonte)
    if atende is None:
        return LINHA_SEM_VEREDITO, None
    return linha_veredito(atende, gates), status_carimbo(atende)


def _altura_svg(svg):
    """Altura do cabecalho do SVG, ou None quando nao parseavel (G155)."""
    try:
        import xml.etree.ElementTree as _ET
        return float(_ET.fromstring(svg).get("height"))
    except (ValueError, TypeError, _ET.ParseError):
        return None


def _marca_colide(svg_teste):
    """True quando a marca nova (VEREDITO/STATUS) colide com rotulo (G155).

    Usa o estimador de colisoes de rotulos: a faixa fixa (20,20) atravessa
    o titulo centrado e longo de algumas folhas da casa."""
    try:
        from desenho_svg_base import colisoes_de_rotulo_svg as _col155
    except ImportError:
        return False
    for a, b in _col155(svg_teste):
        if ("VEREDITO" in a or "VEREDITO" in b
                or "STATUS" in a or "STATUS" in b):
            return True
    return False


def injetar_veredito_no_svg(svg, fonte):
    """Devolve o SVG com a linha do veredito (+ STATUS quando REPROVA) (G155).

    Le da fonte unica (veredito_para_folha_svg): fonte None ou ATENDE
    devolve o SVG intacto (byte-identico); fonte presente SEM veredito
    insere so a linha de indisponibilidade (sem STATUS); REPROVA insere
    a linha com os gates + STATUS antes do `</svg>`. A marca mora na
    primeira faixa livre (candidatas de cima para baixo + rodape),
    conferida pelo estimador - o titulo longo de algumas folhas alcanca
    a faixa fixa. A folha nunca decide gate."""

    if fonte is None or not isinstance(svg, str) or "</svg>" not in svg:
        return svg
    linha, status = veredito_para_folha_svg(fonte)
    if linha is None:
        return svg
    from xml.sax.saxutils import escape as _esc155

    def _marcas(y_lin, y_st):
        marca_linha = '<text x="20" y="%d" font-family="Arial" font-size="12" '\
            'font-weight="bold" fill="#b91c1c">%s</text>' % (
                y_lin, _esc155(linha))
        if status is None:
            return marca_linha
        return marca_linha + '<text x="20" y="%d" font-family="Arial" '\
            'font-size="11" font-weight="bold" fill="#b91c1c">%s</text>' % (
                y_st, _esc155("STATUS: " + status))

    candidatas = [(20, 38), (56, 74), (92, 110)]
    altura = _altura_svg(svg)
    if altura is not None and altura >= 200:
        candidatas.append((int(altura) - 38, int(altura) - 20))
    for y_lin, y_st in candidatas:
        tentativa = svg.replace("</svg>", _marcas(y_lin, y_st) + "</svg>")
        if not _marca_colide(tentativa):
            return tentativa
    return svg.replace("</svg>", _marcas(20, 38) + "</svg>")
