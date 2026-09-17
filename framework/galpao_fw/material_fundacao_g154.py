# ============================================================================
# material_fundacao_g154.py - G154: O MATERIAL DA FUNDACAO QUE VEM DO MODELO
# (D102: default que decide veredito — declarar ou recusar).
#
# Medido por injecao (2026-09-17, antes de mudar; scripts em
# C:/Users/joseh/AppData/Local/Temp/opencode/med_g154_*.py):
# - bloco metalico n=2 (estaca_profunda, N=600): fck 25->15 MPa OK->REPROVA
#   (biela: sig 13,33 vs fcd1 13,66->8,56); fyk 500->250 MPa OK segue OK,
#   As 6,9->13,8 cm2 (quantidade, nao veredito); cobrimento 0,05->0,10 m:
#   h 0,445->0,495 m com d 0,375 inalterado (h = d+cob+emb, Q rigido) —
#   OK inalterado, muda geometria; phi_barra nao lido no bloco (bitola do
#   tirante detalhada, nao entrada) — nao se aplica.
# - sapata isolada predio (fundacao_sapata Parte B, B=2 L=2,5 h=0,5):
#   fck 25->15 MPa em N=1500 OK->REPROVA (u_cd 0,691->1,103, 19.5.3.1);
#   cobrimento 0,05->0,10 m em N=2000 OK->REPROVA (u_cd 0,922->1,041,
#   d 0,438->0,388); phi 12,5->25 mm em N=2120 OK->REPROVA
#   (u_cd 0,977->1,006); fyk 500->250 MPa OK segue OK em M=100..400
#   (As 11,1->22,2 .. 28,6->57,2 cm2; puncao MELHORA 0,133->0,112 com
#   mais aco) — quantidade, nao veredito.
# - sapata corrida casa (fundacao_sapata_corrida._parte_B, mesma Parte B):
#   mesma fisica da isolada (VIVO por construcao); no aprovado tipico o
#   SOLO governa (q=150/sigma=120: B 2,0 passa solo, concreto passa nos
#   dois fck) — o silencio continua defeito (D102) e sai aqui.
# - portas: spec metalico (PS.novo :125 escreve 25e3/500e3/0,05/0,0125
#   antes de qualquer resposta; wizard :317-343 nunca pergunta);
#   predio (spec_fundacao.get(fck, materiais[fck]) herda do predio
#   declarado); corrida (spec.get(fck, 25e3) cala 25 MPa).
#
# Regra por item (motivo escrito, sem valor novo arbitrado, sem trocar
# classe de agressividade):
# - fck, cobrimento, phi_barra: DECLARACAO com origem (modelo vs
#   declarado/herdado). Motivo: decidem veredito (medido acima) e o
#   numero do modelo (PS.novo) chegava a conta sem ninguem declarar.
#   O numero e mantido (nunca outro fck "melhor"); a origem viaja no
#   resultado, no memorial e na folha.
# - fyk: DECLARACAO com origem (mesmo caminho). Motivo: medido que muda
#   quantidade (As, massa de aco), nao veredito — declarar e o D102
#   para item que nao decide veredito mas decide compra.
# - bloco metalico phi_barra: TERCEIRO VALOR ("nao se aplica ao bloco",
#   declarado). Motivo: medido que a conta do bloco nao le phi de
#   entrada (bitola do tirante e detalhada).
#
# Portas de entrada (convencao 11): PS.novo (onde o numero nasce) +
# wizard.construir_spec (onde o declarado nasce) + to_rodar_params
# (passthrough) + rodar_galpao (porta direta) + fundacao_edificio
# (predio, com materiais declarados do predio) + fundacao_sapata_corrida
# (casa, sem 25 MPa calado). Uma fonte so aqui.
# ============================================================================
"""Material da fundacao sem default silencioso (G154, D102).

Fonte unica das origens declarado/modelo/herdado do quarteto
fck/fyk/cobrimento/phi_barra. O memorial e as folhas leem daqui.
STATELESS: funcoes puras.
"""

from __future__ import annotations

# Numeros mantidos — os mesmos que o codigo ja usava (nenhum arbitrado).
FCK_MODELO = 25e3
FYK_MODELO = 500e3
COBRIMENTO_MODELO = 0.05
PHI_BARRA_MODELO = 0.0125

CHAVES = ("fck", "fyk", "cobrimento", "phi_barra")

ORIGEM_MODELO = "modelo_PS_novo"
ORIGEM_DECLARADO = "declarado_no_spec"
ORIGEM_HERDADO_PREDIO = "herdado_material_predio_declarado"
ORIGEM_NAO_SE_APLICA = "nao_se_aplica"
# Specs antigos (JSON/projects sem _origem_material): o numero existe mas
# o nascimento nao foi registrado — tratar como modelo a confirmar
# (nunca comparar valor com 25e3: o usuario pode declarar 25, armadilha).
ORIGEM_MODELO_LEGADO = "modelo_legado_confirmar"


def _e_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def origens_de_spec(spec_fundacao):
    """Origem por chave lida de onde o numero nasceu.

    spec_fundacao com "_origem_material" (escrito por PS.novo e pelo
    wizard quando declara) -> a origem registrada. Sem a chave:
    numero presente = declarado legado (escrito a mao); ausente =
    modelo legado a confirmar (nunca comparar valor).
    """
    spec = spec_fundacao if isinstance(spec_fundacao, dict) else {}
    reg = spec.get("_origem_material")
    reg = reg if isinstance(reg, dict) else {}
    out = {}
    for chave in CHAVES:
        if reg.get(chave) in (ORIGEM_MODELO, ORIGEM_DECLARADO,
                              ORIGEM_HERDADO_PREDIO, ORIGEM_NAO_SE_APLICA,
                              ORIGEM_MODELO_LEGADO):
            out[chave] = reg[chave]
        elif chave in spec and _e_numero(spec[chave]):
            out[chave] = ORIGEM_DECLARADO
        else:
            out[chave] = ORIGEM_MODELO_LEGADO
    return out


def resolver_material(spec_fundacao, materiais_predio=None):
    """Quarteto com valor + origem, sem calar (G154, fonte unica).

    Precedencia por chave: numero no spec (com a origem de
    origens_de_spec) > material declarado do predio (herdado, dito) >
    modelo PS.novo (mantido, dito). Nenhum numero novo arbitrado:
    o modelo sao os mesmos FCK_MODELO/FYK_MODELO/etc.
    """
    spec = spec_fundacao if isinstance(spec_fundacao, dict) else {}
    mat = materiais_predio if isinstance(materiais_predio, dict) else {}
    origens = origens_de_spec(spec)
    padrao = {"fck": FCK_MODELO, "fyk": FYK_MODELO,
              "cobrimento": COBRIMENTO_MODELO, "phi_barra": PHI_BARRA_MODELO}
    out = {}
    for chave in CHAVES:
        if _e_numero(spec.get(chave)):
            out[chave] = float(spec[chave])
            out[chave + "_origem"] = origens[chave]
        elif _e_numero(mat.get(chave)):
            out[chave] = float(mat[chave])
            # herdado do predio declarado — mesmo quando o spec traz
            # _origem_material de modelo (o spec nao declarou, o predio sim).
            out[chave + "_origem"] = ORIGEM_HERDADO_PREDIO
        else:
            out[chave] = float(padrao[chave])
            # sem numero em nenhum lado: e o modelo (novo com registro,
            # ou legado sem registro) — nunca outro valor.
            out[chave + "_origem"] = (origens[chave]
                                      if origens[chave] in (ORIGEM_MODELO,
                                                            ORIGEM_MODELO_LEGADO)
                                      else ORIGEM_MODELO)
    out["origens"] = {c: out[c + "_origem"] for c in CHAVES}
    return out


def _fmt_origem(origem):
    return {"declarado_no_spec": "declarado no spec",
            "modelo_PS_novo": "modelo PS.novo (confirmar)",
            "modelo_legado_confirmar": "modelo (origem nao registrada, confirmar)",
            "herdado_material_predio_declarado":
                "herdado do material declarado do predio",
            "nao_se_aplica": "nao se aplica"}.get(origem, str(origem))


def linha_memorial(resolvido):
    """Linha que o memorial carimba (vem desta fonte so)."""
    if not isinstance(resolvido, dict):
        raise ValueError("resultado sem material resolvido (G154)")
    o = resolvido.get("origens") or {}
    return ("MATERIAL DA FUNDACAO (G154): fck=%.0f kN/m2 (%s) ; "
            "fyk=%.0f kN/m2 (%s) ; cobrimento=%.0f cm (%s) ; "
            "phi=%.1f mm (%s)"
            % (resolvido.get("fck", 0.0), _fmt_origem(o.get("fck")),
               resolvido.get("fyk", 0.0), _fmt_origem(o.get("fyk")),
               resolvido.get("cobrimento", 0.0) * 100.0,
               _fmt_origem(o.get("cobrimento")),
               resolvido.get("phi_barra", 0.0) * 1000.0,
               _fmt_origem(o.get("phi_barra"))))


def linha_folha(resolvido):
    """Linha curta que a folha carimba (fonte unica). None sem o que declarar."""
    if not isinstance(resolvido, dict):
        return None
    o = resolvido.get("origens") or {}
    partes = []
    for chave, rot in (("fck", "fck"), ("fyk", "fyk"),
                       ("cobrimento", "cob"), ("phi_barra", "phi")):
        org = o.get(chave)
        if org in (ORIGEM_MODELO, ORIGEM_MODELO_LEGADO):
            partes.append("%s modelo (confirmar)" % rot)
    if not partes:
        return None
    return "G154 material: " + " ; ".join(partes)


def _selftest():
    # modelo PS.novo simulado
    spec_mod = {"fck": 25e3, "fyk": 500e3, "cobrimento": 0.05,
                "phi_barra": 0.0125,
                "_origem_material": {c: ORIGEM_MODELO for c in CHAVES}}
    r = resolver_material(spec_mod)
    assert r["fck"] == 25e3 and r["origens"]["fck"] == ORIGEM_MODELO
    assert "modelo PS.novo" in linha_memorial(r)
    assert linha_folha(r) is not None and "G154" in linha_folha(r)
    # declarado no spec
    spec_dec = dict(spec_mod)
    spec_dec["fck"] = 30e3
    spec_dec["_origem_material"] = dict(spec_dec["_origem_material"])
    spec_dec["_origem_material"]["fck"] = ORIGEM_DECLARADO
    r2 = resolver_material(spec_dec)
    assert r2["fck"] == 30e3 and r2["origens"]["fck"] == ORIGEM_DECLARADO
    # ausente herda do predio declarado
    r3 = resolver_material({}, {"fck": 30e3, "fyk": 500e3})
    assert r3["fck"] == 30e3
    assert r3["origens"]["fck"] == ORIGEM_HERDADO_PREDIO
    assert "herdado" in linha_memorial(r3)
    # legado sem registro e com numero = declarado; sem numero = modelo legado
    r4 = resolver_material({"fck": 25e3})
    assert r4["origens"]["fck"] == ORIGEM_DECLARADO
    r5 = resolver_material({})
    assert r5["fck"] == 25e3 and r5["origens"]["fck"] == ORIGEM_MODELO_LEGADO
    assert linha_folha({"fck": 1, "origens": {c: ORIGEM_DECLARADO
                                              for c in CHAVES}}) is None
    print("material_fundacao_g154 self-test PASSED")


if __name__ == "__main__":
    _selftest()
