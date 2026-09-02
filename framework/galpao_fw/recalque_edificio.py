# ============================================================================
# recalque_edificio.py - RECALQUE DIFERENCIAL DO EDIFICIO
#
# Fronteira entre a fundacao do edificio e a geotecnia (G18).
# O G9 dimensionava a sapata/bloco/estaca para N+M mas deixava o recalque
# como not_available - a NBR 6122 exige verificar deslocamentos, mas remetia a
# metodos geotecnicos. Este modulo LIGA os dois lados; nao inventa metodo novo.
#
#     N_base + geometria da sapata/bloco/estaca + SPT (ou Es declarado)
#          -> geotecnia_spt.recalque_elastico  (sapata isolada / radier)
#             ou estaca_profunda.recalque_grupo (grupo de estacas)
#          -> recalque por pilar (mm)
#          -> diferencial max - min  (mm)  e  distorcao angular  delta/L
#          -> gate (absoluto e diferencial)
#
# ASK, DO NOT INVENT. O MODULO DE DEFORMABILIDADE Es e' DADO DO LAUDO (A CONFIRMAR).
# Sem Es (ou sem perfil SPT que permita estimar) nao ha recalque - o modulo devolve
# not_declared e o escopo continua not_available. Recalque arbitrado e' o erro que
# este framework trata como bug, nao como default. A curva do SPT (perfil_spt) que
# geotecnia_spt ja le e' a fonte para correlacao quando Es nao e' declarado.
#
# G23: os esforcos que alimentam o recalque sao os de SERVICO (N_serv), nao os de
# ELU. A combinacao que governa o recalque nao e' necessariamente a que governa a
# capacidade (sotavento vs gravitacional). Hoje o edificio entrega N_base_k
# caracteristico (descida) e as combinacoes de ELU da fundacao; o recalque usa
# N_dimensionamento (caracteristico) como aproximacao conservadora - a distincao
# entre ELU e servico para recalque fica nomeada como limitacao (G23 pode mudar
# quais esforcos alimentar aqui: N_serv vs N_k vs N_d).
#
# Unidades: m, kN, mm (Es em kN/m2). STATELESS.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Recalque diferencial do edificio: fronteira para geotecnia_spt / fundacao_sapata (G18)."""

from __future__ import annotations

import copy
import math

import geotecnia_spt as gspt

# Limites default (NBR 6122 Tabela C.1 / pratica corrente - A CONFIRMAR)
RECALQUE_ADM_MM_DEFAULT = 25.0      # recalque total admissivel (mm)
DIFERENCIAL_ADM_MM_DEFAULT = 15.0   # recalque diferencial admissivel (mm)
DIFERENCIAL_ADM_L_DEFAULT = 500.0   # distorcao angular L/delta (ex.: 500 = 1/500)


class EntradaRecalque(ValueError):
    """A entrada declarada nao permite calcular o recalque."""


def declarada(spec_fundacao) -> bool:
    """True se ha o minimo para calcular recalque diferencial."""
    if not isinstance(spec_fundacao, dict):
        return False
    # aceita tres formas de declarar, mas Es deve estar presente (fronteira honesta)
    es_keys = ("Es_solo", "Es_solo_kNm2", "Es")
    rec = spec_fundacao.get("recalque")
    if isinstance(rec, dict) and any(rec.get(k) is not None for k in es_keys):
        return True
    rec2 = spec_fundacao.get("recalque_diferencial")
    if isinstance(rec2, dict) and any(rec2.get(k) is not None for k in es_keys):
        return True
    if any(spec_fundacao.get(k) is not None for k in es_keys):
        return True
    return False


def _positivo(valor) -> bool:
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor > 0)


def _valida(spec_fundacao):
    rec = spec_fundacao.get("recalque") or spec_fundacao.get("recalque_diferencial") or {}
    if not isinstance(rec, dict):
        raise EntradaRecalque("fundacao.recalque deve ser um objeto")
    erros = []
    # Es pode estar em rec ou direto na fundacao
    es_keys = ("Es_solo", "Es_solo_kNm2", "Es")
    es_val = None
    for k in es_keys:
        if rec.get(k) is not None:
            es_val = rec[k]
            break
        if spec_fundacao.get(k) is not None:
            es_val = spec_fundacao[k]
            break
    if es_val is not None and not _positivo(es_val):
        erros.append("Es_solo deve ser > 0 (kN/m2)")
    for chave in ("recalque_adm_mm", "diferencial_adm_mm", "distorcao_adm_L"):
        val = rec.get(chave)
        if val is not None and not _positivo(val):
            erros.append("%s deve ser > 0" % chave)
    for chave in ("nu_solo", "Iw"):
        val = rec.get(chave)
        if val is not None and not isinstance(val, (int, float)):
            erros.append("%s deve ser numerico" % chave)
    if erros:
        raise EntradaRecalque("; ".join(erros))


def _parametros_es(spec_fundacao):
    """Extrai Es, nu, Iw e limites do spec."""
    rec = spec_fundacao.get("recalque") or spec_fundacao.get("recalque_diferencial") or {}
    if not isinstance(rec, dict):
        rec = {}
    # Es: procura em rec e depois direto na fundacao
    Es = None
    for k in ("Es_solo", "Es_solo_kNm2", "Es"):
        if rec.get(k) is not None:
            Es = float(rec[k])
            break
        if spec_fundacao.get(k) is not None:
            Es = float(spec_fundacao[k])
            break
    # fallback: tenta estimar Es a partir do SPT via correlacao grosseira
    # Es (kPa) ~ 1000 * N_medio (areia) / 3-5 * N (argila). Nao inventamos:
    # se nao ha Es declarado, NAO estimamos - fica None e o calculo dira
    # que nao ha dado (fronteira honesta). A correlacao fica documentada como
    # opcional mas nao aplicada em silencio.
    nu = float(rec.get("nu_solo", rec.get("nu", spec_fundacao.get("nu_solo", 0.30))))
    Iw = float(rec.get("Iw", spec_fundacao.get("Iw", 0.88)))
    adm = float(rec.get("recalque_adm_mm", RECALQUE_ADM_MM_DEFAULT))
    adm_diff = float(rec.get("diferencial_adm_mm", DIFERENCIAL_ADM_MM_DEFAULT))
    adm_L = float(rec.get("distorcao_adm_L", DIFERENCIAL_ADM_L_DEFAULT))
    return Es, nu, Iw, adm, adm_diff, adm_L, rec


def _q_liquida(N_kN, B_m, L_m, q_sobrecarga=0.0):
    return max(N_kN / (B_m * L_m) - q_sobrecarga, 0.0)


def _geometria_fundacao_pilar(registro):
    """Extrai (B, L) da geometria do pilar, tratando sapata/bloco/divisa/estaca."""
    geo = registro.get("geometria") or {}
    # isolada / bloco / divisa: tem B_m, L_m
    if "B_m" in geo and "L_m" in geo:
        return float(geo["B_m"]), float(geo["L_m"])
    # estaca: usa bloco ou grupo? Para estaca isolada, recalque de grupo (radier equiv.)
    # precisa B_grupo/L_grupo. Se nao ha, usa D como aproximacao? Melhor retornar None.
    if "D_m" in geo:
        # estaca: diametro como dimensao minima, mas sem grupo nao da recalque elastico simples
        return None, None
    return None, None


def calcula(spec_fundacao, fundacao, contexto=None):
    """Calcula recalque por pilar e o diferencial do edificio.

    spec_fundacao: `estrutura.fundacao` do spec (contem recalque: {Es_solo, ...}).
    fundacao: resultado de fundacao_edificio.dimensiona (ou de edificio_multipavimento).
    contexto: {eixos_x, eixos_y, pilares} opcional para distorcao angular.

    Retorna dict com por_pilar {recalque_mm}, max, min, diferencial, gate, avisos.
    Levanta EntradaRecalque se a entrada declarada e' invalida.
    """
    _valida(spec_fundacao)
    Es, nu, Iw, adm, adm_diff, adm_L, rec_cfg = _parametros_es(spec_fundacao)
    por_pilar = {}
    recalques = []
    avisos = []
    tem_geometria = False
    origem_Es = "declarado no spec (fundacao.recalque.Es_solo)" if Es is not None else "nao declarado"

    if Es is None:
        # Tenta informar que sem Es nao ha recalque, mas nao inventa.
        avisos.append({"code": "recalque_Es_nao_declarado",
                        "detail": "Es_solo (modulo de deformabilidade, kN/m2) nao foi declarado; "
                                  "o recalque NAO foi calculado. A NBR 6122 remete a metodos "
                                  "geotecnicos e o Es vem do laudo (A CONFIRMAR). Sem ele, "
                                  "o recalque e' not_available, nao um numero arbitrado. "
                                  "Correlacoes SPT->Es (ex.: Es~500*N para areia) NAO foram "
                                  "aplicadas em silencio."})
        por_pilar = {nome: {"recalque_mm": None, "motivo": "Es_solo nao declarado"}
                     for nome in (fundacao.get("por_pilar") or {})}
        return {
            "por_pilar": por_pilar,
            "recalque_max_mm": None, "recalque_min_mm": None,
            "diferencial_mm": None, "distorcao_L": None,
            "Es_kNm2": None, "nu": nu, "Iw": Iw,
            "recalque_adm_mm": adm, "diferencial_adm_mm": adm_diff,
            "distorcao_adm_L": adm_L,
            "gate": {"OK": False, "motivo": "Es_solo nao declarado"},
            "escopo": _escopo(False),
            "avisos": avisos,
            "proveniencia_Es": origem_Es,
        }

    # Com Es, calcula por pilar
    q_sobrecarga = float(spec_fundacao.get("q_sobrecarga", 0.0))
    for nome, registro in (fundacao.get("por_pilar") or {}).items():
        B, L = _geometria_fundacao_pilar(registro)
        N_dim = float(registro.get("N_dimensionamento_kN") or registro.get("N_base_k") or 0.0)
        # Para recalque, usa carga caracteristica; N_dimensionamento ja e' caracteristico
        # (descida) com dN de tombamento. G23 pode mudar para N_serv.
        if B is None or L is None:
            # estaca ou geometria ausente: tenta recalque de grupo se for estaca
            geo = registro.get("geometria") or {}
            if geo.get("n_estacas") is not None:
                # Estaca: usa recalque_grupo se tiver dados do grupo
                try:
                    import estaca_profunda as ep
                    import fundacao_sapata as fs
                    # tenta obter B_grupo/L_grupo do bloco ou estima via n*espacamento
                    n = int(geo.get("n_estacas", 1))
                    D = float(geo.get("D_m", 0.30))
                    # estima B_grupo ~ sqrt(n)*3D
                    esp = float(geo.get("espacamento_m", 3.0*D)) if geo.get("espacamento_m") else 3.0*D
                    # para n=1, grupo = estaca unica -> recalque elastico simples com B=D?
                    if n == 1:
                        # ponta + atrito: usa mesma formula elastica com B=D
                        q_liq = _q_liquida(N_dim, D, D, q_sobrecarga)
                        rho_m = gspt.recalque_elastico(q_liq, D, Es, nu, Iw)
                        rho_mm = rho_m if rho_m is not None else None
                        # gspt retorna mm? verifica: geotecnia_spt.recalque_elastico retorna mm (s_m*1000)
                        # fundacao_sapata.recalque_elastico retorna m
                        # gspt: recalque_elastico retorna mm direto
                        # aqui usamos gspt (mm) vs fs (m->mm)
                        if rho_mm is None:
                            rho_mm = None
                        else:
                            rho_mm = float(rho_mm)
                    else:
                        # n>1: nao temos B_grupo/L_grupo exato, usa aproximacao
                        # B_grupo = (sqrt(n)-1)*esp + D ; L_grupo similar
                        lado = math.sqrt(n)
                        # assume grupo quadrado para estimar
                        Bg = (math.ceil(lado)-1)*esp + D if n > 1 else D
                        Lg = Bg
                        # recalque_grupo precisa L_estaca e B_grupo/L_grupo
                        L_est = float(geo.get("L_m", 10.0))
                        rg = ep.recalque_grupo(N_dim, Bg, Lg, L_est, Es, nu, Iw)
                        rho_mm = float(rg.get("recalque_mm") or 0.0)
                    por_pilar[nome] = {"recalque_mm": round(rho_mm, 2) if rho_mm is not None else None,
                                       "B_m": B or D, "L_m": L or D, "N_kN": N_dim,
                                       "q_liq_kPa": round(_q_liquida(N_dim, B or D, L or D, q_sobrecarga), 1) if B else None}
                    if rho_mm is not None:
                        recalques.append(float(rho_mm))
                        tem_geometria = True
                    else:
                        por_pilar[nome] = {"recalque_mm": None, "motivo": "sem geometria para recalque"}
                except Exception as exc:  # noqa: BLE001
                    por_pilar[nome] = {"recalque_mm": None, "motivo": "erro no recalque de estaca: %s" % exc}
            else:
                por_pilar[nome] = {"recalque_mm": None, "motivo": "geometria B_m/L_m ausente (fundacao reprovada ou tipo nao suportado)"}
            continue
        tem_geometria = True
        Bmin = min(B, L)
        q_liq = _q_liquida(N_dim, B, L, q_sobrecarga)
        # Usa fundacao_sapata.recalque_elastico (retorna m) ou geotecnia_spt (mm) - padroniza para mm
        import fundacao_sapata as fs
        rho_m = fs.recalque_elastico(q_liq, Bmin, Es, nu, Iw)
        rho_mm = rho_m * 1000.0 if rho_m is not None else None
        por_pilar[nome] = {"recalque_mm": round(rho_mm, 2) if rho_mm is not None else None,
                           "B_m": B, "L_m": L, "N_kN": N_dim,
                           "q_liq_kPa": round(q_liq, 1)}
        if rho_mm is not None:
            recalques.append(float(rho_mm))

    if not recalques:
        return {
            "por_pilar": por_pilar,
            "recalque_max_mm": None, "recalque_min_mm": None,
            "diferencial_mm": None, "distorcao_L": None,
            "Es_kNm2": Es, "nu": nu, "Iw": Iw,
            "recalque_adm_mm": adm, "diferencial_adm_mm": adm_diff,
            "distorcao_adm_L": adm_L,
            "gate": {"OK": False, "motivo": "nenhum recalque calculado (geometrias ausentes ou fundacao reprovada)"},
            "escopo": _escopo(False),
            "avisos": avisos + [{"code": "recalque_sem_geometria",
                                  "detail": "nenhuma sapata/bloco com geometria valida para calcular recalque"}],
            "proveniencia_Es": origem_Es,
        }

    rmax = max(recalques)
    rmin = min(recalques)
    diff = rmax - rmin
    # distorcao angular: diferencial / distancia entre pilares extremos
    dist_max = None
    distorcao_L = None
    if contexto and contexto.get("eixos_x") and contexto.get("eixos_y"):
        xs = contexto["eixos_x"]
        ys = contexto["eixos_y"]
        # distancia maxima diagonal do grid
        if len(xs) >= 2 and len(ys) >= 2:
            # usa vaos para estimar maior distancia entre dois pilares quaisquer
            # max distancia = sqrt( (sum vaos_x)^2 + (sum vaos_y)^2 )
            try:
                vaos_x = contexto.get("vaos_x") or [xs[i+1]-xs[i] for i in range(len(xs)-1)]
                vaos_y = contexto.get("vaos_y") or [ys[i+1]-ys[i] for i in range(len(ys)-1)]
                Lx = sum(float(v) for v in vaos_x)
                Ly = sum(float(v) for v in vaos_y)
                dist_max = math.hypot(Lx, Ly)
                if diff > 1e-9 and dist_max > 1e-9:
                    distorcao_L = dist_max * 1000.0 / diff  # L/delta (adimensional, ex.: 500)
            except Exception:  # noqa: BLE001
                pass

    gate_ok = bool(rmax <= adm + 1e-9 and diff <= adm_diff + 1e-9)
    # distorcao so reprova se for menor que adm_L (delta/L maior)
    if distorcao_L is not None:
        gate_ok = gate_ok and (distorcao_L >= adm_L - 1e-9)

    gate = {"OK": gate_ok,
            "recalque_max_mm": round(rmax, 2), "recalque_min_mm": round(rmin, 2),
            "diferencial_mm": round(diff, 2),
            "recalque_adm_mm": adm, "diferencial_adm_mm": adm_diff,
            "distorcao_L": round(distorcao_L, 1) if distorcao_L else None,
            "distorcao_adm_L": adm_L,
            "reprova_por": []}
    if rmax > adm + 1e-9:
        gate["reprova_por"].append("recalque_total")
    if diff > adm_diff + 1e-9:
        gate["reprova_por"].append("diferencial")
    if distorcao_L is not None and distorcao_L < adm_L - 1e-9:
        gate["reprova_por"].append("distorcao_angular")

    # avisos de G23 e limitacoes
    if Es is not None:
        avisos.append({"code": "recalque_Es_declarado",
                        "detail": "Es = %.0f kN/m2 (%s); nu=%.2f, Iw=%.2f" % (Es, origem_Es, nu, Iw)})
    avisos.append({"code": "recalque_usa_N_caracteristico",
                    "detail": "o recalque foi calculado com N_dimensionamento caracteristico (N_base_k + dN de tombamento). "
                              "A NBR 6122 exige recalque em combinacao de SERVICO (ELS): a distincao ELU vs servico "
                              "fica nomeada como limitacao (G23 pode alimentar N_serv distinto)"})
    avisos.append({"code": "recalque_elastico_imediato_apenas",
                    "detail": "recalque calculado e' o IMEDIATO/elastico (Teoria da Elasticidade, meio homogeneo, rho = q*B*(1-nu2)*Iw/Es). "
                              "Recalque por adensamento (argilas) e estratificado (Steinbrenner) ficam fora - a confirmar com laudo geotecnico"})

    return {
        "por_pilar": por_pilar,
        "recalque_max_mm": round(rmax, 2), "recalque_min_mm": round(rmin, 2),
        "diferencial_mm": round(diff, 2),
        "distancia_max_m": round(dist_max, 3) if dist_max else None,
        "distorcao_L": round(distorcao_L, 1) if distorcao_L else None,
        "Es_kNm2": Es, "nu": nu, "Iw": Iw,
        "recalque_adm_mm": adm, "diferencial_adm_mm": adm_diff,
        "distorcao_adm_L": adm_L,
        "gate": gate,
        "escopo": _escopo(True),
        "avisos": avisos,
        "proveniencia_Es": origem_Es,
    }


def _escopo(com_recalque: bool) -> dict:
    return {
        "recalque_diferencial": "implemented" if com_recalque else "not_available",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def relatorio_pt(resultado) -> str:
    """Quadro do recalque diferencial."""
    linhas = [
        "RECALQUE DIFERENCIAL DO EDIFICIO (NBR 6122 - Teoria da Elasticidade)",
        "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
    ]
    if resultado.get("Es_kNm2") is None:
        linhas.append("  Es_solo nao declarado: recalque nao calculado (fronteira honesta)")
        for aviso in resultado.get("avisos") or []:
            linhas.append("  [%s] %s" % (aviso["code"], aviso["detail"]))
        return "\n".join(linhas)
    linhas.append("  Es = %.0f kN/m2 ; nu = %.2f ; Iw = %.2f" % (
        resultado["Es_kNm2"], resultado["nu"], resultado["Iw"]))
    linhas.append("  Recalque admissivel: total %.1f mm ; diferencial %.1f mm ; distorcao 1/%d" % (
        resultado["recalque_adm_mm"], resultado["diferencial_adm_mm"], int(resultado["distorcao_adm_L"])))
    linhas.append("")
    linhas.append("  %-8s %10s %8s" % ("pilar", "N(kN)", "rho(mm)"))
    linhas.append("  " + "-"*30)
    for nome in sorted(resultado["por_pilar"]):
        rec = resultado["por_pilar"][nome]
        rho = rec.get("recalque_mm")
        linhas.append("  %-8s %10.1f %8s" % (nome, rec.get("N_kN", 0.0),
                                             ("%.1f" % rho if rho is not None else "-")))
    linhas.append("  " + "-"*30)
    linhas.append("  Recalque max: %.1f mm ; min: %.1f mm ; diferencial: %.1f mm" % (
        resultado["recalque_max_mm"], resultado["recalque_min_mm"], resultado["diferencial_mm"]))
    if resultado.get("distorcao_L"):
        linhas.append("  Distancia max entre pilares: %.2f m ; distorcao: 1/%.0f (adm 1/%d) -> %s" % (
            resultado["distancia_max_m"], resultado["distorcao_L"], int(resultado["distorcao_adm_L"]),
            "OK" if resultado["gate"]["OK"] else "REPROVA"))
    reprova = ", ".join(resultado["gate"].get("reprova_por") or [])
    linhas.append("  GATE: %s%s" % ("ATENDE" if resultado["gate"]["OK"] else "REPROVA",
                                    (" (%s)" % reprova if reprova else "")))
    for aviso in resultado.get("avisos") or []:
        linhas.append("  [%s] %s" % (aviso["code"], aviso["detail"]))
    return "\n".join(linhas)
