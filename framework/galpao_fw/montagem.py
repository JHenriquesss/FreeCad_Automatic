# ============================================================================
# montagem.py - PLANO DE MONTAGEM / ESCORAMENTO (erection plan) do galpao.
#
# Torna EXPLICITA a fase de obra que a NBR 8800 exige documentar mas que o
# projeto de peca (dimensionamento) nao cobre: sequencia de icamento,
# estabilidade do conjunto PARCIALMENTE montado, estaiamento provisorio e
# selecao do guindaste. Modulo PURO (headless), SI (m, kN, kg).
#
# BASE NORMATIVA (conferida no NotebookLM contra os PDFs):
#   - NBR 8800 1.10: aspectos de montagem NAO prescritos -> AISC 303 (Code of
#     Standard Practice for Steel Buildings and Bridges).
#   - NBR 8800 4.2.6: quando o metodo de montagem e condicionante, o projeto deve
#     indicar os PONTOS DE ICAMENTO, os PESOS das pecas e COEFICIENTES DE IMPACTO
#     adequados ao equipamento (guindaste).
#   - NBR 8800 4.4 / 4.3.2: os DESENHOS DE MONTAGEM devem indicar todos os
#     elementos permanentes OU TEMPORARIOS essenciais a integridade da estrutura
#     parcialmente construida, e a sequencia de ligacoes importantes.
#   - NBR 8800 4.9.6.5: combinacao de CONSTRUCAO -> majoracao gamma_f3 = 1,30.
#   - NBR 8800 12.3.2.1: "deve ser usado contraventamento temporario, sempre que
#     necessario, para absorver todas as forcas a que a estrutura possa estar
#     sujeita durante a construcao, incluindo as decorrentes de vento e
#     equipamentos" e permanecer ate a seguranca estar garantida.
#   - NBR 8800 12.3.2.2: o conjunto parcial deve estar parafusado/soldado com
#     seguranca (acao permanente + vento + acoes de montagem) ANTES de soltar do
#     equipamento de icamento.
#   - NBR 8800 12.3.3.1.1: prumo de montagem <= max(H/500 ; 5 mm), com desvio
#     global limitado a 25 mm.
#   - NBR 8800 4.12.6: escoras horizontais podem ser pecas DEFINITIVAS usadas
#     provisoriamente (terca, tesoura), desde que ancoradas.
#   - Bellei 7.6.4: sequencia logica (base -> aprumar -> contraventar -> vigas ->
#     secundarias -> conferir -> torquear); comecar pela extremidade mais
#     inacessivel recuando o guindaste; galpoes LINEARES sao instaveis ate os
#     contraventamentos definitivos -> "estais provisorios" (cabos de aco
#     ancorados no solo/base) que so saem com a estrutura estavel.
#
# NAO consta nas fontes (marcado A CONFIRMAR, NUNCA inventado):
#   - Angulo do cabo de estai (pratica de rigging).
#   - Vento de montagem quantitativo (periodo de retorno reduzido da NBR 6123,
#     fora desta base) -> default = vento de PROJETO integral (conservador).
#   - Coeficiente de impacto do guindaste (depende do equipamento, 4.2.6).
#   - Fator de seguranca do cabo/ancoragem (norma de cabos de aco).
# ============================================================================
"""Plano de montagem / escoramento do galpao (NBR 8800 12.3 + AISC 303 + Bellei)."""

from __future__ import annotations

import math

RHO_ACO = 7850.0                 # densidade do aco (kg/m3)
GAMMA_CONSTRUCAO = 1.30          # NBR 8800 4.9.6.5 (combinacao de construcao)
COEF_IMPACTO_MONTAGEM = 1.10     # default A CONFIRMAR c/ equipamento (NBR 8800 4.2.6)
G = 9.80665                      # m/s2


def tolerancia_prumo_montagem(H_mm):
    """Prumo maximo admissivel na montagem de uma coluna de altura H (NBR 8800
    12.3.3.1.1): max(H/500 ; 5 mm), com desvio GLOBAL da estrutura limitado a
    25 mm. Retorna {tol_mm, criterio, global_mm}."""
    tol = max(H_mm / 500.0, 5.0)
    crit = "H/500 = %.1f mm" % (H_mm / 500.0) if H_mm / 500.0 >= 5.0 else "5 mm (piso)"
    return {"tol_mm": round(tol, 1), "criterio": crit, "global_mm": 25.0}


def peca_mais_pesada(pecas, rafter_pre_montado=True):
    """Peca mais pesada a icar. `pecas` = lista de dicts com 'marca','peso_unit_kg'
    (do romaneio/por_marca). Se rafter_pre_montado, considera tambem a viga
    completa pre-montada no solo (2 meias-aguas da mesma marca V*) - pratica comum
    que dobra o peso de icamento e costuma governar a escolha do guindaste.
    Retorna {marca, peso_kg, descricao}."""
    if not pecas:
        return {"marca": "-", "peso_kg": 0.0, "descricao": "sem dados de peca"}
    cand = []
    for p in pecas:
        w = float(p.get("peso_unit_kg") or 0.0)
        cand.append((w, p.get("marca", "-"), "peca isolada"))
        if rafter_pre_montado and str(p.get("marca", "")).startswith("V"):
            cand.append((2.0 * w, p.get("marca", "-"),
                         "viga completa pre-montada no solo (2 meias-aguas)"))
    w, mk, desc = max(cand)
    return {"marca": mk, "peso_kg": round(w, 1), "descricao": desc}


def guindaste_requerido(peso_peca_kg, raio_m, altura_ic_m,
                        coef_impacto=COEF_IMPACTO_MONTAGEM):
    """Requisito do guindaste para o icamento da peca mais pesada (NBR 8800 4.2.6).
    Aplica o coeficiente de impacto ao peso e devolve o MOMENTO DE CARGA
    (P_ic[t] x raio[m], t.m) - grandeza pela qual as tabelas de carga do guindaste
    sao lidas (a capacidade cai com o raio). Nao seleciona MODELO (A CONFIRMAR:
    equipamento e raio dependem do acesso ao canteiro)."""
    p_ic_kg = peso_peca_kg * coef_impacto
    p_ic_t = p_ic_kg / 1000.0
    momento = p_ic_t * raio_m                       # t.m
    return {
        "peso_peca_kg": round(peso_peca_kg, 1),
        "coef_impacto": coef_impacto,
        "peso_icamento_kg": round(p_ic_kg, 1),
        "peso_icamento_t": round(p_ic_t, 3),
        "raio_m": raio_m,
        "altura_icamento_m": altura_ic_m,
        "momento_carga_tm": round(momento, 2),
        "obs": "A CONFIRMAR: modelo do guindaste, raio de operacao e coef. de "
               "impacto conforme equipamento e acesso (NBR 8800 4.2.6).",
    }


def forca_lateral_montagem(q_kNm2, area_exposta_m2, fator_vento=1.0,
                           gamma=GAMMA_CONSTRUCAO):
    """Forca lateral de montagem sobre o portico ISOLADO (antes do
    contraventamento definitivo). q_kNm2 = pressao dinamica de PROJETO; fator_vento
    reduz para vento de montagem (default 1,0 = vento integral; NBR 6123 permite
    periodo de retorno reduzido p/ estrutura temporaria - A CONFIRMAR o fator, a
    tabela nao esta nesta base). Aplica gamma de construcao (4.9.6.5). Retorna F
    de calculo (kN)."""
    F_k = q_kNm2 * fator_vento * area_exposta_m2
    return round(gamma * F_k, 2)


def estai_provisorio(F_lat_kN, angulo_graus=45.0, n_estais=1, fs_cabo=3.0):
    """Dimensiona o(s) estai(s) provisorio(s) que estabiliza(m) o portico isolado
    (NBR 8800 12.3.2.1; Bellei). F_lat_kN = forca lateral de montagem (ja de
    calculo); angulo = inclinacao do cabo em relacao a HORIZONTAL; n_estais =
    numero de cabos que dividem a forca no sentido considerado. Equilibrio
    horizontal: T.cos(a) por cabo -> T = F/(n.cos a). A componente vertical
    T.sen(a) SOMA compressao na coluna e e a forca de ARRANCAMENTO da ancoragem.
    fs_cabo = fator de seguranca do cabo/ancoragem (A CONFIRMAR: norma de cabos).
    Retorna dict com tracao, componentes e resistencia requerida do cabo."""
    a = math.radians(angulo_graus)
    ca, sa = math.cos(a), math.sin(a)
    if n_estais < 1 or ca <= 0:
        return {"erro": "angulo/numero de estais invalido"}
    T = F_lat_kN / (n_estais * ca)                  # tracao por cabo (kN)
    comp_col = T * sa                               # compressao adicional na coluna
    ancor = T * sa                                  # arrancamento da ancoragem (vertical)
    return {
        "angulo_graus": angulo_graus,
        "n_estais": n_estais,
        "F_lateral_kN": round(F_lat_kN, 2),
        "tracao_cabo_kN": round(T, 2),
        "comp_adicional_coluna_kN": round(comp_col, 2),
        "forca_ancoragem_kN": round(ancor, 2),
        "resistencia_cabo_req_kN": round(T * fs_cabo, 2),
        "fs_cabo": fs_cabo,
        "obs": "A CONFIRMAR: angulo do cabo, bitola/resistencia do cabo e fator "
               "de seguranca conforme rigging e norma de cabos de aco. Ancoragem "
               "no solo/base a verificar quanto ao arrancamento.",
    }


def sequencia_montagem(nvaos=1):
    """Sequencia logica de montagem do galpao (Bellei 7.6.4 adaptado ao portico +
    NBR 8800 12.3.2). Lista ordenada de passos. `nvaos` ajusta a mencao a colunas
    intermediarias."""
    col_txt = ("2 colunas externas" if nvaos <= 1
               else "%d colunas (2 externas + %d interna(s))" % (nvaos + 1, nvaos - 1))
    return [
        "1. Conferir chumbadores e nivelar as BASES na cota de projeto, em pleno "
        "contato com a superficie de apoio (NBR 8800 12.3.2.1).",
        "2. Iniciar pela extremidade MAIS INACESSIVEL, recuando o guindaste a "
        "medida que a montagem avanca (Bellei 7.6.4).",
        "3. Montar o 1o PORTICO transversal (%s + vigas/rafters) e fixar as bases; "
        "prumar as colunas (NBR 8800 12.3.3.1.1)." % col_txt,
        "4. ESTAIAR o 1o portico com cabos provisorios ancorados no solo/base - "
        "isolado ele e INSTAVEL fora do plano (NBR 8800 12.3.2.1; Bellei).",
        "5. Montar o 2o portico e interliga-lo ao 1o com TERCAS e o "
        "CONTRAVENTAMENTO VERTICAL/longitudinal do 1o vao (forma o nucleo rigido).",
        "6. Fechar o CONTRAVENTAMENTO DE COBERTURA (plano das tercas) e de parede "
        "do 1o vao; so entao remover os estais do 1o portico.",
        "7. Prosseguir portico a portico, mantendo SEMPRE >= 1 vao a frente "
        "estaiado/travado; o conjunto parcial deve resistir a acao permanente + "
        "vento + acoes de montagem antes de soltar do guindaste (NBR 8800 12.3.2.2).",
        "8. Montar tercas, tirantes e demais secundarios restantes; conferir "
        "PRUMO, ALINHAMENTO e ESQUADRO finais (Bellei 7.6.4).",
        "9. Torquear as ligacoes parafusadas / concluir as soldas de campo "
        "(NBR 8800 12.3.2.2; 6.7).",
        "10. Remover TODOS os elementos provisorios apenas com a estrutura ja "
        "estavel e contraventamentos definitivos concluidos (NBR 8800 12.3.2.1).",
    ]


def plano_montagem(geometria, pecas, q_kNm2=None, area_exposta_m2=None,
                   raio_m=None, angulo_estai=45.0, n_estais=1,
                   coef_impacto=COEF_IMPACTO_MONTAGEM, fator_vento=1.0):
    """Monta o plano de montagem completo. geometria: {span, eave, ridge, bay,
    comprimento, spans?}. pecas: lista {marca, peso_unit_kg} (romaneio/por_marca).
    Campos dependentes de obra (q, area exposta, raio) sao A CONFIRMAR quando
    ausentes; a estrutura do plano e sempre emitida. Retorna dict."""
    spans = geometria.get("spans") or [geometria.get("span")]
    nvaos = len([s for s in spans if s])
    eave = float(geometria.get("eave") or 0.0)
    ridge = float(geometria.get("ridge") or eave)
    bay = float(geometria.get("bay") or 0.0)
    comp = float(geometria.get("comprimento") or 0.0)
    n_porticos = int(round(comp / bay)) + 1 if bay > 0 else None
    H_mm = eave * 1000.0

    pesada = peca_mais_pesada(pecas)
    # altura de icamento ~ topo (cumeeira) + folga da lingada (A CONFIRMAR)
    altura_ic = ridge if ridge else eave
    # raio: sem dado de canteiro -> None (A CONFIRMAR). Se dado, calcula momento.
    guind = (guindaste_requerido(pesada["peso_kg"], raio_m, altura_ic, coef_impacto)
             if raio_m else
             {"peso_peca_kg": pesada["peso_kg"], "coef_impacto": coef_impacto,
              "peso_icamento_kg": round(pesada["peso_kg"] * coef_impacto, 1),
              "peso_icamento_t": round(pesada["peso_kg"] * coef_impacto / 1000.0, 3),
              "raio_m": None, "altura_icamento_m": altura_ic, "momento_carga_tm": None,
              "obs": "A CONFIRMAR: raio de operacao (acesso ao canteiro) para o "
                     "momento de carga; e o modelo do guindaste (NBR 8800 4.2.6)."})

    # estai: precisa de vento (q) e area exposta -> ambos dependem do metodo/canteiro
    if q_kNm2 and area_exposta_m2:
        F = forca_lateral_montagem(q_kNm2, area_exposta_m2, fator_vento)
        estai = estai_provisorio(F, angulo_estai, n_estais)
    else:
        estai = {"obs": "A CONFIRMAR: vento de montagem (q) e area exposta do "
                        "portico isolado para dimensionar o estai. Ha de resistir "
                        "a NBR 8800 12.3.2.1 (vento + equipamentos), combinacao de "
                        "construcao gamma=1,30 (4.9.6.5)."}

    return {
        "nvaos": nvaos,
        "n_porticos": n_porticos,
        "sequencia": sequencia_montagem(nvaos),
        "peca_mais_pesada": pesada,
        "guindaste": guind,
        "estai": estai,
        "prumo": tolerancia_prumo_montagem(H_mm) if H_mm else None,
        "ref_norma": "NBR 8800 1.10/4.2.6/4.4/4.9.6.5/12.3.2/12.3.3 + AISC 303; Bellei 7.6.4",
    }


def relatorio_pt(pl):
    L = ["=" * 78, "PLANO DE MONTAGEM E ESCORAMENTO (NBR 8800 12.3 + AISC 303)",
         "=" * 78,
         "Porticos: %s   Vaos: %d" % (pl.get("n_porticos") or "-", pl.get("nvaos", 0)),
         "", "SEQUENCIA DE MONTAGEM:"]
    for s in pl["sequencia"]:
        L.append("  " + s)
    p = pl["peca_mais_pesada"]
    L += ["", "ICAMENTO / GUINDASTE:",
          "  Peca mais pesada: marca %s = %.1f kg (%s)"
          % (p["marca"], p["peso_kg"], p["descricao"])]
    g = pl["guindaste"]
    L.append("  Peso de icamento (c/ impacto %.2f): %.1f kg (%.3f t)"
             % (g["coef_impacto"], g["peso_icamento_kg"], g["peso_icamento_t"]))
    if g.get("momento_carga_tm"):
        L.append("  Momento de carga: %.2f t.m @ raio %.1f m (ler tabela do guindaste)"
                 % (g["momento_carga_tm"], g["raio_m"]))
    L.append("  " + g["obs"])
    L += ["", "ESTAIAMENTO PROVISORIO:"]
    e = pl["estai"]
    if e.get("tracao_cabo_kN") is not None:
        L += ["  Forca lateral de montagem (calc): %.2f kN" % e["F_lateral_kN"],
              "  Tracao por cabo (angulo %.0f, n=%d): %.2f kN"
              % (e["angulo_graus"], e["n_estais"], e["tracao_cabo_kN"]),
              "  Compressao adicional na coluna: %.2f kN" % e["comp_adicional_coluna_kN"],
              "  Arrancamento na ancoragem: %.2f kN" % e["forca_ancoragem_kN"],
              "  Resistencia requerida do cabo (fs %.1f): %.2f kN"
              % (e["fs_cabo"], e["resistencia_cabo_req_kN"])]
    L.append("  " + e["obs"])
    if pl.get("prumo"):
        pr = pl["prumo"]
        L += ["", "TOLERANCIA DE PRUMO NA MONTAGEM (12.3.3.1.1):",
              "  <= %.1f mm por coluna (%s); desvio global <= %.0f mm"
              % (pr["tol_mm"], pr["criterio"], pr["global_mm"])]
    L += ["", "Ref.: " + pl["ref_norma"], ""]
    return "\n".join(L)


def _selftest():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    pecas = [{"marca": "C1", "peso_unit_kg": 253.5},
             {"marca": "V1", "peso_unit_kg": 320.0}]
    # peca mais pesada: rafter pre-montado V1 -> 2x320 = 640
    pp = peca_mais_pesada(pecas)
    assert abs(pp["peso_kg"] - 640.0) < 1e-6 and pp["marca"] == "V1"
    # sem rafter pre-montado -> a mais pesada isolada e V1 320
    pp2 = peca_mais_pesada(pecas, rafter_pre_montado=False)
    assert abs(pp2["peso_kg"] - 320.0) < 1e-6
    # prumo: H=6 m -> H/500 = 12 mm (> 5) ; global 25
    pr = tolerancia_prumo_montagem(6000.0)
    assert abs(pr["tol_mm"] - 12.0) < 1e-6 and pr["global_mm"] == 25.0
    # coluna baixa: H=2 m -> H/500=4 < 5 -> piso 5 mm
    assert abs(tolerancia_prumo_montagem(2000.0)["tol_mm"] - 5.0) < 1e-6
    # guindaste: 640 kg, impacto 1,10, raio 8 m -> P_ic 704 kg=0,704 t ; mom 5,632 t.m
    g = guindaste_requerido(640.0, 8.0, 7.0)
    assert abs(g["peso_icamento_kg"] - 704.0) < 1e-6
    assert abs(g["momento_carga_tm"] - 0.704 * 8.0) < 1e-2
    # estai: F=10 kN, 45 graus, 1 cabo -> T = 10/cos45 = 14,142 ; comp = T.sen45 = 10
    e = estai_provisorio(10.0, 45.0, 1)
    assert abs(e["tracao_cabo_kN"] - 10.0 / math.cos(math.radians(45))) < 1e-2
    assert abs(e["comp_adicional_coluna_kN"] - 10.0) < 1e-2
    assert abs(e["forca_ancoragem_kN"] - 10.0) < 1e-2
    # 2 cabos dividem a tracao
    e2 = estai_provisorio(10.0, 45.0, 2)
    assert abs(e2["tracao_cabo_kN"] - e["tracao_cabo_kN"] / 2.0) < 1e-2
    # forca de montagem aplica gamma 1,30
    F = forca_lateral_montagem(1.0, 10.0)     # q=1 kN/m2, area=10 -> 10 kN * 1,30
    assert abs(F - 13.0) < 1e-6
    # plano completo emite sequencia (10 passos) e nao quebra sem dados de canteiro
    pl = plano_montagem(geo, pecas)
    assert len(pl["sequencia"]) == 10 and pl["n_porticos"] == 9
    assert "A CONFIRMAR" in pl["estai"]["obs"]        # sem q/area -> flag
    # com dados de canteiro -> dimensiona
    pl2 = plano_montagem(geo, pecas, q_kNm2=0.8, area_exposta_m2=12.0,
                         raio_m=8.0, n_estais=2)
    assert pl2["estai"]["tracao_cabo_kN"] > 0
    assert pl2["guindaste"]["momento_carga_tm"] > 0
    txt = relatorio_pt(pl2)
    assert "PLANO DE MONTAGEM" in txt and "12.3.3.1.1" in txt
    print("montagem _selftest PASSED")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(plano_montagem(
        {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0},
        [{"marca": "C1", "peso_unit_kg": 253.5}, {"marca": "V1", "peso_unit_kg": 320.0}],
        q_kNm2=0.8, area_exposta_m2=12.0, raio_m=8.0, n_estais=2)))
