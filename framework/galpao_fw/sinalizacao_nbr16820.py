# ============================================================================
# sinalizacao_nbr16820.py - O QUE ESTE SCRIPT FAZ / CALCULA
# SINALIZACAO DE EMERGENCIA do galpao (ABNT NBR 16820:2020), 2o modulo do vertical
# de seguranca contra incendio:
#   1) DIMENSAO x DISTANCIA de visualizacao (5.1): area da placa A > L^2/2000 (L =
#      distancia observador-placa em m, valido L < 50 m, minimo 4 m). Simbolo de
#      orientacao/salvamento quadrado: L = 40 * lado (lado em m) -> 100mm=4m, 150=6m,
#      200=8m, 300=12m, 400=16m (Tab.1). Altura de letra: h > L/125.
#   2) ESPACAMENTO entre placas de orientacao/proibicao/alerta: <= 15 m (risco
#      generalizado, 6.4). Rota continuada no piso: <= 3 m.
#   3) NIVEIS de instalacao: superior >= 1,80 m; intermediario 1,20-1,60 m; inferior
#      0,25-0,50 m (6.3). Tamanho minimo de placa 100x100 mm (L=4 m).
# Valores LIDOS do PDF da NBR 16820:2020 via NotebookLM - NAO de memoria.
# Unidades: distancia em m; lado/altura de placa em mm; area em m2.
# ============================================================================
"""Sinalizacao de emergencia do galpao (NBR 16820:2020): dimensao x distancia de
visualizacao, espacamento de placas e numero de sinais de rota de fuga."""

from __future__ import annotations

import math
from numbers import Real

K_SIMBOLO = 40.0                  # L(m) = 40 * lado(m) p/ orientacao/salvamento (Tab.1)
K_LETRA = 125.0                   # h > L/125 (5.1.3)
ESPACO_PLACAS_M = 15.0           # entre placas (risco generalizado, 6.4)
ESPACO_ROTA_CONTINUA_M = 3.0     # rota continuada no piso (6.5)
DIST_MIN_PROJETO_M = 4.0         # distancia minima de projeto (5.1.1.2)

# lados padronizados de placa quadrada de orientacao/salvamento (mm) -> L (m)
LADOS_PLACA_MM = [100, 150, 200, 250, 300, 400, 600]
NIVEL_SUPERIOR_MIN_M = 1.80      # 6.3.2
NIVEL_INTERMEDIARIO_M = (1.20, 1.60)
NIVEL_INFERIOR_M = (0.25, 0.50)


def _numero_real_finito(nome, valor, *, positivo=True, nao_negativo=False):
    """Valida entradas numéricas sem aceitar bool, NaN ou infinito."""
    if isinstance(valor, bool) or not isinstance(valor, Real):
        raise ValueError(f"{nome} deve ser um número real finito")
    valor = float(valor)
    if not math.isfinite(valor):
        raise ValueError(f"{nome} deve ser um número real finito")
    if positivo and valor <= 0:
        raise ValueError(f"{nome} deve ser positivo")
    if nao_negativo and valor < 0:
        raise ValueError(f"{nome} não pode ser negativo")
    return valor


def distancia_visualizacao(lado_mm):
    """Distancia maxima de visualizacao (m) de uma placa quadrada de orientacao/
    salvamento de lado `lado_mm`: L = 40 * lado(m) = 0,04 * lado(mm)."""
    return K_SIMBOLO * (lado_mm / 1000.0)


def area_minima_placa(L):
    """Area minima da placa (m2) p/ distancia de observacao L (m): A > L^2/2000."""
    return (L ** 2) / 2000.0


def altura_letra_minima_mm(L):
    """Altura minima de letra (mm) p/ distancia L (m): h > L/125."""
    return (L / K_LETRA) * 1000.0


def placa_minima(L_dist):
    """Menor lado padronizado (mm) cuja distancia de visualizacao >= L_dist (m).
    Respeita a distancia minima de projeto de 4 m."""
    L_dist = max(L_dist, DIST_MIN_PROJETO_M)
    for lado in LADOS_PLACA_MM:
        if distancia_visualizacao(lado) >= L_dist:
            return lado
    return LADOS_PLACA_MM[-1]


def numero_placas_orientacao(comprimento_rota, rota_continuada=False):
    """Numero de placas de orientacao ao longo de uma rota (m). Espacamento 15 m
    (placas de parede) ou 3 m (rota continuada no piso). Minimo 2 (origem+destino)."""
    esp = ESPACO_ROTA_CONTINUA_M if rota_continuada else ESPACO_PLACAS_M
    return max(2, math.ceil(comprimento_rota / esp) + 1)


def dimensiona_sinalizacao(caso):
    """Projeta a sinalizacao de rota de fuga do galpao.
    caso: {C, L, dist_visualizacao_m(opc; default = diagonal/2), rota_fuga_m(opc;
           default perimetro), rota_continuada(bool), n_saidas(=2)}.
    Retorna tamanho de placa, area, altura de letra, espacamento e numero de placas."""
    C = _numero_real_finito("C", caso["C"])
    L = _numero_real_finito("L", caso["L"])
    diag = math.hypot(C, L)
    distancia_explicita = "dist_visualizacao_m" in caso
    if distancia_explicita:
        L_vis = _numero_real_finito("dist_visualizacao_m", caso["dist_visualizacao_m"])
        if L_vis >= 50.0:
            raise ValueError("dist_visualizacao_m deve ser menor que 50 m")
    else:
        L_vis = diag / 2.0

    area_informada = "area_placa_m2" in caso
    area_placa = (None if not area_informada else
                  _numero_real_finito("area_placa_m2", caso["area_placa_m2"],
                                      positivo=False, nao_negativo=True))
    limite_normativo_excedido = not distancia_explicita and L_vis >= 50.0
    distancia_calculo = None if limite_normativo_excedido else max(L_vis, DIST_MIN_PROJETO_M)
    area_minima = (None if distancia_calculo is None else area_minima_placa(distancia_calculo))
    area_atende = (None if not area_informada or area_minima is None
                   else area_placa > area_minima)
    lado = placa_minima(L_vis)
    rota = float(caso.get("rota_fuga_m", 2.0 * (C + L)))
    continua = bool(caso.get("rota_continuada", False))
    n_placas = numero_placas_orientacao(rota, rota_continuada=continua)
    n_saidas = int(caso.get("n_saidas", 2))
    # placa_minima satura no maior lado padronizado (600 mm) quando NENHUM cobre
    # L_vis; sem esta checagem a placa sairia subdimensionada com OK=True (rota longa
    # em galpao grande, L_vis > 24 m). O OK exige que a placa ADOTADA cubra L_vis.
    satura = distancia_visualizacao(lado) < L_vis - 1e-9
    ok_area = area_atende is not False
    return {"dist_visualizacao_m": L_vis, "placa_lado_mm": lado,
            "placa_area_min_m2": (None if area_minima is None else round(area_minima, 3)),
            "letra_min_mm": round(altura_letra_minima_mm(L_vis), 1),
            "espacamento_m": ESPACO_ROTA_CONTINUA_M if continua else ESPACO_PLACAS_M,
            "N_placas_orientacao": n_placas, "N_placas_saida": n_saidas,
            "nivel_instalacao_m": NIVEL_SUPERIOR_MIN_M, "placa_satura": satura,
            "N_total": n_placas + n_saidas, "OK": lado >= 100 and not satura and ok_area,
            "distancia_calculo_m": distancia_calculo,
            "area_minima_m2": area_minima,
            "area_placa_m2": area_placa,
            "area_atende": area_atende,
            "limite_normativo_excedido": limite_normativo_excedido}


def _selftest():
    """Afere contra a NBR 16820:2020 (Tab.1 + relacoes 5.1)."""
    # distancia de visualizacao (Tab.1): 100mm->4m, 300mm->12m, 400mm->16m
    assert distancia_visualizacao(100) == 4.0
    assert distancia_visualizacao(300) == 12.0 and distancia_visualizacao(400) == 16.0
    # area minima da placa p/ L=4m: 16/2000 = 0,008 m2
    assert abs(area_minima_placa(4.0) - 0.008) < 1e-9
    # altura de letra p/ L=4m: 4/125*1000 = 32 mm
    assert abs(altura_letra_minima_mm(4.0) - 32.0) < 1e-9
    # menor placa p/ 10 m de visualizacao -> 250 mm (0,04*250=10)
    assert placa_minima(10.0) == 250
    assert placa_minima(2.0) == 100                 # respeita minimo de 4 m -> 100mm
    # numero de placas: rota 60 m, 15 m -> 5 ; rota continuada 3 m -> 21
    assert numero_placas_orientacao(60.0) == 5
    assert numero_placas_orientacao(60.0, rota_continuada=True) == 21
    # projeto do galpao 40x20 (diagonal ~44,7 -> L_vis ~22,4 -> placa 600mm)
    r = dimensiona_sinalizacao({"C": 40.0, "L": 20.0})
    assert r["placa_lado_mm"] == 600 and r["OK"] and not r["placa_satura"]
    assert r["nivel_instalacao_m"] == 1.80
    # galpao grande: L_vis > 24 m (dist. da maior placa 600mm) -> satura e REPROVA
    # em vez de entregar placa subdimensionada com OK=True (contra-seguranca).
    rg = dimensiona_sinalizacao({"C": 100.0, "L": 60.0})   # diag ~116,6 -> L_vis ~58,3
    assert rg["placa_lado_mm"] == 600 and rg["placa_satura"] and not rg["OK"]
    print("sinalizacao_nbr16820 self-test PASSED (NBR 16820:2020 Tab.1 + 5.1)")


if __name__ == "__main__":
    _selftest()
