# ============================================================================
# fundacao_sapata_corrida.py - SAPATA CORRIDA sob parede portante (NBR 6122)
#
# A parede portante entrega carga LINEAR (kN/m) e a sapata isolada entrega
# apoio PONTUAL: sem este modulo o caminho de carga da alvenaria estrutural
# nao tem onde terminar (G61). Dimensiona a largura B pela faixa de 1 m:
# N = q_linear (kN/m) x 1 m, verificada na Parte A de fundacao_sapata
# (tensao no solo + estabilidade, nucleo/borda) e no concreto da Parte B.
#
# REGRA DO G9 INTACTA: SPT e entrada declarada e nao existe default de tensao
# do solo. Sem `sigma_solo_adm` declarada e sem `perfil_spt` que a derive
# (N/50 no bulbo ~2.B, geotecnia_spt), o modulo LEVANTA em vez de arbitrar.
# A declarada vence a derivada do SPT (mesma precedencia de fundacao_edificio).
#
# Unidades: m, kN (sigma em kN/m2). STATELESS, puro.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Sapata corrida sob carga linear: largura B pela faixa de 1 m (NBR 6122)."""

from __future__ import annotations

import math

import fundacao_sapata as fsap
import geotecnia_spt as gspt

# Escada de larguras da corrida (B, h) em m. Altura cresce com B (rigidez
# 22.6.1 e altura util da Parte B); o modulo adota a MENOR que passa.
ESCADA_CORRIDA = [
    (0.40, 0.20),
    (0.50, 0.20),
    (0.60, 0.25),
    (0.80, 0.30),
    (1.00, 0.35),
    (1.20, 0.40),
    (1.50, 0.45),
    (2.00, 0.50),
]

MPA_KNM2 = 1000.0


class EntradaCorrida(ValueError):
    """A entrada declarada nao permite dimensionar a sapata corrida."""


def _positiva(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor > 0)


def sigma_solo(spec_fundacao, B_m):
    """Tensao admissivel (kN/m2): a declarada vence a derivada do SPT.

    Sem nenhuma das duas, LEVANTA (regra do G9): arbitrar sigma e inventar
    o dado que decide toda a fundacao. Com perfil, deriva N/50 no bulbo
    ~2.B abaixo da cota de apoio (geotecnia_spt); N medio < 8 -> None
    (solo fraco: fundacao profunda, nao corrida).
    """
    declarada = spec_fundacao.get("sigma_solo_adm")
    if declarada is not None:
        if not _positiva(declarada):
            raise EntradaCorrida(
                "sigma_solo_adm deve ser numerica > 0 (kN/m2)")
        return float(declarada), "declarada no spec"
    perfil = spec_fundacao.get("perfil_spt")
    if perfil:
        lot = [{"N": c["N"], "dz": c["dz"]} for c in perfil]
        N_med = gspt._n_medio_bulbo(
            lot, spec_fundacao.get("cota_apoio_m", 1.0), float(B_m))
        sig_MPa, nota = gspt.sigma_adm_spt(N_med)
        if sig_MPa is None:
            raise EntradaCorrida(
                "solo fraco na cota de apoio (N medio %.1f < 8 no bulbo "
                "2.B): sapata corrida nao cabe; avaliar fundacao profunda "
                "(NBR 6122)" % N_med)
        return float(sig_MPa * MPA_KNM2), (
            "derivada do SPT (N/50; N medio no bulbo = %.1f; %s)"
            % (N_med, nota))
    raise EntradaCorrida(
        "sem sigma_solo_adm declarada e sem perfil_spt que a derive: "
        "fundacao corrida nao pode ser dimensionada (regra do G9)")


def verifica_corrida_A(q_kN_m, B, h, spec_fundacao, sigma_solo=None):
    """Parte A da faixa de 1 m: N = q x 1 m sob tensao N+M (M = 0, V = 0).

    Devolve o dict de fundacao_sapata.verifica_sapata_A com B, L = 1 m.
    """
    if not _positiva(B) or not _positiva(h):
        raise EntradaCorrida("B e h da corrida devem ser > 0")
    if q_kN_m is None or float(q_kN_m) < 0:
        raise EntradaCorrida("q linear da corrida nao pode ser negativa")
    sig = float(sigma_solo) if sigma_solo else sigma_solo_fn(spec_fundacao, B)[0]
    caso = {
        "N": float(q_kN_m) * 1.0, "V": 0.0, "M": 0.0,
        # B e SEMPRE a largura TRANSVERSAL e L = 1 m a faixa ao longo do muro.
        # Trocar os dois quando B > 1 m (para manter "B = menor lado") troca as
        # DIRECOES na Parte B: o balanco transversal, o unico que existe,
        # passaria a ser medido ao longo do muro. Como M = 0, a Parte A nao
        # depende da ordem; a Parte B depende, e e ela que arma a peca.
        "B": float(B), "L": 1.0,
        "h": float(h),
        "sigma_solo_adm": sig,
        "mu": spec_fundacao.get("mu_solo", 0.5),
        "coesao": spec_fundacao.get("coesao", 0.0),
        "h_reaterro": spec_fundacao.get("cota_apoio_m", 1.0),
        "verificacao_estabilidade":
            spec_fundacao.get("verificacao_estabilidade"),
    }
    r = fsap.verifica_sapata_A(caso)
    r["q_kN_m"] = float(q_kN_m)
    return r


def sigma_solo_fn(spec_fundacao, B_m):
    """Alias importavel da precedencia declarada-vence-SPT."""
    return sigma_solo(spec_fundacao, B_m)


def dimensiona_corrida(q_kN_m, spec_fundacao, escada=None):
    """Adota a MENOR largura da escada que passa a Parte A na faixa de 1 m.

    q_kN_m: carga LINEAR caracteristica (kN/m) no nivel da base da parede
    + baldrame (o peso proprio da corrida entra por dentro via Parte A).
    spec_fundacao: {sigma_solo_adm? | perfil_spt?, cota_apoio_m?, mu_solo?,
    coesao?, ...}. Sem sigma e sem perfil, LEVANTA (G9).
    """
    if q_kN_m is None or not isinstance(q_kN_m, (int, float)) \
            or isinstance(q_kN_m, bool) or float(q_kN_m) < 0:
        raise EntradaCorrida("q linear da corrida deve ser numerica >= 0")
    # G9: a ausencia de solo falha AQUI, antes da escada (fail-closed).
    _trav = spec_fundacao.get("sigma_solo_adm")
    if _trav is None and not spec_fundacao.get("perfil_spt"):
        raise EntradaCorrida(
            "sem sigma_solo_adm declarada e sem perfil_spt que a derive: "
            "fundacao corrida nao pode ser dimensionada (regra do G9)")
    escada = escada or ESCADA_CORRIDA
    linhas, aprovado, parte_B = [], None, None
    for (B, h) in escada:
        sig, prov = sigma_solo(spec_fundacao, B)
        r = verifica_corrida_A(float(q_kN_m), B, h, spec_fundacao,
                               sigma_solo=sig)
        r["proveniencia_sigma"] = prov
        rB = _parte_B(float(q_kN_m), B, h, spec_fundacao) if r["OK_A"] else None
        r["OK_B"] = bool(rB["OK_B"]) if rB else None
        r["rigida"] = bool(rB["rigida"]) if rB else None
        linhas.append(r)
        # A largura adotada tem de passar no SOLO **e** no CONCRETO. A Parte B
        # era calculada e nunca consultada: uma largura que reprovasse a flexao
        # saia adotada com o OK do solo - o irmao do "analisado e nunca
        # verificado" do G13.
        if r["OK_A"] and rB and rB["OK_B"] and aprovado is None:
            aprovado = (B, h, r, {"sigma_solo_adm": sig,
                                  "proveniencia_sigma": prov})
            parte_B = rB
    return {"aprovado": aprovado, "parte_B": parte_B, "linhas": linhas,
            "q_kN_m": float(q_kN_m),
            "tabela": _tabela(linhas, aprovado, float(q_kN_m),
                              spec_fundacao)}


def _parte_B(q_kN_m, B, h, spec_fundacao):
    """Concreto da faixa de 1 m (NBR 6118) sobre a geometria B x 1 m x h.

    Pedestal ficticio: d_ped = 1,0 m corre na direcao L (ao longo do muro),
    onde o balanco e ZERO; b_ped = largura do baldrame corre na direcao B,
    onde esta o unico balanco real, (B - b_ped)/2.
    """
    b_ped = min(float(spec_fundacao.get("b_baldrame_m", 0.15)), B - 0.05)         if B > 0.20 else B / 2.0
    caso_b = {
        "N": float(q_kN_m) * 1.0, "V": 0.0, "M": 0.0,
        "fck": spec_fundacao.get("fck", 25e3),
        "fyk": spec_fundacao.get("fyk", 500e3),
        "cobrimento": spec_fundacao.get("cobrimento", 0.05),
        "gamma_f": spec_fundacao.get("gamma_f", 1.4),
        "d_ped": 1.0, "b_ped": max(b_ped, 0.10),
    }
    return fsap.dimensiona_sapata_B(caso_b, {"B": float(B), "L": 1.0, "h": h})


def quantitativo_corrida(B, h, comprimento_m, parte_B=None):
    """Volume de concreto (m3) e aco (kg) do trecho corrido.

    Mesma convencao de fundacao_sapata.quantitativo: As (m2, por largura)
    x comprimento das barras. A faixa e B x 1 m; o trecho multiplica por
    comprimento_m.
    """
    vol_1m = float(B) * float(h) * 1.0
    aco_1m = 0.0
    if isinstance(parte_B, dict):
        try:
            b_eff = min(float(B), 1.0)
            l_eff = max(float(B), 1.0)
            as_l = float((parte_B.get("flexao_L") or {}).get("As_adot") or 0.0)
            as_b = float((parte_B.get("flexao_B") or {}).get("As_adot") or 0.0)
            aco_1m = as_l * max(b_eff - 0.10, 0.0) + as_b * max(l_eff - 0.10, 0.0)
            aco_1m *= 7850.0
        except (TypeError, ValueError):
            aco_1m = 0.0
    vol = vol_1m * float(comprimento_m)
    aco = aco_1m * float(comprimento_m)
    return {"vol_conc_m3": round(vol, 2), "massa_aco_kg": round(aco, 1),
            "B_m": B, "h_m": h, "L_m": comprimento_m}


def _tabela(linhas, aprovado, q, spec):
    L = ["=" * 78, "DIMENSIONAMENTO DA SAPATA CORRIDA - CARGA LINEAR (NBR 6122)",
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL", "=" * 78, "",
         "q linear caracteristica = %.2f kN/m (faixa de 1 m: N = q x 1 m)"
         % q,
         "Solo: sigma declarada vence SPT (N/50 no bulbo 2.B); sem nenhum, "
         "o modulo recusa (G9).", ""]
    L.append("%10s | %8s %6s %7s %7s | res" % ("Bxh (m)", "sig_max", "u_solo",
                                              "FS_tomb", "FS_desl"))
    L.append("-" * 78)
    for r in linhas:
        tag = ("PASSA" if (r["OK_A"] and r.get("OK_B")) else
               ("solo ok / concreto NAO" if r["OK_A"] else "nao"))
        sm = ("%.0f" % r["sigma_max"]) if r["sigma_max"] else "---"
        L.append("%.2fx%.2f | %8s %6.2f %7.2f %7.2f | %s"
                 % (r["B"], r["h"], sm, r["u_solo"], r["fs_tomb"],
                    r["fs_desl"], tag))
    L += ["-" * 78, ""]
    if aprovado:
        B, h, r, _ = aprovado
        L.append("ADOTADA (menor que passa): B = %.2f m x h = %.2f m "
                 "(sigma_max = %.0f <= %.0f kN/m2, %s)"
                 % (B, h, r["sigma_max"] or 0, r["sigma_adm"],
                    r.get("proveniencia_sigma", "")))
    else:
        L.append("NENHUMA largura da escada passou no solo E no concreto - "
                 "alargar a escada, engrossar h ou usar profunda.")
    L.append("[FLAG] sigma_solo_adm ou perfil SPT: sondagem (geotecnia).")
    return "\n".join(L)


def _selftest():
    spec = {"sigma_solo_adm": 150.0}
    r = dimensiona_corrida(60.0, spec)
    assert r["aprovado"] is not None
    B, h, rA, _ = r["aprovado"]
    assert B * 150.0 >= 60.0, (B, rA["sigma_max"])
    assert rA["OK_A"] is True
    # G9: sem solo, levanta em vez de arbitrar
    try:
        dimensiona_corrida(60.0, {})
        assert False
    except EntradaCorrida as e:
        assert "G9" in str(e) or "perfil_spt" in str(e)
    # SPT deriva quando nao ha declarada
    spec_spt = {"perfil_spt": [{"tipo": "areia", "N": 15, "dz": 6.0}],
                "cota_apoio_m": 1.0}
    r2 = dimensiona_corrida(40.0, spec_spt)
    assert r2["aprovado"] is not None
    print("fundacao_sapata_corrida self-test PASSED")
    return True


if __name__ == "__main__":
    _selftest()
