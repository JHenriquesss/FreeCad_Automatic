"""D158 - o solver do pilar mais rapido e bit a bit o mesmo.

Medido (D158): uma rodada do predio gastava 99 % do tempo em
`pilar_concreto._resultante_concreto` (500 mil chamadas, 30 milhoes de
`_sigma_c`/`_eps_fibra`); 80,5 % das chamadas de `_N_M_resistente` repetiam
argumentos exatos. A otimizacao tira do laco o que nao depende da fibra e
memoriza `_N_M_resistente` (funcao pura, devolve tupla imutavel).

Por que isto nao e tautologia: a referencia abaixo e o laco ORIGINAL, que
chama as primitivas `_eps_fibra` e `_sigma_c` (inalteradas) por fibra; a
producao nao as chama mais dentro do laco. Se a otimizacao trocar uma
operacao de ponto flutuante de lugar, o `==` quebra.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import pilar_concreto as pc

FCKS = (20e3, 30e3, 45e3, 50e3, 55e3, 60e3, 75e3, 90e3)
SECOES = ((0.20, 0.20, 0.04), (0.20, 0.40, 0.04), (0.30, 0.60, 0.05),
          (0.25, 0.25, 0.035))


def _resultante_referencia(x, b, h, d, fck, n=60):
    """O laco original (antes do D158), fibra a fibra pelas primitivas."""
    fcd = fck / pc.GAMMA_C
    dz = h / n
    Rcc = 0.0
    Mcc = 0.0
    for i in range(n):
        z = (i + 0.5) * dz
        s = pc._sigma_c(pc._eps_fibra(z, x, d, h, fck), fcd, fck)
        f = s * b * dz
        Rcc += f
        Mcc += f * (h / 2.0 - z)
    return Rcc, Mcc


def _profundidades(h, d, fck):
    ecu = pc.eps_cu(fck / 1000.0)
    x23 = d * ecu / (ecu + pc.EPS_SU)
    return (1e-5, 0.05 * h, x23 * 0.999, x23, x23 * 1.001, 0.5 * h,
            0.999 * h, h, 1.001 * h, 3.0 * h / 7.0 + 1e-6, 2.0 * h, 20.0 * h,
            d, d * 0.9999)


def test_01_resultante_bit_a_bit_igual_ao_laco_original():
    """Um assert so: dominios 2, 3/4 e 5, fronteiras x23/h, C20 a C90."""
    quebras = []
    n = 0
    for fck in FCKS:
        for b, h, dl in SECOES:
            d = h - dl
            for x in _profundidades(h, d, fck):
                n += 1
                agora = pc._resultante_concreto(x, b, h, d, fck)
                ref = _resultante_referencia(x, b, h, d, fck)
                if agora != ref:
                    quebras.append("fck=%r b=%r h=%r x=%r: %r != %r"
                                   % (fck, b, h, x, agora, ref))
    assert n > 400, n
    assert not quebras, "D158 mudou numero:\n" + "\n".join(quebras[:20])


def test_02_cache_devolve_o_mesmo_que_a_funcao_sem_cache():
    """Um assert so: `_N_M_resistente` memorizado == a funcao crua, na
    primeira chamada e na repetida (cache quente)."""
    cru = pc._N_M_resistente.__wrapped__
    quebras = []
    for fck in FCKS:
        for b, h, dl in SECOES:
            d = h - dl
            for As in (0.0, 4e-4, 12e-4, 0.08 * b * h):
                for x in _profundidades(h, d, fck):
                    ref = cru(x, As, b, h, dl, fck, 500e3)
                    frio = pc._N_M_resistente(x, As, b, h, dl, fck, 500e3)
                    quente = pc._N_M_resistente(x, As, b, h, dl, fck, 500e3)
                    if not (frio == quente == ref):
                        quebras.append("fck=%r h=%r As=%r x=%r: %r %r %r"
                                       % (fck, h, As, x, ref, frio, quente))
    assert not quebras, "cache D158 divergiu:\n" + "\n".join(quebras[:20])


def test_04_vermelho_uma_operacao_trocada_de_lugar_acusa():
    """O instrumento consegue acusar: a mesma integral com UMA operacao
    reordenada (f*(h/2-z) -> f*h/2 - f*z, algebricamente igual) difere do
    laco original em pelo menos um caso da varredura - o `==` do test_01
    pega ulp, nao so erro grosso."""
    def _reordenada(x, b, h, d, fck, n=60):
        fcd = fck / pc.GAMMA_C
        dz = h / n
        Rcc = 0.0
        Mcc = 0.0
        for i in range(n):
            z = (i + 0.5) * dz
            s = pc._sigma_c(pc._eps_fibra(z, x, d, h, fck), fcd, fck)
            f = s * b * dz
            Rcc += f
            Mcc += f * h / 2.0 - f * z
        return Rcc, Mcc

    diferentes = 0
    for fck in FCKS:
        for b, h, dl in SECOES:
            d = h - dl
            for x in _profundidades(h, d, fck):
                if _reordenada(x, b, h, d, fck) != _resultante_referencia(
                        x, b, h, d, fck):
                    diferentes += 1
    assert diferentes > 0, "a varredura nao distingue uma reordenacao de ulp"


def test_03_armadura_e_momento_iguais_com_cache_frio_e_quente():
    """Um assert so: o dimensionamento completo (bisseccao sobre bisseccao)
    sai igual com o cache limpo e com o cache cheio."""
    casos = [(800.0, 60.0, 0.20, 0.40, 0.04, 30e3, 500e3),
             (1500.0, 20.0, 0.25, 0.25, 0.035, 60e3, 500e3),
             (300.0, 90.0, 0.30, 0.60, 0.05, 90e3, 500e3)]
    pc._N_M_resistente.cache_clear()
    frio = [(pc.armadura_flexao_composta(*c), pc.MRd_para_Nd(c[0], 8e-4, *c[2:]))
            for c in casos]
    quente = [(pc.armadura_flexao_composta(*c), pc.MRd_para_Nd(c[0], 8e-4, *c[2:]))
              for c in casos]
    assert frio == quente, (frio, quente)
