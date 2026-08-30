# ============================================================================
# caderno_encargos.py - O QUE ESTE SCRIPT PRODUZ
# CADERNO DE ENCARGOS / ESPECIFICACOES TECNICAS de materiais e servicos por
# disciplina - o documento contratual que diz COMO executar e COMO aceitar cada
# servico (o calculo diz "o que"; o caderno diz "como/criterio"). Cada item traz:
#   - especificacao do MATERIAL (o que comprar/atender),
#   - EXECUCAO (como fazer),
#   - CONTROLE/ACEITACAO (como medir/aceitar),
#   - NORMAS de referencia (apenas os NUMEROS das ABNT/procedimentos - referencia,
#     nao valores tabelados; o modulo nao inventa criterios numericos de norma:
#     onde ha limite numerico, remete a norma).
# STATELESS: gerar_caderno(disciplinas) monta o documento a partir da biblioteca de
# clausulas. Saida em markdown/texto. Base normativa = as mesmas ABNT ja usadas
# pelos verticais de calculo do projeto.
# ============================================================================
"""Caderno de encargos / especificacoes tecnicas por disciplina (material +
execucao + controle + normas). STATELESS: gerar_caderno(disciplinas) -> markdown."""

from __future__ import annotations

# Biblioteca de clausulas por disciplina. Cada clausula: (titulo, material, execucao,
# controle, [normas]). NORMAS = referencias ABNT (numeros), nao valores inventados.
_CLAUSULAS = {
    "fundacao": [
        ("Concreto das fundacoes",
         "Concreto usinado fck conforme projeto (>= C25 em contato com solo), "
         "abatimento e agregados conforme dosagem; cimento resistente a sulfatos "
         "quando o laudo indicar agressividade do solo.",
         "Lancamento com concreto fresco, adensamento por vibrador de imersao, "
         "cura umida minima conforme norma; forma limpa e escorada; armadura com "
         "cobrimento e espacadores garantindo o cobrimento nominal de projeto.",
         "Controle tecnologico por lote (moldagem de corpos de prova, rompimento a "
         "7 e 28 dias); verificacao de cota de apoio contra o relatorio geotecnico; "
         "recebimento da cota/sondagem antes da concretagem.",
         ["NBR 6118", "NBR 6122", "NBR 12655", "NBR 5738/5739"]),
        ("Estacas (quando fundacao profunda)",
         "Estaca conforme tipo de projeto (pre-moldada/hélice/escavada), secao e "
         "comprimento definidos pela sondagem SPT.",
         "Cravacao/escavacao com controle de nega/energia (cravadas) ou de "
         "verticalidade e concretagem continua (escavadas); registro por estaca.",
         "Controle de nega e repique (cravadas); prova de carga quando exigida pela "
         "NBR 6122 (FS conforme haja ou nao prova de carga).",
         ["NBR 6122", "NBR 6118"]),
    ],
    "concreto": [
        ("Estrutura de concreto (pilares/vigas pre-moldados ou moldados in loco)",
         "Concreto fck de projeto; aco CA-50/CA-60 conforme detalhamento; classe de "
         "agressividade ambiental definindo cobrimento e relacao a/c.",
         "Formas, armacao e concretagem conforme projeto; para pre-moldados, "
         "controle de icamento/idade de saque; ligacoes (calice/chumbadores) "
         "conforme NBR 9062; protensao (se houver) com controle de forca/alongamento.",
         "Corpos de prova por lote; verificacao de cobrimento e posicionamento de "
         "armadura; tolerancias dimensionais de fabricacao/montagem.",
         ["NBR 6118", "NBR 9062", "NBR 14931", "NBR 12655"]),
    ],
    "aco": [
        ("Estrutura metalica",
         "Perfis em aco estrutural conforme especificado (ex.: ASTM A572/A36 ou "
         "equivalente da norma), chapas, parafusos de alta resistencia e eletrodos "
         "compativeis; galvanizacao/pintura conforme plano de pintura.",
         "Fabricacao com marcas de peca (piece marks), soldas por soldador "
         "qualificado e EPS, torque/pretensao dos parafusos; montagem conforme plano "
         "de montagem (sequencia, contraventamento provisorio, prumo/nivel).",
         "Inspecao visual de solda e ensaios nao destrutivos quando exigidos; "
         "verificacao de torque; controle dimensional e de contraflecha; recebimento "
         "do plano de pintura (espessura de pelicula seca).",
         ["NBR 8800", "NBR 14762", "NBR 8681", "AWS D1.1"]),
        ("Cobertura e fechamento metalico",
         "Telhas metalicas (aco/aluzinco) termoacusticas conforme projeto; "
         "acessorios, calhas e rufos; parafusos com vedacao.",
         "Montagem com recobrimento e fixacao conforme fabricante; calhas e "
         "condutores dimensionados pela drenagem pluvial.",
         "Verificacao de estanqueidade e caimentos; ensaio de vazamento em calhas.",
         ["NBR 8800", "NBR 10844"]),
    ],
    "piso": [
        ("Piso industrial de concreto",
         "Concreto de piso fck de projeto; reforco por fibras (dosagem do fabricante) "
         "ou tela soldada de retracao; sub-base compactada e regularizada; "
         "espacadores e barras de transferencia nas juntas.",
         "Preparo do subleito/sub-base (compactacao ao grau de projeto), lancamento e "
         "acabamento (desempeno mecanico), juntas serradas na profundidade e prazo "
         "corretos, cura conforme norma; selagem das juntas.",
         "Verificacao de planicidade (FF/FL ou regua), espessura, resistencia por "
         "corpos de prova; controle do modulo de reacao do subleito (ensaio de placa).",
         ["NBR 6118", "ACI 360 (referencia)"]),
    ],
    "eletrico": [
        ("Instalacoes eletricas de baixa tensao",
         "Condutores de cobre isolacao conforme projeto; eletrodutos/eletrocalhas; "
         "quadros (QGF/QDC) e dispositivos (disjuntores/DR/DPS) de fabricante "
         "certificado; luminarias e tomadas conforme luminotecnica/planta.",
         "Instalacao com identificacao de circuitos, separacao de iluminacao e "
         "tomadas (4.2.5.5), taxa de ocupacao dos eletrodutos; aterramento e "
         "equipotencializacao conforme SPDA/aterramento.",
         "Ensaios de continuidade, isolamento e funcionalidade dos DR/DPS; medicao de "
         "resistencia de aterramento; conferencia do QDC (bitola/disjuntor por circuito).",
         ["NBR 5410", "NBR 5419", "NBR 14039 (MT quando houver)"]),
    ],
    "hidraulica": [
        ("Instalacoes hidrossanitarias",
         "Tubos e conexoes conforme material de projeto (PVC/PPR/aco), reservatorios, "
         "registros e metais; ralos e caixas de inspecao.",
         "Assentamento com declividades minimas, ventilacao e fecho hidrico dos "
         "aparelhos; ancoragem de tubulacoes; testes antes do fechamento.",
         "Teste de estanqueidade (pressao na agua fria, estanqueidade no esgoto); "
         "verificacao de vazoes/velocidades e declividades.",
         ["NBR 5626", "NBR 8160", "NBR 10844"]),
    ],
    "incendio": [
        ("Seguranca contra incendio",
         "Extintores, hidrantes/mangotinhos, sinalizacao e iluminacao de emergencia, "
         "deteccao/alarme e sprinklers (quando exigidos) conforme projeto e IT do "
         "Corpo de Bombeiros; materiais com certificacao/marcacao.",
         "Instalacao conforme projeto aprovado; rede de hidrantes/sprinklers testada; "
         "sinalizacao foto-luminescente posicionada nas rotas de fuga.",
         "Testes de vazao/pressao da rede; comissionamento de deteccao/alarme; "
         "vistoria para AVCB.",
         ["NBR 13714", "NBR 10897", "NBR 17240", "NBR 16820", "NBR 10898", "NBR 9077"]),
    ],
    "terraplenagem": [
        ("Terraplenagem e drenagem do lote",
         "Solo de emprestimo/aterro conforme especificacao (ISC/expansao); materiais "
         "de drenagem (tubos, canaletas, brita).",
         "Corte/aterro conforme greide de projeto, aterro em camadas compactadas ao "
         "grau exigido; execucao das canaletas/valas e dispositivos de drenagem.",
         "Controle de compactacao (grau/umidade otima - ensaio Proctor/densidade in "
         "situ); verificacao de cotas e caimentos; capacidade das canaletas.",
         ["DNIT (referencia)", "NBR 10844 (drenagem)"]),
    ],
}

# nomes de exibicao das disciplinas
_TITULO_DISC = {
    "fundacao": "FUNDACOES", "concreto": "ESTRUTURA DE CONCRETO",
    "aco": "ESTRUTURA METALICA E COBERTURA", "piso": "PISO INDUSTRIAL",
    "eletrico": "INSTALACOES ELETRICAS", "hidraulica": "INSTALACOES HIDROSSANITARIAS",
    "incendio": "SEGURANCA CONTRA INCENDIO", "terraplenagem": "TERRAPLENAGEM E DRENAGEM",
}
# ordem canonica de apresentacao
_ORDEM = ["terraplenagem", "fundacao", "concreto", "aco", "piso", "eletrico",
          "hidraulica", "incendio"]


def disciplinas_disponiveis():
    """Lista das disciplinas com clausulas na biblioteca."""
    return [d for d in _ORDEM if d in _CLAUSULAS]


def gerar_caderno(disciplinas=None):
    """Monta o caderno de encargos. disciplinas: lista de chaves (default: todas).
    Retorna dict estruturado {disciplinas:[{disciplina, titulo, clausulas:[...]}], ...}."""
    if disciplinas is None:
        disciplinas = disciplinas_disponiveis()
    invalidas = [d for d in disciplinas if d not in _CLAUSULAS]
    if invalidas:
        raise ValueError("disciplina(s) sem clausulas: %r" % invalidas)
    secoes = []
    for d in _ORDEM:
        if d not in disciplinas:
            continue
        clausulas = []
        for (titulo, material, execucao, controle, normas) in _CLAUSULAS[d]:
            clausulas.append({"titulo": titulo, "material": material,
                              "execucao": execucao, "controle": controle,
                              "normas": list(normas)})
        secoes.append({"disciplina": d, "titulo": _TITULO_DISC.get(d, d.upper()),
                       "clausulas": clausulas})
    normas = sorted({n for s in secoes for c in s["clausulas"] for n in c["normas"]})
    return {"secoes": secoes, "n_secoes": len(secoes),
            "n_clausulas": sum(len(s["clausulas"]) for s in secoes),
            "normas_referenciadas": normas}


def caderno_de_turnkey(R):
    """Seleciona as disciplinas do caderno a partir de um resultado de
    galpao_turnkey.rodar(R) (as executadas) + fundacao/piso/terraplenagem quando
    o concreto rodou. Best-effort, nunca quebra."""
    execs = set(R.get("executadas", []))
    disc = [d for d in _ORDEM if d in execs]
    if "concreto" in execs:
        # FUNDACAO sempre acompanha o concreto (o vertical sempre dimensiona a
        # fundacao). PISO so entra se foi DIMENSIONADO: especificar planicidade,
        # espessura e modulo de reacao do subleito de uma laje que ninguem
        # projetou e' o caderno prometendo o que o projeto nao entrega (e o
        # espelho do orcamento que omitia o insumo).
        if "fundacao" not in disc:
            disc.append("fundacao")
        piso = ((R.get("disciplinas", {}).get("concreto", {}) or {})
                .get("raw", {}) or {}).get("piso")
        if piso and "piso" not in disc:
            disc.append("piso")
    return gerar_caderno([d for d in _ORDEM if d in disc]) if disc else gerar_caderno()


def markdown(caderno, titulo="CADERNO DE ENCARGOS - ESPECIFICACOES TECNICAS"):
    """Renderiza o caderno em markdown."""
    L = ["# %s" % titulo, ""]
    for i, s in enumerate(caderno["secoes"], start=1):
        L.append("## %d. %s" % (i, s["titulo"]))
        for j, c in enumerate(s["clausulas"], start=1):
            L.append("### %d.%d %s" % (i, j, c["titulo"]))
            L.append("**Material:** %s" % c["material"])
            L.append("")
            L.append("**Execucao:** %s" % c["execucao"])
            L.append("")
            L.append("**Controle/aceitacao:** %s" % c["controle"])
            L.append("")
            L.append("**Normas:** %s" % ", ".join(c["normas"]))
            L.append("")
    L.append("---")
    L.append("**Normas referenciadas:** %s" % ", ".join(caderno["normas_referenciadas"]))
    return "\n".join(L)


# ----------------------------------- selftest --------------------------------
def _selftest():
    cad = gerar_caderno()
    assert cad["n_secoes"] == len(disciplinas_disponiveis())
    assert cad["n_clausulas"] >= cad["n_secoes"]
    # cada clausula tem os 4 campos + normas nao vazias
    for s in cad["secoes"]:
        for c in s["clausulas"]:
            assert c["material"] and c["execucao"] and c["controle"] and c["normas"]
    # ordem canonica: terraplenagem antes de fundacao antes de concreto
    ordem = [s["disciplina"] for s in cad["secoes"]]
    assert ordem.index("terraplenagem") < ordem.index("fundacao") < ordem.index("concreto")

    # subconjunto de disciplinas
    sub = gerar_caderno(["eletrico", "hidraulica"])
    assert sub["n_secoes"] == 2
    assert {s["disciplina"] for s in sub["secoes"]} == {"eletrico", "hidraulica"}

    # disciplina invalida levanta
    try:
        gerar_caderno(["inexistente"]); assert False
    except ValueError:
        pass

    # markdown tem cabecalhos e as normas
    md = markdown(cad)
    assert md.startswith("# CADERNO DE ENCARGOS") and "## 1." in md
    assert "**Material:**" in md and "NBR 8800" in md

    # caderno_de_turnkey seleciona pelas executadas + acrescenta a fundacao
    R = {"executadas": ["concreto", "eletrico"],
         "disciplinas": {"concreto": {"raw": {"piso": None}}}}
    ct = caderno_de_turnkey(R)
    discs = {s["disciplina"] for s in ct["secoes"]}
    assert "concreto" in discs and "fundacao" in discs and "eletrico" in discs
    # PISO nao dimensionado (raw['piso'] None) NAO pode virar clausula: o caderno
    # nao especifica o que o projeto nao entregou.
    assert "piso" not in discs, discs
    # com piso dimensionado, a clausula entra
    R2 = {"executadas": ["concreto"],
          "disciplinas": {"concreto": {"raw": {"piso": {"OK": True, "area_m2": 800.0}}}}}
    assert "piso" in {s["disciplina"] for s in caderno_de_turnkey(R2)["secoes"]}
    return True


if __name__ == "__main__":
    _selftest()
    print(markdown(gerar_caderno(["fundacao", "aco", "piso"]))[:1200])
    print("...\nselftest OK")
