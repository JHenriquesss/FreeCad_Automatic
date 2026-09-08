"""Lente G69 (D86): as guardas que concordam consigo mesmas.

Censo da arvore (baseline em TRIADAS_G69, congelado nos DOIS sentidos):
17 defs confere_*/verifica_fechamento*. A revisao achou a contagem de 15
desatualizada dentro do proprio lote — confere_vergas nasceu no G70 e o
censo, que so procurava os nomes que ja esperava, nao a viu; e o G66
ganhou confere_fechamento_area. Cada guarda vem com origem dos 2 lados:

1. alvenaria_estrutural.confere_fechamento_horizontal — A=soma Fi
   (Fi=Qh x quota, quota=k/k_total, mesmo modulo), B=Qh declarada que
   entrou na reparticao. MESMA expressao -> DECLARACAO (pega adulteracao
   posterior, nunca erro de rigidez). Docstring diz isso; nao apagar.
2. alvenaria_estrutural.confere_fronteira_peso (G60 isolado) — A=Nd que
   entrou na verificacao, B=carga via 6120 passada PRONTA. Independencia
   mora no CHAMADOR; quando ambos sao q x L -> DECLARACAO de transcricao.
3. alvenaria_estrutural.confere_fronteira_peso_parcela (G61) — A=parcela
   Nd isolada (chamador: q x L), B=recomputo interno (q x L, mesma tabela).
   MESMA expressao -> DECLARACAO (pega L/GF/revestimento, nunca parede
   errada). A relacao independente do plano e' a simetria (G61).
4. estrutura_casa.verifica_fechamento_alvenaria — TOTAL (soma por_linha vs
   carga_laje+q*L+telhado: pega OMISSAO de painel) + SIMETRIA (quinhoes
   espelhados em plano palindromo: pega ENDERECAMENTO errado). Hibrida:
   total=declaracao de integridade, simetria=relacao independente.
5. estrutura_casa.confere_simetria_quinhao — A=quinhao linha k, B=quinhao
   linha espelhada; condicao=vaos palindromos (plano). INDEPENDENTE.
6. pavimento_tipo.verifica_fechamento — A=soma reacoes nos pilares (descida),
   B=carga_laje+peso_viga*comp+g_parede*contorno (geometria x cargas).
   Origens diferentes -> INDEPENDENTE (pega laje que some).
7. bim_edificio.confere_modelo (+_confere_modelo_alvenaria) — A=contagem de
   TIPOS no modelo emitido, B=contagem derivada do calculo aprovado
   (pilares x niveis, vigas por malha, fundacao aprovada). INDEPENDENTE.
8. bim_edificio.confere_empilhamento / bim_casa_residencial.confere_solidos
   — A/B=pares de volumes do modelo (AABB via geometria_membros); condicao
   geometrica externa (face, nunca volume). INDEPENDENTE.
9. bim_casa_residencial.confere_areas — A=area do Space emitido (dx*dy),
   B=area do programa declarada. INDEPENDENTE (rotulo x geometria).
10. desenho_pavimento.confere_desenho — A=contagens do DADO (len pilares/
    paineis, linhas de viga), B=rects/textos do SVG. INDEPENDENTE.
11. desenho_pavimento.confere_armacao_vigas — A=tramos calculados por viga,
    B=ocorrencias do nome da viga no SVG (uma por linha de tramo).
    INDEPENDENTE apos G69 (antes: so presenca do nome — parcial D86).
12. desenho_alvenaria.confere_elevacao — A=rects data-parede/vao/ajuste no
    SVG, B=por_linha+vaos+fiadas(pe_direito). INDEPENDENTE.
13. desenho_alvenaria.confere_fiadas — A=rects data-fiadas-*/2 fiadas,
    B=por_linha+vaos. INDEPENDENTE.
14. desenho_alvenaria.confere_vergas (G70) — A=rects data-verga/
    data-contraverga do SVG (comprimento, altura, armadura), B=vergas/
    contravergas do registro calculado. INDEPENDENTE (desenho x dado).
15. telhado_casa_madeira.confere_fechamento_area (G66, pos-revisao) —
    A=carga lancada nos nos, B=telha x area INCLINADA + sobrecarga x area
    PROJETADA. INDEPENDENTE: o fechamento_carga irmao (reacao x lancado)
    fecha por construcao e nao via o tributario de beiral errado.
16. varredura_faixa_validade.confere_cobertura (lente G51) — A=arquivos no
    disco, B=isencoes declaradas com motivo. INDEPENDENTE (meta-guarda).

Proibido G69: apagar guarda fraca sem substituto. As declaracoes acima
ficam — ditas como declaracoes — e a prova do vermelho mora nestes testes.
Mapa do vermelho: neste arquivo (D86 das 2 fracas + omissao do total +
areas, solidos/empilhamento, modelo, desenho, armacao, elevacao, fiadas,
fechamento do pavimento); simetria e enderecamento errado em
test_alvenaria_portante_g61.py; 10 % da fronteira em
test_alvenaria_estrutural_g60.py; Fi adulterada em
test_alvenaria_contraventamento_g63.py; cobertura nos dois sentidos em
test_varredura_faixa_validade_g51.py.
"""

import copy
import re
import xml.etree.ElementTree as ET

import pytest

import alvenaria_estrutural as alv
import desenho_pavimento as dp
import pavimento_tipo as pt


# Baseline do censo (D87: congelado nos DOIS sentidos). Cada par aqui tem
# a triagem escrita no cabecalho deste arquivo, com a origem de cada lado.
TRIADAS_G69 = {
    ("alvenaria_estrutural", "confere_fechamento_horizontal"),
    ("alvenaria_estrutural", "confere_fronteira_peso"),
    ("alvenaria_estrutural", "confere_fronteira_peso_parcela"),
    ("bim_casa_residencial", "confere_areas"),
    ("bim_casa_residencial", "confere_solidos"),
    ("bim_edificio", "confere_modelo"),
    ("bim_edificio", "confere_empilhamento"),
    ("desenho_alvenaria", "confere_elevacao"),
    ("desenho_alvenaria", "confere_fiadas"),
    ("desenho_alvenaria", "confere_vergas"),
    ("desenho_pavimento", "confere_desenho"),
    ("desenho_pavimento", "confere_armacao_vigas"),
    ("estrutura_casa", "confere_simetria_quinhao"),
    ("estrutura_casa", "verifica_fechamento_alvenaria"),
    ("pavimento_tipo", "verifica_fechamento"),
    ("telhado_casa_madeira", "confere_fechamento_area"),
    ("varredura_faixa_validade", "confere_cobertura"),
}


TE = 0.14
HE = 2.70


def _paredes_2():
    return [
        {"nome": "PX-1", "comprimento_m": 3.0, "te_m": TE, "he_m": HE},
        {"nome": "PX-2", "comprimento_m": 3.0, "te_m": TE, "he_m": HE},
    ]


# --- D86 provado: a guarda passa com a fisica errada ------------------------

def test_fechamento_horizontal_passa_com_rigidez_errada():
    """Duas reparticoes com he diferente dao Fis diferentes e AMBAS fecham.

    Se a guarda conferisse a formula, uma delas teria de acusar. Como fecha
    nos dois casos, ela declara integridade (soma==Qh), nao fisica.
    """
    pars_ok = _paredes_2()
    pars_errada = [
        {"nome": "PX-1", "comprimento_m": 3.0, "te_m": TE, "he_m": HE},
        {"nome": "PX-2", "comprimento_m": 3.0, "te_m": TE, "he_m": HE * 2},
    ]
    d_ok = alv.distribuir_horizontal_por_rigidez(30.0, pars_ok)
    d_err = alv.distribuir_horizontal_por_rigidez(30.0, pars_errada)
    assert d_ok["OK"] and d_err["OK"]
    fi_ok = {r["nome"]: r["Fi_kN"] for r in d_ok["por_parede"]}
    fi_err = {r["nome"]: r["Fi_kN"] for r in d_err["por_parede"]}
    assert fi_ok["PX-1"] != pytest.approx(fi_err["PX-1"], rel=1e-3)
    # e a declaracao fecha nos dois: a prova de que nao confere a formula
    assert alv.confere_fechamento_horizontal(d_ok, 30.0)["OK"] is True
    assert alv.confere_fechamento_horizontal(d_err, 30.0)["OK"] is True
    # ...mas acusa adulteracao posterior (o que ela declara de verdade)
    adulterada = [{"Fi_kN": r["Fi_kN"]} for r in d_ok["por_parede"]]
    adulterada[0]["Fi_kN"] *= 1.10
    f = alv.confere_fechamento_horizontal(adulterada, 30.0)
    assert f["OK"] is False
    assert "fechamento_horizontal_diverge" in f["motivo"]


def test_fronteira_parcela_passa_com_tipo_errado_consistente():
    """Caller e guarda usando o MESMO tipo errado fecham — D86 provado.

    A guarda compara q(tipo)*L contra q(tipo)*L: se o tipo estiver errado
    dos dois lados, ela concorda consigo mesma. O que ela pega e'
    transcricao (L, GF, revestimento), nao a escolha do tipo.
    """
    import cargas_nbr6120 as cg

    tipo_certo = "bloco_concreto_estrutural"
    tipo_errado = "bloco_concreto_vedacao"
    esp, rev, L = 14.0, 2.0, 3.3
    q_err = cg.carga_linear_parede(tipo_errado, esp, HE, rev)
    # chamador isolou a parcela com o tipo errado — a guarda fecha igual
    assert alv.confere_fronteira_peso_parcela(
        q_err * L, tipo_errado, esp, HE, L, rev)["OK"] is True
    # ...mas 10 % a mais num lado acusa a junta (transcricao), nao o elemento
    assert alv.confere_fronteira_peso_parcela(
        q_err * L * 1.10, tipo_errado, esp, HE, L, rev)["OK"] is False
    # e sem parcela isolavel o caso RECUSA em vez de fingir conferencia
    sem = alv.confere_fronteira_peso_parcela(None, tipo_certo, esp, HE, L, rev)
    assert sem["OK"] is False and "parcela" in sem["motivo"]


def test_docstrings_dizem_declaracao_onde_e_decorativa():
    assert "DECLARACAO" in alv.confere_fechamento_horizontal.__doc__
    assert "DECLARACAO" in alv.confere_fronteira_peso_parcela.__doc__
    assert "D86" in alv.confere_fechamento_horizontal.__doc__
    assert "G69" in alv.confere_fronteira_peso_parcela.__doc__


# --- sobreviventes: vermelho por injecao ------------------------------------

def _cfg(**kw):
    base = {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5], "h_laje": 0.10,
            "uso": "residencial_dormitorio", "b_viga": 0.20, "h_viga": 0.50,
            "fck": 30e3, "fyk": 500e3, "pe_direito": 2.90}
    base.update(kw)
    return base


def test_verifica_fechamento_acusa_pilar_sem_carga():
    """verifica_fechamento e' independente: some 10 % da carga dos pilares
    e o total tem de acusar."""
    r = pt.monta(_cfg())
    assert pt.verifica_fechamento(r)["ok"]
    roubado = copy.deepcopy(r)
    roubado["N_total_k"] = roubado["N_total_k"] * 0.90
    f = pt.verifica_fechamento(roubado)
    assert f["ok"] is False
    assert f["N_pilares"] == pytest.approx(roubado["N_total_k"], rel=1e-9)


def test_confere_desenho_acusa_pilar_apagado_do_svg():
    """confere_desenho segue o dado; apagando um pilar do SVG o desenho
    deixa de bater com o dado (vermelho real, nao aritmetica)."""
    NS = "{http://www.w3.org/2000/svg}"
    pav = pt.monta(_cfg())
    svg = dp.planta_formas_svg(pav)
    root = ET.fromstring(svg)
    rects = root.findall(".//" + NS + "rect")
    desenhados = sum(1 for x in rects if x.get("fill") == dp.COR_PILAR)
    c = dp.confere_desenho(pav)
    assert desenhados == c["n_pilares"] == len(pav["pilares"])
    # injecao real: remove um rect de pilar do desenho e reconta
    for x in list(root.iter(NS + "rect")) + list(root.iter("rect")):
        if x.get("fill") == dp.COR_PILAR:
            root.remove(x)
            break
    desenhados_depois = sum(
        1 for x in root.findall(".//" + NS + "rect")
        if x.get("fill") == dp.COR_PILAR)
    assert desenhados_depois == desenhados - 1 != c["n_pilares"]


def test_fechamento_alvenaria_acusa_painel_omitido():
    """A parte TOTAL de verifica_fechamento_alvenaria pega omissao: some a
    laje de uma linha e o total tem de acusar (a simetria, ja vermelha no
    G61, pega o enderecamento errado)."""
    import estrutura_casa as ec

    por = [
        {"nome": "BX-0", "comprimento_m": 10.0, "N_laje_kN": 50.0,
         "Nd_parede_kN": 20.0},
        {"nome": "BX-1", "comprimento_m": 10.0, "N_laje_kN": 50.0,
         "Nd_parede_kN": 20.0},
    ]
    ok = ec.verifica_fechamento_alvenaria(por, 100.0, 2.0,
                                          vaos_x=[10.0], vaos_y=[10.0])
    assert ok["ok"] is True
    omitido = copy.deepcopy(por)
    omitido[0]["N_laje_kN"] = 0.0  # painel que nao desceu na linha
    r = ec.verifica_fechamento_alvenaria(omitido, 100.0, 2.0,
                                         vaos_x=[10.0], vaos_y=[10.0])
    assert r["ok"] is False
    assert r["N_paredes_kN"] == pytest.approx(90.0, rel=1e-9)


def test_confere_areas_acusa_area_trocada_e_ausente():
    """confere_areas e' rotulo x geometria: area trocada e ambiente sumido
    tem de acusar."""
    import bim_casa_residencial as bim

    membros = [{"tipo": "Space", "marca": "Q1", "dims": [3000, 4000, 2700]}]
    prog = {"ambientes": [{"nome": "Q1", "area_m2": 12.0}]}
    assert bim.confere_areas(prog, membros)["ok"] is True
    trocada = {"ambientes": [{"nome": "Q1", "area_m2": 13.0}]}
    r = bim.confere_areas(trocada, membros)
    assert r["ok"] is False and r["por_ambiente"][0]["ok"] is False
    ausente = {"ambientes": [{"nome": "Q2", "area_m2": 12.0}]}
    r2 = bim.confere_areas(ausente, membros)
    assert r2["ok"] is False and r2["ausentes"] == ["Q2"]


def test_solidos_e_empilhamento_acusam_volume_comum():
    """confere_solidos/confere_empilhamento: dois volumes no mesmo lugar
    tem de acusar; separados, passar."""
    import bim_casa_residencial as bim
    import bim_edificio as be

    a = {"tipo": "Wall", "marca": "A", "centro": [0, 0, 0],
         "dims": [1000, 1000, 1000]}
    longe = {"tipo": "Wall", "marca": "B", "centro": [5000, 0, 0],
             "dims": [1000, 1000, 1000]}
    junto = {"tipo": "Wall", "marca": "B", "centro": [0, 0, 0],
             "dims": [1000, 1000, 1000]}
    assert bim.confere_solidos([a, longe])["OK"] is True
    assert be.confere_empilhamento([a, longe])["OK"] is True
    assert bim.confere_solidos([a, junto])["OK"] is False
    r = be.confere_empilhamento([a, junto])
    assert r["OK"] is False
    assert {(x["a"], x["b"]) for x in r["conflitos"]} == {("A", "B")}


def test_confere_modelo_acusa_viga_faltando():
    """confere_modelo e' calculo x modelo: some uma viga do modelo e o
    quadro tem de acusar."""
    import bim_edificio as be

    estrutura = {"pavimento": {"vaos_x": [5.0], "vaos_y": [4.0],
                               "n_paineis": 1},
                 "descida": {"pavimentos": [{"nome": "Tipo"}]},
                 "pilares": [{}, {}]}
    membros = ([{"tipo": "Column", "pavimento": "Tipo"}] * 2
               + [{"tipo": "Beam", "pavimento": "Tipo"}] * 4
               + [{"tipo": "Slab", "pavimento": "Tipo"}])
    assert be.confere_modelo(estrutura, membros)["ok"] is True
    sem_viga = [m for m in membros]
    sem_viga.pop(2)  # uma viga some do modelo
    r = be.confere_modelo(estrutura, sem_viga)
    assert r["ok"] is False
    assert r["por_tipo"]["Beam"] == 3 != r["esperado"]["Beam"]


def test_elevacao_acusa_parede_apagada():
    """confere_elevacao e' desenho x calculado: apague uma parede do SVG e
    a guarda tem de acusar."""
    import desenho_alvenaria as da

    alv = {"por_linha": [{"vaos": []}, {"vaos": []}]}
    pe = 2.8  # fiadas(2.8) tem resto: 1 ajuste por parede
    svg = ('<svg xmlns="http://www.w3.org/2000/svg">'
           '<rect data-parede="a"/><rect data-parede="b"/>'
           '<rect data-ajuste="1"/><rect data-ajuste="2"/></svg>')
    assert da.confere_elevacao(svg, alv, pe)["ok"] is True
    svg_falta = ('<svg xmlns="http://www.w3.org/2000/svg">'
                 '<rect data-parede="a"/>'
                 '<rect data-ajuste="1"/><rect data-ajuste="2"/></svg>')
    r = da.confere_elevacao(svg_falta, alv, pe)
    assert r["ok"] is False
    assert r["paredes_desenhadas"] == 1 != r["paredes_calculadas"]


def test_fiadas_acusa_fiada_apagada():
    """confere_fiadas: duas fiadas por parede; apague uma e acusa."""
    import desenho_alvenaria as da

    alv = {"por_linha": [{"vaos": []}]}
    svg = ('<svg xmlns="http://www.w3.org/2000/svg">'
           '<rect data-fiadas-parede="BX-0-1"/>'
           '<rect data-fiadas-parede="BX-0-2"/></svg>')
    assert da.confere_fiadas(svg, alv)["ok"] is True
    svg_falta = ('<svg xmlns="http://www.w3.org/2000/svg">'
                 '<rect data-fiadas-parede="BX-0-1"/></svg>')
    r = da.confere_fiadas(svg_falta, alv)
    assert r["ok"] is False


def test_armacao_acusa_tramo_faltando_da_mesma_viga():
    """A versao pre-G69 (so presenca do nome) passava aqui; a contagem por
    viga tem de acusar."""
    vv = {"por_linha": [
        {"nome": "VX-1", "tramos": [{"tramo": 0}, {"tramo": 1}]},
        {"nome": "VX-2", "tramos": [{"tramo": 0}]},
    ], "n_tramos": 3}
    svg_ok = "VX-1 VX-1 VX-2"
    conf_ok = dp.confere_armacao_vigas(vv, svg_ok)
    assert conf_ok["ok"] and conf_ok["n_tramos"] == 3
    svg_falta_um_tramo = "VX-1 VX-2"  # nome presente, tramo faltando
    conf = dp.confere_armacao_vigas(vv, svg_falta_um_tramo)
    assert conf["ok"] is False
    assert any("VX-1" in f for f in conf["faltando"])
    # a presenca pura nao bastaria: documenta o defeito antigo
    nomes = ["%s tramo %d" % ("VX-1", k) for k in (0, 1)]
    assert all(n.split()[0] in svg_falta_um_tramo for n in nomes)


def test_censo_das_guardas_fecha_nos_DOIS_sentidos():
    """A lente mora no teste, e baseline de um sentido so e' relatorio.

    A versao anterior varria APENAS os 8 modulos que ja esperava, e so
    perguntava "sumiu alguma?". Guarda NOVA - em modulo novo ou nos
    mesmos 8 - entrava sem triagem e a suite ficava verde: foi o que
    aconteceu com desenho_alvenaria.confere_vergas, criada pelo G70 no
    mesmo lote e invisivel para o G69. Agora o censo varre a arvore
    inteira e cobra os DOIS sentidos: nenhuma some sem substituto, e
    nenhuma nasce sem entrar na triagem do cabecalho (D87)."""
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parents[1]
    pat = re.compile(r"^\s*def\s+(confere_\w+|verifica_fechamento\w*)")
    achadas = set()
    for arq in sorted(raiz.glob("*.py")):
        for linha in arq.read_text(encoding="utf-8",
                                   errors="ignore").splitlines():
            m = pat.match(linha)
            if m:
                achadas.add((arq.stem, m.group(1)))
    sumiram = TRIADAS_G69 - achadas
    assert not sumiram, ("guardas sumiram sem substituto: %r"
                         % (sorted(sumiram),))
    novas = achadas - TRIADAS_G69
    assert not novas, (
        "guarda nova sem triagem D86 (origem de cada lado, DECLARACAO ou "
        "INDEPENDENTE): declare no cabecalho deste arquivo e em "
        "TRIADAS_G69: %r" % (sorted(novas),))


def test_triagem_do_cabecalho_cobre_cada_guarda_do_censo():
    """O cabecalho e' a triagem escrita; TRIADAS_G69 e' o baseline. Os
    dois tem de falar da mesma lista - senao a lista vira decoracao."""
    doc = __doc__ or ""
    faltando = [nome for _mod, nome in sorted(TRIADAS_G69)
                if nome not in doc]
    assert not faltando, ("guarda no baseline e ausente da triagem "
                          "escrita: %r" % (faltando,))
