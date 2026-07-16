# ============================================================================
# validacao.py - SELO DE CONFIABILIDADE (benchmarks independentes)
# Confere o NUCLEO do framework contra solucoes que NAO dependem do proprio
# framework: formulas fechadas e principios de equilibrio. E o "cross-check"
# que separa "roda" de "confio": se o solver, o equilibrio e as formulas de
# norma batem com o resultado analitico, a base esta aferida.
#   1) frame2d vs forma fechada (cantilever PL^3/3EI, M=PL; viga SS M=wL^2/8).
#   2) EQUILIBRIO GLOBAL do portico: soma das reacoes verticais = soma das
#      cargas aplicadas (gravidade) ; soma das reacoes horizontais = carga
#      horizontal aplicada (vento) - independente do metodo de rigidez.
#   3) Vento NBR 6123: Vk = V0*S1*S2*S3 e q = 0,613*Vk^2 batem com o modulo.
# NAO cobre a validacao de SISTEMA contra projeto real/comercial (isso exige um
# caso-referencia externo - ver validacao_referencia()). Estes checks provam o
# NUCLEO, nao o dimensionamento normativo completo.
# ============================================================================
"""Benchmarks independentes (forma fechada + equilibrio + formula) do nucleo."""

from __future__ import annotations

import math

TOL = 1e-6          # tolerancia relativa dos checks analiticos exatos


def check_frame2d():
    """frame2d contra forma fechada (o proprio selftest do modulo já compara
    cantilever e viga biapoiada)."""
    import frame2d
    frame2d._selftest()          # levanta AssertionError se divergir
    return ("frame2d vs forma fechada (cantilever + viga SS)", True, 0.0,
            "PL^3/3EI, M=PL, wL^2/8 conferem < 1e-3")


def _equilibrio_caso(load_fn, eixo):
    """Roda um caso de carga no portico de referencia e compara a soma das
    reacoes (eixo=1 vertical, 0 horizontal) com a resultante aplicada."""
    import galpao_portico as gp
    fr, ix = gp._frame()
    load_fn(fr, ix)
    d, mf = fr.solve()
    R = fr.reactions()
    # resultante APLICADA no eixo: nodais + UDL (wy*L ou wx*L por elemento)
    aplicado = 0.0
    for nd, (fx, fy, m) in fr.nodal_loads.items():
        aplicado += fy if eixo == 1 else fx
    for eidx, (wx, wy) in fr.member_udl.items():
        (xi, yi) = fr.nodes[fr.elements[eidx]["i"]]
        (xj, yj) = fr.nodes[fr.elements[eidx]["j"]]
        L = math.hypot(xj - xi, yj - yi)
        aplicado += (wy if eixo == 1 else wx) * L
    # resultante das REACOES no eixo (todos os apoios)
    reacao = 0.0
    for b in ix["nBases"]:
        reacao += R[3 * b + eixo]
    return aplicado, reacao


def check_equilibrio_gravidade():
    """Equilibrio vertical sob carga permanente G (ref 20x10). A convencao de
    sinal do reactions() do frame2d devolve a reacao com o MESMO sinal da carga;
    o equilibrio e |soma das cargas| = |soma das reacoes| (1a lei de Newton)."""
    import framework as FW
    import galpao_portico as gp
    FW.reset_tudo()
    gp.configurar(span=10.0, eave=6.0, ridge=6.5, bay=5.0, base_fixed=True,
                  G_roof=0.27, rafter_self=0.35)
    aplicado, reacao = _equilibrio_caso(gp.case_G, eixo=1)
    ref = max(abs(aplicado), 1e-9)
    err = abs(abs(aplicado) - abs(reacao)) / ref
    return ("Equilibrio VERTICAL do portico (carga G)", err < 1e-6, err,
            f"|carga aplicada|={abs(aplicado):.3f} kN ; "
            f"|reacoes|={abs(reacao):.3f} kN ; residuo={err:.2e}")


def check_equilibrio_horizontal():
    """Equilibrio horizontal: aplica uma carga horizontal CONHECIDA nos beirais e
    confere que a soma das reacoes horizontais a equilibra. Independente do modulo
    de vento (testa a direcao horizontal do solver)."""
    import framework as FW
    import galpao_portico as gp
    FW.reset_tudo()
    gp.configurar(span=10.0, eave=6.0, ridge=6.5, bay=5.0, base_fixed=True)

    def _horiz(fr, ix):
        for nd in ix["nEaves"]:
            fr.add_nodal_load(nd, Fx=10.0)      # 10 kN/beiral, conhecido
    aplicado, reacao = _equilibrio_caso(_horiz, eixo=0)
    ref = max(abs(aplicado), 1e-9)
    err = abs(abs(aplicado) - abs(reacao)) / ref
    return ("Equilibrio HORIZONTAL do portico (carga conhecida)", err < 1e-6, err,
            f"|carga aplicada|={abs(aplicado):.3f} kN ; "
            f"|reacoes|={abs(reacao):.3f} kN ; residuo={err:.2e}")


def check_vento_formula():
    """Vk = V0*S1*S2*S3 e q = 0,613*Vk^2 (NBR 6123) batem com o modulo."""
    import framework as FW
    import vento_nbr6123 as vento
    FW.reset_tudo()
    r = vento.compute(v0=40.0, cat="II", classe="B", s1=1.0, s3=0.95, z=6.5)
    vk_esp = r["v0"] * r["s1"] * r["s2"] * r["s3"]
    q_esp = 0.613 * vk_esp ** 2 / 1000.0
    err_vk = abs(r["vk"] - vk_esp) / vk_esp
    err_q = abs(r["q_kN_m2"] - q_esp) / q_esp
    ok = err_vk < 1e-2 and err_q < 1e-2      # r arredondado a 2-3 casas
    return ("Vento NBR 6123: Vk=V0*S1*S2*S3 ; q=0,613*Vk^2", ok, max(err_vk, err_q),
            f"Vk={r['vk']} (esp {vk_esp:.2f}) ; q={r['q_kN_m2']} kN/m2 "
            f"(esp {q_esp:.3f})")


def check_b1_amplificacao():
    """MAES B1 (2a ordem local, NBR 8800 Anexo D) contra a forma fechada:
    Ne = pi^2*E*I/L^2 e B1 = Cm/(1 - Nsd/Ne). Alimenta o proprio _combina_grupo
    com um esforco axial de compressao CONHECIDO (N = 0,5*Ne -> B1 = 2,0)."""
    import estabilidade_b1b2 as est
    I, L = 3692e-8, 6.0                       # HEA200, coluna de 6 m
    Ne_esp = math.pi ** 2 * est.E * I / L ** 2
    N = 0.5 * Ne_esp                          # -> B1 esperado = 1/(1-0,5) = 2,0
    # esforcos de barra sinteticos: axial de compressao N no elemento 0
    mf_nt = {0: [N, 0.0, 100.0, -N, 0.0, 0.0]}   # [N_i,V_i,M_i,N_j,V_j,M_j]
    mf_lt = {0: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}
    r = est._combina_grupo(mf_nt, mf_lt, [0], B2=1.0, sec={"I": I, "L": L})
    err_ne = abs(r["Ne"] - Ne_esp) / Ne_esp
    err_b1 = abs(r["B1"] - 2.0) / 2.0
    ok = err_ne < 1e-9 and err_b1 < 1e-9
    return ("MAES B1 (2a ordem) vs forma fechada Cm/(1-Nsd/Ne)", ok,
            max(err_ne, err_b1),
            f"Ne={r['Ne']:.1f} kN (esp {Ne_esp:.1f}) ; B1={r['B1']:.4f} (esp 2,0)")


CHECKS = [check_frame2d, check_equilibrio_gravidade, check_equilibrio_horizontal,
          check_b1_amplificacao, check_vento_formula]


def rodar(verbose=True):
    """Roda todos os benchmarks. Retorna (ok_geral, resultados)."""
    resultados = []
    for fn in CHECKS:
        try:
            nome, ok, err, det = fn()
        except Exception as ex:
            nome, ok, err, det = fn.__name__, False, float("nan"), f"ERRO: {ex}"
        resultados.append((nome, ok, err, det))
    ok_geral = all(ok for _n, ok, _e, _d in resultados)
    if verbose:
        print("=" * 70)
        print("VALIDACAO DO NUCLEO - benchmarks independentes (forma fechada +")
        print("equilibrio + formula de norma). NAO substitui a validacao de")
        print("SISTEMA contra projeto real (ver validacao_referencia).")
        print("=" * 70)
        for nome, ok, err, det in resultados:
            tag = "PASS" if ok else "FALHA"
            print(f"[{tag}] {nome}")
            print(f"        {det}")
        print("=" * 70)
        print(f"RESULTADO: {'TODOS OS BENCHMARKS PASSARAM' if ok_geral else 'HA FALHAS'}")
    return ok_geral, resultados


def validacao_referencia():
    """PLACEHOLDER da validacao de SISTEMA: comparar reacoes/esforcos/perfis
    adotados contra um projeto real aprovado OU software comercial (mCalc/STRAP/
    SAP). Requer um caso-referencia EXTERNO (dados + resultados esperados). Ainda
    nao disponivel - ver tarefa 'Validacao de confianca contra referencia'."""
    raise NotImplementedError(
        "Forneca um caso-referencia (geometria + cargas + resultados esperados) "
        "para a validacao de sistema.")


if __name__ == "__main__":
    ok, _ = rodar()
    import sys
    sys.exit(0 if ok else 1)
