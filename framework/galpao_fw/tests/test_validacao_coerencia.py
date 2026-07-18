# ============================================================================
# test_validacao_coerencia.py - o caminho SPEC-DIRETO (carregar_spec/JSON editado)
# nao pode CERTIFICAR geometria/fisica degenerada. Antes da guarda de coerencia
# em projeto_spec.validar(), specs com span<0, ridge<=eave, slope<=0, V0=0,
# aguas invalido ou abertura > fachada passavam e o motor dava atende_global=True
# (ou crashava em eave=0). Ver cacada de bugs sessao 14.
# ============================================================================
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


def _base():
    """Spec de amostra COMPLETO e valido (fundacao=bloco). validar() -> ok."""
    p = os.path.join(GALPAO, "spec_amostra_engenheiro.json")
    return json.load(open(p, encoding="utf-8"))


def _bloqueado_em(spec, path_prefixo):
    """True se validar() reprova (ok=False) por causa de um item cujo path
    comeca com path_prefixo."""
    r = PS.validar(spec)
    if r["ok"]:
        return False
    return any(p == path_prefixo or p.startswith(path_prefixo) for p, _ in r["faltando"])


def test_amostra_valida_passa():
    """Sanidade: o spec de amostra (valido) NAO e barrado pela guarda."""
    r = PS.validar(_base())
    assert r["ok"], ("amostra valida bloqueada: %s" % r["faltando"])


def test_span_negativo_bloqueia():
    s = _base(); s["geometria"]["span"] = -20.0
    assert _bloqueado_em(s, "geometria.span")


def test_dimensoes_nao_positivas_bloqueiam():
    for campo in ("comprimento", "eave", "bay"):
        s = _base(); s["geometria"][campo] = 0.0
        assert _bloqueado_em(s, "geometria." + campo), campo


def test_ridge_menor_igual_eave_bloqueia():
    # invertido
    s = _base(); s["geometria"]["ridge"] = s["geometria"]["eave"] - 1.0
    assert _bloqueado_em(s, "geometria.ridge")
    # plano (ridge == eave)
    s = _base(); s["geometria"]["ridge"] = s["geometria"]["eave"]
    assert _bloqueado_em(s, "geometria.ridge")


def test_slope_nao_positivo_bloqueia():
    for sl in (0.0, -0.1):
        s = _base(); s["cobertura"]["slope"] = sl
        assert _bloqueado_em(s, "cobertura.slope"), sl


def test_aguas_invalido_bloqueia():
    s = _base(); s["cobertura"]["aguas"] = 3
    assert _bloqueado_em(s, "cobertura.aguas")


def test_v0_abaixo_do_mapa_bloqueia():
    s = _base(); s["vento"]["v0"] = 0.0
    assert _bloqueado_em(s, "vento.v0")
    s = _base(); s["vento"]["v0"] = 25.0
    assert _bloqueado_em(s, "vento.v0")


def test_v0_no_limite_passa():
    s = _base(); s["vento"]["v0"] = 30.0
    r = PS.validar(s)
    assert r["ok"], r["faltando"]


def test_abertura_maior_que_fachada_bloqueia():
    # portao 50 x 40 m num galpao 28,5 x 20 m
    s = _base(); s["aberturas"]["portao_frente"] = [50000.0, 40000.0]
    assert _bloqueado_em(s, "aberturas.portao_frente")


def test_spans_multivao_nao_positivo_bloqueia():
    s = _base(); s["geometria"]["spans"] = [20.0, -5.0]
    assert _bloqueado_em(s, "geometria.spans")


def test_abertura_normal_nao_bloqueia():
    # a amostra ja tem portao 4,5x2,5 e janela 3,0x1,0 - devem passar
    r = PS.validar(_base())
    assert not any(p.startswith("aberturas.") for p, _ in r["faltando"])


# --- plausibilidade fisica (limites duros no gate, nao so no wizard) ---------
def test_sigma_solo_absurdo_bloqueia():
    # typo classico: 5000 em vez de 500 kPa -> fundacao subdimensionada. CRITICO.
    s = _base(); s["fundacao"]["sigma_solo_adm"] = 5000.0
    assert _bloqueado_em(s, "fundacao.sigma_solo_adm")
    # limite inferior tambem (solo ridiculamente fraco / typo)
    s = _base(); s["fundacao"]["sigma_solo_adm"] = 5.0
    assert _bloqueado_em(s, "fundacao.sigma_solo_adm")


def test_sigma_solo_normal_passa():
    for sig in (150.0, 500.0, 1500.0):
        s = _base(); s["fundacao"]["sigma_solo_adm"] = sig
        assert PS.validar(s)["ok"], sig


def test_span_implausivel_bloqueia():
    s = _base(); s["geometria"]["span"] = 200.0
    assert _bloqueado_em(s, "geometria.span")


def test_eave_incomum_mas_aceito_nao_bloqueia():
    # eave=25 m e banda "aviso" (tipico ate 15, duro ate 30): NAO bloqueia.
    s = _base(); s["geometria"]["eave"] = 25.0; s["geometria"]["ridge"] = 26.5
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]


def test_v0_teto():
    s = _base(); s["vento"]["v0"] = 59.0   # aviso, aceito
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]
    s = _base(); s["vento"]["v0"] = 65.0   # implausivel
    assert _bloqueado_em(s, "vento.v0")


def test_cargas_absurdas_bloqueiam():
    s = _base(); s["cargas"]["G"] = 10.0
    assert _bloqueado_em(s, "cargas.G")
    s = _base(); s["cargas"]["Q"] = 20.0
    assert _bloqueado_em(s, "cargas.Q")


def test_slope_teto():
    s = _base(); s["cobertura"]["slope"] = 1.5
    assert _bloqueado_em(s, "cobertura.slope")


# --- coerencia dos dados de fabricante da ponte rolante ----------------------
def _base_ponte():
    s = _base()
    s["ponte"] = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0,
                  "aprox_min": 1.0, "n_rodas_lado": 2, "n_rodas_motoras": 2,
                  "frac_lateral": 0.10, "frac_long": 0.10, "phi": 1.10,
                  "vao_ponte": 9.5, "vao_viga": 5.7}
    return s


def test_ponte_valida_passa():
    r = PS.validar(_base_ponte())
    assert r["ok"], r["faltando"]


def test_ponte_vao_zero_bloqueia():
    s = _base_ponte(); s["ponte"]["vao_ponte"] = 0.0
    assert _bloqueado_em(s, "ponte.vao_ponte")


def test_ponte_aprox_min_alem_do_trilho_bloqueia():
    # aprox_min > vao_ponte gerava reacao de roda NEGATIVA com OK=True
    s = _base_ponte(); s["ponte"]["aprox_min"] = 12.0
    assert _bloqueado_em(s, "ponte.aprox_min")


def test_ponte_Q_negativo_bloqueia():
    s = _base_ponte(); s["ponte"]["Q"] = -100.0
    assert _bloqueado_em(s, "ponte.Q")


def test_ponte_n_rodas_lado_zero_bloqueia():
    s = _base_ponte(); s["ponte"]["n_rodas_lado"] = 0
    assert _bloqueado_em(s, "ponte.n_rodas_lado")


def test_ponte_motoras_acima_do_lado_bloqueia():
    s = _base_ponte(); s["ponte"]["n_rodas_motoras"] = 5
    assert _bloqueado_em(s, "ponte.n_rodas_motoras")


def test_ponte_fracoes_fora_de_faixa_bloqueiam():
    s = _base_ponte(); s["ponte"]["frac_lateral"] = 2.0
    assert _bloqueado_em(s, "ponte.frac_lateral")
    s = _base_ponte(); s["ponte"]["frac_long"] = 0.0
    assert _bloqueado_em(s, "ponte.frac_long")


def test_ponte_phi_menor_que_um_bloqueia():
    s = _base_ponte(); s["ponte"]["phi"] = 0.8
    assert _bloqueado_em(s, "ponte.phi")


# --- coerencia da tesoura (trelica) ------------------------------------------
def _base_tesoura():
    s = _base()
    s["estrutura"]["tipo_portico"] = "tesoura"
    s["estrutura"]["trelica"] = {
        "h": 2.5, "n_paineis": 8, "tipo": "warren",
        "perfil_banzo": [0.20, 0.10, 0.006, 0.008],
        "perfil_diagonal": [0.15, 0.075, 0.005, 0.006]}
    return s


def test_tesoura_valida_passa():
    r = PS.validar(_base_tesoura())
    assert r["ok"], r["faltando"]


def test_tesoura_h_nao_positiva_bloqueia():
    for h in (0.0, -2.5):
        s = _base_tesoura(); s["estrutura"]["trelica"]["h"] = h
        assert _bloqueado_em(s, "estrutura.trelica.h"), h


def test_tesoura_n_paineis_impar_bloqueia():
    s = _base_tesoura(); s["estrutura"]["trelica"]["n_paineis"] = 7
    assert _bloqueado_em(s, "estrutura.trelica.n_paineis")


def test_tesoura_n_paineis_zero_bloqueia():
    # 0 e PAR mas degenera a trelica (ZeroDivisionError no motor)
    s = _base_tesoura(); s["estrutura"]["trelica"]["n_paineis"] = 0
    assert _bloqueado_em(s, "estrutura.trelica.n_paineis")


# --- varredura consolidada: materiais de fundacao, enums de vento, estaca ----
def test_fundacao_materiais_nao_positivos_bloqueiam():
    for campo in ("fck", "fyk", "cobrimento", "phi_barra"):
        s = _base(); s["fundacao"][campo] = 0.0
        assert _bloqueado_em(s, "fundacao." + campo), campo


def test_fundacao_gamma_f_menor_que_um_bloqueia():
    s = _base(); s["fundacao"]["gamma_f"] = 0.9
    assert _bloqueado_em(s, "fundacao.gamma_f")


def test_fundacao_mu_negativo_bloqueia():
    s = _base(); s["fundacao"]["mu"] = -0.5
    assert _bloqueado_em(s, "fundacao.mu")


def test_vento_cat_invalida_bloqueia():
    s = _base(); s["vento"]["cat"] = "X"
    assert _bloqueado_em(s, "vento.cat")


def test_vento_classe_invalida_bloqueia():
    s = _base(); s["vento"]["classe"] = "Z"
    assert _bloqueado_em(s, "vento.classe")


def test_vento_enums_validos_passam():
    for cat in ("I", "II", "III", "IV", "V"):
        s = _base(); s["vento"]["cat"] = cat
        assert PS.validar(s)["ok"], cat


def test_baldrame_secao_nao_positiva_bloqueia():
    s = _base(); s["baldrame"] = {"b": 0.0, "h": 0.4, "q_parede": 5.0}
    assert _bloqueado_em(s, "baldrame.b")


# --- estaca (fundacao profunda) ----------------------------------------------
def _base_estaca():
    s = _base()
    s["fundacao"]["tipo"] = "estaca"
    s["fundacao"]["estaca"] = {
        "perfil_spt": [{"tipo": "argila_siltosa", "N": 12, "dz": 8.0}],
        "tipo_estaca": "pre_moldada", "D": 0.30, "L": 10.0, "FS": 3.0}
    return s


def test_estaca_valida_passa():
    r = PS.validar(_base_estaca())
    assert r["ok"], r["faltando"]


def test_estaca_tipo_invalido_bloqueia():
    s = _base_estaca(); s["fundacao"]["estaca"]["tipo_estaca"] = "inventada"
    assert _bloqueado_em(s, "fundacao.estaca.tipo_estaca")


def test_estaca_D_L_nao_positivos_bloqueiam():
    for k in ("D", "L"):
        s = _base_estaca(); s["fundacao"]["estaca"][k] = 0.0
        assert _bloqueado_em(s, "fundacao.estaca." + k), k


def test_estaca_spt_degenerado_bloqueia():
    s = _base_estaca(); s["fundacao"]["estaca"]["perfil_spt"][0]["dz"] = 0.0
    assert _bloqueado_em(s, "fundacao.estaca.perfil_spt")
    s = _base_estaca(); s["fundacao"]["estaca"]["perfil_spt"][0]["N"] = -5
    assert _bloqueado_em(s, "fundacao.estaca.perfil_spt")


# --- campos de menor risco + modulos opcionais (completa a varredura) --------
def test_telha_peso_nao_positivo_bloqueia():
    s = _base(); s["cobertura"]["telha_peso"] = 0.0
    assert _bloqueado_em(s, "cobertura.telha_peso")


def test_cargas_negativas_bloqueiam():
    s = _base(); s["cargas"]["self"] = -0.35
    assert _bloqueado_em(s, "cargas.self")


def test_terreno_fracoes_fora_de_faixa_bloqueiam():
    s = _base(); s["terreno"]["to_max"] = 1.5
    assert _bloqueado_em(s, "terreno.to_max")
    s = _base(); s["terreno"]["area_lote_m2"] = 0.0
    assert _bloqueado_em(s, "terreno.area_lote_m2")


def test_neve_negativa_bloqueia():
    s = _base(); s["neve"] = {"sk": -1.0, "Ce": 1.0, "Ct": 1.0}
    assert _bloqueado_em(s, "neve.sk")


def test_fogo_trrf_nao_positivo_bloqueia():
    s = _base(); s["fogo"] = {"TRRF_min": 0}
    assert _bloqueado_em(s, "fogo.TRRF_min")


def test_escada_dims_nao_positivas_bloqueiam():
    s = _base(); s["escada"] = {"desnivel": 0.0, "projecao": 4.0, "largura": 1.2}
    assert _bloqueado_em(s, "escada.desnivel")


def test_plataforma_dims_nao_positivas_bloqueiam():
    s = _base(); s["plataforma"] = {"L": 0.0, "b_trib": 2.0, "q_perm": 1.0, "q_acidental": 3.0}
    assert _bloqueado_em(s, "plataforma.L")
    s = _base(); s["plataforma"] = {"L": 5.0, "b_trib": 2.0, "q_perm": -1.0, "q_acidental": 3.0}
    assert _bloqueado_em(s, "plataforma.q_perm")


def test_z_abaixo_da_cumeeira_avisa_nao_bloqueia():
    # z do vento abaixo da cumeeira SUB-representa o S2 (nao-conservador) -> AVISO,
    # nao bloqueio. O wizard usa z=ridge; so o spec-direto desincroniza.
    s = _base()
    s["vento"]["z"] = s["geometria"]["eave"]     # 8 m < ridge 9,5 m
    r = PS.validar(s)
    assert r["ok"], r["faltando"]
    assert any(p == "vento.z" for p, _ in r["avisos"]), r["avisos"]


def test_z_igual_ridge_nao_avisa():
    s = _base()                                  # amostra ja tem z = ridge = 9,5
    r = PS.validar(s)
    assert not any(p == "vento.z" for p, _ in r["avisos"])


def test_opcionais_validos_passam():
    s = _base()
    s["neve"] = {"sk": 0.5, "Ce": 1.0, "Ct": 1.0}
    s["fogo"] = {"TRRF_min": 30}
    s["escada"] = {"desnivel": 3.0, "projecao": 4.0, "largura": 1.2}
    s["plataforma"] = {"L": 5.0, "b_trib": 2.0, "q_perm": 1.0, "q_acidental": 3.0}
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]
