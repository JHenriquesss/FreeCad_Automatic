"""Testes do ELS de vibracao de piso (NBR 8800:2008, 11.4 e Anexo L) - G11.

Os valores normativos (3/4/6/8 Hz, 20/9/5 mm, psi_1 da Tabela 2) foram conferidos
LITERALMENTE na fonte antes de codar. Estes testes protegem tres coisas que a
barra verde nao pegaria sozinha:

  1. a viga tem de entrar BIAPOIADA mesmo sendo continua (L.3.2/L.3.3);
  2. o deslocamento e o IMEDIATO, sem a fluencia da NBR 6118;
  3. uso sem classe NAO pode cair num default - trocar 9 mm por 20 mm em
     silencio e a saturacao silenciosa de sempre.
"""

import pytest

import vibracao_piso as vp


def _cfg(**kw):
    base = {
        "uso": "residencial_dormitorio", "fck": 30e3, "g": 5.0, "q": 1.5,
        "laje": {"caso": 1, "lx": 4.0, "ly": 5.0, "h": 0.10, "As_m2": 3.0e-4},
        "viga": {"L": 5.0, "b": 0.20, "h": 0.50, "g_kN_m": 20.0,
                 "q_kN_m": 6.0, "As_m2": 8.0e-4},
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# os numeros da norma, transcritos
# ---------------------------------------------------------------------------
def test_limites_das_classes_batem_com_o_anexo_L():
    assert vp.F_MIN_ABSOLUTA_HZ == 3.0                       # L.1.2
    assert vp.criterio("caminhada") == (4.0, 0.020, "L.3.2")
    assert vp.criterio("ritmica") == (6.0, 0.009, "L.3.3")
    assert vp.criterio("ritmica_repetitiva") == (8.0, 0.005, "L.3.3")


def test_psi_1_da_tabela_2_da_nbr8800():
    assert vp.psi_1("restrito") == 0.4       # linha 1 (nota b: residenciais)
    assert vp.psi_1("publico") == 0.6        # linha 2 (nota c: escritorios)
    assert vp.psi_1("deposito") == 0.7       # linha 3 (bibliotecas, garagens)


def test_escritorio_cai_na_linha_2_e_nao_na_1():
    """Armadilha da Tabela 2: a nota c diz "comerciais, DE ESCRITORIOS e de
    acesso publico". Classificar escritorio como linha 1 daria psi_1 = 0,4 e
    subestimaria a parcela variavel da combinacao frequente."""
    _classe, linha = vp.classifica("escritorio_sala_uso_geral")
    assert vp.psi_1(linha) == 0.6


# ---------------------------------------------------------------------------
# 1. VIGA BIAPOIADA - o que a norma manda e o que seria facil errar
# ---------------------------------------------------------------------------
def test_viga_entra_biapoiada_e_nao_continua():
    """L.3.2/L.3.3: "calculado considerando-se as vigas como biapoiadas". A
    flecha biapoiada (5/384) e' ~1,92x a da continua (2,6/384). Se o modulo
    reaproveitasse a flecha da viga continua, um piso reprovado passaria calado.
    """
    import viga_baldrame as vb

    cfg = _cfg()["viga"]
    w = 22.0
    bi = vp.flecha_viga_biapoiada(cfg, w, 30e3)
    cont = vb._flecha_alvenaria(cfg["b"], cfg["h"], cfg["h"] - 0.04, cfg["L"],
                                w, 30e3, cfg["As_m2"], continua=True)
    assert bi["d_imediata_mm"] > cont["d_imediata_mm"]
    # Piso da razao: 5/2,6 = 1,92, so dos coeficientes de flecha. Na pratica ela
    # e' MAIOR porque o momento de servico tambem muda (1/8 contra 1/10), a viga
    # biapoiada fissura mais e o I_eq de Branson cai - ou seja, tomar a flecha
    # da continua subestima ainda mais do que a razao 1,92 sugere.
    razao = bi["d_imediata_mm"] / cont["d_imediata_mm"]
    assert razao > 5.0 / 2.6


def test_deslocamento_e_o_imediato_e_nao_o_diferido():
    """"excluindo a parcela dependente do tempo": o valor comparado aos 20 mm
    NAO leva o (1+alpha_f) de fluencia da NBR 6118 17.3.2.1.2. Sao dois ELS
    distintos e nao podem ser trocados um pelo outro."""
    import viga_baldrame as vb

    cfg = _cfg()["viga"]
    fl = vb._flecha_alvenaria(cfg["b"], cfg["h"], cfg["h"] - 0.04, cfg["L"],
                              22.0, 30e3, cfg["As_m2"], continua=False)
    bi = vp.flecha_viga_biapoiada(cfg, 22.0, 30e3)
    assert bi["d_imediata_mm"] == fl["d_imediata_mm"]
    assert bi["d_imediata_mm"] < fl["d_total_mm"]


def test_laje_mantem_a_vinculacao_real_do_painel():
    """A norma manda biapoiar as VIGAS, nao as LAJES. Um painel engastado em
    duas bordas (caso 4) tem de continuar flechando menos que o mesmo painel
    com as 4 bordas apoiadas (caso 1)."""
    apoiada = vp.flecha_laje_frequente(
        {"caso": 1, "lx": 4.0, "ly": 5.0, "h": 0.10}, 6.0, 30e3)
    engastada = vp.flecha_laje_frequente(
        {"caso": 4, "lx": 4.0, "ly": 5.0, "h": 0.10}, 6.0, 30e3)
    assert engastada["d_imediata_mm"] < apoiada["d_imediata_mm"]


# ---------------------------------------------------------------------------
# 2. CLASSIFICACAO SEM DEFAULT
# ---------------------------------------------------------------------------
def test_uso_desconhecido_reprova_em_vez_de_adotar_caminhada():
    r = vp.verifica(_cfg(uso="uso_que_nao_existe"))
    assert r["OK"] is False
    assert r["motivo"] == "nao_classificado"
    assert "20 mm" in " ".join(r["avisos"]) or "caminhada" in " ".join(r["avisos"])


def test_todo_uso_da_tabela_10_tem_classe():
    """O mapa nao tem default DE PROPOSITO - mas entao ele tem de cobrir a
    Tabela 10 inteira. Acrescentar um uso em `cargas_nbr6120.CARGAS_USO` sem
    classifica-lo aqui faria o gate reprovar o edificio inteiro por um uso que o
    projetista declarou legitimamente. Este teste e' o par do 'sem default'."""
    import cargas_nbr6120 as cg

    faltando = sorted(set(cg.CARGAS_USO) - set(vp.CLASSE_POR_USO))
    assert faltando == [], faltando
    validos = set(vp.CLASSES_ANEXO_L) | {vp.CLASSE_NAO_APLICAVEL}
    for uso, (classe, linha) in vp.CLASSE_POR_USO.items():
        assert classe in validos, uso
        assert linha in vp.PSI_1_TAB2, uso


def test_ginasio_usa_9mm_e_nao_20mm():
    """O limite de um piso ritmico e' 9 mm, nao 20. Cair no default de
    caminhada mais que dobraria o limite sem nenhum gate reclamar."""
    r = vp.verifica(_cfg(uso="ginasio_esportes", q=5.0))
    assert r["classe"] == "ritmica"
    assert r["d_lim_mm"] == 9.0
    assert r["f_min_Hz"] == 6.0


def test_cobertura_nao_e_piso_de_circulacao_regular():
    r = vp.verifica(_cfg(uso="cobertura_manutencao"))
    assert r["aplicavel"] is False
    assert r["OK"] is True
    assert "Anexo L" in " ".join(r["avisos"])


def test_classe_declarada_sem_uso_exige_psi_1():
    """psi_1 depende da ocupacao e nao tem default: declarar so a classe nao
    pode fazer o modulo escolher 0,4 por conta propria."""
    cfg = _cfg(classe="ritmica")
    cfg.pop("uso")
    with pytest.raises(vp.UsoNaoClassificado):
        vp.verifica(cfg)
    cfg["psi_1"] = 0.6
    assert vp.verifica(cfg)["psi_1"] == 0.6


# ---------------------------------------------------------------------------
# 3. OS VEREDITOS
# ---------------------------------------------------------------------------
def test_piso_corrente_atende_pela_via_simplificada():
    r = vp.verifica(_cfg())
    assert r["OK"] is True
    assert r["avaliacao"].startswith("simplificada")
    assert r["d_total_mm"] == pytest.approx(r["d_laje_mm"] + r["d_viga_mm"], abs=0.02)
    # a ressalva de L.3.1 acompanha SEMPRE a via simplificada
    assert any("L.3.1" in a for a in r["avisos"])


def test_vao_grande_estoura_os_20mm_e_aponta_a_analise_dinamica():
    r = vp.verifica(_cfg(viga={"L": 11.0, "b": 0.20, "h": 0.50,
                               "g_kN_m": 30.0, "q_kN_m": 10.0, "As_m2": 12e-4}))
    assert r["ok_deslocamento"] is False
    assert r["OK"] is False
    texto = " ".join(r["avisos"])
    assert "L.2" in texto and "DG11" in texto


def test_frequencia_declarada_governa_e_nunca_e_estimada():
    """A NBR 8800 NAO da formula para f_n - conferido na fonte. Ou o projetista
    declara o f_n da sua analise dinamica, ou a via e' a do deslocamento."""
    reprova_por_deslocamento = _cfg(
        viga={"L": 11.0, "b": 0.20, "h": 0.50, "g_kN_m": 30.0, "q_kN_m": 10.0,
              "As_m2": 12e-4})
    sem_fn = vp.verifica(reprova_por_deslocamento)
    assert sem_fn["OK"] is False and sem_fn["f_n_Hz"] is None

    com_fn = vp.verifica(dict(reprova_por_deslocamento, f_n_Hz=5.2))
    assert com_fn["OK"] is True                       # 5,2 Hz >= 4 Hz de L.3.2
    assert com_fn["avaliacao"] == "frequencia declarada"


def test_piso_absoluto_de_3hz_reprova_qualquer_classe():
    """L.1.2: "em nenhum caso ... inferior a 3 Hz"."""
    r = vp.verifica(_cfg(f_n_Hz=2.5))
    assert r["ok_f_min_absoluta"] is False
    assert r["OK"] is False
    assert "3 Hz" in " ".join(r["avisos"])


def test_4hz_reprova_caminhada_mesmo_acima_do_piso_absoluto():
    r = vp.verifica(_cfg(f_n_Hz=3.5))
    assert r["ok_f_min_absoluta"] is True
    assert r["ok_frequencia"] is False
    assert r["OK"] is False


def test_viga_que_fissura_sem_As_declarada_nao_pode_ser_dada_por_atendida():
    """Sem As, `_flecha_alvenaria` devolve secao BRUTA em silencio (I_eq = I_c
    quando As <= 0). Bruta subestima a flecha assim que a viga fissura, entao um
    OK aqui seria OK por dado ausente - piso conservador: nao avaliavel."""
    viga = {"L": 8.0, "b": 0.20, "h": 0.50, "g_kN_m": 30.0, "q_kN_m": 10.0}
    r = vp.verifica(_cfg(viga=viga))
    assert r["viga"]["fissura"] is True
    assert r["viga"]["secao"].startswith("bruta")
    assert r["avaliavel"] is False
    assert r["OK"] is False
    assert any("As_m2" in a for a in r["avisos"])

    r2 = vp.verifica(_cfg(viga=dict(viga, As_m2=10e-4)))
    assert r2["avaliavel"] is True


def test_relatorio_nomeia_a_viga_biapoiada():
    txt = vp.relatorio_pt(vp.verifica(_cfg()))
    assert "BIAPOIADA" in txt
    assert "L.3.2" in txt
