"""G84 - declara-ou-recusa (padrao G75) nos 4 modulos com mais A CONFIRMAR.

Medido (fora de testes): galpao_hidraulica 16, piso_industrial 14,
secundarios_nbr8800 13, montagem 13. A CONFIRMAR nao e defeito; o alvo e o
default silencioso disfarcado (.get(chave, valor) ou cfg.get(k) or padrao
que decide veredito sem declaracao). A lente G75 nao via nenhum sitio nos
4 (0 de 101); o G84 estende o vocabulario com 24 chaves (+51 sitios,
piso 101 -> 152) e tria cada uma com numero, nao opiniao.

TRIAGEM (a = fica e o escopo nomeia; b = vira calculo; c = vira recusa):

HIDRAULICA (galpao_hidraulica.py) - tudo (a), dado de sitio flagado ou
decisao conservadora documentada:
- i_pluvial_mm_h=150: i=100 -> DN125 (igual ao default); i=200 -> DN150.
  Decide o DN, mas sai flagado (i_default + "[A CONFIRMAR i local]"); i por
  cidade (Tab.5) e dado de sitio fora do acervo.
- p_alim_kPa=100 (2 sitios): omitido -> ATENDE True; declarado 5 kPa ->
  gate pressao_agua reprova e ATENDE False. O gate e INFORMATIVO quando
  assumido (p_alim_assumida) e EFETIVO quando declarado: o silencio nao
  existe, esta escrito no gate.
- metodo_agua='soma': soma Q=2,62 DN40 vs pesos Q=0,424 DN20. Default =
  conservador (maior vazao); NBR 5626:2020 6.14.2 aceita os dois.
- n_condutores=4 (2 sitios): n=1 -> 800 m2/ponto DN250; n=0 -> gate
  reprova. 4 = 1 por canto, layout emitido no BIM (membros_bim).
- decl_pluvial/calha_pct=1.0: 0,5% -> DN150 vs 1,0% -> DN125. 1% e pratica
  usual (minimo 0,5% NBR 10844 5.7.1), decisao de projeto documentada.
- decl_esgoto_pct=1.0: minimo NBR 8160 4.2.3.2 (0,5% levanta ValueError com
  endereco); UHC=20: 1% e 2% -> DN100.
- area_telhado_m2=L*W: geometria (projecao), nao opcao normativa.
- Irma residencial (hidraulica_residencial.py): p_alim OBRIGATORIO (o
  precedente declara-ou-recusa: aviso p_alim_assumida + recusa de L_real);
  metodo/decls iguais; n_condutores=2 (default de 2 aguas). Tudo (a).

PISO (piso_industrial.py):
- (c) UDL sem sigma: udl=500 sem sigma -> OK True; com sigma=100 -> OK
  False. `None or pressao <= sigma` decidia o veredito em silencio. Vira
  recusa "sigma_solo_adm_kN_m2 nao declarado" (test_10). udl/sigma seguem
  OBRIGATORIO na lente.
- (a) posicoes=[interior,borda]: varredura 48 casos (4h x 4P x 3a) -> 0
  canto-governante; caso P45: h=280 igual com e sem canto (test_13). O
  default nao esconde o pior ponto na faixa do modulo.
- (a) k_MN_m3/cbr_pct OBRIGATORIO: o else k=35 sai flagado em k_fonte
  ("DEFAULT 35 ... A CONFIRMAR"); k=80 -> h220, k=15 -> h250: quem le o
  k_fonte sabe que o numero e assumido.

SECUNDARIOS (secundarios_nbr8800.py) - tudo (a), conservador medido:
- gamma_W=1.40/gamma_G=1.25: declarado 1,0 -> inter 1,117 vs default
  1,559 (Tab.1 ELU, maximo).
- n_tirantes=1: n=0 -> Msdy 1,562; n=1 -> 0,391; n=2 -> 0,174. Default 1 =
  Ly maxima no dominio n>=1; n=0 segue expressivel.
- mesa_interna_travada=False: Lb = vao cheio; sem MF o UPE100 reprova, com
  2 MF passa (selftest).
- n_maos_francesas=n_t: so lido com mesa travada; 0 -> Lb cheio.
- peso_proprio=0.10: UPE100 pesa 0,096 kN/m no catalogo (12.53e-4 x 78,5);
  peso 0 -> inter 1,54 vs 1,559. 0.31 da escora = HEA160 (0,304); omitido
  == declarado (inter 0,105 ambos).
- Nsd=5.0: 5 -> 0,116; 50 -> 0,156 (+34%); 120 -> 0,311; omisso == 5,0.
  Axial pequeno por natureza (gravidade do montante).
- Lb=vao/H (cheio), Cb=1.0 (minimo), continua OBRIGATORIO (falsy ->
  biapoio 1/8 > 1/10).
- Vizinhos da mesma chave: rodar_galpao n_tirantes=2 (seed do dimensiona;
  o spec materializa), projeto_spec mesa=False + n_maos OBRIGATORIO
  (normalizador), wizard n_maos or 0 (so aviso), tercas continua=False
  (biapoio conservador), ponte Cb=1.0/Lb=cheio (conservadores),
  pilar_continuo peso=True (bool que soma peso: conservador),
  viga_baldrame continua = leitura de resultado (emissao, nao conta).

MONTAGEM (montagem.py) - (a): sem gate OK (plano, nao veredito). So
peso_unit_kg entra na lente (via `or`: ausente vira 0,0 kg; lista vazia
diz "sem dados"). coef_impacto/fator_vento/fs/angulo sao args default com
A CONFIRMAR no cabecalho, fora da lente por declaracao.

Fora da lente, dito aqui (molde DIVIDA-LENTE): W/G (1 letra, 12/8 sitios
ruidosos), fck_MPa (chave generica do concreto; galpao_concreto
materializa do spec), gamma/cargas (dicts genericos).
"""
import os
import sys
from collections import Counter

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_defaults_veredito as vd


def _contagem():
    return Counter((d["arquivo"], d["chave"], d["default"], d["via"])
                   for d in vd.varredura())


def test_10_piso_udl_sem_sigma_recusa_nomeando():
    """G84 (c): udl declarada sem admissivel recusava em silencio (OK True).
    Superficie: dict com OK False + motivo (molde do caminho sem cargas),
    nao excecao - descoberto pelo vermelho antes da assercao."""
    import piso_industrial as pi
    base = {"L": 40.0, "W": 20.0, "k_MN_m3": 35.0,
            "cargas": [{"nome": "t", "P_kN": 30.0,
                        "area_contato_cm2": 300.0}]}
    sem = dict(base, udl_kN_m2=500.0)
    r = pi.verifica_piso(sem)
    assert r["OK"] is False
    assert "sigma_solo_adm_kN_m2 nao declarado" in r["motivo"], r["motivo"]
    com_pouco = dict(base, udl_kN_m2=500.0, sigma_solo_adm_kN_m2=100.0)
    r2 = pi.verifica_piso(com_pouco)
    assert r2["OK"] is False and r2["udl"]["OK"] is False
    com_folga = dict(base, udl_kN_m2=40.0, sigma_solo_adm_kN_m2=200.0)
    r3 = pi.verifica_piso(com_folga)
    assert r3["OK"] is True and r3["udl"]["OK"] is True
    sem_udl = pi.verifica_piso(dict(base))
    assert sem_udl["OK"] is True


def test_11_lente_cobre_os_quatro_modulos():
    """A lente G75 via 0 sitios nos 4; depois do G84 ve 29, todos triados."""
    tudo = vd.varredura()
    por_arq = Counter(d["arquivo"] for d in tudo
                      if d["arquivo"] in ("galpao_hidraulica.py",
                                          "piso_industrial.py",
                                          "secundarios_nbr8800.py",
                                          "montagem.py"))
    assert por_arq["galpao_hidraulica.py"] == 10, dict(por_arq)
    assert por_arq["piso_industrial.py"] == 5, dict(por_arq)
    assert por_arq["secundarios_nbr8800.py"] == 13, dict(por_arq)
    assert por_arq["montagem.py"] == 1, dict(por_arq)
    assert {d["chave"] for d in tudo} <= vd.NORMATIVAS_G75


_GAP_G84_GET = [
    "def dimensiona(cfg):",
    "    p = float(cfg.get(\"p_alim_kPa\", 100.0))",
    "    return p",
    "",
    "def verifica(caso):",
    "    s = caso.get(\"sigma_solo_adm_kN_m2\")",
    "    if s is None:",
    "        raise ValueError(\"sigma_solo_adm_kN_m2 nao declarado\")",
    "    return float(s)",
    "",
]

_GAP_G84_OR = [
    "def plano(pecas):",
    "    w = pecas.get(\"peso_unit_kg\") or 0.0",
    "    return w",
    "",
]


def test_12_vermelho_por_injecao_chaves_g84(tmp_path):
    """Baseline nos dois sentidos p/ o vocabulario novo, em dir temporario
    (licao do D81: sem mutar o repo). Sentido get: default visto;
    declara-ou-recusa sai OBRIGATORIO. Sentido or: resgate visto."""
    gap = tmp_path / "zz_g84.py"
    gap.write_text(chr(10).join(_GAP_G84_GET) + chr(10), encoding="utf-8")
    achados = {(d["arquivo"], d["chave"], d["default"], d["via"])
               for d in vd.varredura(raiz=str(tmp_path))}
    assert ("zz_g84.py", "p_alim_kPa", "100.0", "get") in achados, achados
    assert ("zz_g84.py", "sigma_solo_adm_kN_m2", "OBRIGATORIO", "get") \
        in achados, achados
    limpo = tmp_path / "zz_limpo.py"
    limpo.write_text("def soma(a, b):\n    return a + b\n", encoding="utf-8")
    so_limpo = [d for d in vd.varredura(raiz=str(tmp_path))
                if d["arquivo"] == "zz_limpo.py"]
    assert so_limpo == [], so_limpo
    gap_or = tmp_path / "zz_or_g84.py"
    gap_or.write_text(chr(10).join(_GAP_G84_OR) + chr(10), encoding="utf-8")
    ach_or = {(d["arquivo"], d["chave"], d["default"], d["via"])
              for d in vd.varredura(raiz=str(tmp_path))}
    assert ("zz_or_g84.py", "peso_unit_kg", "0.0", "or") in ach_or, ach_or


def test_13_piso_posicoes_default_nao_esconde_canto():
    """O default [interior, borda] (opt-out do canto livre) nao muda a h
    adotada no caso de referencia: a borda governa (fonte independente: o
    h comercial adotado, nao a formula interna)."""
    import piso_industrial as pi
    carga = {"nome": "pe porta-palete", "P_kN": 45.0,
             "area_contato_cm2": 200.0}
    base = {"L": 40.0, "W": 20.0, "fck_MPa": 30.0, "k_MN_m3": 35.0,
            "cargas": [carga]}
    r1 = pi.verifica_piso(base)
    com_canto = dict(base)
    com_canto["cargas"] = [dict(carga, posicoes=["interior", "borda",
                                                 "canto"])]
    r2 = pi.verifica_piso(com_canto)
    assert r1["pontos"][0]["pos_governante"] == "borda"
    assert r1["h_mm"] == r2["h_mm"] == 280, (r1["h_mm"], r2["h_mm"])
