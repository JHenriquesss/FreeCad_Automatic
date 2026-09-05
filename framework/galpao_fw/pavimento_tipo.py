# ============================================================================
# pavimento_tipo.py - O QUE ESTE SCRIPT FAZ / CALCULA
# PAVIMENTO-TIPO de edificio: a malha estrutural de um pavimento (pilares nos nos
# da malha, vigas nas linhas, lajes nos paineis) e o encadeamento completo da
# carga ate o pilar, que e o que faltava para o multipavimento (G3):
#
#     carga de uso (NBR 6120 Tab.10)  ->  LAJE  ->  VIGA CONTINUA  ->  PILAR
#
#   1) PAINEIS: cada painel (i,j) e uma laje de lx x ly. A VINCULACAO de cada borda
#      sai da malha, nao de uma escolha manual: borda com painel vizinho e continua
#      (engastada); borda de contorno e simplesmente apoiada. As 9 combinacoes da
#      `laje_concreto` cobrem todos os casos a menos de simetria, e o mapeamento e
#      feito por CONTAGEM de bordas engastadas longas e curtas.
#   2) REACOES NAS VIGAS pelos quinhoes de carga de 14.7.6.1 (charneiras a 45 e 60
#      graus), reusando `laje_concreto.reacoes_apoios`, ja aferido contra os Quadros
#      7.8/7.9 de Carvalho & Figueiredo. As reacoes sao calculadas com carga unitaria
#      e escaladas para g e q SEPARADAMENTE, porque a viga continua precisa das duas
#      parcelas distintas para montar a alternancia de 14.6.6.3.
#   3) VIGAS: cada linha da malha vira uma viga continua de varios tramos
#      (`viga_continua`), carregada pelas lajes dos dois lados + parede + peso
#      proprio. As REACOES DE APOIO dessa viga sao a carga que cada pilar recebe.
#   4) PAREDES: peso do painel de alvenaria pela Tabela 2 da NBR 6120 (kN/m2 DE
#      PAREDE), convertido em carga linear pela altura - nunca multiplicado pela
#      espessura do bloco (ver cargas_nbr6120.carga_linear_parede).
#
# CONFERENCIA DE FECHAMENTO (o analogo do "rotulo x geometria" aqui): a soma das
# reacoes que chegam aos pilares tem de reproduzir a carga total do pavimento, mais
# o peso proprio das vigas. `verifica_fechamento` faz essa conta e o teste reprova
# se sobrar ou faltar carga - e assim que se pega uma laje cuja reacao nao foi
# lancada em nenhuma viga (carga que some em silencio).
#
# Unidades: m, kN. Saidas em portugues.
# ============================================================================
"""Pavimento-tipo de edificio: malha de pilares/vigas/lajes, vinculacao deduzida da
malha, reacoes das lajes (14.7.6.1), vigas continuas (14.6.6) e a carga que chega a
cada pilar."""

from __future__ import annotations

import cargas_nbr6120 as cg
import fissuracao_nbr6118 as fis
import laje_concreto as lj
import viga_continua as vc

GAMMA_CONC = cg.PESO_ESPECIFICO["concreto_armado"]      # 25 kN/m3


def caso_por_bordas(n_eng_longas, n_eng_curtas):
    """Mapeia (nº de bordas LONGAS engastadas, nº de bordas CURTAS engastadas) para o
    caso 1..9 de vinculacao da `laje_concreto`.

    Na convencao da laje_concreto, lx e o MENOR vao; as bordas 'x0'/'x1' tem
    comprimento ly (sao as LONGAS) e 'y0'/'y1' tem comprimento lx (as CURTAS). Os 9
    casos esgotam as combinacoes a menos de simetria, entao basta contar."""
    tabela = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4, (0, 2): 5,
              (2, 0): 6, (1, 2): 7, (2, 1): 8, (2, 2): 9}
    chave = (int(n_eng_longas), int(n_eng_curtas))
    if chave not in tabela:
        raise ValueError("combinacao de bordas engastadas invalida: %s "
                         "(cada contagem deve ser 0, 1 ou 2)" % (chave,))
    return tabela[chave]


class Painel:
    """Um painel de laje da malha, na posicao (i, j)."""

    def __init__(self, i, j, lx_global, ly_global, engastes):
        # engastes: dict com as 4 bordas globais -> bool (True = continua/engastada)
        self.i, self.j = i, j
        self.lx_global = lx_global        # dimensao em X (m)
        self.ly_global = ly_global        # dimensao em Y (m)
        self.engastes = dict(engastes)    # chaves: 'esq','dir','inf','sup'
        self.area = lx_global * ly_global
        # --- traducao para a convencao local da laje_concreto -----------------
        # lx local = MENOR vao. As bordas perpendiculares ao menor vao sao as LONGAS.
        if lx_global <= ly_global:
            self.lx, self.ly = lx_global, ly_global
            # menor vao em X -> bordas 'esq'/'dir' (comprimento ly) sao as LONGAS
            longas, curtas = ("esq", "dir"), ("inf", "sup")
        else:
            self.lx, self.ly = ly_global, lx_global
            longas, curtas = ("inf", "sup"), ("esq", "dir")
        # ORDEM DENTRO DE CADA PAR: a borda ENGASTADA vem primeiro. Os casos da
        # laje_concreto nomeiam explicitamente QUAL borda esta engastada - o caso 4,
        # por exemplo, e ('x0','y0'), com o engaste na PRIMEIRA borda de cada par. Se
        # o par for mapeado em ordem fixa, o painel de canto cujo engaste esta em
        # 'dir'/'sup' recebe a reacao do engaste na borda livre e vice-versa: a carga
        # TOTAL continua fechando (o painel inteiro e distribuido), mas vai para os
        # pilares errados. Foi assim que uma malha 2x2 perfeitamente simetrica saiu
        # com 26,5 kN num canto e 18,5 kN no canto oposto.
        self.longas = tuple(sorted(longas, key=lambda b: not self.engastes[b]))
        self.curtas = tuple(sorted(curtas, key=lambda b: not self.engastes[b]))
        n_long = sum(1 for b in self.longas if self.engastes[b])
        n_curt = sum(1 for b in self.curtas if self.engastes[b])
        self.caso = caso_por_bordas(n_long, n_curt)

    def reacoes_unitarias(self):
        """Reacao em cada borda GLOBAL (kN/m por kN/m2 de carga no painel)."""
        r = lj.reacoes_apoios(self.caso, self.lx, self.ly, 1.0)
        # r vem nas chaves locais x0/x1 (bordas longas) e y0/y1 (curtas); o valor
        # util e r[b]['v'] = reacao media por metro de borda (kN/m por kN/m2).
        return {self.longas[0]: r["x0"]["v"], self.longas[1]: r["x1"]["v"],
                self.curtas[0]: r["y0"]["v"], self.curtas[1]: r["y1"]["v"]}


def monta_paineis(vaos_x, vaos_y):
    """Constroi a matriz de paineis, deduzindo a vinculacao de cada borda da malha:
    borda com painel vizinho -> continua (engastada); borda de contorno -> apoiada."""
    nx, ny = len(vaos_x), len(vaos_y)
    if nx < 1 or ny < 1:
        raise ValueError("a malha precisa de pelo menos um vao em cada direcao")
    if min(list(vaos_x) + list(vaos_y)) <= 0:
        raise ValueError("todos os vaos devem ser > 0")
    paineis = []
    for i in range(nx):
        for j in range(ny):
            eng = {"esq": i > 0, "dir": i < nx - 1,
                   "inf": j > 0, "sup": j < ny - 1}
            paineis.append(Painel(i, j, vaos_x[i], vaos_y[j], eng))
    return paineis


def _carga_do_painel(cfg, painel):
    """(g, q) do painel em kN/m2: permanente (peso proprio da laje + revestimento +
    eventual adicional de paredes sem posicao definida) e variavel (Tabela 10)."""
    h = cfg["h_laje"]
    g = GAMMA_CONC * h + cfg.get("revestimento_kN_m2", 1.0)
    uso = cfg["uso"]
    q = cg.carga_uso(uso)["q"]
    tab11 = None
    pp = cfg.get("parede_sem_posicao_pp")
    if pp:
        tab11 = cg.parede_sem_posicao_definida(pp, q)
        if not tab11["ok"]:
            raise ValueError(
                "paredes divisorias sem posicao definida: %s" % tab11["motivo"])
        q += tab11["adicional_kN_m2"]
    return g, q, tab11


def monta(cfg):
    """Monta o pavimento-tipo e devolve a carga que chega a cada pilar.

    cfg: {
      'vaos_x', 'vaos_y' : listas de vaos da malha (m);
      'h_laje'  : espessura da laje (m);
      'uso'     : chave da Tabela 10 da NBR 6120 (cargas_nbr6120.CARGAS_USO);
      'revestimento_kN_m2' : permanente de revestimento/contrapiso (default 1,0);
      'parede_sem_posicao_pp' : (opc) p.proprio da parede acabada (kN/m) -> Tab.11;
      'b_viga','h_viga' : secao das vigas (m, default 0,20 x 0,50);
      'parede_sobre_vigas' : (opc) {'tipo','espessura_cm','revestimento_cm','altura'}
                    -> carga linear de alvenaria em TODAS as vigas de contorno;
      'fck','fyk' : resistencias (kN/m2);
      'pe_direito': (opc) usado como altura default da parede.
    }

    Retorna {'paineis','vigas_x','vigas_y','pilares','carga_total_kN', ...}."""
    vaos_x, vaos_y = list(cfg["vaos_x"]), list(cfg["vaos_y"])
    nx, ny = len(vaos_x), len(vaos_y)
    b_v, h_v = cfg.get("b_viga", 0.20), cfg.get("h_viga", 0.50)
    fck = cfg.get("fck", 25e3)

    paineis = monta_paineis(vaos_x, vaos_y)

    g_pav, q_pav, tab11 = _carga_do_painel(cfg, paineis[0])

    # --- carga linear que cada painel entrega a cada linha de viga -----------
    # linhas em X: indexadas por j (0..ny), com nx tramos
    # linhas em Y: indexadas por i (0..nx), com ny tramos
    gx = [[0.0] * nx for _ in range(ny + 1)]
    qx = [[0.0] * nx for _ in range(ny + 1)]
    gy = [[0.0] * ny for _ in range(nx + 1)]
    qy = [[0.0] * ny for _ in range(nx + 1)]
    for p in paineis:
        ru = p.reacoes_unitarias()
        # bordas 'inf'/'sup' descarregam nas vigas que correm em X (linhas j e j+1)
        gx[p.j][p.i] += ru["inf"] * g_pav
        qx[p.j][p.i] += ru["inf"] * q_pav
        gx[p.j + 1][p.i] += ru["sup"] * g_pav
        qx[p.j + 1][p.i] += ru["sup"] * q_pav
        # bordas 'esq'/'dir' descarregam nas vigas que correm em Y (linhas i e i+1)
        gy[p.i][p.j] += ru["esq"] * g_pav
        qy[p.i][p.j] += ru["esq"] * q_pav
        gy[p.i + 1][p.j] += ru["dir"] * g_pav
        qy[p.i + 1][p.j] += ru["dir"] * q_pav

    # --- parede sobre as vigas de contorno -----------------------------------
    par = cfg.get("parede_sobre_vigas")
    g_parede = 0.0
    if par:
        alt = par.get("altura", cfg.get("pe_direito", 2.90)) - h_v
        if alt <= 0:
            raise ValueError("altura livre da parede <= 0 (pe-direito menor que a viga)")
        g_parede = cg.carga_linear_parede(par["tipo"], par["espessura_cm"], alt,
                                          par.get("revestimento_cm", 1.0))

    peso_viga = GAMMA_CONC * b_v * h_v          # kN/m

    # --- resolve cada linha de viga ------------------------------------------
    reacoes_pilar = {}                          # (i, j) -> kN (envoltoria)
    reac_g = {}                                 # (i, j) -> kN, so permanente
    reac_q = {}                                 # (i, j) -> kN, so variavel
    vigas_x, vigas_y = [], []

    def _resolve_linha(vaos, g_lin, q_lin, contorno, nome):
        tramos = [{"L": L, "b": b_v, "h": h_v} for L in vaos]
        g = [g_lin[k] + peso_viga + (g_parede if contorno else 0.0)
             for k in range(len(vaos))]
        r = vc.analisa({"tramos": tramos, "g": g, "q": list(q_lin), "fck": fck,
                        "g_area_kN_m2": g_pav, "q_area_kN_m2": q_pav})
        r["nome"] = nome
        # Reacoes SEPARADAS em permanente e variavel. Sao necessarias porque a
        # reducao de cargas variaveis de 6.12 incide APENAS sobre a parcela variavel:
        # aplicar alpha_n sobre a reacao total reduziria tambem o peso proprio, o que
        # a norma nao permite. A analise e linear, entao a superposicao e exata.
        # Para a descida de cargas usa-se o carregamento pleno (a envoltoria de
        # alternancia serve aos esforcos INTERNOS da viga, nao ao normal do pilar).
        vazio = [[] for _ in vaos]
        # EI p/ reacoes separadas g/q (8.2.8, G50): Eci pela primitiva unica ;
        # 0,85 legado de rigidez relativa (C50 bit-a-bit inalterado).
        tramos_ei = [{"L": t["L"],
                      "EI": (0.85 * fis.eci(fck))
                            * b_v * h_v ** 3 / 12.0} for t in tramos]
        rg = vc._analisa_caso(tramos_ei, g, vazio)
        rq = vc._analisa_caso(tramos_ei, list(q_lin), vazio)
        r["reacoes_g"] = rg["reacoes"]
        r["reacoes_q"] = rq["reacoes"]
        # Carga de cada tramo SEPARADA em permanente e variavel, e a secao. Sao
        # os dados que faltavam para montar qualquer combinacao de SERVICO por
        # fora (a analise devolve esforcos, nao o carregamento). O ELS de
        # vibracao do Anexo L da NBR 8800 precisa exatamente disto: g + psi_1*q
        # por tramo, com a viga recalculada como BIAPOIADA.
        r["g_tramos"] = list(g)
        r["q_tramos"] = list(q_lin)
        r["b"] = b_v
        r["h"] = h_v
        # a linha e' de CONTORNO? E' o que decide se ela leva a alvenaria de
        # fechamento - e, com ela, qual limite de flecha da Tabela 13.3 se
        # aplica (L/500 sob parede x L/250 visual). Sem publicar isso, quem
        # verifica a secao depois teria de re-deduzir a condicao a partir do
        # nome da viga, que e' rotulo, nao geometria.
        r["contorno"] = bool(contorno)
        return r

    for j in range(ny + 1):
        contorno = (j == 0 or j == ny)
        r = _resolve_linha(vaos_x, gx[j], qx[j], contorno, "VX-%d" % j)
        vigas_x.append(r)
        for i in range(nx + 1):
            reacoes_pilar[(i, j)] = reacoes_pilar.get((i, j), 0.0) + r["reacoes"][i]
            reac_g[(i, j)] = reac_g.get((i, j), 0.0) + r["reacoes_g"][i]
            reac_q[(i, j)] = reac_q.get((i, j), 0.0) + r["reacoes_q"][i]

    for i in range(nx + 1):
        contorno = (i == 0 or i == nx)
        r = _resolve_linha(vaos_y, gy[i], qy[i], contorno, "VY-%d" % i)
        vigas_y.append(r)
        for j in range(ny + 1):
            reacoes_pilar[(i, j)] = reacoes_pilar.get((i, j), 0.0) + r["reacoes"][j]
            reac_g[(i, j)] = reac_g.get((i, j), 0.0) + r["reacoes_g"][j]
            reac_q[(i, j)] = reac_q.get((i, j), 0.0) + r["reacoes_q"][j]

    area = sum(vaos_x) * sum(vaos_y)
    pilares = []
    for (i, j), N in sorted(reacoes_pilar.items()):
        borda_i = i in (0, nx)
        borda_j = j in (0, ny)
        if borda_i and borda_j:
            posicao = "canto"
        elif borda_i or borda_j:
            posicao = "extremidade"
        else:
            posicao = "interno"
        pilares.append({"i": i, "j": j, "nome": "P%d%d" % (i + 1, j + 1),
                        "posicao": posicao, "N_k": round(N, 2),
                        "N_g_k": round(reac_g[(i, j)], 3),
                        "N_q_k": round(reac_q[(i, j)], 3)})

    return {
        "vaos_x": vaos_x, "vaos_y": vaos_y, "area_m2": round(area, 2),
        "n_paineis": len(paineis), "n_pilares": len(pilares),
        "paineis": [{"i": p.i, "j": p.j, "lx": p.lx_global, "ly": p.ly_global,
                     "caso": p.caso, "engastes": p.engastes,
                     "reacoes_unitarias": p.reacoes_unitarias()} for p in paineis],
        "g_kN_m2": round(g_pav, 3), "q_kN_m2": round(q_pav, 3),
        "tab11": tab11, "g_parede_kN_m": round(g_parede, 3),
        # a SECAO da viga usada na analise. Publicada porque quem monta o modelo
        # 3D/BIM precisa desenhar a MESMA viga que foi calculada; sem isso o
        # emissor teria de re-adivinhar b e h a partir do peso proprio.
        "b_viga": b_v, "h_viga": h_v,
        # a espessura de laje que gerou a carga permanente deste pavimento. E' o
        # que permite conferir, depois, que a laje ADOTADA no dimensionamento e'
        # a mesma que pesou aqui.
        "h_laje_usada": cfg.get("h_laje", 0.10),
        "peso_viga_kN_m": round(peso_viga, 3),
        "vigas_x": vigas_x, "vigas_y": vigas_y,
        "pilares": pilares,
        "N_total_k": round(sum(p["N_k"] for p in pilares), 2),
        "carga_laje_total_kN": round((g_pav + q_pav) * area, 2),
    }


def verifica_fechamento(r, tol=0.02):
    """FECHAMENTO DE CARGA: a soma das reacoes nos pilares tem de reproduzir a carga
    total do pavimento (lajes + peso proprio das vigas + paredes). Sem esta conta, uma
    laje cuja reacao nao foi lancada em nenhuma viga simplesmente SOME - a estrutura
    fica mais leve e nenhum gate de flexao ou cortante reclama.

    Devolve {'ok','N_pilares','carga_esperada','erro_rel','detalhe'}."""
    carga_laje = r["carga_laje_total_kN"]
    comp_x = sum(sum(v["vaos"]) for v in r["vigas_x"])
    comp_y = sum(sum(v["vaos"]) for v in r["vigas_y"])
    carga_vigas = r["peso_viga_kN_m"] * (comp_x + comp_y)
    # paredes: so nas linhas de contorno (2 em X e 2 em Y)
    comp_contorno = 2 * sum(r["vaos_x"]) + 2 * sum(r["vaos_y"])
    carga_paredes = r["g_parede_kN_m"] * comp_contorno
    esperada = carga_laje + carga_vigas + carga_paredes
    N = r["N_total_k"]
    erro = abs(N - esperada) / esperada if esperada > 0 else 0.0
    return {"ok": erro <= tol, "N_pilares": round(N, 2),
            "carga_esperada": round(esperada, 2), "erro_rel": round(erro, 5),
            "detalhe": {"lajes": round(carga_laje, 2), "vigas": round(carga_vigas, 2),
                        "paredes": round(carga_paredes, 2)}}


def relatorio(r):
    """Quadro-resumo do pavimento-tipo."""
    L = ["PAVIMENTO-TIPO - malha %d x %d vaos ; area %.1f m2"
         % (len(r["vaos_x"]), len(r["vaos_y"]), r["area_m2"]),
         "  vaos X: %s m" % ", ".join("%.2f" % v for v in r["vaos_x"]),
         "  vaos Y: %s m" % ", ".join("%.2f" % v for v in r["vaos_y"]),
         "  carga da laje: g = %.2f kN/m2 ; q = %.2f kN/m2" % (r["g_kN_m2"], r["q_kN_m2"])]
    if r["tab11"]:
        L.append("  paredes sem posicao definida (Tab.11): %s" % r["tab11"]["motivo"])
    if r["g_parede_kN_m"]:
        L.append("  parede sobre vigas de contorno: %.2f kN/m" % r["g_parede_kN_m"])
    L += ["", "%-8s %-13s %12s" % ("PILAR", "POSICAO", "N_k (kN)")]
    L.append("-" * 36)
    for p in r["pilares"]:
        L.append("%-8s %-13s %12.1f" % (p["nome"], p["posicao"], p["N_k"]))
    L.append("-" * 36)
    L.append("%-22s %12.1f" % ("TOTAL", r["N_total_k"]))
    f = verifica_fechamento(r)
    L += ["", "Fechamento de carga: %s (pilares %.1f kN x esperado %.1f kN ; "
          "erro %.2f%%)" % ("OK" if f["ok"] else "NAO FECHA", f["N_pilares"],
                            f["carga_esperada"], 100 * f["erro_rel"])]
    return "\n".join(L)
