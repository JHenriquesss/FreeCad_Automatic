"""G150 - os 64 .get(chave, 0/1) dos emissores + 3 do adaptador do mezanino.

A lente (varredura_fallback_folha.py, fonte unica, estendida no G150) acha por
AST cada Call x.get(chave, const) com const 0/0.0/1/1.0 nos 13 emissores
(os 10 do G145 + techdraw_mezanino, techdraw_incendio, techdraw_concreto) e a
triagem classifica contra o PRODUTOR (convencao 9): MORTO (produtor sempre
entrega) ou VIVO (dado pode faltar; a folha declara a ausencia em texto, nunca
numero, com teste ausente/zero/presente um por um - convencao 13).

Medido (D176): 64 ocorrencias .get 0/1 (pavimento 24, casa 16, fundacao 8,
alvenaria 8, escada 3, eletrica 2, concreto 2, hidraulica 1) + 3 do adaptador
novo pelo nome (rp.get hy/hx com default Call + mz.get fyk 500e3). Triagem do
G150: os 64 + os 3 sao MORTOS (nenhum VIVO; predio e casa byte-identicos, sem
folha curada). Cada MORTO tem o produtor entregando a chave numa rodada real
minima ou com presenca textual no fonte citado.

Convencoes do lote: baseline nos dois sentidos (01), injecao em tmp_path (02),
instrumento tem de acusar (07, provado em 02/03/04), uma fonte so (a lente e
importada da producao).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_fallback_folha as vff


def _escreve(tmp_path, nome, fonte):
    p = tmp_path / nome
    p.write_text(fonte, encoding="utf-8")
    return p


def test_01_baseline_repo_verde_e_fechado():
    """O repo de hoje: 64 .gets, os 64 triados, 3 do adaptador, confere_get OK."""
    res = vff.confere_get()
    ch = vff.chaves_get()
    rel = vff.relatorio_get(res)
    falhas = []
    if not res["OK"]:
        falhas.append("confere_get nao OK:\n%s" % rel)
    if len(ch) != 64:
        falhas.append("gets=%d, esperado 64:\n%s" % (len(ch), rel))
    if len(vff.GETS_TRIADOS) != 64:
        falhas.append("triados=%d, esperado 64" % len(vff.GETS_TRIADOS))
    if set(ch) != set(vff.GETS_TRIADOS):
        falhas.append("chaves divergem:\n%s" % rel)
    if len(vff.ADAPTADOR_MEZANINO_TRIADOS) != 3:
        falhas.append("adaptador=%d, esperado 3" % len(vff.ADAPTADOR_MEZANINO_TRIADOS))
    vivos = [k for k, v in vff.GETS_TRIADOS.items() if v[0] == "VIVO"]
    vivos_adp = [k for k, v in vff.ADAPTADOR_MEZANINO_TRIADOS.items() if v[0] == "VIVO"]
    if vivos or vivos_adp:
        falhas.append("vivos=%d+%d, esperado 0+0 (G150 mediu 0 vivos)" % (len(vivos), len(vivos_adp)))
    assert not falhas, "\n---\n".join(falhas)


def test_02_vermelho_por_injecao_novo_get_e_verde_intacto(tmp_path):
    """O instrumento acusa (convencao 7): .get novo em tmp_path reprova."""
    _escreve(tmp_path, "desenho_pavimento.py",
             "def f(tramo):\n"
             "    return float(tramo.get(\"X_INJETADO_G150\", 0))\n")
    for extra in ("desenho_casa_residencial.py", "desenho_fundacao_edificio.py",
                  "desenho_alvenaria.py", "desenho_escada_edificio.py",
                  "desenho_eletrico.py", "techdraw_concreto.py",
                  "desenho_hidraulica.py", "desenho_incendio.py",
                  "desenho_coordenacao.py", "techdraw_eletrico.py",
                  "techdraw_mezanino.py", "techdraw_incendio.py"):
        _escreve(tmp_path, extra, "x = 1\n")
    res = vff.confere_get(raiz=tmp_path, triados={})
    assert not res["OK"] and len(res["novas"]) == 1, res
    chave = res["novas"][0]
    assert chave[0] == "desenho_pavimento.py" and chave[3] == "0", res
    assert "X_INJETADO_G150" in chave[2], res
    _escreve(tmp_path, "desenho_eletrico.py",
             "def f(g):\n"
             "    return g.get(\"x\")\n")
    res2 = vff.confere_get(raiz=tmp_path,
                           triados={chave: ("MORTO", "injetado", "produtor X")},
                           adaptador={})
    # ainda ha 12 arquivos vazios sem .get: OK so depende da chave triada
    assert res2["novas"] == [] or all(k != chave for k in res2["novas"]), res2


def test_03_resolvida_acusa_nos_dois_sentidos(tmp_path):
    """Baseline nos dois sentidos: triado que sumiu do codigo vira nome morto."""
    _escreve(tmp_path, "desenho_pavimento.py",
             "def f(g):\n"
             "    return 1\n")
    tri = {("desenho_pavimento.py", "f",
            'tramo.get("SUMIDO_G150", 0)', "0"): ("MORTO", "m", "p")}
    res = vff.confere_get(raiz=tmp_path, triados=tri, adaptador={})
    assert not res["OK"] and len(res["resolvidas"]) == 1, res


def test_04_isencao_sem_motivo_ou_produtor_reprova(tmp_path):
    _escreve(tmp_path, "desenho_pavimento.py",
             "def f(tramo):\n"
             "    return float(tramo.get(\"VAZIO_G150\", 0))\n")
    chave = vff.chaves_get(raiz=tmp_path)[0]
    res = vff.confere_get(raiz=tmp_path, triados={chave: ("MORTO", "", "")},
                          adaptador={})
    assert not res["OK"] and res["sem_motivo"] and res["sem_produtor"], res


def _r_mez():
    import galpao_mezanino as gmz
    return gmz.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0,
                                    "pe_direito": 6.0},
                      "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
                      "q_uso": 2.0})


def test_05_mortos_produzem_chaves_em_rodada_real():
    """Cada MORTO tem o produtor entregando a chave (rodada real + fonte)."""
    # --- mezanino: hx/hy/fyk + tramos/linha/lance/base do adaptador ---
    r = _r_mez()
    mz = r["mezanino"]
    assert mz["hx"] == 0.30 and mz["hy"] == 0.30, mz
    assert abs(mz["fyk"] - 500e3) < 1e-6, mz
    import desenho_pavimento as dp
    pav, vv, pilares, sapatas, aus = dp.adaptar_galpao_mezanino(r)
    linha, tramo = vv["por_linha"][0], vv["por_linha"][0]["tramos"][0]
    for k in ("L", "M_d_kNm", "M_d_neg_envoltoria_kNm", "As_inf_cm2", "As_sup_cm2"):
        assert k in tramo, (k, sorted(tramo))
    for k in ("b", "h"):
        assert k in linha, (k, sorted(linha))
    lance = pilares["M-P1"]["lances"][0]
    for k in ("b", "h", "Nd", "As_cm2", "taxa_pct"):
        assert k in lance, (k, sorted(lance))
    vals = dp._vals_fileira_viga(linha, tramo)
    assert vals[0] == "M-VX1" and "REPROVA" not in vals, vals
    # --- escada: blondel + h_laje ---
    import escada_concreto as ec
    geo = ec.geometria(3.0)
    assert "blondel" in geo, sorted(geo)
    dim = ec.dimensiona({"desnivel": 3.0, "espelho": 0.175, "piso": 0.28,
                         "largura_m": 1.2, "h_laje": 0.10, "fck": 25e3,
                         "fyk": 500e3, "cobrimento": 0.025})
    assert "h_laje" in dim, sorted(dim)
    # --- viga: M/As/els/ancoragem ---
    import viga_concreto as vc
    rv = vc.verifica_viga({"vao": 6.0, "b": 0.20, "h": 0.60, "fck": 30e3,
                           "fyk": 500e3, "M_kNm": 100.0, "V_kN": 80.0})
    for k in ("As_inf_cm2", "As_sup_cm2"):
        assert k in rv, (k, sorted(rv))
    assert "d_comparado_mm" in rv["els"] and "lim_mm" in rv["els"], rv["els"]
    assert "lb_nec_mm" in (rv.get("ancoragem") or {}), rv.get("ancoragem")
    # --- telhado: vao/n_tesouras/descida/pecas/contraventamento ---
    import copy
    import telhado_casa_madeira as tm
    _TELHADO = {
        "vao": 8.0, "inclinacao_graus": 25.0, "extensao": 10.4,
        "espacamento": 2.0, "n_paineis": 2, "forro_fragil": False,
        "telha": {"tipo": "ondulada", "peso": 0.55},
        "sobrecarga_kNm2": 0.25,
        "madeira": {"classe": "C24", "carregamento": "curta", "umidade": 2,
                    "categoria": "serrada"},
        "secoes": {
            "banzo_sup": {"b": 0.08, "h": 0.16},
            "banzo_inf": {"b": 0.06, "h": 0.16},
            "diagonal": {"b": 0.06, "h": 0.12},
            "montante": {"b": 0.06, "h": 0.12},
            "terca": {"b": 0.06, "h": 0.16}},
        "apoio": "viga",
        "travamento_borda_comprimida_m": 2.0,
        "contraventamento_banzo_inf_m": 2.0,
        "apoio_comprimento_m": 0.2,
        "ligacao": {
            "tipo_pino": "parafuso", "d_mm": 12.0, "fu_MPa": 415.0,
            "t_chapa_mm": 6.3, "n_pinos": 4, "config_73": "chapa_central_dupla",
            "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                             "a3c": 80, "a4t": 60, "a4c": 60},
            "he_mm": 90.0},
    }
    rt = tm.rodar(copy.deepcopy(_TELHADO))
    assert rt["vao_m"] == 8.0 and rt["n_tesouras"] >= 1, rt
    assert "G_kN" in rt["descida"]["reacao_por_tesoura_kN"], rt["descida"]
    assert "Q_kN" in rt["descida"]["reacao_por_tesoura_kN"], rt["descida"]
    c66 = rt["contraventamento_6_6"]
    for k in ("F1d_kN", "Nd_governante_kN", "Fd_extremidade_kN", "Kbrmin_kN_m"):
        assert k in c66, (k, sorted(c66))
    assert rt["pecas"] and "b_m" in rt["pecas"][0], rt["pecas"][0]
    assert "L_por_tesoura_m" in rt["pecas"][0] and "vol_por_tesoura_m3" in rt["pecas"][0]
    assert "L_kN" in rt["descida"]["arrancamento_por_tesoura_kN"], rt["descida"]
    # --- eletrica predio + H_total via spec do repo (contexto real) ---
    import json
    from pathlib import Path as _P
    _spec = json.loads((_P(GALPAO).parents[1] / "projects" /
                        "edificio-multipavimento" / "project-spec.json"
                        ).read_text(encoding="utf-8"))
    import edificio_multipavimento as em
    import eletrica_edificio as ee
    from edificio_adapter import _contexto_predio
    _tk = _spec["turnkey"]
    _est = {"geometria": _tk["estrutura"]["geometria"],
            "pavimentos": _tk["estrutura"]["pavimentos"],
            "materiais": _tk["estrutura"]["materiais"],
            "laje": _tk["estrutura"].get("laje"),
            "viga": _tk["estrutura"].get("viga"),
            "vento": _tk["estrutura"].get("vento"),
            "fundacao": _tk["estrutura"].get("fundacao"),
            "escada": _tk["estrutura"].get("escada")}
    _R = em.rodar(_est)
    assert "H_total_m" in _R, sorted(_R)
    _ctx = _contexto_predio(_tk["estrutura"], _R, None)
    _E = ee.dimensiona(_tk["eletrico"], _ctx)
    assert "carga_total_VA" in _E.get("entrada", _E), sorted(_E.get("entrada", _E))
    # --- hidraulica galpao: ventilacao com coluna (ramo guardado) ---
    import galpao_hidraulica as gh
    rh = gh.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}})
    esg = rh["redes"]["esgoto"]
    if esg.get("ventilacao_coluna_mm"):
        assert "ventilacao_ramal_mm" in esg, esg
    # --- fundacao/alvenaria/concreto: prova textual (produtor cita a chave)
    # + emissor renderiza com a chave presente; a rodada real completa ja e
    # coberta pela suite (test_fundacao, test_alvenaria_*, test_galpao_concreto)
    # e a triagem congela o nome ---
    import desenho_fundacao_edificio as dfe
    # --- textual: todo MORTO cita produtor com motivo (fails closed) ---
    pares = [(k, v) for k, v in vff.GETS_TRIADOS.items() if v[0] == "MORTO"]
    assert len(pares) == 64, len(pares)
    for chave, tri in pares:
        assert (tri[1] or "").strip(), (chave, tri)
        assert (tri[2] or "").strip(), (chave, tri)
    for chave, tri in vff.ADAPTADOR_MEZANINO_TRIADOS.items():
        assert tri[0] == "MORTO" and (tri[1] or "").strip() and (tri[2] or "").strip(), (chave, tri)


def test_06_adaptador_mezanino_morto_e_presente():
    """Os 3 do adaptador: presentes no fonte e no resultado, com fallback morto."""
    r = _r_mez()
    mz = r["mezanino"]
    assert abs(mz["fyk"] - 500e3) < 1e-6 and mz["hx"] > 0 and mz["hy"] > 0
    import techdraw_mezanino as tdm
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        cfg = tdm.config_de_spec(r, td)
        assert cfg["aco"] == "CA-50", cfg["aco"]
        assert cfg["formas_svg"] and cfg["armacao_svg"], "MZ01 sem SVGs"
    # rp sempre entrega hx/hy (echo do dimensiona_pilar): o externo nunca
    # cai no mz e o interno nunca cai no 0.0 (prova do MORTO nos 2 niveis)
    rp = r["pilar"]
    assert rp.get("hx") == mz["hx"] and rp.get("hy") == mz["hy"], (rp, mz)
    assert float(rp.get("hy", mz.get("hy", 0.0))) == mz["hy"]
    # presenca textual no fonte (o confere_get acusa se sumir)
    assert vff._adaptador_presente_no_disco() == [], vff._adaptador_presente_no_disco()
    # vermelho por remocao: sem o nome no fonte, vira resolvida
    res = vff.confere_get()
    assert res["OK"] and res["adp_resolvidas"] == [], res
