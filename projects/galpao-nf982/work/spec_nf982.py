# Spec do projeto galpao-nf982 (framework: projeto_spec). Fonte unica da verdade.
# Caminhos RELATIVOS (descoberta da raiz do repo) - roda em qualquer PC.
import sys, math, pathlib
PROJ = pathlib.Path(__file__).resolve().parents[1]          # .../projects/galpao-nf982
REPO = PROJ.parents[1]                                      # raiz do repo
sys.path.insert(0, str(REPO / "framework" / "galpao_fw"))
import projeto_spec as PS
import terreno as T


def build_spec():
    s = PS.novo()
    s["slug"] = "galpao-nf982"
    s["descricao"] = "Deposito 20x10x6, base engastada, ponte leve 100 kN, norte fluminense"
    # --- Gate T (terreno) ---
    kml = str(PROJ / "inputs" / "lote.kml")
    pts = T.parse_kml(kml); xy = T.projeta_metros(pts)
    terr = T.analisa_terreno({"pts_xy": xy, "to_max": 0.60, "ca_max": 1.0,
                              "tp_min": 0.20, "recuo_frente": 5.0,
                              "recuo_lateral": 1.5, "recuo_fundos": 3.0, "n_pav": 1})
    s["terreno"].update(kml=kml, area_lote_m2=terr["area_lote_m2"], to_max=0.60,
                        ca_max=1.0, tp_min=0.20,
                        recuos={"frente": 5.0, "lateral": 1.5, "fundos": 3.0}, n_pav=1)
    s["terreno"]["pts_xy_mm"] = _lote_no_referencial(xy)
    # --- Gate 0 / 1 / 2 ---
    s["geometria"].update(span=10.0, comprimento=20.0, eave=6.0, ridge=6.5,
                         bay=5.0, base_fixed=True)
    s["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal_simples",
                         telha_peso=0.10, calha=True)
    s["estrutura"].update(perfil_col="HEA200", perfil_raf="HEA180",
                         contraventamento="X_extremidades")
    # --- Gate 3 (fechamento paredes) ---
    s["fechamento"].update(tipo="alvenaria_telha", altura_alvenaria=2500.0, peso=0.12)
    # --- Gate 4 (aberturas) ---
    s["aberturas"] = {"portao_frente": (4000.0, 4500.0), "portao_fundo": None,
                      "porta_frente": None, "porta_fundo": (900.0, 2130.0),
                      "porta_lateral": None, "janelas_laterais": (4300.0, 5300.0)}
    # --- Gate 5 (vento/sitio) ---
    s["vento"].update(v0=35.0, cat="II", classe="B", s1=1.0, s3=0.95, z=6.5,
                      abertura_dominante="portao_oitao_frente")
    # --- ponte (Gate 0 -> leve 100 kN) ---
    s["ponte"] = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0,
                  "aprox_min": 1.0, "n_rodas_lado": 2, "phi": 1.10,
                  "frac_lateral": 0.10, "frac_long": 0.10, "d_rodas": 3.0,
                  "siderurgica": False, "excentricidade": 0.30, "Hvr": 4.5}
    # --- cargas ---
    s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.10)
    # --- fundacao (sapata) ---  sigma_solo_adm da sondagem (A CONFIRMAR)
    s["fundacao"]["sigma_solo_adm"] = 200.0        # kN/m2 (= 0,20 MPa)
    # provisorios (confirmar depois)
    PS.marcar_a_confirmar(s, "vento.v0", "terreno.to_max", "terreno.ca_max",
                          "terreno.tp_min", "ponte", "vento.abertura_dominante",
                          "fundacao.sigma_solo_adm")
    return s


def _lote_no_referencial(xy_m):
    """Poligono do lote (m) -> mm no referencial do galpao (OBB alinhado, galpao
    centrado). Mesma transformacao do Gate T."""
    lm, ln, ang = T._obb(xy_m)
    c, si = math.cos(-ang), math.sin(-ang)
    rot = [(x * c - y * si, x * si + y * c) for x, y in xy_m]
    xs = [p[0] for p in rot]; ys = [p[1] for p in rot]
    if (max(xs) - min(xs)) < (max(ys) - min(ys)):
        rot = [(y, -x) for x, y in rot]
        xs = [p[0] for p in rot]; ys = [p[1] for p in rot]
    cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2
    return [(round((x - cx + 10.0) * 1000, 1), round((y - cy + 5.0) * 1000, 1))
            for x, y in rot]


if __name__ == "__main__":
    s = build_spec()
    print(PS.resumo_pt(s))
