# ============================================================================
# varredura_constantes_orfas.py - G124: AS 51 CONSTANTES QUE NINGUEM LE.
# MODULO DE PRODUCAO (fonte unica das 39 dividas): ORFAS_TRIADAS e o que o
# cliente recebe (via exigencias_nao_verificadas_g130 -> pacote_legal, G130);
# a lente e o teste importam daqui. (Uma fonte so - regra do lote.)
# Rodado a mao/CI (python varredura_constantes_orfas.py) e pelo teste-guarda
# tests/test_varredura_constantes_orfas_g124.py. IMPORTADO pela producao
# (exigencias_nao_verificadas_g130, que le ORFAS_TRIADAS ao vivo) - por isso
# NAO e script avulso (ver test_alcancabilidade; G130 promoveu o dado a
# producao sem copiar a clausula).
#
# Motivacao (G124, classe que apareceu duas vezes no G119): um limite de
# norma escrito numa constante que nenhuma conta le significa uma de tres
# coisas - a exigencia esta implementada EM OUTRO LUGAR (numero duplicado,
# livre para divergir), NAO ESTA implementada (a folha nao a verifica), ou
# a constante e RESIDUO. A ancora do G114 era o caso 3 disfarcado de caso 1
# (constante "medida" que a producao nao lia). A triagem das 61 remedidas
# neste goal (o G119 media 51 antes do arco G120-G123; a 61a,
# validacao.TOL, foi achada pela propria lente, que nao bebe do .venv):
# 7 viraram fonte unica, 15 foram removidas, 39 sao divida declarada em
# ORFAS_TRIADAS.
#
# Maquina: AST sobre framework/galpao_fw/*.py (a medida do G119). Definicao
# = atribuicao de topo com alvo Name em MAIUSCULAS (apos tirar "_", len>=3,
# com letra, sem dunder). Uso = Name em Load, atributo .NOME, ou
# `from mod import NOME`, em QUALQUER .py do diretorio (recursivo,
# incluindo tests/). Mencao em string NAO e uso (substring nao e conta).
# Orfa = definida e sem nenhum uso no repo inteiro.
#
# Licao do G98 (renomear para escapar): a chave do baseline e (arquivo,
# nome) EXATO, e a lente inclui nomes com "_" inicial - PUBLICO->PRIVADO
# nao escapa. Renomear para minusculas tira a definicao do alcance da
# lente, MAS a entrada do baseline vira "resolvida" e o confere REPROVA na
# mesma (baseline nos dois sentidos): sumir sem triagem escrita e defeito,
# nao cura. O teste-guarda prova os tres vermelhos.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - constantes de FUNCAO ou de classe (so as de modulo entram);
#   - leitura por getattr/dicionario de simbolos (ninguem no repo faz isso
#     com constante de norma; se um dia fizer, a orfa acusa e a triagem diz);
#   - arquivos que nao compilam (pulados como nas outras lentes);
#   - duplicata em PROSA (nota de tabela citando o numero): prosa nao e
#     conta e nao conta como uso - a triagem dessas e DIVIDA, nao FONTE.
# ============================================================================
"""Varredura G124: constantes de modulo escritas e nunca lidas no repo."""

from __future__ import annotations

import ast
import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent

EU = "varredura_constantes_orfas.py"


def _e_constante(nome):
    """Regra de definicao (a medida do G119): MAIUSCULAS, len>=3, com letra,
    sem dunder. Inclui "_" inicial (licao do G98: _FOO nao escapa)."""
    s = nome.strip("_")
    return (len(s) >= 3 and s == s.upper()
            and any(c.isalpha() for c in s)
            and not nome.startswith("__"))


def _definicoes(arvore):
    """[(nome, lineno, valor_repr)] das constantes de topo do modulo."""
    achadas = []
    for no in arvore.body:
        if isinstance(no, (ast.Assign, ast.AnnAssign)):
            tgts = no.targets if isinstance(no, ast.Assign) else [no.target]
            for t in tgts:
                if isinstance(t, ast.Name) and _e_constante(t.id):
                    try:
                        val = repr(ast.literal_eval(no.value))[:120]
                    except Exception:
                        val = "<expressao>"
                    achadas.append((t.id, no.lineno, val))
    return achadas


def _usos(arvore):
    """(names_load, attrs, importfrom) usados no arquivo."""
    names, attrs, impfrom = set(), set(), set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Name) and isinstance(no.ctx, ast.Load):
            names.add(no.id)
        elif isinstance(no, ast.Attribute):
            attrs.add(no.attr)
        elif isinstance(no, ast.ImportFrom):
            for a in no.names:
                impfrom.add(a.name)
    return names, attrs, impfrom


def varredura(raiz=None):
    """Orfas repo-wide: [{arquivo, nome, linha, valor}]. Ordem estavel.

    `raiz` (molde G51-rev): diretorio a varrer, default o proprio
    galpao_fw. Existe para o teste-guarda provar o VERMELHO num diretorio
    temporario, sem escrever modulo falso no repo vivo."""
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    defs = {}
    usos = {}
    arquivos = sorted(base.glob("*.py"))
    for caminho in arquivos:
        if caminho.name == EU and raiz is None:
            continue
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        rel = caminho.name
        defs[rel] = _definicoes(arvore)
        usos[rel] = _usos(arvore)
    for caminho in sorted(base.rglob("*.py")):
        if caminho.parent == base:
            continue
        # fora do repo: ambiente virtual, cache e saidas nao sao consumo.
        if any(p.startswith(".") or p == "__pycache__"
               for p in caminho.relative_to(base).parts[:-1]):
            continue
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        try:
            rel = caminho.relative_to(base).as_posix()
        except ValueError:
            rel = caminho.name
        if rel in usos:
            continue
        usos[rel] = _usos(arvore)
    orfas = []
    for arquivo, lista in sorted(defs.items()):
        nomes_proprios, attrs_proprios, _imp = usos.get(
            arquivo, (set(), set(), set()))
        for nome, linha, valor in lista:
            if nome in nomes_proprios or nome in attrs_proprios:
                # Lida no proprio modulo: nao e orfa. A medida do G119
                # parte das nunca-lidas-no-proprio-modulo; sem este filtro
                # toda constante de uso interno viraria "orfa".
                continue
            lido = False
            for outro, (names, attrs, impfrom) in usos.items():
                if outro == arquivo:
                    continue
                if nome in names or nome in attrs or nome in impfrom:
                    lido = True
                    break
            if not lido:
                orfas.append({"arquivo": arquivo, "nome": nome,
                              "linha": linha, "valor": valor})
    orfas.sort(key=lambda d: (d["arquivo"], d["nome"]))
    return orfas


def chaves_orfas(raiz=None):
    return sorted((d["arquivo"], d["nome"]) for d in varredura(raiz))


# ---------------------------------------------------------------------------
# ORFAS_TRIADAS (G124). Cada orfa repo-wide ou esta aqui, com destino,
# motivo e endereco - ou a suite fica vermelha. Destinos:
#   DIVIDA   - valor normativo (ou gap de modelagem) sem conta que o leia;
#              o endereco e a CLAUSULA (ou o arquivo:linha do gap).
# FONTE_UNICA e RESIDUO nao deixam entrada: o rewire faz a constante ser
# lida (sai do conjunto) e o residuo e removido (sai do disco) - e o
# confere acusa nos dois sentidos se alguem desfizer sem triagem.
# Entrada com motivo vazio reprova (sem_motivo); com endereco vazio
# reprova (sem_endereco); triada que voltou a ser lida ou sumiu do disco
# reprova como resolvida/ausente (nome morto, licao do G98).
# Medido na triagem: 61 orfas (o G119 media 51 antes do G120-G123),
# 7 fonte-unica + 15 residuos tratados, 39 dividas abaixo.
# ---------------------------------------------------------------------------
ORFAS_TRIADAS = {
    ("alvenaria_estrutural.py", "FVK_ARMADA_COEF"): (
        "DIVIDA",
        "fvk da alvenaria ARMADA (0,35+17,5.rho) sem conta: so a Tab.4 "
        "(nao armada) e calculada, via FVK_TABELA_4/fvk_caracteristico_6226.",
        "NBR 16868-1 11.4.3"),
    ("alvenaria_estrutural.py", "FVK_ARMADA_RHO_TETO"): (
        "DIVIDA",
        "teto rho<=2% da mesma formula armada, sem conta (ver FVK_ARMADA_COEF).",
        "NBR 16868-1 11.4.3"),
    ("alvenaria_estrutural.py", "FVK_ARMADA_TAU0_MP"): (
        "DIVIDA",
        "tau0=0,35 da mesma formula armada, sem conta (ver FVK_ARMADA_COEF).",
        "NBR 16868-1 11.4.3"),
    ("alvenaria_estrutural.py", "FVK_ARMADA_TETO_MP"): (
        "DIVIDA",
        "teto 0,7 MPa da mesma formula armada, sem conta (ver FVK_ARMADA_COEF).",
        "NBR 16868-1 11.4.3"),
    ("aterramento_nbr15749.py", "R_MAX_EXPLOSIVO"): (
        "DIVIDA",
        "limite 1 ohm p/ locais a prova de explosao; dimensiona_aterramento "
        "so aplica o default R_MAX_SPDA (10 ohm), sem ramificacao por local.",
        "aterramento_nbr15749.py:27 (fonte citada: Negrisoli, sem clausula NBR)"),
    ("cargas_nbr6120.py", "Q_BORDA_GUARDA_CORPO"): (
        "DIVIDA",
        "2 kN/m na borda com guarda-corpo: o numero so existe em prosa "
        "(nota da sacada_*); nenhuma conta soma a parcela de borda.",
        "NBR 6120 nota j da Tab.10"),
    ("cargas_nbr6120.py", "Q_ELEMENTO_ISOLADO_COBERTURA"): (
        "DIVIDA",
        "1 kN concentrado isolado: so existe em prosa (nota da "
        "cobertura_manutencao); nenhuma conta o aplica isolado das demais.",
        "NBR 6120 6.4"),
    ("condutores_nbr5410.py", "DV_TERMINAL_MAX"): (
        "DIVIDA",
        "queda no ramal terminal (quadro->equipamento) <=4%: dimensiona_ "
        "condutor so cobra DV_LIMITE por origem (5/7/7%), sem conceito de "
        "ramal terminal no circ.",
        "NBR 5410 6.2.7"),
    ("desempenho_nbr15575.py", "COMB_FACHADA"): (
        "DIVIDA",
        "combinacao Sd=0,9Sgk+0,8Swk: verifica_fachada recebe d_h pronto; "
        "a combinacao e trabalho do chamador, nunca aplicada aqui.",
        "NBR 15575-4:2013 7.2.1 Tab.1"),
    ("desempenho_nbr15575.py", "NOTA_B_TAB2"): (
        "DIVIDA",
        "reclassificacao 'sem aberturas' com dispositivos no contorno: "
        "limite_tab2 recebe linha/coluna prontas, sem ramificacao da nota b.",
        "NBR 15575-2 Tab.2 nota b"),
    ("deteccao_alarme_nbr17240.py", "AFASTAMENTO_PAREDE_MIN_M"): (
        "DIVIDA",
        "0,15 m do teto a parede/viga: sem conta que posicione detector.",
        "NBR 17240 5.4.1.2"),
    ("deteccao_alarme_nbr17240.py", "LINEAR_PAREDE_MAX_M"): (
        "DIVIDA",
        "feixe <=7,5 m das paredes: a docstring de numero_detectores_ "
        "lineares cita, mas o codigo so usa ENTRE_FEIXES (15) e ALCANCE (100).",
        "NBR 17240 5.4.4"),
    ("deteccao_alarme_nbr17240.py", "RAIO_DETECTOR_M"): (
        "DIVIDA",
        "raio 6,3 m (quadrado 9x9) da cobertura 81 m2: cobertura_detector "
        "trabalha em area, sem conta em raio.",
        "NBR 17240 5.4.1.1"),
    ("escada.py", "Q_CONCENTRADA"): (
        "DIVIDA",
        "2,5 kN concentrados sem verificacao local na escada metalica.",
        "escada.py:17 (origem normativa sem clausula citada no codigo)"),
    ("fissuracao_nbr6118.py", "ETA1_ENTALHADA"): (
        "DIVIDA",
        "eta1=1,4 (barra entalhada): abertura_wk aceita eta1 por parametro "
        "mas so referencia a nervurada por default; sem validacao contra "
        "estes valores.",
        "NBR 6118 9.3.2.1"),
    ("fissuracao_nbr6118.py", "ETA1_LISA"): (
        "DIVIDA",
        "eta1=1,0 (barra lisa): idem ETA1_ENTALHADA.",
        "NBR 6118 9.3.2.1"),
    ("fronteiras.py", "UNIDADE_TIPO_ENUM"): (
        "DIVIDA",
        "enum de tipos de membro sem validacao consumidora: orcamento, "
        "ifc_emit e ifc_map comparam literais ('Footing' etc.) sem passar "
        "por ele.",
        "fronteiras.py:41 (contrato F06); literais em orcamento.py:308-309,347-348, "
        "ifc_emit.py:457, ifc_map.py:40"),
    ("galpao_concreto.py", "PSI0_SOBRECARGA"): (
        "DIVIDA",
        "psi0=0,7 da sobrecarga de cobertura: comb1 usa 1,4(G+Q) cheia e "
        "comb2 usa Nd minimo 1,0*G sem Q; o 0,7 nunca e aplicado.",
        "NBR 8681 (combinacoes de _dimensiona_pilar_secao)"),
    ("gusset_ligacao.py", "K_UMA_BORDA"): (
        "DIVIDA",
        "K=1,2 do gusset em bandeira: sem ramificacao por tipo; o usuario "
        "informa K manualmente (default K_DUAS_BORDAS). Valor citado na "
        "docstring, nao aplicado.",
        "AISC DG29"),
    ("hidraulica_edificio.py", "SOBREPRESSAO_TRANSIENTE_MAX_KPA"): (
        "DIVIDA",
        "transiente ate 200 kPa acima da dinamica: sem conta de golpe.",
        "NBR 5626 6.9.7"),
    ("hidraulica_predial.py", "P_DIN_MIN_REDE_KPA"): (
        "DIVIDA",
        "5 kPa em qualquer ponto da rede: verifica_pressao so cobra "
        "P_DIN_MIN_PONTO_KPA (10 kPa, 6.9.2).",
        "NBR 5626 6.9.4"),
    ("iluminacao_emergencia_nbr10898.py", "ESPACO_ALTO_MAX_M"): (
        "DIVIDA",
        "teto absoluto 20 m do espacamento de aclaramento: "
        "espacamento_aclaramento devolve o ideal (15 m) sem cortar no maximo.",
        "NBR 10898 (espacamento de aclaramento)"),
    ("iluminacao_emergencia_nbr10898.py", "FLUXO_MIN_BALIZ_DUPLO_LM"): (
        "DIVIDA",
        "400 lm do balizamento de dupla funcao: dimensiona_iluminacao_ "
        "emergencia so cobra o fluxo de aclaramento (300 lm).",
        "NBR 10898 5.2.4"),
    ("iluminacao_emergencia_nbr10898.py", "FLUXO_MIN_BALIZ_EXCLUSIVO_LM"): (
        "DIVIDA",
        "30 lm do balizamento exclusivo: idem FLUXO_MIN_BALIZ_DUPLO_LM.",
        "NBR 10898 5.2.3"),
    ("laje_concreto.py", "THETA_APOIO_LIM"): (
        "DIVIDA",
        "rotacao limite 0,0017 rad no apoio: Tab 13.3 implementada para "
        "flecha, sem conta de rotacao. Ja citada como orfa sem efeito no "
        "inventario do G116.",
        "NBR 6118 Tab 13.3"),
    ("luminotecnica_nbr8995.py", "REFLETANCIA_PAREDE"): (
        "DIVIDA",
        "refletancias medias: Fu entra por catalogo/input "
        "(fator_utilizacao_tms/projeto_luminotecnico), sem derivacao das "
        "refletancias.",
        "Mamede 2.6.7.1.2"),
    ("luminotecnica_nbr8995.py", "REFLETANCIA_PISO"): (
        "DIVIDA",
        "idem REFLETANCIA_PAREDE.",
        "Mamede 2.6.7.1.2"),
    ("luminotecnica_nbr8995.py", "REFLETANCIA_TETO"): (
        "DIVIDA",
        "idem REFLETANCIA_PAREDE.",
        "Mamede 2.6.7.1.2"),
    ("madeira_nbr7190.py", "GAMMA_W_ELS"): (
        "DIVIDA",
        "gamma_w=1,0 no ELS: resistencias_calculo recebe gamma_w por "
        "parametro mas nenhum caminho ELS de resistencia o consome (o ELS "
        "do modulo e flecha).",
        "NBR 7190 5.8.6"),
    ("perdas_protensao_nbr6118.py", "EPS_CS_PADRAO"): (
        "DIVIDA",
        "retracao tipica -5,0e-4: o processo aproximado implementado nao "
        "destaca a parcela de retracao; valor da Tab.A.1 sem consumidor.",
        "NBR 6118 Tab.A.1"),
    ("plataforma.py", "PESO_ACO"): (
        "DIVIDA",
        "77 kN/m3: viga_secundaria recebe q_perm do chamador; peso proprio "
        "nunca somado.",
        "plataforma.py:18 (gap de modelagem, sem clausula)"),
    ("plataforma.py", "Q_CONCENTRADA"): (
        "DIVIDA",
        "2,0 kN concentrados p/ verificacao local: viga_secundaria so "
        "verifica carga distribuida.",
        "plataforma.py:15 (gap de modelagem, sem clausula)"),
    ("premoldado_nbr9062.py", "ESP_FUNDO_MIN"): (
        "DIVIDA",
        "0,20 m de fundo sob o pilar: dimensiona_calice verifica parede "
        "(ESP_PAREDE_MIN, lida) mas nao o fundo.",
        "NBR 9062 7.7.5.1"),
    ("proteccao_sprinklers_nbr10897.py", "PAREDE_MIN_MM"): (
        "DIVIDA",
        "100 mm a parede: sem conta que posicione chuveiro.",
        "NBR 10897 7.7.3"),
    ("sinalizacao_nbr16820.py", "NIVEL_INFERIOR_M"): (
        "DIVIDA",
        "nivel inferior 0,25-0,50 m: dimensiona_sinalizacao so emite o "
        "superior (NIVEL_SUPERIOR_MIN_M, lido).",
        "NBR 16820 6.3"),
    ("sinalizacao_nbr16820.py", "NIVEL_INTERMEDIARIO_M"): (
        "DIVIDA",
        "nivel intermediario 1,20-1,60 m: idem NIVEL_INFERIOR_M.",
        "NBR 16820 6.3"),
    ("sismo_nbr15421.py", "_CUP"): (
        "DIVIDA",
        "Cup por zona (Tab.10): periodo_aproximado devolve Ta sem teto; o "
        "Cup so limitaria o T de extracao modal, que nao existe no modulo.",
        "NBR 15421 Tab.10"),
    ("spda_nbr5419.py", "CD_LOCALIZACAO"): (
        "DIVIDA",
        "fator Cd por localizacao: sem conta de risco que o consuma.",
        "NBR 5419-2 Tab.A.1"),
    ("spda_nbr5419.py", "RT_R3"): (
        "DIVIDA",
        "risco toleravel de perda de patrimonio cultural: "
        "protecao_necessaria so avalia R1 (default RT_R1).",
        "NBR 5419-2 Tab.4"),
}


def confere(raiz=None, triadas=None):
    """Guarda D87 em forma chamavel: orfas nao triadas vs triagem.

    Devolve {"OK", "novas", "resolvidas", "sem_motivo", "sem_endereco",
    "ausentes"}:
      - novas: orfas fora da triagem (constante nova sem destino);
      - resolvidas: triadas que voltaram a ser lidas ou sumiram (nome
        morto - inclusive renomeada para minusculas, licao do G98);
      - sem_motivo / sem_endereco: isencao sem motivo/endereco escrito;
      - ausentes: triada cujo arquivo sumiu do disco.
    """
    tri = ORFAS_TRIADAS if triadas is None else triadas
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    orfas = {(d["arquivo"], d["nome"]) for d in varredura(raiz)}
    novas = sorted(k for k in orfas if k not in (tri or {}))
    no_disco = {p.name for p in base.glob("*.py")}
    resolvidas = sorted(k for k in (tri or {})
                        if k[0] in no_disco and k not in orfas)
    sem_motivo = sorted(k for k, v in (tri or {}).items()
                        if len(v) < 2 or not (v[1] or "").strip())
    sem_endereco = sorted(k for k, v in (tri or {}).items()
                          if len(v) < 3 or not (v[2] or "").strip())
    ausentes = sorted(k for k in (tri or {}) if k[0] not in no_disco)
    return {"OK": not (novas or resolvidas or sem_motivo or sem_endereco
                       or ausentes),
            "novas": novas, "resolvidas": resolvidas,
            "sem_motivo": sem_motivo, "sem_endereco": sem_endereco,
            "ausentes": ausentes}


def relatorio_pt(res=None):
    """Uma mensagem so com todos os lados (receita do G97)."""
    res = confere() if res is None else res
    linhas = ["VARREDURA G124 - CONSTANTES ORFAS"]
    for lado in ("novas", "resolvidas", "sem_motivo", "sem_endereco",
                 "ausentes"):
        linhas.append("  [%s] %d" % (lado, len(res.get(lado) or [])))
        for arquivo, nome in (res.get(lado) or []):
            linhas.append("    %-12s %s::%s" % (lado, arquivo, nome))
    return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    res = confere()
    print(relatorio_pt(res))
    print("orfas=%d triadas=%d OK=%s"
          % (len(varredura()), len(ORFAS_TRIADAS), res["OK"]))
