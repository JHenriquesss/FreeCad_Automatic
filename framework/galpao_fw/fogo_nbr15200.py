# ============================================================================
# fogo_nbr15200.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verificacao de estruturas de concreto em SITUACAO DE INCENDIO pelo METODO
# TABULAR (metodo simplificado A) da NBR 15200:2024. Confere se a secao tem
# dimensao minima (bmin) e distancia do eixo da armadura a face (c1) suficientes
# para o TRRF exigido - sem calculo termico, so as tabelas da norma:
#   - VIGAS biapoiadas: Tabela 4 (bmin/c1 alternativos + bw,min).
#   - PILARES 1 face exposta: Tabela 12.
#   - PILARES-parede: Tabela 13 (por nivel de carga mu_fi e nº de faces).
# Pilar retangular com MAIS de uma face exposta cai fora do tabular simples ->
# a norma remete ao Anexo E (omega, nu, e) ou ao metodo analitico 8.3.2; nesse
# caso o modulo NAO inventa um "passou": devolve requer_anexo_E=True.
# c1 = cobrimento + phi_estribo + phi_barra/2. Protendido: +10 mm (barra) ou
# +15 mm (fio/cordoalha) sobre c1 (nota das Tabelas 4/... da norma).
# TRRF vem da NBR 14432/legislacao (entrada A CONFIRMAR - nao inventado; galpao
# terreo pode ser ISENTO). Valores lidos do PDF NBR 15200:2024 (NotebookLM).
# Unidades desta interface: MILIMETROS (como as tabelas da norma).
# ============================================================================
"""Metodo tabular da NBR 15200:2024 (concreto em incendio): dimensoes minimas
bmin/c1 por TRRF para vigas biapoiadas, pilares e pilares-parede."""

from __future__ import annotations

TRRF_VALIDOS = (30, 60, 90, 120, 180)

# Tabela 4 - vigas biapoiadas: por TRRF, {bw_min, combos [(bmin, c1min), ...]}.
# Os combos sao ALTERNATIVOS: b maior admite c1 menor.
VIGA_BIAPOIADA = {
    30:  {"bw": 80,  "combos": [(80, 25), (120, 20), (160, 15), (190, 15)]},
    60:  {"bw": 100, "combos": [(120, 40), (160, 35), (190, 30), (300, 25)]},
    90:  {"bw": 100, "combos": [(140, 60), (190, 45), (300, 40), (400, 35)]},
    120: {"bw": 120, "combos": [(190, 68), (240, 60), (300, 55), (500, 50)]},
    180: {"bw": 140, "combos": [(240, 80), (300, 70), (400, 65), (600, 60)]},
}

# Tabela 12 - pilares com UMA face exposta: (bmin, c1).
PILAR_1FACE = {30: (155, 25), 60: (155, 25), 90: (155, 25), 120: (175, 35), 180: (230, 55)}

# Tabela 13 - pilares-parede: chave (mu_fi, faces) -> {TRRF: (bmin, c1)}.
# mu_fi = Nsd,fi / Nrd (nivel de carga em incendio). faces: 1 ou 2 (2 = "2 ou mais").
PILAR_PAREDE = {
    (0.35, 1): {30: (100, 10), 60: (110, 10), 90: (120, 20), 120: (150, 25), 180: (180, 40)},
    (0.35, 2): {30: (120, 10), 60: (120, 10), 90: (140, 10), 120: (160, 25), 180: (200, 45)},
    (0.70, 1): {30: (120, 10), 60: (130, 10), 90: (140, 25), 120: (160, 35), 180: (210, 50)},
    (0.70, 2): {30: (120, 10), 60: (140, 10), 90: (170, 25), 120: (220, 35), 180: (270, 55)},
}


def _valida_trrf(TRRF):
    if TRRF not in TRRF_VALIDOS:
        raise ValueError(f"TRRF {TRRF} invalido; use um de {TRRF_VALIDOS} (NBR 15200 Tab.4/12/13)")


def c1_efetivo(cobrimento_mm, phi_estribo_mm, phi_barra_mm, protendido=False, cordoalha=True):
    """Distancia do eixo (CG) da armadura a face: c1 = cob + phi_estribo + phi_barra/2.
    Para elemento protendido, o c1 EXIGIDO pela tabela cresce (+10 mm barra, +15 mm
    fio/cordoalha); aqui devolvemos o c1 GEOMETRICO real (o acrescimo entra na verificacao)."""
    return cobrimento_mm + phi_estribo_mm + phi_barra_mm / 2.0


def _acrescimo_protensao(protendido, cordoalha):
    if not protendido:
        return 0.0
    return 15.0 if cordoalha else 10.0


def verifica_viga_fogo(b_mm, c1_mm, TRRF, protendida=False, cordoalha=True):
    """Verifica uma viga biapoiada pelo metodo tabular (Tabela 4). b_mm = largura;
    c1_mm = distancia real do eixo da armadura a face. Escolhe o combo (bmin,c1min)
    valido para a largura dada e exige c1 >= c1min (+ acrescimo de protensao)."""
    _valida_trrf(TRRF)
    tab = VIGA_BIAPOIADA[TRRF]
    acr = _acrescimo_protensao(protendida, cordoalha)
    # combo governante: o de MAIOR bmin que ainda cabe em b (b maior -> c1 menor).
    c1_req = None
    for (bmin, c1min) in tab["combos"]:
        if b_mm >= bmin:
            c1_req = c1min + acr            # ultimo (maior bmin) prevalece
    if c1_req is None:                       # b menor que o menor bmin da tabela
        bmin0, c1min0 = tab["combos"][0]
        return {"OK": False, "b_mm": b_mm, "bmin_req": bmin0, "c1_mm": c1_mm,
                "c1_req": c1min0 + acr, "bw_min": tab["bw"], "TRRF": TRRF,
                "motivo": f"largura {b_mm:.0f} < bmin {bmin0} mm"}
    ok = (b_mm >= tab["bw"]) and (c1_mm >= c1_req)
    return {"OK": ok, "b_mm": b_mm, "bw_min": tab["bw"], "c1_mm": c1_mm,
            "c1_req": c1_req, "TRRF": TRRF, "protendida": protendida}


def verifica_pilar_fogo(b_mm, c1_mm, TRRF, faces_expostas=4, pilar_parede=False,
                        mu_fi=0.70):
    """Verifica um pilar pelo metodo tabular. Casos cobertos pela norma:
      - pilar-parede (Tabela 13): informe pilar_parede=True + mu_fi (0,35 ou 0,70)
        + faces_expostas (1 ou >=2);
      - pilar comum com UMA face exposta (Tabela 12): faces_expostas=1.
    Pilar retangular comum com MAIS de uma face exposta NAO e coberto pelo tabular
    simples -> a norma exige o Anexo E / metodo analitico 8.3.2. Nesse caso devolve
    requer_anexo_E=True (nao finge aprovacao)."""
    _valida_trrf(TRRF)
    if pilar_parede:
        chave = (0.35 if mu_fi <= 0.35 else 0.70, 1 if faces_expostas <= 1 else 2)
        bmin, c1min = PILAR_PAREDE[chave][TRRF]
        ok = (b_mm >= bmin) and (c1_mm >= c1min)
        return {"OK": ok, "tabela": "13 (pilar-parede)", "bmin_req": bmin,
                "c1_req": c1min, "b_mm": b_mm, "c1_mm": c1_mm, "mu_fi": mu_fi,
                "faces": faces_expostas, "TRRF": TRRF}
    if faces_expostas <= 1:
        bmin, c1min = PILAR_1FACE[TRRF]
        ok = (b_mm >= bmin) and (c1_mm >= c1min)
        return {"OK": ok, "tabela": "12 (1 face)", "bmin_req": bmin, "c1_req": c1min,
                "b_mm": b_mm, "c1_mm": c1_mm, "faces": 1, "TRRF": TRRF}
    return {"OK": None, "requer_anexo_E": True, "b_mm": b_mm, "c1_mm": c1_mm,
            "faces": faces_expostas, "TRRF": TRRF,
            "motivo": "pilar retangular com mais de uma face exposta: usar Anexo E "
                      "(omega, nu, e) ou metodo analitico 8.3.2 (NBR 15200)"}


def relatorio_pt(viga=None, pilar=None, TRRF=None):
    L = [f"SITUACAO DE INCENDIO - METODO TABULAR (NBR 15200:2024)"
         + (f" ; TRRF = {TRRF} min" if TRRF else "")]
    if viga:
        L.append(f"  VIGA biapoiada: b={viga['b_mm']:.0f} mm (bw,min {viga['bw_min']}) ; "
                 f"c1={viga['c1_mm']:.0f} >= {viga['c1_req']:.0f} mm "
                 f"-> {'ATENDE' if viga['OK'] else 'REPROVA'}")
    if pilar:
        if pilar.get("requer_anexo_E"):
            L.append(f"  PILAR: {pilar['faces']} faces expostas -> requer Anexo E "
                     f"(tabular simples nao se aplica)")
        else:
            L.append(f"  PILAR (Tab.{pilar['tabela']}): b={pilar['b_mm']:.0f} >= "
                     f"{pilar['bmin_req']} mm ; c1={pilar['c1_mm']:.0f} >= {pilar['c1_req']} mm "
                     f"-> {'ATENDE' if pilar['OK'] else 'REPROVA'}")
    return "\n".join(L)


def _selftest():
    # viga 200x600 mm, c1=45 mm, TRRF 60: combo 190/30 -> c1_req 30 -> ATENDE
    v = verifica_viga_fogo(200, 45, 60)
    assert v["OK"] and v["c1_req"] == 30, v
    # viga fina 100 mm, TRRF 60 (bw_min 100, menor bmin 120) -> REPROVA por largura
    v2 = verifica_viga_fogo(100, 50, 60)
    assert not v2["OK"], v2
    # protendida com cordoalha: c1_req soma 15 mm
    vp = verifica_viga_fogo(300, 40, 60, protendida=True, cordoalha=True)
    assert vp["c1_req"] == 25 + 15, vp     # combo 300/25 + 15
    # pilar 1 face, 200 mm, c1 30, TRRF 90: Tab.12 155/25 -> ATENDE
    p = verifica_pilar_fogo(200, 30, 90, faces_expostas=1)
    assert p["OK"] and p["tabela"].startswith("12"), p
    # pilar comum 4 faces -> requer Anexo E (nao finge)
    p4 = verifica_pilar_fogo(200, 30, 90, faces_expostas=4)
    assert p4["OK"] is None and p4["requer_anexo_E"], p4
    # pilar-parede mu_fi 0,70, 2 faces, TRRF 120: Tab.13 -> 220/35
    pp = verifica_pilar_fogo(220, 35, 120, faces_expostas=2, pilar_parede=True, mu_fi=0.70)
    assert pp["OK"] and pp["bmin_req"] == 220 and pp["c1_req"] == 35, pp
    # TRRF invalido levanta erro
    try:
        verifica_viga_fogo(200, 40, 45)
        assert False
    except ValueError:
        pass
    print("fogo_nbr15200 self-test PASSED")
    print(relatorio_pt(v, p, TRRF=60))


if __name__ == "__main__":
    _selftest()
