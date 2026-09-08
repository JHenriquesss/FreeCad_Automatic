"""G51 - a faixa de validade declarada vira guarda (NBR 6118 + ferramenta).

Contexto: terceira vez que a mesma assinatura paga (lambda<=90 no G3,
C50 no G49/G50): o limite do metodo esta no comentario, o autor sabia,
e nao virou if. Desta vez o gap medido e' o theta da trelica de torcao
(17.5: 30..45 graus, escrito no cabecalho de torcao_nbr6118 e aceito sem
cheque por verifica_torcao).

1. FERRAMENTA (varredura_faixa_validade.py, estende a maquina de AST do G48):
   casa comentarios/docstrings que declaram faixa com a funcao onde moram e
   classifica em guardada / desguardada / inverificavel. O balde
   inverificavel (caso Wenner) impede a ferramenta de virar gerador de
   falso-positivo. Piso: enxerga >= 64 declaracoes (hoje: ~157).
2. GAP FECHADO: verifica_torcao RECUSA fail-closed (OK=False, motivo nomeado)
   theta fora de 30..45. 45 graus bit-a-bit inalterado.
3. TRIAGEM (rigor G10): cada desguardada abaixo foi MEDIDA; so theta virou
   correcao. Falso-positivo e registrado com o motivo; rho_min (Tab.17.3
   C55-C90) fica ABERTO: saturar no valor de C50 e' comportamento medido,
   mas o numero certo exige a tabela da norma - sem numero certo, sem
   correcao. Pode ser que a varredura devolva so o theta: nesse caso o valor
   do goal e' a ferramenta permanente.
4. RESTOS G50: s_limite_governante composto em C55-C90; orfas de
   fundacao_sapata privatizadas com compat fs.XD_LIM == 0.45.
"""
import math
import os
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import torcao_nbr6118 as tor
import varredura_faixa_validade as vf


def _por(funcao, arquivo="torcao_nbr6118.py"):
    return [d for d in vf.varredura()
            if d["arquivo"] == arquivo and d["funcao"] == funcao]


def test_01_ferramenta_enxerga_piso_e_classifica():
    tudo = vf.varredura()
    assert len(tudo) >= 64, "piso G51: a varredura tem de enxergar >= 64, viu %d" % len(tudo)
    baldes = {d["balde"] for d in tudo}
    assert {"guardada", "desguardada", "inverificavel"} <= baldes
    # Wenner: a>>b no cabecalho, b fora da assinatura -> inverificavel, NAO bug
    wenner = [d for d in tudo if d["arquivo"] == "aterramento_nbr15749.py"
              and d["funcao"] == "resistividade_wenner"]
    assert wenner and all(d["balde"] == "inverificavel" for d in wenner), wenner
    assert any("b" in d["motivo"] for d in wenner)
    # theta, depois do fix: guardada (virava desguardada antes do G51)
    theta = _por("verifica_torcao")
    assert theta and all(d["balde"] == "guardada" for d in theta), theta
    # referencias G49/G50 ja certas seguem guardadas
    assert any(d["balde"] == "guardada" for d in _por("_fctm", "viga_protendida.py"))
    assert any(d["balde"] == "guardada" for d in _por("eci_MPa", "fissuracao_nbr6118.py"))


def _theta_refusado(th):
    r = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=th)
    # G51-rev: quem recusa e' OK. biela_ok voltou a significar so a biela e
    # aqui ela PASSA (Td=20 <= TRd2) - ver test_07.
    assert r["OK"] is False
    assert r["theta_valido"] is False and "G51" in r["motivo"]
    return r


def test_02_sweep_theta_fora_da_faixa_recusa():
    """Guarda do item 2: falha se algum theta fora de 30..45 devolver OK=True."""
    for th in (0.0, 10.0, 20.0, 29.9, 45.1, 50.0, 60.0, 90.0):
        _theta_refusado(th)
    for th in (30.0, 35.0, 45.0):
        r = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=th)
        assert r["theta_valido"] is True and r["motivo"] == ""
    # dentro da faixa o numero manda: torcao alta continua esmagando a biela
    assert tor.verifica_torcao(300.0, 0.20, 0.50, 0.04, 30e3)["OK"] is False


def test_02b_vermelho_numero_errado_que_saia():
    """Red-proof G10/G21 numa COPIA sem o fix: com theta=20 o OK era True -
    o numero errado que saia hoje (TRd2=24,4 >= Td=20). A guarda so vale
    depois deste vermelho."""
    fonte = open(os.path.join(GALPAO, "torcao_nbr6118.py"),
                 encoding="utf-8").read()
    sem_fix = fonte.replace('"OK": bool(biela_ok and theta_valido)}',
                            '"OK": biela_ok}')
    assert sem_fix != fonte
    ns = {"__name__": "torcao_sem_fix"}
    exec(compile(sem_fix, "torcao_sem_fix", "exec"), ns)
    r_velho = ns["verifica_torcao"](20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=20.0)
    assert r_velho["OK"] is True, "o vermelho nao mordeu: sem o fix, theta=20 passava?"
    r_novo = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=20.0)
    assert r_novo["OK"] is False
    assert abs(r_velho["TRd2"] - 24.4) < 0.2, r_velho["TRd2"]


def test_03_theta_45_bit_a_bit_e_relatorio():
    """Continuidade: o caso de 45 graus fica bit-a-bit inalterado (chaves
    antigas identicas a formula pre-G51); o recusado aparece no relatorio."""
    r = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=45.0)
    g = tor.secao_vazada_equivalente(0.20, 0.50, 0.04)
    fcd = 30e3 / 1.4
    av2 = 1.0 - 30.0 / 250.0
    assert r["TRd2"] == 0.50 * av2 * fcd * g["Ae"] * g["he"] * math.sin(math.radians(90))
    assert r["he"] == round(g["he"], 4) and r["Ae"] == round(g["Ae"], 4)
    assert r["biela_ok"] is True and r["OK"] is True
    rel = tor.relatorio_pt(_theta_refusado(20.0))
    assert "THETA RECUSADO" in rel and "G51" in rel
    assert "REPROVA por theta" in rel
    assert "THETA RECUSADO" not in tor.relatorio_pt(r)


def test_04_s_limite_governante_composto():
    """Resto G50-1: em C55-C90 o rotulo diz qual limite foi cortado
    (calculo inalterado: s_max cai exatamente a metade)."""
    import pilar_concreto as pc
    base = {"b": 0.30, "h": 0.30, "Nk": 800.0, "le_x": 2.80, "le_y": 2.80,
            "fck": 50e3, "fyk": 500e3, "dl": 0.04, "Vd": 50.0}
    r50 = pc.dimensiona_pilar(dict(base))
    r60 = pc.dimensiona_pilar(dict(base, fck=60e3))
    assert r60["s_limite_governante"] == (
        r50["s_limite_governante"] + " + NOTA C55-C90 50% (G49/G51)")
    assert abs(r60["s_estribo_max"] - 0.5 * r50["s_estribo_max"]) < 1e-12
    assert "NOTA C55-C90 50%" in r60["s_limite_governante"]


def test_05_constantes_orfas_privatizadas_com_compat():
    """Resto G50-2: LAMBDA_BLOCO/ALPHA_C/XD_LIM saem do namespace (viravam
    armadilha C50) mas fs.XD_LIM ainda devolve 0,45 para quem vier depois."""
    import fundacao_sapata as fs
    corpo = open(os.path.join(GALPAO, "fundacao_sapata.py"),
                 encoding="utf-8").read()
    assert "\nLAMBDA_BLOCO =" not in corpo and "\nXD_LIM =" not in corpo
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert fs.XD_LIM == 0.45
        assert fs.LAMBDA_BLOCO == 0.80 and fs.ALPHA_C == 0.85
        assert any(issubclass(x.category, DeprecationWarning) for x in w), \
            "compat sem aviso vira armadilha de novo"
    assert fs.xd_lim(50.0) == 0.45 and fs.xd_lim(90.0) == 0.35
    # G50 segue verde: nenhum ok_dominio com x/d > 0,35 em C55-C90
    As, xd, z, ok = fs._armadura_flexao(300.0, 0.5, 0.45, 90e3, 500e3)
    assert (not ok) or xd <= 0.35 + 1e-9


# --- TRIAGEM item 3: medido, com numero; falso-positivo com motivo --------
def test_06_desaprumo_guarda_nomeada_nao_bug():
    """desaprumo (FP): 'limitado a [1/300,1/200]' - satura nos dois lados com
    'saturou' nomeado. A ferramenta nao resolve constante-expressao
    (THETA_1_MIN = 1/300 e' BinOp) - limite documentado, nao silencio."""
    import estabilidade_edificio as e
    assert e.THETA_1_MIN == 1.0 / 300.0 and e.THETA_1_MAX == 1.0 / 200.0
    r_min = e.desaprumo(10000.0, 4)   # bruto 0,0001 -> piso
    r_max = e.desaprumo(1.0, 4)       # bruto 0,01 -> teto
    assert r_min["theta_1"] == e.THETA_1_MIN and r_min["saturou"] == "theta_1min"
    assert r_max["theta_1"] == e.THETA_1_MAX and r_max["saturou"] == "theta_1max"


def test_06b_escada_gate_reprova_nao_bug():
    """escada/geometria (FP): gate PISO_MIN/MAX com motivo. Medido: piso
    0,13 m -> ok False (ferramenta nao resolve constante nomeada)."""
    import escada_concreto as ec
    assert (ec.PISO_MIN, ec.PISO_MAX) == (0.25, 0.32)
    r = ec.geometria(0.5, espelho_max=0.5)
    assert r["piso"] == 0.13 and r["ok"] is False and "25" in r["motivo"]


def test_06c_pilar_delega_as_bipartidas_nao_bug():
    """pilar x27 (FP): os 9 funcoes do diagrama C50 alcançam eps_cu/eps_c2/
    expoente_n/alpha_c_pilar (G50) em ate 3 saltos. A lente ve 1 nivel -
    mesma fronteira do 'return atravessou' do G48. Medido: C60 muda o numero
    (fck flui), C50 legado identico."""
    import pilar_concreto as pc
    fcd = 30e3 / 1.4
    assert pc._sigma_c(0.002, fcd, 60e3) != pc._sigma_c(0.002, fcd, None)
    assert pc._sigma_c(0.001, fcd) == pc._sigma_c(0.001, fcd, 30e3)
    assert abs(pc.eps_cu(60.0) - 0.0028835) < 1e-6


def test_06d_sismo_recusa_e_satura_nao_bug():
    """sismo (FP com 2 ressalvas honestas): zona fora de 0..4 levanta
    ValueError (recusa, nao numero); Ca/Cv satura nas bordas. Classe F da
    KeyError (fail-closed feio, sem numero errado) - higiene futura, nao
    guarda de faixa; periodo_aproximado ignora zona por definicao (Ta=CT.hn^x,
    zona entra via ag/Cup no chamador)."""
    import sismo_nbr15421 as s
    try:
        s.verifica_sismo(1000.0, 7)
        raise AssertionError("zona 7 devia recusar")
    except ValueError:
        pass
    assert s.coef_ca_cv(0.05, "C") == s.coef_ca_cv(0.10, "C")
    assert s.coef_ca_cv(0.20, "C") == s.coef_ca_cv(0.15, "C")
    assert s.ZONA_CATEGORIA == {0: "A", 1: "A", 2: "B", 3: "C", 4: "C"}


def test_06e_chaves_e_tabelas_recusam_nao_bug():
    """cargas/nbr8400 (FP): guarda por pertinencia (NotIn -> KeyError/
    ValueError). A ferramenta so le Compare numerico - limite documentado."""
    import cargas_nbr6120 as cn, nbr8400 as n8
    try:
        cn.carga_uso("coisa_que_nao_existe")
        raise AssertionError("chave invalida devia recusar")
    except KeyError:
        pass
    try:
        n8.coef_dinamico("HC9", 30.0)
        raise AssertionError("classe invalida devia recusar")
    except (ValueError, KeyError):
        pass


def test_06f_rho_min_faixa_alta_fechada_na_tabela_17_3():
    """fundacao rho_min (FECHADO no D94/G59): a Tabela 17.3 COMPLETA esta no
    acervo (NBR 6118:2014 p. 130, linha Retangular, foto no verbete) e a
    saturacao em C50 virou os valores literais: 55:0,211 60:0,219 65:0,226
    70:0,233 75:0,239 80:0,245 85:0,251 90:0,256 %. C50 bit-a-bit intacto."""
    import fundacao_sapata as fs
    assert fs.rho_min(50.0) == 0.00208
    assert abs(fs.rho_min(60.0) - 0.00219) < 1e-12
    assert abs(fs.rho_min(90.0) - 0.00256) < 1e-12
    assert fs.rho_min(90.0) > fs.rho_min(50.0)  # nao satura mais
    assert fs.rho_min(25.0) == 0.00150


# --- G51-rev (revisao): a recusa do theta ATRAVESSA ate a viga -------------
def test_07_biela_ok_volta_a_significar_biela():
    """Rotulo x dado: com theta=20 a biela PASSA (Td=20 <= TRd2=24,4) e o
    relatorio dizia 'REPROVA (aumentar secao)' - remedio errado, a secao esta
    sobrando. biela_ok volta a ser so a biela; quem recusa e' OK."""
    r = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=20.0)
    assert r["Td"] <= r["TRd2"]              # a biela realmente passa
    assert r["biela_ok"] is True             # e a chave agora diz isso
    assert r["OK"] is False and r["theta_valido"] is False
    rel = tor.relatorio_pt(r)
    assert "REPROVA (aumentar secao)" not in rel, rel
    assert "REPROVA por theta" in rel and "nao usar" in rel
    # dentro da faixa, a biela esmagada segue reprovando pela biela
    r2 = tor.verifica_torcao(300.0, 0.20, 0.50, 0.04, 30e3, theta_deg=45.0)
    assert r2["biela_ok"] is False and r2["OK"] is False
    assert "REPROVA (aumentar secao)" in tor.relatorio_pt(r2)


def test_07b_theta_recusado_derruba_o_OK_DA_VIGA():
    """A guarda que importa: o fail-closed nao pode morar so no dict da
    torcao. Mede no resultado da VIGA (viga_concreto le a chave OK). Sem
    isso, trocar de chave desligaria a propagacao em silencio - a licao do
    filtro de nome morto ('conferi que so um lugar le')."""
    import viga_concreto as vc
    # h=0,60: a viga passa em TUDO (com h=0,50 o ELS ja reprova e o OK
    # final ficaria False de qualquer jeito - o teste nao mediria nada).
    cfg = {"vao": 6.0, "b": 0.20, "h": 0.60, "fck": 30e3, "fyk": 500e3,
           "q": 15.0, "T_d": 18.0}
    r_ok = vc.verifica_viga(dict(cfg))
    assert r_ok["tor_ok"] is True and r_ok["OK"] is True

    # viga_concreto fixa theta=45; forca 20 para medir a travessia de fato
    orig = tor.verifica_torcao
    try:
        tor.verifica_torcao = (lambda Td, b, h, c1, fck, fywk=500e3,
                               theta_deg=45.0:
                               orig(Td, b, h, c1, fck, fywk, theta_deg=20.0))
        r_bad = vc.verifica_viga(dict(cfg))
    finally:
        tor.verifica_torcao = orig
    assert r_bad["torcao"]["theta_valido"] is False
    assert r_bad["torcao"]["biela_ok"] is True     # a biela passa...
    assert r_bad["tor_ok"] is False                # ...e mesmo assim reprova
    assert r_bad["OK"] is False, "theta recusado nao chegou ao OK da viga"


def test_07c_orfa_lambda_bloco_do_pilar_saiu():
    """Item 3 da revisao: pilar_concreto tinha LAMBDA_BLOCO=0,80 '(fck<=50)'
    com ZERO consumidores - mesma armadilha que o G51 tirou de
    fundacao_sapata, um modulo ao lado. O pilar integra parabola-retangulo,
    nao usa bloco retangular. ALPHA_C fica: e' consumida por alpha_c_pilar."""
    import pilar_concreto as pc
    corpo = open(os.path.join(GALPAO, "pilar_concreto.py"),
                 encoding="utf-8").read()
    assert (chr(10) + "LAMBDA_BLOCO =") not in corpo
    assert not hasattr(pc, "LAMBDA_BLOCO")
    assert pc.ALPHA_C == 0.85 and pc.alpha_c_pilar(30.0) == 0.85
    assert abs(pc.alpha_c_pilar(60.0) - 0.85 * 0.95) < 1e-12


# --- G51-rev: a varredura nao pode crescer sozinha -------------------------
def test_08_baseline_desguardadas_nos_dois_sentidos():
    """Regra do G33 aplicada a esta varredura. Sem o baseline a ferramenta e'
    RELATORIO, nao guarda: medido na revisao, um modulo novo com faixa
    declarada e nao guardada era classificado certo e a suite ficava VERDE."""
    varridas = vf.chaves_desguardadas()
    declaradas = sorted(vf.DESGUARDADAS_TRIADAS)
    novas = sorted(set(varridas) - set(declaradas))
    sumidas = sorted(set(declaradas) - set(varridas))
    assert not novas, (
        "faixa de validade DECLARADA em comentario e nao guardada por um if, "
        "que nao estava triada: %r. Ou vira guarda (o if que compara), ou "
        "entra em varredura_faixa_validade.DESGUARDADAS_TRIADAS com o motivo "
        "medido pelo qual NAO e' bug (rigor G10)." % (novas,))
    assert not sumidas, (
        "declaradas que a varredura nao acha mais: %r. Se viraram guarda, o "
        "baseline tem de DIMINUIR junto (senao protege nome morto)."
        % (sumidas,))


_GAP_SEM_GUARDA = [
    "def verifica_algo(theta_deg, x):",
    "    # metodo so vale para theta entre 30 e 45 graus",
    "    return {'v': x * theta_deg, 'OK': True}",
]
_GAP_COM_GUARDA = [
    "def verifica_algo(theta_deg, x):",
    "    # metodo so vale para theta entre 30 e 45 graus",
    "    if not (30.0 <= theta_deg <= 45.0):",
    "        return {'v': None, 'OK': False}",
    "    return {'v': x * theta_deg, 'OK': True}",
]


def test_08b_vermelho_do_baseline_fora_do_repo(tmp_path):
    """Prova que o baseline morde. O modulo falso e' escrito em tmp_path, NAO
    dentro do galpao_fw: teste que muta o repo vivo foi uma das causas do
    D81 (suite nao deterministica)."""
    alvo = tmp_path / "zz_gap.py"
    alvo.write_text(chr(10).join(_GAP_SEM_GUARDA) + chr(10), encoding="utf-8")
    desg = [d for d in vf.varredura(raiz=str(tmp_path))
            if d["balde"] == "desguardada"]
    assert desg and desg[0]["parametro"] == "theta_deg", desg
    assert desg[0]["numeros"] == [30.0, 45.0]
    novas = set(vf.chaves_desguardadas(raiz=str(tmp_path))) - set(
        vf.DESGUARDADAS_TRIADAS)
    assert novas, "o baseline nao morderia um gap novo"

    # guardando o parametro, some do balde: a saida do vermelho e' o if
    alvo.write_text(chr(10).join(_GAP_COM_GUARDA) + chr(10), encoding="utf-8")
    assert not [d for d in vf.varredura(raiz=str(tmp_path))
                if d["balde"] == "desguardada"]


# --- G64: a lente enxerga o que entrou depois dela ---------------------------
# alvenaria_estrutural produzia ZERO chaves (161 em 50 arquivos, sem ela).
# O modulo esta GUARDADO - estes dois testes medem as guardas que a triagem
# do baseline alega (rigor G10: sem numero medido, sem triagem).
def test_06g_alvenaria_patamar_fora_dos_tabelados_recusa():
    """Patamar de fpk fora da Tab.1 RECUSA (nao interpola em silencio)."""
    import alvenaria_estrutural as alv
    assert alv.modulo_deformacao(20000.0, "bloco_concreto") == 800.0 * 20000.0
    assert alv.modulo_deformacao(22000.0, "bloco_concreto") == 750.0 * 22000.0
    assert alv.modulo_deformacao(26000.0, "bloco_concreto") == 700.0 * 26000.0
    for fpkfora in (21000.0, 23000.0, 25000.0):
        try:
            alv.modulo_deformacao(fpkfora, "bloco_concreto")
            raise AssertionError("patamar %.0f MPa devia recusar" % (fpkfora / 1000.0,))
        except alv.EntradaAlvenaria as exc:
            assert "Ea_sem_patamar_tabelado" in str(exc)


def test_06h_alvenaria_lambda_acima_do_teto_reprova():
    """Lambda acima do teto da Tab.9 REPROVA (nao satura, regra G51/D82)."""
    import alvenaria_estrutural as alv
    assert alv.teto_esbeltez(False) == 24.0
    assert alv.teto_esbeltez(True) == 30.0
    r = alv.verifica_parede_compressao(100.0, 4000.0, 3.0, 0.10, 0.20)
    assert r["lambda_"] == 30.0 and r["OK"] is False
    assert "esbeltez_acima_do_teto" in r["motivo"]
    r2 = alv.verifica_pilar_armado(100.0, 4000.0, 3.5, 0.10, 0.20, 0.002,
                                   500e3, 10.0)
    assert r2["OK"] is False and "esbeltez_acima_do_teto" in r2["motivo"]
    # dentro do teto a conta manda: mesma parede curta aprova
    r3 = alv.verifica_parede_compressao(10.0, 4000.0, 2.0, 0.20, 0.40)
    assert r3["OK"] is True and r3["lambda_teto"] == 24.0


def test_09_cobertura_todo_py_varrido_ou_isento():
    """D87: a lente vira portao. Todo *.py ou produz chave, ou esta em
    SEM_FAIXA_DECLARADA com motivo. Modulo novo invisivel = suite vermelha;
    isencao sem motivo, isencao que virou nome morto e isencao de arquivo
    sumido tambem."""
    r = vf.confere_cobertura()
    assert not r["faltando"], (
        "modulo invisivel a lente e sem isencao: %r. Ou a lente passa a "
        "enxergar o vocabulario (como o G64 fez com a Tab.9), ou o arquivo "
        "entra em varredura_faixa_validade.SEM_FAIXA_DECLARADA com o motivo "
        "pelo qual zero chaves e o esperado." % (r["faltando"],))
    assert not r["sobrando"], (
        "isencao virou nome morto (arquivo agora produz chave): %r. A "
        "isencao tem de SAIR junto (senao protege modulo morto)." % (r["sobrando"],))
    assert not r["sem_motivo"], (
        "isencao sem motivo: %r. Lista de isentos sem motivo e silencio, "
        "nao triagem." % (r["sem_motivo"],))
    assert not r["ausentes"], (
        "isencao de arquivo que sumiu do disco: %r. Remover a entrada "
        "junto com o arquivo." % (r["ausentes"],))
    assert r["OK"]


def test_09b_vermelho_cobertura_nos_dois_sentidos(tmp_path):
    """Vermelho provado por injecao, sem mutar o repo (licao do D81).
    Sentido 1: modulo com faixa desguardada e pego (varrido, nao some em
    sem_chave, e o baseline o acusa como nao triado). Sentido 2: modulo sem
    faixa e pego pela cobertura sem isencao; isencao motivada libera;
    motivo apagado reprova."""
    gap = tmp_path / "zz_faixa.py"
    gap.write_text(chr(10).join(_GAP_SEM_GUARDA) + chr(10), encoding="utf-8")
    limpo = tmp_path / "zz_limpo.py"
    limpo.write_text("def soma(a, b):\n    return a + b\n", encoding="utf-8")
    # sentido 1: com faixa desguardada, a lente VE (nao cai em sem_chave)
    # e o baseline MORDE (nao esta triado)
    assert "zz_faixa.py" not in vf.arquivos_sem_chave(raiz=str(tmp_path))
    novas = set(vf.chaves_desguardadas(raiz=str(tmp_path))) - set(
        vf.DESGUARDADAS_TRIADAS)
    assert any(a == "zz_faixa.py" for a, _d in novas), novas
    # sentido 2: sem faixa e sem isencao, a cobertura MORDE
    r = vf.confere_cobertura(raiz=str(tmp_path), isentos={})
    assert "zz_limpo.py" in r["faltando"] and not r["OK"], r
    # isencao motivada libera...
    r2 = vf.confere_cobertura(
        raiz=str(tmp_path),
        isentos={"zz_limpo.py": "modulo injetado sem faixa (prova do vermelho)",
                 "zz_faixa.py": "prova do vermelho: tem chave, isencao sobraria - "
                                "usar baseline, nao esta lista"})
    assert "zz_faixa.py" in r2["sobrando"] and not r2["OK"], r2
    so_limpo = {"zz_limpo.py": "modulo injetado sem faixa (prova do vermelho)"}
    # ...mas zz_faixa tem chave e nao pode estar na lista; so o limpo libera
    # (ainda falta triar zz_faixa no baseline, que e outro portao):
    # para a cobertura pura, diretorio so com o limpo + isencao = verde
    limpo_only = tmp_path / "so_limpo"
    limpo_only.mkdir()
    (limpo_only / "zz_limpo.py").write_text(
        "def soma(a, b):\n    return a + b\n", encoding="utf-8")
    assert vf.confere_cobertura(raiz=str(limpo_only), isentos=so_limpo)["OK"]
    # motivo apagado reprova
    r3 = vf.confere_cobertura(raiz=str(limpo_only),
                              isentos={"zz_limpo.py": "   "})
    assert r3["sem_motivo"] == ["zz_limpo.py"] and not r3["OK"], r3


def test_09c_vocabulario_estreito_permanece_estreito():
    """Cada termo novo do G64 veio com a contagem de FP; os primos ruidosos
    continuam fora: 'patamar' de escada (23 hits), 'a partir de' sem numero
    (42 hits) e 'teto' generico (78 hits, forro e ductilidade) nao viram
    declaracao. Se um dia entrarem, e com triagem propria."""
    tudo = vf.varredura()
    assert not [d for d in tudo if d["arquivo"] == "escada.py"
                and "patamar" in d["declaracao"].lower()], \
        "patamar de escada virou declaracao: a lente alargou alem do medido"
    assert not [d for d in tudo if "a partir de um payload" in d["declaracao"]], \
        "'a partir de' sem numero virou declaracao"
    assert not [d for d in tudo
                if "ponto de luz fixo no teto" in d["declaracao"]], \
        "'teto' arquitetonico virou declaracao"
    # e o vocabulario novo esta mesmo enxergando a alvenaria (nao so o FP
    # antigo do 'limitada a 10%'): teto da Tab.9 e patamar de fpk produzem
    # chaves que o G51 nao via
    alv = [d for d in tudo if d["arquivo"] == "alvenaria_estrutural.py"]
    assert any("Tab.9" in d["declaracao"] for d in alv), alv
    assert any("patamar de fpk" in d["declaracao"].lower() for d in alv), alv
    assert len(alv) >= 10, "alvenaria segue quase invisivel: %d chaves" % len(alv)
