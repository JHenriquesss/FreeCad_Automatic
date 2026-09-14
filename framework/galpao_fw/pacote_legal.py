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

from edicao_nbr6118_g123 import (
    carimbo_composicao as _composicao_ed_g123,
    edicao_de_spec as _edicao_de_spec_g123,
    rotulo_edicao as _rotulo_ed_g123,
)

try:
    import exigencias_nao_verificadas_g130 as _exig_g130
except ImportError:  # uso isolado fora do pacote
    _exig_g130 = None

# prefixo de prancha e titulo por disciplina
_PRANCHAS = {
    "arquitetura": ("PE-AR", ["Planta de implantacao", "Planta baixa", "Cortes e fachadas"]),
    "terraplenagem": ("PE-TP", ["Terraplenagem (corte/aterro)", "Drenagem do lote"]),
    "concreto": ("PE-CO", ["Formas e fundacoes", "Armacao pilares/vigas", "Detalhes",
                         # G80: a fundacao dimensionada por pilar vira folha -
                         # locacao/formas com dimensoes, cota e carga por
                         # elemento. Sem esta entrada a prancha evaporaria no
                         # `continue` do indice (o mesmo D89 da fundacao no G56
                         # e da alvenaria no G62).
                         "Locacao e formas da fundacao"]),
    # G62: a parede calculada vira folha - elevacao com fiadas/vaos/quadro +
    # plantas de 1a/2a fiada. Sem esta entrada as folhas evaporariam no
    # `continue` do indice (o mesmo D89 da fundacao no G56).
    "alvenaria_estrutural": ("PE-AL", ["Elevacao das paredes portantes",
                                       "Plantas de 1a e 2a fiadas"]),
    # G66: a tesoura calculada vira folha - elevacao com quadro de pecas.
    # Sem esta entrada a prancha telhado-tesoura.svg evaporaria no `continue`
    # do indice (o mesmo D89 da fundacao no G56).
    "madeira": ("PE-MD", ["Tesoura de madeira (NBR 7190-1)"]),
    "aco": ("PE-ES", ["Portico e locacao", "Detalhes de ligacoes", "Cobertura/fechamento"]),
    "piso": ("PE-PI", ["Planta de juntas do piso industrial"]),
    "eletrico": ("PE-EL", ["Unifilar", "Planta de instalacao", "Infraestrutura/aterramento", "Quadros/QDC"]),
    "hidraulica": ("PE-HI", ["Agua fria", "Esgoto/ventilacao", "Pluvial"]),
    "incendio": ("PE-IN", ["Planta de prevencao (PPCI)", "Detalhes hidrantes/rotas",
                          # G81: a escada calculada vira folha - planta e corte
                          # com espelho/piso, Blondel, largura exigida x
                          # adotada e tipo Tab.11. Sem esta entrada a prancha
                          # evaporaria no `continue` do indice (o mesmo D89 da
                          # fundacao no G56 e da alvenaria no G62).
                          "Escada de emergencia (planta e corte)"]),
    "climatizacao": ("PE-CL", ["Climatizacao/ventilacao"]),
    "coordenacao": ("PE-CD", ["Modelo federado / compatibilizacao"]),
}
_ORDEM_DISC = ["arquitetura", "terraplenagem", "concreto", "alvenaria_estrutural",
               "madeira", "aco", "piso", "eletrico",
               "hidraulica", "incendio", "climatizacao", "coordenacao"]

# ART/RRT por disciplina: instrumento e conselho
_ART = {
    "arquitetura": ("RRT", "CAU", "Projeto arquitetonico"),
    "terraplenagem": ("ART", "CREA", "Terraplenagem e drenagem"),
    "concreto": ("ART", "CREA", "Projeto estrutural (concreto)"),
    # G62: a parede portante tem responsabilidade propria (NBR 16868).
    "alvenaria_estrutural": ("ART", "CREA", "Projeto de alvenaria estrutural"),
    # G66: a tesoura de madeira tambem (NBR 7190).
    "madeira": ("ART", "CREA", "Projeto estrutural (madeira)"),
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


def checklist_ppci_avcb(pendencias=None):
    """Checklist do PROCESSO PPCI/AVCB (aprovacao no Corpo de Bombeiros). Distinto do
    dimensionamento (que os verticais ja fazem). Etapas de referencia (a IT e o rito
    variam por estado - A CONFIRMAR no CBM local).

    G57 (o portao): `pendencias` e' a lista de itens do escopo que seguem
    `not_available` e travam a aprovacao (ex. SPDA nao avaliado, alimentacao de
    emergencia nao dimensionada). Cada uma vira um item PENDENTE no fim do
    checklist - o pacote nunca afirma completude sobre o buraco. Sem
    pendencias, a saida e' identica a de antes."""
    base = [
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
    for pend in (pendencias or []):
        base.append("PENDENTE - %s" % pend)
    return base


# grupo de elementos do checklist LOD -> disciplina que o ENTREGA. Grupo sem
# disciplina executada nao vai para o pacote: prometer LOD 300 de instalacoes
# eletricas num projeto que nao tem projeto eletrico e declaracao falsa num
# documento de aprovacao.
_LOD_DISCIPLINA = {
    "Estrutura (pilares/vigas/fundacoes)": ("concreto", "aco"),
    # G62: paredes portantes com fiadas, vergas e quadro de blocos.
    "Alvenaria estrutural (paredes portantes)": ("alvenaria_estrutural",),
    # G66: a tesoura da casa entrega geometria + secoes + material (o grupo
    # era so do aco do galpao; a casa metalica segue sem madeira).
    "Cobertura/fechamento": ("aco", "madeira"),
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
        {"grupo": "Alvenaria estrutural (paredes portantes)", "lod": "LOD 350",
         "entrega": "paredes + fiadas + vergas + quadro de blocos + material"},
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
        # G62: parede portante (NBR 16868-2: prumo, fissuras, graute).
        "alvenaria_estrutural": ("Alvenaria estrutural", "Inspecao de prumo, "
                                 "fissuras e eflorescencia; rejunte e reparo de "
                                 "revestimento onde indicado.", "anual"),
        # G66: tesoura e telha (fixacao, preservativo, telhas soltas).
        "madeira": ("Estrutura de madeira do telhado", "Inspecao de pecas, "
                    "ligacoes e fixacao das telhas; tratamento preservativo "
                    "onde indicado.", "anual"),
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


def gerar_pacote(disciplinas=None, R=None, spec=None, memorial=None,
                 pendencias=None, edicao=None, tipologia=None,
                 cimento_calculado=None, protensao_calculada=None):
    """Monta o pacote legal completo. disciplinas: chaves (default: as de _ART); se
    R (turnkey) for dado, usa as executadas e inclui o memorial consolidado.

    `memorial`: memorial JA consolidado, para as tipologias que nao passam por
    `galpao_turnkey` (o edificio multipavimento monta o seu em
    `gestao_edificio.memorial`). Ter as duas portas evita que um segundo
    orquestrador tenha de se disfarcar de resultado de turnkey so para
    atravessar esta funcao.

    `pendencias` (G57): itens de escopo `not_available` que travam a aprovacao;
    vao para o checklist PPCI/AVCB como PENDENTE (o portao do G57).

    G123 (chave DESLIGADA): `edicao` = '2014' ou '2023+Em1'; ausente = a
    edicao declarada no `spec` (norma_6118_edicao) ou, sem ela, o
    comportamento de hoje (2014) declarado na folha (sem default silencioso).
    O carimbo mora na fonte unica edicao_nbr6118_g123.

    G126: o cimento do fckj sai da chave "cimento" do `spec`; ausente = piso
    conservador declarado (nunca CPV); invalido levanta. A linha mora na
    fonte unica cimento_nbr6118_g126.

    G133: a protensao (fck da viga protendida e fckj da transferencia) sai
    do que o CALCULO usou (`protensao_calculada`, do resultado); sem ela, o
    spec (ausente = fck do projeto / fckj = fck, com a ausencia dita) ou
    "sem viga protendida" para casa/predio. Declarado x usado divergentes
    LEVANTA. A linha mora na fonte unica protensao_fck_g133.

    G130: `tipologia` = 'casa'/'predio'/'galpao' ("edificio" e alias de
    "predio"); ausente = a uniao das tres (o pacote nunca esconde divida
    por falta de rotulo). Cada divida de ORFAS_TRIADAS aplicavel a
    tipologia sai em exigencias_nao_verificadas (fonte unica
    exigencias_nao_verificadas_g130, que le ORFAS ao vivo). Invalida
    levanta; divida nova sem triagem aparece em sem_triagem (vermelho por
    injecao). Nao implementa verificacao nenhuma."""
    if tipologia is not None and _exig_g130 is not None:
        _tip_canon = _exig_g130.normaliza_tipologia(tipologia)
    elif tipologia is not None:
        _tip_canon = str(tipologia).strip().lower()
    else:
        _tip_canon = None
    if disciplinas is None:
        disciplinas = (R.get("executadas") if R else None) or list(_ART.keys())
    disciplinas = [d for d in _ORDEM_DISC if d in disciplinas] or list(_ART.keys())
    # Resolve a edicao: parametro explicito vence; senao o spec; senao hoje.
    # G135: fonte unica, sem copia literal do carimbo aqui.
    from edicao_nbr6118_g123 import normaliza_edicao as _norm_ed
    _ed_resolvida = None
    if edicao is not None:
        _ed_resolvida = _norm_ed(edicao)
    elif isinstance(spec, dict):
        try:
            _ed_resolvida = _edicao_de_spec_g123(spec)
        except ValueError:
            raise
    pac = {"indice_pranchas": indice_de_pranchas(disciplinas + ["coordenacao"]),
           "lista_art": lista_art(disciplinas),
           "checklist_ppci_avcb": checklist_ppci_avcb(pendencias),
           "checklist_lod_bim": checklist_lod_bim(disciplinas),
           "manual_oem": manual_oem(disciplinas)}
    pac["edicao_6118"] = _ed_resolvida
    # G132: o carimbo do projeto diz a composicao (quais itens seguem a
    # 2023+Em1, o resto pela 2014); `edicao_6118` segue sendo a edicao
    # declarada no projeto (metadado, nao conta de peca).
    pac["carimbo_edicao_6118"] = _composicao_ed_g123(_ed_resolvida)
    # G126/G131: o cimento que o pacote declara e o que o CALCULO usou
    # (`cimento_calculado`, do resultado); sem ele, casa/predio declaram que
    # nao ha icamento calculado e o resto le o spec (ausente = piso dito).
    # Declarado no spec x usado na conta divergentes LEVANTA (fonte unica,
    # sem copia literal da linha aqui).
    from cimento_nbr6118_g126 import cimento_da_entrega as _cim_ent_pl
    from cimento_nbr6118_g126 import linha_cimento as _lin_cim_pl
    _cim_res = _cim_ent_pl(cimento_calculado, spec, _tip_canon)
    _cim_linha = _lin_cim_pl(_cim_res)
    pac["cimento"] = _cim_res
    pac["linha_cimento"] = _cim_linha
    # G133: a protensao que o pacote declara e a que o CALCULO usou
    # (`protensao_calculada`, do resultado); sem ela, casa/predio declaram
    # que nao ha viga protendida e o resto le o spec (ausente = piso dito).
    # Declarado no spec x usado na conta divergentes LEVANTA (fonte unica,
    # sem copia literal da linha aqui).
    from protensao_fck_g133 import protensao_da_entrega as _prot_ent_pl
    from protensao_fck_g133 import linha_protensao as _lin_prot_pl
    _prot_res = _prot_ent_pl(protensao_calculada, spec, _tip_canon)
    _prot_linha = _lin_prot_pl(_prot_res)
    pac["protensao"] = _prot_res
    pac["linha_protensao"] = _prot_linha
    # G130: as dividas aplicaveis a tipologia saem no pacote como exigencia
    # nao verificada (fonte unica; sem tipologia = a uniao; invalida levanta
    # acima; divida nova sem triagem viaja em sem_triagem).
    if _exig_g130 is not None:
        pac["tipologia_exigencias"] = _tip_canon
        pac["exigencias_nao_verificadas"] = \
            _exig_g130.exigencias_para_tipologia(_tip_canon)
    else:
        pac["tipologia_exigencias"] = _tip_canon
        pac["exigencias_nao_verificadas"] = []
    if pendencias:
        pac["pendencias_aprovacao"] = list(pendencias)
    if R is not None:
        pac["memorial_consolidado"] = memorial_consolidado(R, spec)
    elif memorial is not None:
        pac["memorial_consolidado"] = memorial
    return pac


# CORRESPONDENCIA_NUMERACAO_GALPAO (G112): a razao escrita e a tabela que o
# cliente do galpao recebe no pacote-legal.md - que folha do executivo
# (numeracao por arquivo de producao) responde por que codigo(s) do indice
# (numeracao por disciplina). FONTE UNICA: entregaveis_projeto a passa ao
# markdown e a lente varredura_carimbo_mapa (G112) a importa daqui. Mora
# neste modulo porque ele nao importa nada - a lente e script avulso e
# importar entregaveis_projeto direto dispara o ciclo project_loop ->
# adaptadores -> entregaveis_projeto. Cada entrada: {arquivo, carimbo,
# cobre ([] = sem codigo proprio no indice), motivo}.
CORRESPONDENCIA_NUMERACAO_GALPAO = {
    "intro": (
        "O executivo numera as folhas por arquivo de producao "
        "(PE-HID/PE-INC/PE-CLI para esquema+quadro; PE-01..PE-16 na "
        "sequencia do aco; PE-01..PE-03 na sequencia do concreto; PE-COORD "
        "na coordenacao) enquanto o indice numera por disciplina "
        "(PE-HI/PE-IN/PE-CL/PE-ES/PE-CO/PE-EL/PE-CD). As numeracoes diferem "
        "porque (a) um arquivo de esquema cobre N codigos do indice "
        "(HID01_ESQUEMA.pdf cobre PE-HI-01/02/03; INC01_PLANTA.pdf cobre "
        "PE-IN-01 enquanto PE-IN-02/03 nao tem emissor ligado); (b) as "
        "folhas de quadro (HID02_QUADRO.pdf com PE-HID-02, INC02_RESUMO.pdf, "
        "CLI02_QUADRO.pdf, COORD02_CLASH.pdf com PE-COORD-02) nao tem codigo "
        "proprio no indice - PE-HID-02 colide em numero com PE-HI-02 "
        "\"Esgoto/ventilacao\" mas e outra folha; (c) o aco emite 17 folhas "
        "contra 3 codigos PE-ES e o carimbo PE-01 esta em dois arquivos "
        "distintos (PE01_FORMAS.pdf do concreto e PE01_COBERTURA.pdf do "
        "aco); (d) a coordenacao emite 2 folhas contra 1 codigo PE-CD. "
        "Carimbar um unico codigo do indice nessas folhas afirmaria uma "
        "cobertura que a folha nao tem (convencao 6: a folha diz o que "
        "desenha) - por isso a numeracao propria permanece, e a tabela "
        "abaixo diz ao cliente que folha do executivo responde por que "
        "codigo(s) do indice."
    ),
    "entradas": [
        {"arquivo": "CLI01_ESQUEMA.pdf", "carimbo": "PE-CLI-01",
         "cobre": ["PE-CL-01"],
         "motivo": "folha de esquema da climatizacao (carimbo PE-CLI-01) "
                   "responde pelo unico codigo do indice PE-CL-01 "
                   "Climatizacao/ventilacao; o prefixo difere (CLI vs CL) "
                   "mas a cobertura e 1:1 e esta escrita aqui"},
        {"arquivo": "COORD01_PLANTA.pdf", "carimbo": "PE-COORD-01",
         "cobre": ["PE-CD-01"],
         "motivo": "planta de coordenacao (carimbo PE-COORD-01) responde "
                   "pelo unico codigo do indice PE-CD-01 Modelo federado / "
                   "compatibilizacao; o prefixo difere (COORD vs CD) mas a "
                   "cobertura e 1:1 e esta escrita aqui"},
        {"arquivo": "HID01_ESQUEMA.pdf", "carimbo": "PE-HID-01",
         "cobre": ["PE-HI-01", "PE-HI-02", "PE-HI-03"],
         "motivo": "um esquema cobre as 3 redes do indice (contrato G82: "
                   "PE-HI-01 Agua fria, PE-HI-02 Esgoto/ventilacao, PE-HI-03 "
                   "Pluvial); carimbar um so codigo afirmaria cobertura "
                   "parcial"},
        {"arquivo": "INC01_PLANTA.pdf", "carimbo": "PE-INC-01",
         "cobre": ["PE-IN-01"],
         "motivo": "planta de prevencao (carimbo PE-INC-01) responde por "
                   "PE-IN-01 Planta de prevencao (PPCI); PE-IN-02/03 nao tem "
                   "emissor ligado ao hook do galpao (motivos no laco G93)"},
        {"arquivo": "PE01_COBERTURA.pdf", "carimbo": "PE-01",
         "cobre": ["PE-ES-03"],
         "motivo": "folha de cobertura/fechamento do aco (carimbo PE-01, "
                   "primeiro na ordem de producao do executivo) responde por "
                   "PE-ES-03 Cobertura/fechamento; PE-01 aqui e cobertura, em "
                   "PE01_FORMAS.pdf e formas - o numero so casa com o arquivo"},
        {"arquivo": "PE01_FORMAS.pdf", "carimbo": "PE-01",
         "cobre": ["PE-CO-01"],
         "motivo": "planta de formas do concreto (carimbo PE-01, primeira da "
                   "sequencia do concreto) responde por PE-CO-01 Formas e "
                   "fundacoes; PE-01 aqui e formas, em PE01_COBERTURA.pdf e "
                   "cobertura - o numero so casa com o arquivo"},
        {"arquivo": "PE02_PORTICO.pdf", "carimbo": "PE-02",
         "cobre": ["PE-CO-02"],
         "motivo": "portico tipico do concreto (carimbo PE-02) responde por "
                   "PE-CO-02 Armacao pilares/vigas; numeracao da sequencia do "
                   "concreto, nao do indice"},
        {"arquivo": "PE03_QUADROS.pdf", "carimbo": "PE-03",
         "cobre": ["PE-CO-03"],
         "motivo": "quadros do concreto (carimbo PE-03) respondem por "
                   "PE-CO-03 Detalhes; numeracao da sequencia do concreto, "
                   "nao do indice"},
        {"arquivo": "PE04_PORTICO.pdf", "carimbo": "PE-04",
         "cobre": ["PE-ES-01"],
         "motivo": "portico tipico do aco (carimbo PE-04, quarto na ordem de "
                   "producao do executivo) responde por PE-ES-01 Portico e "
                   "locacao"},
        {"arquivo": "PE07_DET_JOELHO.pdf", "carimbo": "PE-07",
         "cobre": ["PE-ES-02"],
         "motivo": "detalhe da ligacao joelho do aco (carimbo PE-07, setimo "
                   "na ordem de producao do executivo) responde por PE-ES-02 "
                   "Detalhes de ligacoes"},
        {"arquivo": "HID02_QUADRO.pdf", "carimbo": "PE-HID-02",
         "cobre": [],
         "motivo": "quadro de dimensionamento da hidraulica (carimbo "
                   "PE-HID-02) nao tem codigo proprio no indice; PE-HID-02 "
                   "colide em numero com PE-HI-02 Esgoto/ventilacao mas e "
                   "outra folha - mesmo numero, folhas diferentes"},
        {"arquivo": "INC02_RESUMO.pdf", "carimbo": "PE-INC-02",
         "cobre": [],
         "motivo": "quadro-resumo de incendio (carimbo PE-INC-02) nao tem "
                   "codigo proprio no indice (PE-IN-02 Detalhes "
                   "hidrantes/rotas nao tem emissor ligado)"},
        {"arquivo": "CLI02_QUADRO.pdf", "carimbo": "PE-CLI-02",
         "cobre": [],
         "motivo": "quadro de capacidade da climatizacao (carimbo PE-CLI-02) "
                   "nao tem codigo proprio no indice (PE-CL-01 ja respondido "
                   "por CLI01_ESQUEMA.pdf)"},
        {"arquivo": "COORD02_CLASH.pdf", "carimbo": "PE-COORD-02",
         "cobre": [],
         "motivo": "quadro de clash da coordenacao (carimbo PE-COORD-02) nao "
                   "tem codigo proprio no indice (PE-CD-01 ja respondido por "
                   "COORD01_PLANTA.pdf)"},
        {"arquivo": "PE02_FUNDACOES.pdf", "carimbo": "PE-02",
         "cobre": [],
         "motivo": "planta de fundacoes do aco (carimbo PE-02) fora do "
                   "recorte de 3 representantes do mapa do galpao; numeracao "
                   "de producao, sem codigo do indice"},
        {"arquivo": "PE03_ELEVACOES.pdf", "carimbo": "PE-03",
         "cobre": [],
         "motivo": "elevacoes do aco (carimbo PE-03) fora do recorte de 3 "
                   "representantes do mapa do galpao; numeracao de producao, "
                   "sem codigo do indice"},
        {"arquivo": "PE05_CONTRAVENTAMENTO.pdf", "carimbo": "PE-05",
         "cobre": [],
         "motivo": "contraventamentos do aco (carimbo PE-05) fora do recorte "
                   "de 3 representantes do mapa do galpao; numeracao de "
                   "producao, sem codigo do indice"},
        {"arquivo": "PE06_DET_BASE.pdf", "carimbo": "PE-06",
         "cobre": [],
         "motivo": "detalhe de base de coluna do aco (carimbo PE-06) fora do "
                   "recorte de 3 representantes do mapa do galpao; numeracao "
                   "de producao, sem codigo do indice"},
        {"arquivo": "PE08_FECHAMENTO.pdf", "carimbo": "PE-08",
         "cobre": [],
         "motivo": "fechamento/tercas/mao-francesa do aco (carimbo PE-08) "
                   "fora do recorte de 3 representantes do mapa do galpao; "
                   "numeracao de producao, sem codigo do indice"},
        {"arquivo": "PE09_QUADROS.pdf", "carimbo": "PE-09",
         "cobre": [],
         "motivo": "quadros e notas do aco (carimbo PE-09) fora do recorte "
                   "de 3 representantes do mapa do galpao; numeracao de "
                   "producao, sem codigo do indice"},
        {"arquivo": "PE14_CROQUIS.pdf", "carimbo": "PE-14",
         "cobre": [],
         "motivo": "croquis de fabricacao do aco (carimbo PE-14) fora do "
                   "recorte de 3 representantes do mapa do galpao; numeracao "
                   "de producao, sem codigo do indice"},
        {"arquivo": "PE16_MONTAGEM.pdf", "carimbo": "PE-16",
         "cobre": [],
         "motivo": "plano de montagem do aco (carimbo PE-16) fora do recorte "
                   "de 3 representantes do mapa do galpao; numeracao de "
                   "producao, sem codigo do indice"},
    ],
}


def markdown(pac, titulo="PACOTE DE PROJETO - DOCUMENTOS DE GESTAO E APROVACAO",
              emitidas=None, correspondencia=None):
    """Renderiza o pacote legal em markdown.

    `emitidas`: pranchas efetivamente desenhadas nesta rodada (quando dado e
    menor que o indice, o .md avisa - o indice e o escopo do executivo, nao o
    conteudo da pasta. Sem isso o .md lista 13 folhas ao lado de 3 arquivos e
    passa por completo (G52 achado 1 / G14).

    `correspondencia` (G112): {"intro": texto, "entradas": [{arquivo,
    carimbo, cobre, motivo}]} com a tabela de numeracao propria que o
    cliente recebe (galpao: numeracao por arquivo de producao vs indice por
    disciplina). Quando None (default, casa/predio e chamadas antigas), a
    saida e byte-identica a de antes - nenhuma secao nova, EXCETO as secoes
    G123 (edicao da NBR 6118), G126 (cimento do fckj) e G130 (exigencias
    nao verificadas), que sao declaracao obrigatoria e saem sempre (a
    ausencia reprova no portao)."""
    L = ["# %s" % titulo, ""]
    # G123/G135: declaracao obrigatoria da edicao de calculo (fonte unica;
    # sem o parametro, o comportamento e o de hoje - 2014 - e a folha diz
    # qual e; sem copia literal aqui).
    # G132: o carimbo do projeto diz a composicao (fonte unica).
    _carimbo_txt = pac.get("carimbo_edicao_6118")
    if not _carimbo_txt:
        _carimbo_txt = _composicao_ed_g123(pac.get("edicao_6118"))
    L.append("## Norma de calculo do concreto (G123)")
    L.append("")
    L.append(str(_carimbo_txt))
    L.append("")
    # G126: declaracao obrigatoria do cimento do fckj (fonte unica; sem o
    # cimento, o piso conservador, com a ausencia dita).
    _cim_txt = pac.get("linha_cimento")
    if not _cim_txt:
        # G131: pacote montado fora de gerar_pacote declara pela fonte unica
        # (sem copia literal da linha aqui).
        from cimento_nbr6118_g126 import linha_cimento as _lin_cim_md
        _cim_txt = _lin_cim_md(pac.get("cimento"))
    L.append("## Cimento do concreto (G126)")
    L.append("")
    L.append(str(_cim_txt))
    L.append("")
    # G133: declaracao obrigatoria do fck da protendida e do fckj (fonte
    # unica; sem declaracao, o fck do projeto / fckj = fck, com a ausencia
    # dita; sem viga protendida, o terceiro valor declarado).
    _prot_txt = pac.get("linha_protensao")
    if not _prot_txt:
        # pacote montado fora de gerar_pacote declara pela fonte unica
        # (sem copia literal da linha aqui).
        from protensao_fck_g133 import linha_protensao as _lin_prot_md
        _prot_txt = _lin_prot_md(pac.get("protensao"))
    L.append("## Protensao da viga (G133)")
    L.append("")
    L.append(str(_prot_txt))
    L.append("")
    if "memorial_consolidado" in pac:
        m = pac["memorial_consolidado"]
        L.append("## Memorial descritivo consolidado")
        g = m["geometria"]
        if g:
            L.append("- Geometria: %s" % ", ".join("%s=%s" % (k, v) for k, v in g.items()))
        for it in m["disciplinas"]:
            L.append("- %s: **%s**" % (it["disciplina"], it["veredito"]))
            # G66: o memorial da casa detalha o telhado (tesouras, vao,
            # volume, reacao); sem detalhe a linha sai como antes.
            if it.get("detalhe"):
                L.append("  - %s" % it["detalhe"])
        L.append("- **Veredito global:** %s" % ("ATENDE" if m["atende_global"] else "verificar"))
        L.append("")
    L.append("## Indice de pranchas")
    for p in pac["indice_pranchas"]:
        L.append("- %s - %s (%s)" % (p["codigo"], p["titulo"], p["disciplina"]))
    if emitidas is not None and emitidas < len(pac["indice_pranchas"]):
        L.append("")
        L.append("> AVISO: o indice lista %d prancha(s) do projeto executivo e "
                 "esta rodada emitiu %d: as demais ainda tem de ser desenhadas "
                 "(o indice e' o escopo do executivo, nao o conteudo da pasta "
                 "desta rodada)."
                 % (len(pac["indice_pranchas"]), emitidas))
    L.append("")
    L.append("## Lista de ART/RRT")
    for a in pac["lista_art"]:
        L.append("- %s (%s) - %s | RT: %s" % (a["instrumento"], a["conselho"],
                                              a["escopo"], a["responsavel_tecnico"]))
    L.append("")
    L.append("## Checklist PPCI/AVCB")
    for i, s in enumerate(pac["checklist_ppci_avcb"], 1):
        L.append("%d. %s" % (i, s))
    if pac.get("pendencias_aprovacao"):
        L.append("")
        L.append("> AVISO: %d pendencia(s) de escopo travam a aprovacao e estao "
                 "marcadas PENDENTE acima - o pacote nao afirma completude "
                 "sobre elas." % len(pac["pendencias_aprovacao"]))
    L.append("")
    L.append("## Checklist LOD (BIM)")
    for c in pac["checklist_lod_bim"]:
        L.append("- %s: **%s** - %s" % (c["grupo"], c["lod"], c["entrega"]))
    L.append("")
    L.append("## Manual de O&M")
    for o in pac["manual_oem"]:
        L.append("- %s (%s): %s" % (o["sistema"], o["periodicidade"], o["rotina"]))
    # G130: declaracao obrigatoria das exigencias nao verificadas (fonte
    # unica; sem tipologia = a uniao; a ausencia reprova no portao).
    L.append("")
    if _exig_g130 is not None:
        _tip_sec = pac.get("tipologia_exigencias")
        try:
            _sec130 = _exig_g130.markdown_secao(_tip_sec)
        except ValueError:
            raise
        # markdown_secao ja traz o titulo; carimba as linhas da fonte unica.
        # Quando o pacote foi montado sem a fonte (uso isolado), cai no
        # ramo abaixo com as exigencias que viajaram no dict.
        L.append(_sec130)
    else:
        L.append("## %s" % ("Exigências não verificadas pelo framework (G130)"))
        L.append("")
        for it in pac.get("exigencias_nao_verificadas") or []:
            L.append("- %s (%s): %s — %s [não verificada pelo framework]"
                     % (it.get("nome"), it.get("arquivo"), it.get("motivo"),
                        it.get("endereco")))
    if correspondencia is not None:
        L.append("")
        L.append("## Correspondencia de numeracao do executivo (G112)")
        L.append("")
        intro = (correspondencia.get("intro") if isinstance(correspondencia, dict)
                 else None)
        entradas = (correspondencia.get("entradas") if isinstance(correspondencia, dict)
                    else correspondencia)
        if intro:
            L.append(str(intro))
            L.append("")
        for e in entradas or []:
            carimbo = e.get("carimbo") or "(sem carimbo extraivel)"
            cobre = list(e.get("cobre") or [])
            cobertura = (", ".join(cobre) if cobre
                         else "(sem codigo proprio no indice)")
            L.append("- %s — carimbo %s — cobre %s — %s"
                     % (e.get("arquivo"), carimbo, cobertura, e.get("motivo")))
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
