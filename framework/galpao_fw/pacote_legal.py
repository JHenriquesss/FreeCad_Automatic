# ============================================================================
# pacote_legal.py - O QUE ESTE SCRIPT PRODUZ
# O PACOTE que torna o projeto VALIDO/ENTREGAVEL (nao so correto): os documentos de
# gestao e aprovacao que amarram o conjunto tecnico. Consolida, a partir do
# resultado do turnkey:
#   - INDICE DE PRANCHAS unico (numeracao por disciplina, uma tabela so).
#   - MEMORIAL DESCRITIVO consolidado do empreendimento (sumario executivo por
#     disciplina, a partir dos gates/vereditos de cada vertical).
#   - LISTA DE ART/RRT por disciplina (instrumento CREA/CAU - dados do responsavel
#     tecnico sao A CONFIRMAR; o modulo estrutura, nao inventa nomes/numeros).
#   - CHECKLIST PPCI/AVCB (o PROCESSO de aprovacao no Corpo de Bombeiros - distinto
#     do dimensionamento de incendio, que os verticais ja fazem).
#   - CHECKLIST LOD do BIM (nivel de desenvolvimento por elemento na entrega).
#   - MANUAL DE USO, OPERACAO E MANUTENCAO (O&M) por sistema.
# Tudo e' estruturacao/consolidacao (texto); nao ha valor de norma inventado - as
# normas/ITs sao REFERENCIADAS. STATELESS. Saida estruturada + markdown.
# ============================================================================
"""Pacote legal/gestao: indice de pranchas, memorial consolidado, lista de ART,
checklists PPCI-AVCB e LOD-BIM, manual O&M. STATELESS. Dados do RT = A CONFIRMAR."""

from __future__ import annotations

# prefixo de prancha e titulo por disciplina
_PRANCHAS = {
    "arquitetura": ("PE-AR", ["Planta de implantacao", "Planta baixa", "Cortes e fachadas"]),
    "terraplenagem": ("PE-TP", ["Terraplenagem (corte/aterro)", "Drenagem do lote"]),
    "concreto": ("PE-CO", ["Formas e fundacoes", "Armacao pilares/vigas", "Detalhes"]),
    "aco": ("PE-ES", ["Portico e locacao", "Detalhes de ligacoes", "Cobertura/fechamento"]),
    "piso": ("PE-PI", ["Planta de juntas do piso industrial"]),
    "eletrico": ("PE-EL", ["Unifilar", "Planta de instalacao", "Infraestrutura/aterramento", "Quadros/QDC"]),
    "hidraulica": ("PE-HI", ["Agua fria", "Esgoto/ventilacao", "Pluvial"]),
    "incendio": ("PE-IN", ["Planta de prevencao (PPCI)", "Detalhes hidrantes/rotas"]),
    "climatizacao": ("PE-CL", ["Climatizacao/ventilacao"]),
    "coordenacao": ("PE-CD", ["Modelo federado / compatibilizacao"]),
}
_ORDEM_DISC = ["arquitetura", "terraplenagem", "concreto", "aco", "piso", "eletrico",
               "hidraulica", "incendio", "climatizacao", "coordenacao"]

# ART/RRT por disciplina: instrumento e conselho
_ART = {
    "arquitetura": ("RRT", "CAU", "Projeto arquitetonico"),
    "terraplenagem": ("ART", "CREA", "Terraplenagem e drenagem"),
    "concreto": ("ART", "CREA", "Projeto estrutural (concreto)"),
    "aco": ("ART", "CREA", "Projeto estrutural (metalica)"),
    "piso": ("ART", "CREA", "Piso industrial"),
    "eletrico": ("ART", "CREA", "Projeto eletrico"),
    "hidraulica": ("ART", "CREA", "Projeto hidrossanitario"),
    "incendio": ("ART", "CREA", "Projeto de prevencao e combate a incendio"),
    "climatizacao": ("ART", "CREA", "Climatizacao/AVAC"),
}


def indice_de_pranchas(disciplinas):
    """Indice unico de pranchas: numera as folhas por disciplina (PE-XX-NN).
    disciplinas: lista de chaves. Retorna lista de {codigo, disciplina, titulo}."""
    linhas = []
    for d in _ORDEM_DISC:
        if d not in disciplinas or d not in _PRANCHAS:
            continue
        pref, titulos = _PRANCHAS[d]
        for i, t in enumerate(titulos, start=1):
            linhas.append({"codigo": "%s-%02d" % (pref, i), "disciplina": d,
                           "titulo": t})
    return linhas


def lista_art(disciplinas):
    """Lista de ART/RRT por disciplina. Dados do responsavel tecnico (nome, numero
    do registro, numero da ART) sao A CONFIRMAR - o modulo estrutura os campos."""
    out = []
    for d in _ORDEM_DISC:
        if d not in disciplinas or d not in _ART:
            continue
        instrumento, conselho, escopo = _ART[d]
        out.append({"disciplina": d, "instrumento": instrumento, "conselho": conselho,
                    "escopo": escopo, "responsavel_tecnico": "A CONFIRMAR",
                    "registro": "A CONFIRMAR", "numero_art": "A CONFIRMAR"})
    return out


def checklist_ppci_avcb():
    """Checklist do PROCESSO PPCI/AVCB (aprovacao no Corpo de Bombeiros). Distinto do
    dimensionamento (que os verticais ja fazem). Etapas de referencia (a IT e o rito
    variam por estado - A CONFIRMAR no CBM local)."""
    return [
        "Classificar a ocupacao/uso e a area construida (define as medidas exigidas)",
        "Levantar as ITs/normas aplicaveis do CBM do estado (A CONFIRMAR)",
        "Projeto tecnico (PT/PPCI): plantas com saidas, rotas de fuga, hidrantes, "
        "extintores, sinalizacao, iluminacao de emergencia, deteccao/alarme, sprinklers",
        "Memorial de calculo das medidas (vazao/pressao de hidrantes, lotacao/saidas)",
        "ART/RRT do responsavel pelo PPCI",
        "Protocolo no CBM e atendimento de exigencias",
        "Execucao conforme aprovado + comissionamento das instalacoes",
        "Vistoria e emissao do AVCB/CLCB",
    ]


# grupo de elementos do checklist LOD -> disciplina que o ENTREGA. Grupo sem
# disciplina executada nao vai para o pacote: prometer LOD 300 de instalacoes
# eletricas num projeto que nao tem projeto eletrico e declaracao falsa num
# documento de aprovacao.
_LOD_DISCIPLINA = {
    "Estrutura (pilares/vigas/fundacoes)": ("concreto", "aco"),
    "Cobertura/fechamento": ("aco",),
    "Instalacoes eletricas": ("eletrico",),
    "Instalacoes hidrossanitarias": ("hidraulica",),
    "Incendio": ("incendio",),
    "Coordenacao/federado": None,          # sempre entra (o federado e do pacote)
}


def checklist_lod_bim(disciplinas=None):
    """Checklist de LOD (Level of Development / nivel de desenvolvimento) por grupo
    de elementos na entrega BIM. LOD como referencia (BIM Forum / ABNT 15965).
    Com ``disciplinas``, mantem so os grupos que as disciplinas EXECUTADAS
    entregam (sem elas, devolve o checklist completo, como antes)."""
    itens = [
        {"grupo": "Estrutura (pilares/vigas/fundacoes)", "lod": "LOD 350",
         "entrega": "geometria + ligacoes + armadura/marcas + material"},
        {"grupo": "Cobertura/fechamento", "lod": "LOD 300",
         "entrega": "geometria + secoes + material"},
        {"grupo": "Instalacoes eletricas", "lod": "LOD 300",
         "entrega": "eletrocalhas/quadros/luminarias/tomadas + circuitos"},
        {"grupo": "Instalacoes hidrossanitarias", "lod": "LOD 300",
         "entrega": "tubulacoes com diametro + aparelhos + reservatorios"},
        {"grupo": "Incendio", "lod": "LOD 300",
         "entrega": "hidrantes/sprinklers/rotas + sinalizacao"},
        {"grupo": "Coordenacao/federado", "lod": "LOD 350",
         "entrega": "modelo federado + relatorio de clash/compatibilizacao (BCF)"},
    ]
    if disciplinas is None:
        return itens
    tem = set(disciplinas)
    return [it for it in itens
            if _LOD_DISCIPLINA.get(it["grupo"]) is None
            or tem.intersection(_LOD_DISCIPLINA[it["grupo"]])]


def manual_oem(disciplinas):
    """Manual de Uso, Operacao e Manutencao (O&M) por sistema. Rotinas de referencia
    (periodicidade conforme fabricante/norma - A CONFIRMAR)."""
    base = {
        "concreto": ("Estrutura de concreto", "Inspecao visual de fissuras/corrosao; "
                     "reparo de cobrimento quando exposto.", "anual"),
        "aco": ("Estrutura metalica", "Inspecao de pintura/galvanizacao e de "
                "parafusos/soldas; retoque anticorrosivo.", "anual"),
        "piso": ("Piso industrial", "Reselagem de juntas; verificacao de fissuras e "
                 "desgaste; limpeza.", "semestral"),
        "eletrico": ("Instalacoes eletricas", "Reaperto de conexoes, teste de DR/DPS, "
                     "termografia de quadros; medicao de aterramento.", "anual"),
        "hidraulica": ("Instalacoes hidrossanitarias", "Limpeza de calhas/ralos e "
                       "reservatorio; verificacao de vazamentos.", "semestral"),
        "incendio": ("Seguranca contra incendio", "Recarga/teste de extintores e "
                     "hidrantes; teste de alarme e iluminacao de emergencia; "
                     "renovacao do AVCB.", "conforme IT / anual"),
        "climatizacao": ("Climatizacao", "Limpeza de filtros/serpentinas (PMOC); "
                         "verificacao de gas/fluido.", "conforme PMOC"),
        "terraplenagem": ("Drenagem do lote", "Limpeza de canaletas/valas; "
                          "verificacao de erosao/assoreamento.", "conforme estacao chuvosa"),
    }
    out = []
    for d in _ORDEM_DISC:
        if d in disciplinas and d in base:
            sistema, rotina, period = base[d]
            out.append({"disciplina": d, "sistema": sistema, "rotina": rotina,
                        "periodicidade": period})
    return out


def memorial_consolidado(R, spec=None):
    """Memorial descritivo consolidado do empreendimento a partir do resultado do
    turnkey (R = galpao_turnkey.rodar). Sumario por disciplina com o veredito."""
    geo = R.get("geometria", {})
    itens = []
    for d in R.get("executadas", []):
        disc = R["disciplinas"][d]
        atende = disc.get("ATENDE")
        veredito = "ATENDE" if atende else ("REPROVA" if atende is False else "-")
        itens.append({"disciplina": d, "veredito": veredito,
                      "reprovados": disc.get("reprovados", [])})
    return {"geometria": geo, "disciplinas": itens,
            "atende_global": R.get("ATENDE"),
            "executadas": R.get("executadas", []),
            "puladas": R.get("puladas", [])}


def gerar_pacote(disciplinas=None, R=None, spec=None):
    """Monta o pacote legal completo. disciplinas: chaves (default: as de _ART); se
    R (turnkey) for dado, usa as executadas e inclui o memorial consolidado."""
    if disciplinas is None:
        disciplinas = (R.get("executadas") if R else None) or list(_ART.keys())
    disciplinas = [d for d in _ORDEM_DISC if d in disciplinas] or list(_ART.keys())
    pac = {"indice_pranchas": indice_de_pranchas(disciplinas + ["coordenacao"]),
           "lista_art": lista_art(disciplinas),
           "checklist_ppci_avcb": checklist_ppci_avcb(),
           "checklist_lod_bim": checklist_lod_bim(disciplinas),
           "manual_oem": manual_oem(disciplinas)}
    if R is not None:
        pac["memorial_consolidado"] = memorial_consolidado(R, spec)
    return pac


def markdown(pac, titulo="PACOTE DE PROJETO - DOCUMENTOS DE GESTAO E APROVACAO"):
    """Renderiza o pacote legal em markdown."""
    L = ["# %s" % titulo, ""]
    if "memorial_consolidado" in pac:
        m = pac["memorial_consolidado"]
        L.append("## Memorial descritivo consolidado")
        g = m["geometria"]
        if g:
            L.append("- Geometria: %s" % ", ".join("%s=%s" % (k, v) for k, v in g.items()))
        for it in m["disciplinas"]:
            L.append("- %s: **%s**" % (it["disciplina"], it["veredito"]))
        L.append("- **Veredito global:** %s" % ("ATENDE" if m["atende_global"] else "verificar"))
        L.append("")
    L.append("## Indice de pranchas")
    for p in pac["indice_pranchas"]:
        L.append("- %s - %s (%s)" % (p["codigo"], p["titulo"], p["disciplina"]))
    L.append("")
    L.append("## Lista de ART/RRT")
    for a in pac["lista_art"]:
        L.append("- %s (%s) - %s | RT: %s" % (a["instrumento"], a["conselho"],
                                              a["escopo"], a["responsavel_tecnico"]))
    L.append("")
    L.append("## Checklist PPCI/AVCB")
    for i, s in enumerate(pac["checklist_ppci_avcb"], 1):
        L.append("%d. %s" % (i, s))
    L.append("")
    L.append("## Checklist LOD (BIM)")
    for c in pac["checklist_lod_bim"]:
        L.append("- %s: **%s** - %s" % (c["grupo"], c["lod"], c["entrega"]))
    L.append("")
    L.append("## Manual de O&M")
    for o in pac["manual_oem"]:
        L.append("- %s (%s): %s" % (o["sistema"], o["periodicidade"], o["rotina"]))
    return "\n".join(L)


# ----------------------------------- selftest --------------------------------
def _selftest():
    todas = list(_ART.keys())
    pac = gerar_pacote(todas)
    # indice de pranchas: codigos unicos e no formato PE-XX-NN
    cods = [p["codigo"] for p in pac["indice_pranchas"]]
    assert len(cods) == len(set(cods))
    assert all(c.startswith("PE-") and c[-2:].isdigit() for c in cods)
    # coordenacao entra no indice mesmo sem estar nas disciplinas de ART
    assert any(p["disciplina"] == "coordenacao" for p in pac["indice_pranchas"])

    # lista ART: RT/registro/numero = A CONFIRMAR (nao inventa)
    for a in pac["lista_art"]:
        assert a["responsavel_tecnico"] == "A CONFIRMAR"
        assert a["numero_art"] == "A CONFIRMAR"
    # arquitetura usa RRT/CAU; engenharia usa ART/CREA
    arq = [a for a in lista_art(["arquitetura"])][0]
    assert arq["instrumento"] == "RRT" and arq["conselho"] == "CAU"
    eng = [a for a in lista_art(["concreto"])][0]
    assert eng["instrumento"] == "ART" and eng["conselho"] == "CREA"

    # checklists nao vazios
    assert len(pac["checklist_ppci_avcb"]) >= 5
    assert any("AVCB" in s for s in pac["checklist_ppci_avcb"])
    assert all("lod" in c and c["lod"].startswith("LOD") for c in pac["checklist_lod_bim"])
    assert pac["manual_oem"]

    # com R do turnkey: memorial consolidado
    R = {"geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
         "executadas": ["concreto", "eletrico"], "puladas": [],
         "disciplinas": {"concreto": {"ATENDE": True, "reprovados": []},
                         "eletrico": {"ATENDE": False, "reprovados": ["curto"]}},
         "ATENDE": False}
    pac2 = gerar_pacote(R=R)
    m = pac2["memorial_consolidado"]
    assert m["atende_global"] is False
    vered = {it["disciplina"]: it["veredito"] for it in m["disciplinas"]}
    assert vered["concreto"] == "ATENDE" and vered["eletrico"] == "REPROVA"

    # markdown tem as secoes
    md = markdown(pac2)
    for sec in ("Indice de pranchas", "Lista de ART", "Checklist PPCI/AVCB",
                "Checklist LOD", "Manual de O&M", "Memorial descritivo"):
        assert sec in md, sec
    return True


if __name__ == "__main__":
    _selftest()
    print(markdown(gerar_pacote(["concreto", "aco", "eletrico", "incendio"]))[:1400])
    print("...\nselftest OK")
