# ============================================================================
# estabilidade_b1b2.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Analise de 2a ordem APROXIMADA pelo Metodo da Amplificacao dos Esforcos
# Solicitantes (MAES), ABNT NBR 8800:2008, Anexo D. Para o portico transversal
# de base rotulada (sway frame), amplifica os esforcos de 1a ordem:
#   Msd = B1*Mnt + B2*Mlt   ;   Nsd = Nnt + B2*Nlt
#   B1 = Cm/(1 - Nsd1/Ne) >= 1   (efeito local P-delta, por barra)
#   B2 = 1/(1 - (1/Rs)*(dh*sumN)/(H*sumH))   (efeito global P-Delta, por andar)
# Decompoe cada combinacao ELU em:
#   nt (no translation): estrutura com contencoes horizontais FICTICIAS nos
#       beirais -> Mnt, Nnt, e a reacao das contencoes (= forca lateral).
#   lt (lateral translation): mesma estrutura, sem as ficticias, carregada com
#       as reacoes ficticias INVERTIDAS -> Mlt, Nlt e o deslocamento dh.
# Classifica a deslocabilidade por B2 (<=1,1 pequena ; <=1,4 media ; >1,4 grande).
# Rs = 0,85 (portico estabilizado pela rigidez a flexao e ligacoes rigidas).
# Saida: esforcos AMPLIFICADOS (Msd, Nsd, Vsd) para alimentar o check_nbr8800.
# NAO verifica perfil (check_nbr8800) nem gera as pressoes de vento (vento_nbr6123).
# Reusa frame2d (com reactions()) e a geometria/cargas do galpao_portico.
# ============================================================================
"""2a ordem aproximada (MAES) conforme NBR 8800 Anexo D. Saidas em portugues.
Calcula apenas; pendente revisao do engenheiro responsavel. Unidades: m, kN."""

from __future__ import annotations

import math
import re

import numpy as np

import frame2d as f2d
import galpao_portico as gp
import vento_nbr6123 as vento

H_STORY = gp.EAVE            # altura do andar (pe-direito ate o beiral)
RS = 0.85                    # Anexo D.2.3: portico de nós rígidos
E = gp.E

# Combinacoes ELU (identicas as do galpao_portico; Q favoravel = 0 no uplift).
COMBOS = {
    "C1_gravidade":   {"G": 1.25, "Q": 1.50, "W2": 0.6 * 1.40},
    "C2_uplift":      {"G": 1.00, "W1": 1.40},
    "C3_vento_Gdesf": {"G": 1.25, "W2": 1.40, "Q": 0.8 * 1.50},
    "C3_vento_Gfav":  {"G": 1.00, "W2": 1.40},
}

# Secoes: (A, I) e comprimento real para o Ne (flambagem no plano do portico).
SEC = {"coluna": {"A": gp.A_COL, "I": gp.I_COL, "L": gp.EAVE},
       "viga":   {"A": gp.A_RAF, "I": gp.I_RAF,
                  "L": math.hypot(gp.SPAN / 2, gp.RIDGE - gp.EAVE)}}

# Cargas gravitacionais VERTICAIS totais do andar (para a forca nocional).
# Aplicadas como UDL vertical por metro de barra sobre as duas aguas.
_L_RAF = SEC["viga"]["L"]
GVERT = (gp.G_ROOF * gp.BAY + gp.RAFTER_SELF) * 2 * _L_RAF   # permanente
QVERT = (gp.Q_ROOF * gp.BAY * gp.COS) * 2 * _L_RAF           # sobrecarga
PVERT = 0.0         # vertical da ponte (para a forca nocional; 0 se sem ponte)
FN_FRAC = 0.003     # 4.9.7.1.1: forca nocional = 0,3% da carga gravitacional


def sincronizar():
    """Recalcula SEC / cargas / H_STORY a partir da geometria atual do
    galpao_portico (apos gp.configurar). Chamado no inicio de analyse()."""
    global _L_RAF, GVERT, QVERT, H_STORY, PVERT
    SEC["coluna"].update(A=gp.A_COL, I=gp.I_COL, L=gp.EAVE)
    SEC["viga"].update(A=gp.A_RAF, I=gp.I_RAF,
                       L=math.hypot(gp.SPAN / 2, gp.RIDGE - gp.EAVE))
    _L_RAF = SEC["viga"]["L"]
    GVERT = (gp.G_ROOF * gp.BAY + gp.RAFTER_SELF) * 2 * _L_RAF
    QVERT = (gp.Q_ROOF * gp.BAY * gp.COS) * 2 * _L_RAF
    PVERT = abs(gp.PONTE["R_vert"]) if gp.PONTE else 0.0
    H_STORY = gp.EAVE


def _forca_nocional(combo):
    """Forca horizontal equivalente (imperfeicao geometrica, 4.9.7.1.1) =
    0,3% da carga gravitacional de cálculo do andar (so G e Q; vento nao entra)."""
    return FN_FRAC * (combo.get("G", 0.0) * GVERT + combo.get("Q", 0.0) * QVERT
                      + combo.get("PONTE", 0.0) * PVERT)


# ---- aplicacao das cargas FATORADAS de um caso sobre um frame --------------
def _apply_case(fr, ix, cs, fac):
    if cs == "G":
        wy = -(gp.G_ROOF * gp.BAY + gp.RAFTER_SELF) * fac
        for e in ix["rafL"] + ix["rafR"]:
            fr.add_member_udl(e, wy=wy)
    elif cs == "Q":
        wy = -(gp.Q_ROOF * gp.BAY * gp.COS) * fac
        for e in ix["rafL"] + ix["rafR"]:
            fr.add_member_udl(e, wy=wy)
    elif cs in ("W1", "W2"):
        key = "portao_barlavento" if cs == "W1" else "portao_sotavento"
        r = vento.compute()
        q = r["q_kN_m2"]
        net = r["net"][key]
        for e in ix["colL"]:
            fr.add_member_udl(e, wx=+net["parede_barlavento"] * q * gp.BAY * fac)
        for e in ix["colR"]:
            fr.add_member_udl(e, wx=-net["parede_sotavento"] * q * gp.BAY * fac)
        for e in ix["rafL"]:
            p = net["cobertura_barlavento"] * q * gp.BAY * fac
            fr.add_member_udl(e, wx=-p * (-gp.SIN), wy=-p * gp.COS)
        for e in ix["rafR"]:
            p = net["cobertura_sotavento"] * q * gp.BAY * fac
            fr.add_member_udl(e, wx=-p * (gp.SIN), wy=-p * gp.COS)
    elif cs == "PONTE" and gp.PONTE:
        p = gp.PONTE
        fr.add_nodal_load(ix["nConsL"], Fy=-abs(p["R_vert"]) * fac,
                          M=p["M_exc"] * fac, Fx=abs(p["H_transv"]) * fac)


def _apply_combo(fr, ix, combo):
    for cs, fac in combo.items():
        _apply_case(fr, ix, cs, fac)


# ---- combinacao nt/lt de um grupo de sub-barras (na MESMA secao) -----------
# Convencao frame2d: mf[e] = [N_i, V_i, M_i, N_j, V_j, M_j] = forcas que a barra
# exerce nos nos. Esforco normal INTERNO (tracao +) = -N_i = +N_j (compressao
# negativa). Amplificacao (Anexo D.2.1): Msd=B1*Mnt+B2*Mlt ; Nsd=Nnt+B2*Nlt ;
# Vsd=Vnt+Vlt (D.2.4, cortante nao amplificado). B1/B2 escalares; combinam-se
# os esforcos de nt e lt na mesma secao (mesmo no), depois toma-se o maximo.
def _combina_grupo(mf_nt, mf_lt, elems, B2, sec, Efac=1.0):
    # 1) Nsd1 (1a ordem) = normal interno MAIS COMPRIMIDO (mais negativo) do grupo
    Nsd1 = 0.0
    for e in elems:
        for Nint in (-(mf_nt[e][0] + mf_lt[e][0]),  # i-end (tracao +)
                     (mf_nt[e][3] + mf_lt[e][3])):   # j-end
            if Nint < Nsd1:
                Nsd1 = Nint
    # media deslocabilidade -> Ne tambem com a rigidez reduzida (4.9.7.1.3)
    Ne = math.pi ** 2 * (E * Efac) * sec["I"] / sec["L"] ** 2
    Cm = 1.0                     # ha cargas transversais na barra (D.2.2)
    B1 = max(Cm / (1.0 - abs(Nsd1) / Ne), 1.0) if Nsd1 < 0 else 1.0
    # 2) combina na mesma secao (i e j de cada sub-barra) e toma o maximo
    Msd = Nsd = Vsd = Mnt = Mlt = 0.0
    for e in elems:
        for im, iN, iV, sgn in ((2, 0, 1, -1.0), (5, 3, 4, +1.0)):
            m = B1 * mf_nt[e][im] + B2 * mf_lt[e][im]
            n = sgn * (mf_nt[e][iN] + B2 * mf_lt[e][iN])   # interno (tracao+)
            v = mf_nt[e][iV] + mf_lt[e][iV]
            Msd = max(Msd, abs(m))
            Nsd = max(Nsd, abs(n))
            Vsd = max(Vsd, abs(v))
            Mnt = max(Mnt, abs(mf_nt[e][im]))
            Mlt = max(Mlt, abs(mf_lt[e][im]))
    return {"B1": B1, "Ne": Ne, "Nsd1": abs(Nsd1), "Mnt": Mnt, "Mlt": Mlt,
            "Msd": Msd, "Nsd": Nsd, "Vsd": Vsd}


def _scale_E(fr, fac):
    """Multiplica EA e EI de todas as barras por 'fac' (media deslocabilidade:
    reduz a rigidez tangencial a 80% - NBR 8800 4.9.7.1.2/4.9.7.1.3)."""
    if fac != 1.0:
        for e in fr.elements:
            e["E"] *= fac


def _analisa_combo(nome, combo, Efac=1.0):
    """Decomposicao nt/lt e coeficientes B1/B2 para uma combinacao.
    Efac<1 aplica a reducao de rigidez da media deslocabilidade.
    A forca nocional (imperfeicao geometrica) e somada no sentido do vento."""
    # ---- estrutura nt: contencao horizontal FICTICIA nos dois beirais ------
    fr, ix = gp._frame()
    _scale_E(fr, Efac)
    fr.add_support(ix["nEaveL"], u=True)     # contencao ficticia (so horizontal)
    fr.add_support(ix["nEaveR"], u=True)
    _apply_combo(fr, ix, combo)
    # 1a resolucao (sem nocional) so para achar o sentido do vento
    fr.solve()
    R0 = fr.reactions()
    Hap = -(R0[3 * ix["nEaveL"]] + R0[3 * ix["nEaveR"]])   # carga lateral aplicada
    sgn = 1.0 if Hap >= 0 else -1.0
    # forca nocional no MESMO sentido do vento (desfavoravel), dividida nos beirais
    Fn = _forca_nocional(combo)
    fr.add_nodal_load(ix["nEaveL"], Fx=sgn * Fn / 2.0)
    fr.add_nodal_load(ix["nEaveR"], Fx=sgn * Fn / 2.0)
    _, mf_nt = fr.solve()
    R_nt = fr.reactions()
    # reacao das contencoes ficticias (horizontal nos beirais)
    Hfict_L = R_nt[3 * ix["nEaveL"]]
    Hfict_R = R_nt[3 * ix["nEaveR"]]
    # carga gravitacional total do andar = reacoes verticais nas bases
    sumN = abs(R_nt[3 * ix["nBaseL"] + 1] + R_nt[3 * ix["nBaseR"] + 1]) \
        if "nBaseL" in ix else None

    # ---- estrutura lt: sem ficticias, carregada com -Hfict nos beirais -----
    fr2, ix2 = gp._frame()
    _scale_E(fr2, Efac)
    fr2.add_nodal_load(ix2["nEaveL"], Fx=-Hfict_L)
    fr2.add_nodal_load(ix2["nEaveR"], Fx=-Hfict_R)
    d_lt, mf_lt = fr2.solve()
    sumH = abs(Hfict_L + Hfict_R)                  # forca lateral total (lt)
    dh = max(abs(d_lt[3 * ix2["nEaveL"]]), abs(d_lt[3 * ix2["nEaveR"]]))

    # ---- B2 (global P-Delta), Anexo D.2.3 ----------------------------------
    if sumH < 1e-9:            # combinacao sem forca lateral liquida
        B2 = 1.0
    else:
        B2 = 1.0 / (1.0 - (1.0 / RS) * (dh * sumN) / (H_STORY * sumH))

    # ---- esforcos amplificados por grupo (coluna / viga) -------------------
    out = {"nome": nome, "B2": B2, "dh": dh, "sumN": sumN, "sumH": sumH, "Fn": Fn}
    # Varre os dois lados juntos: B1 pega a maior compressao e Msd e a envoltoria.
    grupos = {"coluna": ix["colL"] + ix["colR"],
              "viga":   ix["rafL"] + ix["rafR"]}
    for g, elems in grupos.items():
        out[g] = _combina_grupo(mf_nt, mf_lt, elems, B2, SEC[g], Efac)
    return out


def _classe(B2max):
    if B2max <= 1.1:
        return "pequena deslocabilidade (2a ordem dispensavel; ver 4.9.7.1.4)"
    if B2max <= 1.4:
        return "media deslocabilidade (usar B1/B2 com rigidez reduzida a 80%)"
    return "GRANDE deslocabilidade (exige analise rigorosa P-Delta; MAES so a criterio do responsavel)"


def _combos_ativos():
    """COMBOS + combinacoes da ponte (se houver), identicas as do galpao_portico."""
    c = dict(COMBOS)
    if gp.PONTE:
        c["C4_ponte_princ"] = {"G": 1.25, "PONTE": 1.50, "W2": 0.6 * 1.40, "Q": 0.8 * 1.50}
        c["C5_vento_ponte"] = {"G": 1.25, "W2": 1.40, "PONTE": 0.7 * 1.50, "Q": 0.8 * 1.50}
    return c


def analyse():
    sincronizar()          # reflete a geometria/secoes atuais (gp.configurar)
    combos = _combos_ativos()
    # 1o passo: rigidez integral -> classifica a deslocabilidade pelo B2.
    base = [_analisa_combo(n, c, 1.0) for n, c in combos.items()]
    B2max0 = max(r["B2"] for r in base)
    classe = _classe(B2max0)
    # 2o passo: se media (ou grande via MAES), refaz com rigidez reduzida a 80%
    # (4.9.7.1.2) -> esforcos FINAIS. Se pequena, mantem a rigidez integral.
    reduziu = B2max0 > 1.1
    Efac = 0.8 if reduziu else 1.0
    final = [_analisa_combo(n, c, Efac) for n, c in combos.items()] if reduziu else base
    B2max_f = max(r["B2"] for r in final)
    return {"combos": final, "B2max": B2max_f, "B2max0": B2max0,
            "classe": classe, "reduziu": reduziu, "Efac": Efac}


def memoria_pt(a):
    L = ["=" * 70,
         "2a ORDEM - METODO DA AMPLIFICACAO (MAES) - NBR 8800 Anexo D",
         "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL", "=" * 70, "",
         "1. METODO",
         "   Msd = B1*Mnt + B2*Mlt ; Nsd = Nnt + B2*Nlt (D.2.1)",
         "   B1 = Cm/(1 - Nsd1/Ne) >= 1 ; Cm = 1,0 (ha cargas transversais na barra)",
         "   B2 = 1/(1 - (1/Rs)*(dh*sumN)/(H*sumH)) ; Rs = 0,85 (portico de nós rígidos)",
         f"   H (pe-direito) = {H_STORY:.1f} m",
         "   Decomposicao: nt = beirais travados (contencao ficticia) ;",
         "                 lt = reacoes das ficticias aplicadas ao contrario.",
         "   Imperfeicao geometrica: forca nocional = 0,3% da carga gravitacional",
         "   do andar (4.9.7.1.1), somada no sentido do vento em cada combinacao."]
    if a["reduziu"]:
        L += [f"   RIGIDEZ REDUZIDA: media deslocabilidade -> EA e EI x {a['Efac']:.1f}",
              f"   (E = {E*a['Efac']/1e6:.0f} GPa) nos coeficientes e esforcos abaixo",
              f"   (4.9.7.1.2). B2 na rigidez integral = {a['B2max0']:.3f}."]
    else:
        L += ["   Rigidez integral (pequena deslocabilidade - sem reducao)."]
    L += ["", "2. COEFICIENTES POR COMBINACAO (rigidez "
          + ("reduzida 80%" if a["reduziu"] else "integral") + ")"]
    for r in a["combos"]:
        L += [f"   {r['nome']}: B2 = {r['B2']:.3f}  "
              f"(dh={r['dh']*1000:.1f} mm ; sumN={r['sumN']:.1f} kN ; "
              f"sumH={r['sumH']:.1f} kN ; Fnocional={r['Fn']:.2f} kN)"]
        for g in ("coluna", "viga"):
            d = r[g]
            L += [f"     {g}: B1={d['B1']:.3f} (Ne={d['Ne']:.0f} kN ; "
                  f"Nsd1={d['Nsd1']:.1f} kN)",
                  f"        1a ordem Mnt={d['Mnt']:.1f} ; Mlt={d['Mlt']:.1f} kN.m  ->  "
                  f"2a ordem Msd={d['Msd']:.1f} kN.m ; Nsd={d['Nsd']:.1f} ; Vsd={d['Vsd']:.1f}"]
    L += ["", "3. DESLOCABILIDADE",
          f"   Classificacao (rigidez integral): B2,max = {a['B2max0']:.3f}  ->  {a['classe']}"]
    if a["reduziu"]:
        L += [f"   B2,max com rigidez reduzida (final) = {a['B2max']:.3f}"]
    L += ["", "4. ESFORCOS AMPLIFICADOS FINAIS (para o check_nbr8800)"]
    # envoltoria: maior Msd por grupo entre todas as combinacoes
    for g in ("coluna", "viga"):
        best = max(a["combos"], key=lambda r: r[g]["Msd"])
        d = best[g]
        L += [f"   {g.upper()} (governa {best['nome']}): "
              f"Msd={d['Msd']:.1f} kN.m ; Nsd={d['Nsd']:.1f} kN ; Vsd={d['Vsd']:.1f} kN"]
    L += ["", "5. OBSERVACOES"]
    if a["reduziu"]:
        L += ["   - Esforcos finais gerados com a RIGIDEZ TANGENCIAL REDUZIDA em 20%",
              "     (EA e EI x 0,8), conforme media deslocabilidade (4.9.7.1.2)."]
    L += ["   - Imperfeicao geometrica INCLUIDA (forca nocional 0,3%, 4.9.7.1.1).",
          "   - Se GRANDE deslocabilidade (B2>1,4): rigor pede P-Delta real; MAES e limite.",
          "   - Alimentar check_nbr8800 (com K=1, 4.9.6.2) com os Msd/Nsd/Vsd acima."]
    # virgula decimal (PT) sem mastigar numeros de clausula (4.9.7.1.2): so
    # converte digito.digito que NAO faca parte de uma cadeia pontilhada.
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


if __name__ == "__main__":
    print(memoria_pt(analyse()))
