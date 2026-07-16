# ============================================================================
# escopo.py - ENVELOPE COBERTO + DETECCAO DE FORA-DE-ESCOPO + CARIMBO DE ART
# O framework dimensiona/desenha o galpao de aco REGULAR (portico de alma cheia
# ou tesoura, cobertura 1-2 aguas, ponte rolante NBR 8400, fundacao rasa/profunda,
# vento 6123, sismo estatico 15421 §9, fogo 14323 por barras). Alguns fenomenos
# ficam FORA do envelope por decisao de projeto (nao sao bugs). Este modulo:
#   - declara o que E coberto (envelope_coberto) para o memorial;
#   - detecta quando o projeto TOCA uma fronteira (avaliar) -> AVISO explicito,
#     em vez de entregar silenciosamente algo fora do metodo;
#   - emite o carimbo de responsabilidade (carimbo_art): o entregavel e
#     CONCEITUAL, pendente de revisao e ART/CREA do engenheiro responsavel.
# Ask-Do-Not-Invent e o gate legal: a ferramenta entrega pronto p/ revisao, NAO
# dispensa o engenheiro. Nenhum aviso aqui BLOQUEIA - todos vao para a memoria de
# calculo (auditoria/ART), como os avisos do projeto_spec.validar().
# ============================================================================
"""Envelope de escopo do framework + deteccao de fora-de-escopo + carimbo ART."""

from __future__ import annotations

PENDENTE = "__PENDENTE__"

# O que o framework cobre (declarado no memorial). Denso, verificavel no codigo.
ENVELOPE = [
    "Portico plano de aco: alma cheia (prismatico ou alma variavel/misula) e",
    "  tesoura trelicada; 1 ou multiplos vaos; base rotulada ou engastada.",
    "Cobertura 1-2 aguas; tercas Ue formadas a frio (NBR 14762, FSM); telha,",
    "  calha e condutores (NBR 10844).",
    "Acoes: peso proprio + sobrecarga + vento (NBR 6123, Cpe/Cpi + zonas locais)",
    "  + ponte rolante (NBR 8400) + sismo ESTATICO equivalente (NBR 15421 §9)",
    "  + incendio por barras isoladas (NBR 14323, ISO 834).",
    "Dimensionamento aco NBR 8800 (MAES B1/B2 2a ordem, Anexo D), ligacoes",
    "  parafusadas/soldadas, base + chumbadores (cone ACI 318).",
    "Fundacao rasa (sapata, incl. divisa/alavanca) e profunda (estaca: Aoki-",
    "  Velloso / Decourt / Teixeira, grupo, bloco, baldrame) - NBR 6122/6118.",
]

# Fronteiras do envelope. Cada regra: (id, predicado(spec,res)->bool, mensagem).
# predicado True = o projeto TOCA a fronteira -> emite o aviso. Nao bloqueia.
def _tem(spec, key):
    v = spec.get(key)
    return v not in (None, PENDENTE, {}, [])


def _regras():
    return [
        # incendio: verifica barras isoladas; flambagem GLOBAL do portico por
        # dilatacao termica em incendio NAO e coberta (fora de escopo p/ galpao
        # regular; exigiria analise termo-estrutural avancada).
        ("fogo_global",
         lambda s, r: _tem(s, "fogo"),
         "FOGO: verificado por BARRAS ISOLADAS (NBR 14323). Flambagem GLOBAL do "
         "portico por dilatacao termica em incendio NAO esta no escopo - se o "
         "projeto exigir, requer analise termo-estrutural dedicada."),
        # sismo: forcas horizontais equivalentes (estatico, §9). Analise modal
        # espectral (§10) ou historica no tempo (§11) fora de escopo.
        ("sismo_modal",
         lambda s, r: bool((r or {}).get("sismo_theta")),
         "SISMO: metodo das forcas horizontais equivalentes (ESTATICO, NBR 15421 "
         "§9). Analise MODAL espectral (§10) / historica (§11) fora de escopo - "
         "cobre galpao regular; estrutura irregular exige analise dinamica."),
        # ponte rolante: cargas e impacto automatizados; VERIFICACAO A FADIGA
        # (Anexo K NBR 8800) e apenas sinalizada, nao automatizada (depende da
        # categoria de detalhe de fabricacao).
        ("ponte_fadiga",
         lambda s, r: _tem(s, "ponte"),
         "PONTE ROLANTE: cargas/impacto (NBR 8400) automatizados. FADIGA (Anexo K "
         "NBR 8800) e SINALIZADA, nao automatizada - depende da categoria de "
         "detalhe de fabricacao; o engenheiro conclui a verificacao de fadiga."),
        # fundacao: quantitativo de aco de anteprojeto (~10-15% baixo sem ganchos/
        # arranques 22.6.4.1); detalhamento/ancoragem = executivo.
        ("fundacao_detalhe",
         lambda s, r: True,
         "FUNDACAO/CONCRETO: quantitativo de aco de ANTEPROJETO (ganchos, arranques "
         "e traspasses de 22.6.4.1 nao detalhados -> ~10-15% a menos). O "
         "detalhamento executivo das armaduras e responsabilidade do projetista."),
        # cobertura com mais de 2 aguas: o vento/tesoura e calibrado p/ 1-2 aguas.
        ("aguas",
         lambda s, r: isinstance(s.get("cobertura"), dict)
         and isinstance(s["cobertura"].get("aguas"), int)
         and s["cobertura"]["aguas"] > 2,
         "COBERTURA: >2 aguas foge da faixa calibrada (1-2 aguas) do vento/tesoura "
         "- revisar os coeficientes de forma e o esquema estrutural."),
    ]


def avaliar(spec, res=None):
    """Retorna lista [(id, mensagem)] das fronteiras de escopo que o projeto toca.
    Nao bloqueia - sao avisos para a memoria de calculo (auditoria/ART)."""
    out = []
    for rid, pred, msg in _regras():
        try:
            if pred(spec, res):
                out.append((rid, msg))
        except Exception:
            pass                     # regra defensiva: nunca derruba o pipeline
    return out


def carimbo_art(carimbo_versao="framework galpao_fw"):
    """Bloco de responsabilidade tecnica. O entregavel e CONCEITUAL: pronto para
    revisao e assinatura, NAO dispensa o engenheiro (ART/CREA - Lei 5194/66)."""
    return [
        "=" * 70,
        "RESPONSABILIDADE TECNICA - LEIA ANTES DE USAR",
        "=" * 70,
        f"{carimbo_versao}",
        "Este material e CONCEITUAL e gerado automaticamente. NAO substitui o",
        "projeto assinado: os calculos, o modelo 3D e as pranchas 2D devem ser",
        "REVISADOS e ASSINADOS por engenheiro civil/estrutural habilitado, com",
        "ART/RRT no CREA/CAU (Lei 5194/1966). Os dados de SITIO (solo/sondagem)",
        "e de FABRICANTE (ponte, protecao ao fogo, catalogo de perfis) sao de",
        "responsabilidade de quem os informou. Sem a revisao e a ART, este",
        "documento NAO tem valor de projeto executivo.",
        "=" * 70,
    ]


def relatorio_escopo(spec, res=None, carimbo_versao="framework galpao_fw"):
    """Texto: envelope coberto + fronteiras tocadas + carimbo ART. Vai para a
    memoria de calculo/relatorio consolidado."""
    L = ["=" * 70, "ESCOPO E LIMITES DO DIMENSIONAMENTO", "=" * 70,
         "Coberto por este framework:"]
    L += ["  " + s for s in ENVELOPE]
    tocadas = avaliar(spec, res)
    L += ["", "Fronteiras de escopo ATIVAS neste projeto (avisos, nao bloqueiam):"]
    if tocadas:
        for _rid, msg in tocadas:
            L.append("  [ESCOPO] " + msg)
    else:
        L.append("  (nenhuma - projeto dentro do envelope regular)")
    L += [""] + carimbo_art(carimbo_versao)
    return "\n".join(L)


def _selftest():
    import copy
    base = {"cobertura": {"aguas": 2}, "fogo": None, "ponte": None}
    # projeto regular: so a fronteira 'fundacao_detalhe' (sempre ativa) aparece
    t = avaliar(base, None)
    ids = {i for i, _ in t}
    assert ids == {"fundacao_detalhe"}, ids
    # com fogo + ponte + sismo -> as tres fronteiras acendem
    s = copy.deepcopy(base)
    s["fogo"] = {"TRRF_min": 30}
    s["ponte"] = {"Q": 50}
    r = {"sismo_theta": {"ok": True}}
    ids = {i for i, _ in avaliar(s, r)}
    assert {"fogo_global", "ponte_fadiga", "sismo_modal"} <= ids, ids
    # >2 aguas acende 'aguas'
    s2 = copy.deepcopy(base)
    s2["cobertura"]["aguas"] = 4
    assert "aguas" in {i for i, _ in avaliar(s2)}
    # carimbo ART sempre presente
    assert any("ART" in ln for ln in carimbo_art())
    assert "ESCOPO E LIMITES" in relatorio_escopo(base)
    print("escopo self-test PASSED")
    print(f"  regras: {len(_regras())} ; envelope: {len(ENVELOPE)} linhas")


if __name__ == "__main__":
    _selftest()
