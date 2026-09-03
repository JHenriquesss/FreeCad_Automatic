# ============================================================================
# test_varredura_nao_verificados.py - G33: A VARREDURA NAO PODE CRESCER SOZINHA.
# Molde do test_alcancabilidade.py: a lista de ilhas e DECLARADA e CONFERIDA,
# nao so listada. Se um par novo (elemento, esforco calculado) aparecer sem
# cheque, este teste fica vermelho. Se um par for corrigido, a lista tem que
# diminuir aqui - e o teste tambem fica vermelho ate a declaracao acompanhar.
#   - test_lista_confere_com_varredura: o coracao (scan == declarado).
#   - test_toda_ilha_declarada_ainda_existe: filtro de nome morto - se o
#     arquivo for renomeado ou o trecho sair, a declaracao morre em voz alta.
#   - test_pilar_do_galpao_agora_E_verificado_a_cortante (G39): prova em
#     execucao de que a ilha do pilar foi corrigida (o esforco existe E o
#     cheque roda), nao artefato do parser. Trava a transicao.
#   - test_tipologias_varridas_existem: a cobertura nao pode encolher.
# ============================================================================
"""Guarda da varredura G33: analisado e nunca verificado."""

import os
import pathlib
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = pathlib.Path(os.path.dirname(HERE))
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))

import varredura_nao_verificados as var


def test_lista_confere_com_varredura():
    declaradas = var.chaves_declaradas()
    varridas = var.chaves_varridas()
    novas = sorted(set(varridas) - set(declaradas))
    corrigidas = sorted(set(declaradas) - set(varridas))
    assert not novas, (
        "pares (elemento, esforco) calculados e sem cheque que NAO estavam "
        "declarados: %r. Ou o par passa a ser verificado (e entra o cheque), "
        "ou entra declarado em varredura_nao_verificados.NAO_VERIFICADOS." % (novas,))
    assert not corrigidas, (
        "pares declarados que a varredura NAO acha mais: %r. Se o cheque foi "
        "ligado, atualize NAO_VERIFICADOS (a lista tem que diminuir junto)." % (corrigidas,))


def test_toda_ilha_declarada_ainda_existe():
    # Filtro de nome morto: se o arquivo for renomeado, a declaracao continua
    # compilando e a ilha some em silencio.
    for ilha in var.NAO_VERIFICADOS:
        trecho = ilha.get("trecho")
        if not trecho:
            continue
        dono = None
        for arq in ("edificio_multipavimento.py", "galpao_concreto.py",
                    "estrutura_casa.py", "galpao_mezanino.py"):
            if trecho in (GALPAO / arq).read_text(encoding="utf-8"):
                dono = arq
                break
        assert dono is not None, (
            "ilha declarada %(tipologia)s/%(elemento)s/%(esforco)s com trecho "
            "%r que nao aparece em nenhum orquestrador: a ponte morreu" % ilha)
    # O cheque-irmao da casa tem que continuar existindo: G34 reusou ele no
    # edificio, entao ele e' o padrao dos DOIS.
    fonte_casa = (GALPAO / "estrutura_casa.py").read_text(encoding="utf-8")
    assert "def verifica_vigas" in fonte_casa, (
        "estrutura_casa.verifica_vigas sumiu: o padrao-irmao que a varredura "
        "usa como referencia de verificacao por tramo morreu")
    assert 'enumerate(linha["vaos"])' in fonte_casa
    # G34: o edificio tambem verifica por tramo -- se o repasse sumir, a
    # varredura volta a achar as 3 ilhas de viga e test_lista_confere falha.
    fonte_ed = (GALPAO / "edificio_multipavimento.py").read_text(encoding="utf-8")
    assert "verifica_vigas" in fonte_ed, (
        "edificio_multipavimento perdeu o verifica_vigas por tramo (G34): "
        "a viga voltaria a ser so analisada")


def test_vigas_do_edificio_agora_SAO_verificadas():
    # G34 FECHOU as 3 ilhas de viga: prova em execucao de que o esforco existe
    # E o cheque roda (o contrario do teste abaixo, que prova a ilha restante).
    import edificio_multipavimento as em
    r = em.rodar({
        "geometria": {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5],
                      "pe_direito": 2.90},
        "pavimentos": ([{"nome": "Cobertura", "uso": "cobertura_manutencao"}]
                       + [{"nome": "Tipo %d" % i, "uso": "residencial_dormitorio"}
                          for i in range(2, 0, -1)]),
        "laje": {"h": 0.10}, "viga": {"b": 0.20, "h": 0.50},
        "materiais": {"fck": 30e3, "fyk": 500e3},
    })
    v0 = r["vigas"][0]
    assert max(map(abs, v0["M_positivo"])) > 0, "sem M_positivo a prova evaporou"
    assert max(map(abs, v0["M_apoios"])) > 0, "sem M_apoios a prova evaporou"
    assert max(map(abs, v0["V_max"])) > 0, "sem V_max a prova evaporou"
    # a verificacao por tramo existe e cobre flexao/cortante/ELS/ancoragem
    vv = r.get("vigas_verificacao")
    assert isinstance(vv, dict) and vv.get("por_linha"), (
        "edificio sem vigas_verificacao: G34 desfeito em silencio")
    assert vv["OK"], vv["reprovados"]
    for linha in vv["por_linha"]:
        for tramo in linha["tramos"]:
            assert tramo["OK"], (linha["nome"], tramo)
            assert tramo["As_inf_cm2"] > 0 and tramo["As_sup_cm2"] > 0
            assert tramo["V_d_kN"] > 0 and tramo["cort_ok"]
            assert tramo["momento_negativo_coberto"]
            ver = tramo["verificacao"]
            assert ver["els_ok"] and ver["fissu_ok"]
            assert ver["ancoragem"]["lb_nec_mm"] > 0
    # e a varredura nao lista mais viga: se voltar a listar, a lista-guarda
    # tem que diminuir junto (test_lista_confere) -- nunca em silencio.
    assert ("edificio", "viga", "M_positivo") not in var.chaves_varridas()
    assert ("edificio", "viga", "M_apoios") not in var.chaves_varridas()
    assert ("edificio", "viga", "V_max") not in var.chaves_varridas()
    assert ("edificio", "viga", "M_positivo") not in var.chaves_declaradas()


def test_pilar_do_galpao_agora_E_verificado_a_cortante():
    # G39 FECHOU a ilha do pilar: prova em execucao de que o esforco existe
    # E o cheque roda (o contrario do que a ilha afirmava). Trava a transicao:
    # se o repasse de V cair, este teste -- e o test_lista_confere -- ficam
    # vermelhos, nunca em silencio.
    import galpao_concreto as gc
    rg = gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
                   "n_porticos": 7, "v0": 40.0, "G_roof": 0.30, "Q_roof": 0.25,
                   "fck": 30e3, "sigma_solo_adm": 250.0,
                   "travamento_longitudinal": "topo"})
    assert rg["gates"]["vento"]["V_base_k"] > 0, "sem V a prova evaporou"
    p = rg["pilar"]
    assert p.get("Vd_gov", p.get("Vd", 0.0)) > 0, "fuste sem Vd: repasse caiu"
    assert p.get("VRd2", 0.0) > 0 and p.get("cort_ok") is True, (
        "fuste sem verificacao de cortante: %r" % ({k: p.get(k) for k in
        ("Vd", "Vd_gov", "VRd2", "u_cort", "cort_ok")},))
    # Vd_gov e o vento principal majorado: 1,4 * V_base_k
    assert p.get("Vd_gov", 0.0) == abs(1.4 * rg["gates"]["vento"]["V_base_k"]) or \
        abs(p.get("Vd_gov", 0.0) - 1.4 * rg["gates"]["vento"]["V_base_k"]) < 0.2, \
        (p.get("Vd_gov"), rg["gates"]["vento"]["V_base_k"])
    assert p["OK"] and rg["gates"]["pilar"]["OK"], (p, rg["gates"]["pilar"])
    # e a varredura nao lista mais o pilar: se voltar a listar, a lista-guarda
    # tem que voltar junto (test_lista_confere) -- nunca em silencio.
    assert ("galpao", "pilar", "V (cortante de base V_w_k do vento)") \
        not in var.chaves_varridas()
    assert ("galpao", "pilar", "V (cortante de base V_w_k do vento)") \
        not in var.chaves_declaradas()


def test_tipologias_varridas_existem():
    for tipologia, arquivos in var.TIPOLOGIAS.items():
        assert arquivos, "tipologia %s sem orquestrador declarado" % tipologia
        for arq in arquivos:
            assert (GALPAO / arq).is_file(), (
                "orquestrador %s da tipologia %s sumiu" % (arq, tipologia))


def test_casa_e_mezanino_continuam_sem_ilha_nova():
    # Direto no mecanismo (nao so na lista): quem monta pavimento e verifica
    # por tramo nao pode aparecer como ilha.
    import ast
    for arq in ("estrutura_casa.py", "galpao_mezanino.py", "galpao_concreto.py",
                "edificio_multipavimento.py"):
        caminho = GALPAO / arq
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        no = None
        for n in ast.walk(arvore):
            if isinstance(n, ast.FunctionDef) and n.name == "rodar":
                no = n
                break
        assert no is not None, "%s perdeu o rodar()" % arq
    # A casa monta pavimento E verifica por tramo: nunca pode virar ilha da
    # regra 1 sem este teste acusar. G34: o edificio entrou no mesmo grupo.
    fonte = (GALPAO / "estrutura_casa.py").read_text(encoding="utf-8")
    assert "verifica_vigas(pav" in fonte
    fonte_ed = (GALPAO / "edificio_multipavimento.py").read_text(encoding="utf-8")
    assert "verifica_vigas" in fonte_ed
