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
# veredito e DESCONHECIDO (None) e a folha sai como antes, byte-identica.
#
# Formas de resultado lidas (nunca decididas aqui):
#   - maiusculas: {"ATENDE": bool, "reprovados": [...]} (concreto, eletrico,
#     incendio, hidraulica, climatizacao, mezanino via galpao_turnkey._norm);
#   - minusculas do aco: {"atende_global"|"atende": bool, "falhas_verificacao":
#     [...]} (rodar_projeto.calcular/rodar_tudo). O `calcular` carimba o
#     veredito no spec (`estrutura.veredito_aco`, lido por
#     `veredito_de_spec_aco`) - o carimbo viaja do resultado, nunca de conta
#     refeita na folha.
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


def extrair_veredito(fonte):
    """(atende, reprovados) lidos da fonte, sem decidir nada.

    Devolve `(True|False|None, [gates])`. `None` = a fonte nao declara
    veredito (chaves ausentes ou valor None): a folha nao inventa um, sai
    como antes. `reprovados` vazio com `False` declara a REPROVA sem nomear
    gates (nunca omite o veredito).
    """
    if not isinstance(fonte, dict):
        return None, []
    if "ATENDE" in fonte:
        at = fonte.get("ATENDE")
        rep = fonte.get("reprovados") or []
        if isinstance(rep, (list, tuple)):
            gates = [str(x) for x in rep]
        else:
            gates = [str(rep)]
        return (None if at is None else bool(at)), gates
    if "atende_global" in fonte or "atende" in fonte:
        at = fonte.get("atende_global", fonte.get("atende"))
        falhas = fonte.get("falhas_verificacao",
                           fonte.get("falhas", fonte.get("reprovados", []))) or []
        if isinstance(falhas, (list, tuple)):
            gates = [str(x) for x in falhas]
        else:
            gates = [str(falhas)]
        return (None if at is None else bool(at)), gates
    return None, []


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
