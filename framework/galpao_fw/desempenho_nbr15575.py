# ============================================================================
# desempenho_nbr15575.py - O QUE ESTE SCRIPT FAZ / VERIFICA
# DESEMPENHO de edificacao HABITACIONAL pela ABNT NBR 15575 - o gate que faltava
# inteiro: antes deste modulo, `grep -rn 15575` nao retornava uma linha de codigo
# do projeto. Como a 15575 traz limites MAIS RESTRITIVOS que a 6118/8800 em
# varios pontos, um projeto habitacional passava em todos os gates do framework e
# reprovaria na 15575 - reprovacao que so apareceria na obra.
#
# O QUE ESTE MODULO COBRE (tudo transcrito da fonte, nao de memoria):
#   15575-2:2013 7.3.1 - Tabela 1 (deslocamentos-limites), Tabela 2 (flechas
#                        maximas por tipo de vedacao/piso/forro), o teto do
#                        deslocamento horizontal no TOPO do edificio e o limite
#                        absoluto de abertura de fissura de 0,6 mm;
#   15575-3:2021 7.5.1 - carga vertical concentrada de 1 kN no ponto mais
#                        desfavoravel, com d_v <= L/500 (rigido) ou L/300 (ductil);
#   15575-4:2013 7.2.1 - fachada sob vento de servico Sd = 0,9 Sgk + 0,8 Swk.
#
# A REGRA DE APLICABILIDADE, QUE E' FACIL DE ERRAR PARA O LADO CONTRA A SEGURANCA:
# a 15575-2 7.3.1 diz que os componentes nao podem apresentar "deslocamentos
# maiores que os estabelecidos nas Normas de projeto estrutural (ABNT NBR 6118,
# ... 8800 ...) OU, NA FALTA DE NORMA BRASILEIRA ESPECIFICA, utilizar as Tabelas
# 1 ou 2". Ou seja: as Tabelas 1 e 2 sao o criterio SUPLETIVO. Este modulo
# aplica as duas assim mesmo e publica QUAL governa, porque:
#   - o limite de fissura de 0,6 mm e o teto do topo do edificio NAO sao
#     supletivos ("em qualquer situacao", "para qualquer tipo de solicitacao");
#   - onde a 6118 e' mais folgada que a Tabela 2, adotar o menor dos dois e' o
#     PISO CONSERVADOR para requisito de desempenho contratualmente exigivel.
# O campo `governante` de cada verificacao diz de onde veio o limite adotado,
# para que o projetista possa dispensar a tabela supletiva com conhecimento de
# causa - nunca em silencio.
#
# 15575-1:2025 (setima edicao) NAO revogou nem alterou esses criterios: o seu
# item 9.2.1-c remete de volta as partes 2 a 6 ("deformacoes e defeitos acima dos
# limites especificados nas ABNT NBR 15575-2 a ABNT NBR 15575-6"). Conferido na
# fonte - por isso os valores continuam datados de 2013 (parte 2) e 2021 (parte 3).
#
# ARMADILHA DA NOTA c DA TABELA 2: a 15575 obtem a flecha FINAL "reduzindo a
# rigidez dos elementos analisados pela metade", que NAO e' o (1+alpha_f) de
# fluencia da NBR 6118 17.3.2.1.2. Sao duas convencoes distintas para a mesma
# grandeza; aplicar as duas juntas conta o efeito diferido duas vezes, e aplicar
# a da 6118 achando que atende a 15575 subestima a flecha final. `flecha_final`
# implementa a convencao da 15575 e diz isso no nome.
#
# Unidades: m, kN. Deslocamentos publicados em mm.
# ============================================================================
"""Desempenho de edificacao habitacional (NBR 15575): Tabelas 1 e 2 da parte 2,
topo do edificio, fissura de 0,6 mm, carga concentrada de piso da parte 3 e
deslocamento de fachada da parte 4."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 15575-2:2013, Tabela 1 - deslocamentos-limites para cargas permanentes e
# cargas acidentais em geral. H = altura do elemento estrutural; L = vao teorico.
# `div_L` e `div_H` sao os divisores; None onde a norma nao da a alternativa.
# ---------------------------------------------------------------------------
TAB1_15575_2 = {
    "visual": {
        "razao": "Visual/inseguranca psicologica",
        "elemento": "Pilares, paredes, vigas, lajes (componentes visiveis)",
        "div_L": 250.0, "div_H": 300.0,
        "tipo": "deslocamento final incluindo fluencia (carga total)"},
    "caixilhos_instalacoes_acabamentos_rigidos": {
        "razao": "Destacamentos, fissuras em vedacoes ou acabamentos, falhas na "
                 "operacao de caixilhos e instalacoes",
        "elemento": "Caixilhos, instalacoes, vedacoes e acabamentos rigidos "
                    "(pisos, forros etc.)",
        "div_L": 800.0, "div_H": None,
        "tipo": "parcela da flecha ocorrida APOS a instalacao da carga "
                "correspondente ao elemento em analise"},
    "divisorias_leves_acabamentos_flexiveis": {
        "razao": "Destacamentos, fissuras em vedacoes ou acabamentos, falhas na "
                 "operacao de caixilhos e instalacoes",
        "elemento": "Divisorias leves, acabamentos flexiveis (pisos, forros etc.)",
        "div_L": 600.0, "div_H": None,
        "tipo": "parcela da flecha ocorrida APOS a instalacao da carga "
                "correspondente ao elemento em analise"},
    "vedacoes_rigidas": {
        "razao": "Destacamentos e fissuras em vedacoes",
        "elemento": "Paredes e/ou acabamentos rigidos",
        "div_L": 500.0, "div_H": 500.0,
        "tipo": "distorcao horizontal ou vertical provocada por variacoes de "
                "temperatura ou acao do vento, distorcao angular devida ao "
                "recalque de fundacoes (deslocamentos totais)"},
    "vedacoes_flexiveis": {
        "razao": "Destacamentos e fissuras em vedacoes",
        "elemento": "Paredes e acabamentos flexiveis",
        "div_L": 400.0, "div_H": 400.0,
        "tipo": "distorcao horizontal ou vertical provocada por variacoes de "
                "temperatura ou acao do vento, distorcao angular devida ao "
                "recalque de fundacoes (deslocamentos totais)"},
}

# ---------------------------------------------------------------------------
# 15575-2:2013, Tabela 2 - flechas maximas para vigas e lajes (cargas
# gravitacionais permanentes e acidentais). Valores = DIVISORES do vao L.
# Colunas, na ordem da norma:
#   'Sgk'          - flecha imediata sob a carga permanente;
#   'Sqk'          - flecha imediata sob a carga acidental;
#   'Sgk+0,7Sqk'   - flecha IMEDIATA da combinacao;
#   'final'        - flecha FINAL (total) da mesma combinacao, com a rigidez
#                    reduzida a metade (nota c).
# `None` onde a norma traz travessao (viga calha so tem Sgk e final).
# ---------------------------------------------------------------------------
COLUNAS_TAB2 = ("Sgk", "Sqk", "Sgk+0,7Sqk", "final")
PSI_TAB2 = 0.7          # coeficiente FIXO da Tabela 2 - nao e' o psi_1 da 6118

TAB2_15575_2 = {
    # paredes monoliticas, em alvenaria ou paineis unidos/rejuntados com
    # material RIGIDO
    "parede_rigida_com_aberturas": (1000.0, 2800.0, 800.0, 400.0),
    "parede_rigida_sem_aberturas": (750.0, 2100.0, 600.0, 340.0),
    # paredes em paineis com juntas flexiveis, divisorias leves, gesso acartonado
    "parede_flexivel_com_aberturas": (1050.0, 1700.0, 730.0, 330.0),
    "parede_flexivel_sem_aberturas": (850.0, 1400.0, 600.0, 300.0),
    # pisos
    "piso_rigido": (700.0, 1500.0, 530.0, 320.0),
    "piso_flexivel": (750.0, 1200.0, 520.0, 280.0),
    # forros
    "forro_rigido": (600.0, 1700.0, 480.0, 300.0),
    "forro_flexivel": (560.0, 1600.0, 450.0, 260.0),
    # coberturas
    "laje_cobertura_impermeabilizada": (850.0, 1400.0, 600.0, 320.0),
    "viga_calha": (750.0, None, None, 300.0),
}

# Nota a da Tabela 2: para vigas e lajes em BALANCO sao permitidos deslocamentos
# correspondentes a 1,5 vez os respectivos valores indicados.
FATOR_BALANCO = 1.5

# Nota b da Tabela 2: com dispositivos e detalhes construtivos que absorvam as
# tensoes concentradas no contorno das aberturas, a parede pode ser considerada
# "sem aberturas".
NOTA_B_TAB2 = ("no caso do emprego de dispositivos e detalhes construtivos que "
               "absorvam as tensoes concentradas no contorno das aberturas das "
               "portas e janelas, as paredes podem ser consideradas 'sem aberturas'")

# Nota c da Tabela 2: para a verificacao dos deslocamentos na flecha final,
# reduzir a rigidez dos elementos analisados pela metade.
FATOR_RIGIDEZ_REDUZIDA = 0.5

# ---------------------------------------------------------------------------
# 15575-2:2013, Tabela 1 nota a - teto do deslocamento horizontal no TOPO.
# "Para qualquer tipo de solicitacao, o deslocamento horizontal maximo no topo do
# edificio deve ser limitado a H_total/500 ou 3 cm, respeitando-se o MENOR dos
# dois limites."
# ---------------------------------------------------------------------------
DIV_TOPO = 500.0
TETO_TOPO_M = 0.030

# 15575-2:2013 7.3.1 - "abertura superior a 0,6 mm em qualquer situacao".
WK_MAX_MM = 0.6

# ---------------------------------------------------------------------------
# 15575-3:2021 7.5.1 - cargas verticais concentradas nos sistemas de piso.
# A parte 3 NAO tem criterio proprio de carga distribuida (remete a parte 2) e
# NAO trata de vibracao - o conforto vibratorio de piso e do Anexo L da NBR 8800
# (ver `vibracao_piso`). Conferido na fonte.
# ---------------------------------------------------------------------------
Q_CONCENTRADA_PISO_kN = 1.0
DIV_PISO_CONCENTRADA = {"rigido": 500.0, "ductil": 300.0}

# ---------------------------------------------------------------------------
# 15575-4:2013 (EM2:2021) 7.2.1, Tabela 1 - fachada sob vento de servico.
# Sd = 0,9 Sgk + 0,8 Swk ; d_h = deslocamento instantaneo, d_hr = residual.
# Nota b: para paredes de fachada LEVES (G <= 60 kgf/m2) SEM funcao estrutural,
# os valores de d_h podem atingir o DOBRO (o d_hr nao).
# ---------------------------------------------------------------------------
COMB_FACHADA = {"Sgk": 0.9, "Swk": 0.8}
FACHADA_15575_4 = {
    "estrutural": {"div_dh": 500.0, "div_dhr": 2500.0},
    "vedacao": {"div_dh": 350.0, "div_dhr": 1750.0},
}
G_PAREDE_LEVE_kgf_m2 = 60.0

APLICABILIDADE_7_3_1 = (
    "15575-2 7.3.1: os deslocamentos nao podem ser maiores que os estabelecidos "
    "nas Normas de projeto estrutural (NBR 6118, 7190, 8800, 9062, 15961, 14762) "
    "ou, NA FALTA DE NORMA BRASILEIRA ESPECIFICA, utilizar as Tabelas 1 ou 2. As "
    "Tabelas 1 e 2 sao criterio SUPLETIVO; aqui sao aplicadas assim mesmo, e o "
    "campo 'governante' diz qual limite prevaleceu")


class EntradaDesempenho(ValueError):
    """Entrada que nao permite verificar o desempenho: reprovar com motivo e
    melhor que verificar contra um limite arbitrado."""


# ---------------------------------------------------------------------------
# 1. LIMITES
# ---------------------------------------------------------------------------

def limite_tab1(linha, L=None, H=None):
    """Limite da Tabela 1 da 15575-2 (m). Devolve o MENOR entre as alternativas
    L/div_L e H/div_H que a linha oferece e para as quais o vao/altura foi dado.
    Exige pelo menos uma - a linha 'visual' com L e H ambos ausentes nao pode
    devolver limite nenhum, e devolver infinito seria aprovar por dado faltante."""
    if linha not in TAB1_15575_2:
        raise EntradaDesempenho("linha da Tabela 1 desconhecida: %r (use %s)"
                                % (linha, sorted(TAB1_15575_2)))
    d = TAB1_15575_2[linha]
    cands = []
    if d["div_L"] and L:
        cands.append(("L/%g" % d["div_L"], L / d["div_L"]))
    if d["div_H"] and H:
        cands.append(("H/%g" % d["div_H"], H / d["div_H"]))
    if not cands:
        raise EntradaDesempenho(
            "Tabela 1 linha %r: nenhuma das grandezas exigidas foi dada "
            "(div_L=%s -> precisa de L ; div_H=%s -> precisa de H)"
            % (linha, d["div_L"], d["div_H"]))
    expr, lim = min(cands, key=lambda c: c[1])
    return {"linha": linha, "limite_m": lim, "expressao": expr,
            "razao": d["razao"], "elemento": d["elemento"], "tipo": d["tipo"],
            "fonte": "NBR 15575-2:2013 Tabela 1"}


def limite_tab2(linha, coluna, L, balanco=False):
    """Limite da Tabela 2 da 15575-2 (m) para um vao teorico L.

    `balanco=True` aplica a nota a (1,5 vez os valores indicados) - o que
    AFROUXA o limite, e por isso so pode ser ligado por declaracao explicita de
    que o elemento e' em balanco."""
    if linha not in TAB2_15575_2:
        raise EntradaDesempenho("linha da Tabela 2 desconhecida: %r (use %s)"
                                % (linha, sorted(TAB2_15575_2)))
    if coluna not in COLUNAS_TAB2:
        raise EntradaDesempenho("coluna da Tabela 2 desconhecida: %r (use %s)"
                                % (coluna, list(COLUNAS_TAB2)))
    div = TAB2_15575_2[linha][COLUNAS_TAB2.index(coluna)]
    if div is None:
        raise EntradaDesempenho(
            "Tabela 2: a linha %r nao tem valor na coluna %r (a norma traz "
            "travessao) - nao ha limite a verificar nessa combinacao"
            % (linha, coluna))
    lim = L / div
    if balanco:
        lim *= FATOR_BALANCO
    return {"linha": linha, "coluna": coluna, "limite_m": lim,
            "expressao": "L/%g%s" % (div, " x 1,5 (balanco)" if balanco else ""),
            "balanco": bool(balanco), "fonte": "NBR 15575-2:2013 Tabela 2"}


def flecha_final(f_imediata_m):
    """Flecha FINAL pela convencao da nota c da Tabela 2: rigidez dos elementos
    analisados reduzida PELA METADE. Como a flecha e' inversamente proporcional
    a EI, meia rigidez dobra o deslocamento.

    NAO e' a fluencia da NBR 6118 17.3.2.1.2 (x (1+alpha_f)) - sao convencoes
    distintas para a mesma grandeza. Somar as duas conta o diferido duas vezes;
    usar a da 6118 achando que atende a 15575 subestima a flecha final."""
    return f_imediata_m / FATOR_RIGIDEZ_REDUZIDA


def limite_topo(H_total):
    """Teto do deslocamento horizontal no topo do edificio (m):
    min(H_total/500 ; 3 cm) - nota a da Tabela 1, valida "para qualquer tipo de
    solicitacao"."""
    if not H_total or H_total <= 0:
        raise EntradaDesempenho("H_total deve ser positivo para o limite de topo")
    por_altura = H_total / DIV_TOPO
    lim = min(por_altura, TETO_TOPO_M)
    return {"limite_m": lim, "por_altura_m": por_altura, "teto_m": TETO_TOPO_M,
            "governante": "H_total/500" if por_altura <= TETO_TOPO_M else "3 cm",
            "fonte": "NBR 15575-2:2013 Tabela 1, nota a"}


# ---------------------------------------------------------------------------
# 2. VERIFICACOES
# ---------------------------------------------------------------------------

def verifica_topo(u_topo_m, H_total, u_norma_m=None):
    """Deslocamento horizontal no topo do edificio.

    `u_norma_m` opcional e' o limite que a norma de projeto especifica ja impoe
    (p.ex. H/1700 da Tabela 13.3 da NBR 6118). Quando dado, o limite adotado e'
    o MENOR dos dois e `governante` diz de qual norma ele veio."""
    lim = limite_topo(H_total)
    adotado, gov = lim["limite_m"], "NBR 15575-2 (%s)" % lim["governante"]
    if u_norma_m is not None and u_norma_m < adotado:
        adotado, gov = u_norma_m, "norma de projeto estrutural"
    return {"u_topo_mm": round(u_topo_m * 1000, 2),
            "limite_15575_mm": round(lim["limite_m"] * 1000, 2),
            "limite_norma_mm": (None if u_norma_m is None
                                else round(u_norma_m * 1000, 2)),
            "limite_adotado_mm": round(adotado * 1000, 2), "governante": gov,
            "H_total_m": H_total, "OK": u_topo_m <= adotado + 1e-12,
            "fonte": lim["fonte"]}


def verifica_fissura(wk_mm, wk_lim_norma_mm=None):
    """Abertura de fissura. A 15575-2 7.3.1 impoe 0,6 mm "em qualquer situacao";
    quando a norma de projeto (NBR 6118 Tabela 13.4, por CAA) for mais
    restritiva, e' ela que governa."""
    adotado, gov = WK_MAX_MM, "NBR 15575-2 (0,6 mm em qualquer situacao)"
    if wk_lim_norma_mm is not None and wk_lim_norma_mm < adotado:
        adotado, gov = wk_lim_norma_mm, "NBR 6118 Tabela 13.4 (CAA)"
    return {"wk_mm": round(wk_mm, 3), "limite_15575_mm": WK_MAX_MM,
            "limite_norma_mm": wk_lim_norma_mm,
            "limite_adotado_mm": adotado, "governante": gov,
            "OK": wk_mm <= adotado + 1e-9,
            "fonte": "NBR 15575-2:2013 7.3.1"}


def verifica_flecha(linha, coluna, L, flecha_m, balanco=False,
                    lim_norma_m=None):
    """Flecha de viga ou laje contra a Tabela 2 da 15575-2 (e, se dado, contra o
    limite da norma de projeto; adota-se o menor)."""
    lim = limite_tab2(linha, coluna, L, balanco=balanco)
    adotado, gov = lim["limite_m"], "NBR 15575-2 Tabela 2 (%s)" % lim["expressao"]
    if lim_norma_m is not None and lim_norma_m < adotado:
        adotado, gov = lim_norma_m, "norma de projeto estrutural"
    return dict(lim, flecha_mm=round(flecha_m * 1000, 2),
                limite_15575_mm=round(lim["limite_m"] * 1000, 2),
                limite_norma_mm=(None if lim_norma_m is None
                                 else round(lim_norma_m * 1000, 2)),
                limite_adotado_mm=round(adotado * 1000, 2), governante=gov,
                L=L, OK=flecha_m <= adotado + 1e-12)


def verifica_piso_carga_concentrada(d_v_m, L, acabamento):
    """15575-3:2021 7.5.1 - carga vertical concentrada de 1 kN no ponto mais
    desfavoravel: d_v <= L/500 (piso rigido) ou L/300 (piso ductil)."""
    if acabamento not in DIV_PISO_CONCENTRADA:
        raise EntradaDesempenho(
            "acabamento de piso desconhecido: %r (use %s) - o limite muda de "
            "L/500 para L/300 entre eles, entao nao ha default"
            % (acabamento, sorted(DIV_PISO_CONCENTRADA)))
    div = DIV_PISO_CONCENTRADA[acabamento]
    lim = L / div
    return {"Q_kN": Q_CONCENTRADA_PISO_kN, "acabamento": acabamento,
            "d_v_mm": round(d_v_m * 1000, 2), "limite_mm": round(lim * 1000, 2),
            "expressao": "L/%g" % div, "L": L, "OK": d_v_m <= lim + 1e-12,
            "fonte": "NBR 15575-3:2021 7.5.1"}


def verifica_fachada(d_h_m, h, funcao, d_hr_m=None, G_kgf_m2=None):
    """15575-4:2013 7.2.1 - deslocamento da parede de fachada sob o vento de
    servico Sd = 0,9 Sgk + 0,8 Swk.

    `funcao` e' 'estrutural' ou 'vedacao'. A nota b dobra o limite de d_h (e SO
    o de d_h) para paredes de fachada LEVES (G <= 60 kgf/m2) SEM funcao
    estrutural - por isso o dobro exige `G_kgf_m2` declarado E funcao 'vedacao'."""
    if funcao not in FACHADA_15575_4:
        raise EntradaDesempenho("funcao de fachada desconhecida: %r (use %s)"
                                % (funcao, sorted(FACHADA_15575_4)))
    d = FACHADA_15575_4[funcao]
    leve = bool(funcao == "vedacao" and G_kgf_m2 is not None
                and G_kgf_m2 <= G_PAREDE_LEVE_kgf_m2)
    lim_dh = h / d["div_dh"] * (2.0 if leve else 1.0)
    lim_dhr = h / d["div_dhr"]
    r = {"funcao": funcao, "h_m": h, "parede_leve": leve,
         "combinacao": "Sd = 0,9 Sgk + 0,8 Swk",
         "d_h_mm": round(d_h_m * 1000, 2),
         "limite_dh_mm": round(lim_dh * 1000, 2),
         "expressao_dh": "h/%g%s" % (d["div_dh"],
                                     " x 2 (parede leve, nota b)" if leve else ""),
         "limite_dhr_mm": round(lim_dhr * 1000, 2),
         "expressao_dhr": "h/%g" % d["div_dhr"],
         "ok_dh": d_h_m <= lim_dh + 1e-12,
         "fonte": "NBR 15575-4:2013 (EM2:2021) 7.2.1, Tabela 1"}
    if d_hr_m is None:
        # o residual e' medido em ensaio; sem ele a fachada nao esta verificada.
        r["d_hr_mm"] = None
        r["ok_dhr"] = None
        r["OK"] = False
        r["aviso"] = ("deslocamento RESIDUAL d_hr nao declarado: a Tabela 1 da "
                      "15575-4 exige d_h E d_hr, e o residual vem de ensaio. "
                      "Sem ele a fachada nao pode ser dada por atendida")
    else:
        r["d_hr_mm"] = round(d_hr_m * 1000, 2)
        r["ok_dhr"] = d_hr_m <= lim_dhr + 1e-12
        r["OK"] = bool(r["ok_dh"] and r["ok_dhr"])
    return r


# ---------------------------------------------------------------------------
# 3. ORQUESTRADOR
# ---------------------------------------------------------------------------

def verifica(cfg):
    """Consolida as verificacoes de desempenho da NBR 15575 disponiveis a partir
    do que o projeto entrega.

    cfg: {
      'habitacional' : bool - a 15575 so e' exigivel para EDIFICACAO
                       HABITACIONAL. Fora disso o gate sai nao aplicavel, e
                       dizer isso e' diferente de dizer que passou;
      'topo'    : opc {'u_m','H_total_m','u_norma_m' opc};
      'fissura' : opc {'wk_mm','wk_lim_norma_mm' opc};
      'flechas' : opc lista de {'nome','linha','coluna','L','flecha_m',
                  'balanco' opc,'lim_norma_m' opc};
      'piso'    : opc {'d_v_m','L','acabamento'};
      'fachada' : opc {'d_h_m','h','funcao','d_hr_m' opc,'G_kgf_m2' opc};
    }

    Cada verificacao AUSENTE fica registrada em `nao_verificados`, e `completo`
    so e' True quando nao sobrou nenhuma. `OK` REPROVA por limite excedido, nao
    por dado nao declarado - mas um cfg do qual nada pode ser verificado NAO
    devolve OK=True: passar por vacuidade e' a forma mais barata de um gate
    mentir, e aqui ela sai como `nada_verificado`."""
    if not cfg.get("habitacional"):
        return {"aplicavel": False, "OK": True, "completo": True,
                "nada_verificado": True,
                "motivo": "a NBR 15575 e' exigivel para EDIFICACAO HABITACIONAL; "
                          "esta edificacao nao foi declarada como tal",
                "verificacoes": {}, "nao_verificados": [], "reprovados": [],
                "aplicabilidade": APLICABILIDADE_7_3_1}

    ver = {}
    nao = []
    if cfg.get("topo"):
        t = cfg["topo"]
        ver["topo"] = verifica_topo(t["u_m"], t["H_total_m"],
                                    t.get("u_norma_m"))
    else:
        nao.append("topo")
    if cfg.get("fissura"):
        f = cfg["fissura"]
        ver["fissura"] = verifica_fissura(f["wk_mm"], f.get("wk_lim_norma_mm"))
    else:
        nao.append("fissura")
    if cfg.get("flechas"):
        ver["flechas"] = [
            dict(verifica_flecha(x["linha"], x["coluna"], x["L"], x["flecha_m"],
                                 balanco=x.get("balanco", False),
                                 lim_norma_m=x.get("lim_norma_m")),
                 nome=x.get("nome", x["linha"]))
            for x in cfg["flechas"]]
    else:
        nao.append("flechas")
    if cfg.get("piso"):
        p = cfg["piso"]
        ver["piso_carga_concentrada"] = verifica_piso_carga_concentrada(
            p["d_v_m"], p["L"], p["acabamento"])
    else:
        nao.append("piso_carga_concentrada")
    if cfg.get("fachada"):
        fa = cfg["fachada"]
        ver["fachada"] = verifica_fachada(fa["d_h_m"], fa["h"], fa["funcao"],
                                          d_hr_m=fa.get("d_hr_m"),
                                          G_kgf_m2=fa.get("G_kgf_m2"))
    else:
        nao.append("fachada")

    reprovados = []
    for chave, r in ver.items():
        if chave == "flechas":
            reprovados += ["flecha:" + x["nome"] for x in r if not x["OK"]]
        elif not r["OK"]:
            reprovados.append(chave)

    return {"aplicavel": True,
            "OK": bool(ver) and not reprovados,
            "completo": not nao,
            "nada_verificado": not ver,
            "verificacoes": ver, "nao_verificados": nao,
            "reprovados": reprovados,
            "aplicabilidade": APLICABILIDADE_7_3_1,
            "fonte": "NBR 15575-1:2025 9.2.1-c; 15575-2:2013 7.3.1; "
                     "15575-3:2021 7.5.1; 15575-4:2013 7.2.1"}


def relatorio_pt(r):
    """Quadro-resumo do desempenho NBR 15575."""
    if not r.get("aplicavel"):
        return "DESEMPENHO NBR 15575 - NAO APLICAVEL\n  %s" % r.get("motivo")
    L = ["DESEMPENHO NBR 15575 - edificacao habitacional"]
    v = r["verificacoes"]
    if "topo" in v:
        t = v["topo"]
        L.append("  topo do edificio: %.1f mm <= %.1f mm (%s ; H=%.1f m) -> %s"
                 % (t["u_topo_mm"], t["limite_adotado_mm"], t["governante"],
                    t["H_total_m"], "OK" if t["OK"] else "REPROVADO"))
    if "fissura" in v:
        f = v["fissura"]
        L.append("  fissura: wk = %.2f mm <= %.2f mm (%s) -> %s"
                 % (f["wk_mm"], f["limite_adotado_mm"], f["governante"],
                    "OK" if f["OK"] else "REPROVADO"))
    for x in v.get("flechas", []):
        L.append("  flecha %s: %.1f mm <= %.1f mm (%s ; L=%.2f m) -> %s"
                 % (x["nome"], x["flecha_mm"], x["limite_adotado_mm"],
                    x["governante"], x["L"], "OK" if x["OK"] else "REPROVADO"))
    if "piso_carga_concentrada" in v:
        p = v["piso_carga_concentrada"]
        L.append("  piso sob 1 kN concentrado (%s): %.1f mm <= %.1f mm (%s) -> %s"
                 % (p["acabamento"], p["d_v_mm"], p["limite_mm"], p["expressao"],
                    "OK" if p["OK"] else "REPROVADO"))
    if "fachada" in v:
        fa = v["fachada"]
        L.append("  fachada (%s): d_h = %.1f mm <= %.1f mm (%s) -> %s"
                 % (fa["funcao"], fa["d_h_mm"], fa["limite_dh_mm"],
                    fa["expressao_dh"], "OK" if fa["ok_dh"] else "REPROVADO"))
        if fa.get("aviso"):
            L.append("  ! " + fa["aviso"])
    if r["nao_verificados"]:
        L.append("  NAO VERIFICADOS (dado nao declarado): %s"
                 % ", ".join(r["nao_verificados"]))
    L.append("  RESULTADO: %s" % ("ATENDE" if r["OK"] else "REPROVADO"))
    return "\n".join(L)
