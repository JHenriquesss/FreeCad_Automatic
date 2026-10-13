# ============================================================================
# tanque_base.py - TANQUE-BASE INTEGRAL (SKID) SOB CONTEINER SANITARIO DE 20 PES
# Demanda real de 2026-10-11: documento PRU-CT-SAN-RES-001/2026 REV.01.
#
# Primeira fatia: so' o que sai de GEOMETRIA e de massa especifica - volume,
# niveis, encaixe do tanque dentro do skid e inventario de massas. Nenhum
# veredito estrutural aqui: quadro, chapas, apoios de canto e icamento vem nas
# fatias seguintes. O que ainda falta de fonte e de campo esta' em FONTES_AUSENTES.
#
# Os numeros de SPEC_REV01 sao os do PDF do cliente, que os declara
# "pre-especificacao para orcamento". Sao ENTRADA A CONFERIR, nao premissa.
# ============================================================================
"""Geometria, capacidade e massas do tanque-base integral para conteiner 20 pes."""

# NBR 8800:2024/Er1:2025, 4.6.2.9 e) - lido no MCP_Fontes em 2026-10-11
RHO_ACO = 7850.0  # kg/m3

# Lidos no MCP_Fontes em 2026-10-12:
# NBR 8261:2019, Tabela 4 - limite de escoamento minimo, secao quadrada e retangular
FY_TUBO_RETANGULAR = {"A": 269.0, "B": 317.0, "C": 345.0}  # MPa
# NBR 8261:2019, 4.6.6 - o raio externo do canto nao pode exceder 3 x a espessura.
# A norma nao tabela dimensoes (4.4: "conforme a encomenda"); as propriedades
# saem da geometria com o raio no limite, que e' o caso de MENOR area e inercia.
RAIO_EXTERNO_MAX_SOBRE_T = 3.0
# ISO 1496-1:2013, 5.3.4 - sob 1,8 R a base do conteiner pode descer ate' 6 mm
# abaixo do plano das faces inferiores dos cantos. A tampa do tanque tem de
# ficar mais baixa que isso, ou o piso do conteiner apoia na chapa.
FLECHA_BASE_CONTEINER = 6.0  # mm

# Pendencias de fonte e de dado de campo em 2026-10-12.
FONTES_AUSENTES = (
    "ISO 8501-1 (preparo de superficie para pintura)",
    "vazao e depressao do caminhao de succao (dado do operador)",
    "medicao e tara do conteiner real (dado de campo)",
)

SPEC_REV01 = {
    "documento": "PRU-CT-SAN-RES-001/2026 REV.01",
    "skid": {"comp": 6058.0, "larg": 2438.0, "alt": 600.0},          # mm
    "tanque": {"comp": 5550.0, "larg": 2280.0, "alt": 550.0,         # mm, externo
               "t_fundo": 6.35, "t_lateral": 4.75, "t_tampa": 4.75},
    "baia_tecnica": 400.0,                                           # mm, util
    "quadro": {"h": 150.0, "b": 100.0, "t": 6.35},                   # tubo retangular
    "travessa": {"h": 100.0, "b": 50.0, "t": 4.75, "passo": 600.0},  # passo 500-700
    "niveis": {"alerta": 0.70, "alarme_alto": 0.80, "alarme_alto_alto": 0.90},
    # massa especifica do efluente: ADOTADA igual a da agua; o esgoto com solidos
    # e' pouco mais denso. A confirmar com o responsavel tecnico.
    "rho_efluente": 1000.0,                                          # kg/m3
}


def capacidade(spec):
    """Volume interno BRUTO do reservatorio e a altura de cada nivel.

    Nao desconta diafragmas, enrijecedores internos nem o poco do pescador:
    o PDF nao os define. O volume util real e' menor que o daqui.
    """
    t = spec["tanque"]
    comp = t["comp"] - 2 * t["t_lateral"]
    larg = t["larg"] - 2 * t["t_lateral"]
    alt = t["alt"] - t["t_fundo"] - t["t_tampa"]
    v = comp * larg * alt / 1e9
    niveis = {n: {"fracao": f, "volume_m3": v * f, "lamina_mm": alt * f}
              for n, f in spec["niveis"].items()}
    return {"interno_mm": (comp, larg, alt), "volume_bruto_m3": v, "niveis": niveis,
            "nota": "volume bruto: sem desconto de estrutura interna"}


def encaixe(spec):
    """O tanque, a baia e o quadro perimetral cabem na projecao do skid?

    Confere so' a soma das larguras em planta e a altura. Folga negativa quer
    dizer que as pecas se sobrepoem com as dimensoes declaradas.
    """
    s, t, q = spec["skid"], spec["tanque"], spec["quadro"]
    folga_lateral = (s["larg"] - t["larg"]) / 2 - q["b"]
    folga_longitudinal = s["comp"] - t["comp"] - spec["baia_tecnica"] - 2 * q["b"]
    # o que sobra na altura, descontada a flecha admitida da base do conteiner
    folga_altura = s["alt"] - t["alt"] - FLECHA_BASE_CONTEINER
    itens = {"lateral_por_lado_mm": folga_lateral,
             "longitudinal_total_mm": folga_longitudinal,
             "altura_mm": folga_altura}
    return {"folgas": itens, "cabe": all(v >= 0 for v in itens.values())}


def _retangulo_arredondado(h, b, r):
    """Area e inercias (eixo x horizontal, h vertical) do retangulo de cantos de raio r."""
    import math
    area = h * b - (4 - math.pi) * r * r
    iq = (math.pi / 16 - 4 / (9 * math.pi)) * r ** 4      # quarto de circulo, eixo proprio
    aq = math.pi * r * r / 4
    def inercia(alt, larg):
        quad = r ** 4 / 12 + r * r * (alt / 2 - r / 2) ** 2
        quarto = iq + aq * (alt / 2 - r + 4 * r / (3 * math.pi)) ** 2
        return larg * alt ** 3 / 12 - 4 * quad + 4 * quarto
    return area, inercia(h, b), inercia(b, h)


def tubo_retangular(p, raio_sobre_t=RAIO_EXTERNO_MAX_SOBRE_T):
    """Propriedades geometricas do tubo h x b x t (mm) com cantos arredondados.

    Usa a espessura NOMINAL. A NBR 8261 4.6.3 admite +-12,5 % na parede e a
    NBR 8800 5.1.3 exige no minimo 95 %: a espessura de calculo fica a decidir.
    """
    h, b, t = p["h"], p["b"], p["t"]
    re_ = raio_sobre_t * t
    ri = max(re_ - t, 0.0)
    ae, ixe, iye = _retangulo_arredondado(h, b, re_)
    ai, ixi, iyi = _retangulo_arredondado(h - 2 * t, b - 2 * t, ri)
    area, ix, iy = ae - ai, ixe - ixi, iye - iyi
    return {"A_mm2": area, "Ix_mm4": ix, "Iy_mm4": iy,
            "Wx_mm3": ix / (h / 2), "Wy_mm3": iy / (b / 2),
            "massa_kg_m": area / 1e6 * RHO_ACO, "raio_externo_mm": re_}


def _massa_linear_tubo(p):
    return tubo_retangular(p)["massa_kg_m"]


def massas(spec):
    """Inventario de massas (kg): chapas do tanque, tubos do skid e efluente.

    A massa do conteiner, dos equipamentos e dos usuarios NAO entra: depende da
    tara da placa do conteiner real e das acoes de norma.
    """
    s, t = spec["skid"], spec["tanque"]
    c, l, a = t["comp"], t["larg"], t["alt"]
    chapas = {
        "fundo": c * l * t["t_fundo"],
        "tampa": c * l * t["t_tampa"],
        "laterais": 2 * (c + l) * a * t["t_lateral"],
    }
    chapas = {k: v / 1e9 * RHO_ACO for k, v in chapas.items()}

    perimetro_m = 2 * (s["comp"] + s["larg"]) / 1000
    n_travessas = int(s["comp"] // spec["travessa"]["passo"]) - 1
    tubos = {
        "quadro": perimetro_m * _massa_linear_tubo(spec["quadro"]),
        "travessas": n_travessas * s["larg"] / 1000 * _massa_linear_tubo(spec["travessa"]),
    }

    cap = capacidade(spec)
    efluente = {n: d["volume_m3"] * spec["rho_efluente"] for n, d in cap["niveis"].items()}
    efluente["cheio"] = cap["volume_bruto_m3"] * spec["rho_efluente"]

    aco = sum(chapas.values()) + sum(tubos.values())
    return {"chapas": chapas, "tubos": tubos, "n_travessas": n_travessas,
            "aco_total": aco, "efluente": efluente,
            "nao_incluido": ("conteiner", "equipamentos", "usuarios",
                             "diafragmas e enrijecedores", "apoios de canto")}


def relatorio(spec=None):
    spec = spec or SPEC_REV01
    cap, enc, mas = capacidade(spec), encaixe(spec), massas(spec)
    linhas = ["TANQUE-BASE - %s" % spec["documento"],
              "Volume interno bruto: %.2f m3" % cap["volume_bruto_m3"]]
    for n, d in cap["niveis"].items():
        linhas.append("  %-17s %3.0f %%  %.2f m3  lamina %.0f mm  %.0f kg"
                      % (n, d["fracao"] * 100, d["volume_m3"], d["lamina_mm"],
                         mas["efluente"][n]))
    linhas.append("Encaixe em planta e altura: %s" % ("cabe" if enc["cabe"] else "NAO CABE"))
    for k, v in enc["folgas"].items():
        linhas.append("  folga %-22s %+.0f mm" % (k, v))
    linhas.append("Aco (chapas + tubos, preliminar): %.0f kg" % mas["aco_total"])
    linhas.append("Efluente com o tanque cheio: %.0f kg" % mas["efluente"]["cheio"])
    linhas.append("Pendencias de fonte e de dado de campo:")
    linhas += ["  - " + f for f in FONTES_AUSENTES]
    return "\n".join(linhas)


if __name__ == "__main__":
    print(relatorio())
