# ============================================================================
# chaves_to_rodar_g134.py - G134: A PERGUNTA DO CIMENTO QUE NENHUMA CONTA LE.
# CENSO DAS CHAVES DE to_rodar_params SEM LEITOR + MOTIVO DA REMOCAO.
# MODULO DE PRODUCAO (fonte unica): o censo que o teste-guarda confere mora
# aqui; a lente e o teste importam daqui. (Uma fonte so - regra do lote.)
# Rodado a mao/CI (python chaves_to_rodar_g134.py) e pelo teste-guarda
# tests/test_chaves_to_rodar_g134.py. IMPORTADO pela producao
# (projeto_spec, que rejeita o cimento legado com o motivo daqui) - por isso
# NAO e script avulso (ver test_alcancabilidade).
#
# O que foi MEDIDO (G131 + remedicao G134 por AST, antes de mudar):
#   - `to_rodar_params` (projeto_spec.py) escrevia 30 chaves de topo em `p`
#     (coleta por AST: `p["chave"]`, `p.setdefault/get/pop("chave", ...)`):
#     aguas, baldrame, base_fixed, calha, cargas, chuva_I_mm_h, cimento,
#     creditar_cortante_mesa_inclinada, divisa, escada, estaca, fogo, fu,
#     fundacao, fy, geometria, mf_sec, neve, norma_6118_edicao, parede,
#     plataforma, ponte, secundarios, tapered, telha, terreno, tipo_ligacao,
#     tipo_portico, trelica, vento.
#   - Destas, 2 nao apareciam como literal em `rodar_galpao.py`:
#     `norma_6118_edicao` (lida de forma INDIRETA por `edicao_de_spec`,
#     rodar_galpao.py:1554-1561 - NAO e morta) e `cimento` (ZERO leitores:
#     nem literal, nem chamada; `grep cimento rodar_galpao.py` vazio).
#   - O `rodar_galpao` e o galpao METALICO (NBR 8800), sem icamento de
#     pre-moldado. O icamento so e calculado pelo `galpao_concreto` dentro
#     do turnkey, cuja entrada e o project-spec (topo ou
#     `turnkey.concreto`, ligados no G131) - nao o ProjetoSpec. A pergunta
#     do wizard ("Tipo de cimento do concreto p/ o fckj do icamento",
#     wizard.py:197) viajava pelo ProjetoSpec.cimento e `p["cimento"]` ate
#     um orquestrador que nunca a lia: constante que a producao nao le e
#     comentario (convencao 8), agora numa pergunta ao usuario.
#   - A varredura de campos mortos do wizard (S39) conta `p[chave] = ...`
#     como campo fiado; por isso nao acusou: ela confere a ESCRITA, nunca
#     a LEITURA.
#
# Escolha escrita (exigida pelo goal): A PERGUNTA SAI DO FLUXO METALICO.
# Motivo: nao ha conta no caminho metalico que use o cimento (o galpao
# metalico nao calcula icamento; a fundacao sapata/bloco/estaca nao usa o
# `s` da 12.3.3), entao a alternativa do goal ("chegar a uma conta que a
# usa") exigiria inventar um uso - arbitrar dado de projeto (proibido no
# lote). Sair com o motivo escrito e a unica opcao honesta. O cimento do
# project-spec do turnkey (topo ou payload concreto) NAO sai: la ele e
# lido (G131; cimento_de_spec/cimento_do_turnkey). Nao se escolhe cimento
# de projeto nenhum; nao se muda numero nenhum do metalico (a chave nunca
# chegou a conta, entao remover o repasse e byte-identico por construcao).
#
# Maquina: CHAVES_ESPERADAS (as 29 de topo que ficam, sem `cimento`) +
# CHAVE_REMOVIDA (`cimento`, com MOTIVO_REMOCAO_CIMENTO) +
# LEITURAS_DECLARADAS (`norma_6118_edicao` via
# `edicao_nbr6118_g123.edicao_de_spec`: leitura indireta declarada, nao
# morte) + chaves_escritas_por_to_rodar (por AST, nunca substring) +
# leituras_diretas_em_rodar (`params[...]`/`params.get`, por AST: string
# em mensagem nao e leitura) + usa_leitura_declarada (import + chamada,
# por AST, com alias) + chaves_sem_leitor (escritas menos diretas menos
# declaradas usadas) + confere (portao: zero sem-leitor E escritas ==
# esperadas, nos dois sentidos; 'sem_leitor'/'extras'/'faltando' sao os
# acumuladores que o teste faz disparar).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - a familia condicional `mont_*` (mont_q_kNm2, mont_area_exposta_m2,
#     mont_raio_guindaste_m, mont_angulo_estai, mont_n_estais): escrita
#     DINAMICA (`p[_k] = ...` em laco, so quando montagem_params presente)
#     e lida pelo gate de montagem no rodar_galpao (`mont_` presente la).
#     O scan estatico de chaves literais nao a ve dos dois lados; triada
#     no verbete D162, fora do baseline estatico - dito aqui para a
#     ausencia nao parecer esquecimento;
#   - chaves ANINHADAS (ex. `telha.cfg`, `secundarios.longarina`,
#     `fundacao.tipo`): o censo e de topo de `p`; o aninhado e contrato de
#     cada gate, nao do mapper;
#   - os VALORES (so as chaves sao censadas; numero que ninguem le e
#     comentario - convencao 8 - e o G134 nao move numero nenhum);
#   - o cimento do turnkey (mora em `cimento_nbr6118_g126`; aqui e so o
#     fluxo metalico ProjetoSpec/wizard -> rodar_galpao).
# ============================================================================
"""Censo das chaves de to_rodar_params sem leitor (G134): fonte unica."""

from __future__ import annotations

import ast
import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent

# As 29 chaves de topo que to_rodar_params escreve depois do G134 (sem
# `cimento`). Ordem alfabetica, baseline nos dois sentidos: chave nova sem
# triagem = vermelho; chave sumida = nome morto = vermelho.
CHAVES_ESPERADAS = frozenset({
    "aguas",
    "baldrame",
    "base_fixed",
    "calha",
    "cargas",
    "chuva_I_mm_h",
    "creditar_cortante_mesa_inclinada",
    "divisa",
    "escada",
    "estaca",
    "fogo",
    "fu",
    "fundacao",
    "fy",
    "geometria",
    "mf_sec",
    "neve",
    "norma_6118_edicao",
    "parede",
    "plataforma",
    "ponte",
    "secundarios",
    "tapered",
    "telha",
    "terreno",
    "tipo_ligacao",
    "tipo_portico",
    "trelica",
    "vento",
})

# A chave que saiu do fluxo metalico (G134), com o motivo escrito (o goal
# exige "com o motivo escrito": ele mora aqui, na fonte unica, e e citado
# pelo projeto_spec ao rejeitar o legado e pelo verbete D162).
CHAVE_REMOVIDA = "cimento"
MOTIVO_REMOCAO_CIMENTO = (
    "G134: o galpao metalico (rodar_galpao, NBR 8800) nao calcula icamento "
    "de pre-moldado nem usa o `s` da NBR 6118 12.3.3 em conta nenhuma; a "
    "pergunta do wizard viajava pelo ProjetoSpec.cimento e p[cimento] ate "
    "um orquestrador com zero leitores (constante que a producao nao le e "
    "comentario, convencao 8). A pergunta sai do fluxo metalico; o cimento "
    "do project-spec do turnkey (topo ou turnkey.concreto) fica - la ele e "
    "lido (G131)."
)

# Leituras INDIRETAS declaradas: chave -> (modulo, funcao). Uma chave nesta
# tabela so conta como lida quando o rodar_galpao IMPORTA e CHAMA a funcao
# (usa_leitura_declarada, por AST, com alias). Declarar sem usar = vermelho
# (a funcao some ou o call some e a chave volta a sem-leitor).
LEITURAS_DECLARADAS = {
    "norma_6118_edicao": ("edicao_nbr6118_g123", "edicao_de_spec"),
}


def _caminho(raiz=None, nome="projeto_spec.py"):
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    return base / nome


def _ast_de(caminho):
    try:
        texto = pathlib.Path(caminho).read_text(encoding="utf-8",
                                                errors="replace")
    except OSError:
        return None
    try:
        return ast.parse(texto, filename=str(caminho))
    except SyntaxError:
        return None


def chaves_escritas_por_to_rodar(raiz=None):
    """Chaves de topo que to_rodar_params escreve em `p` (por AST).

    Coleta `p["chave"]` (Subscript sobre o Name `p` com slice literal) e
    `p.setdefault/get/pop("chave", ...)` (primeiro arg literal). Escritas
    dinamicas (`p[_k]`, ex. familia mont_*) nao aparecem aqui: sao
    condicionais, triadas no D162 fora do baseline estatico (dito na fonte).
    `raiz` (molde G51-rev): diretorio a varrer, default o proprio galpao_fw;
    existe para o teste-guarda provar o VERMELHO num diretorio temporario.
    """
    arvore = _ast_de(_caminho(raiz))
    if arvore is None:
        return set()
    fn = None
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == "to_rodar_params":
            fn = no
            break
    if fn is None:
        return set()
    chaves = set()
    for no in ast.walk(fn):
        if isinstance(no, ast.Subscript):
            if isinstance(no.value, ast.Name) and no.value.id == "p":
                sl = no.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    chaves.add(sl.value)
        elif isinstance(no, ast.Call):
            f = no.func
            if (isinstance(f, ast.Attribute)
                    and isinstance(f.value, ast.Name)
                    and f.value.id == "p"
                    and f.attr in ("setdefault", "get", "pop")
                    and no.args
                    and isinstance(no.args[0], ast.Constant)
                    and isinstance(no.args[0].value, str)):
                chaves.add(no.args[0].value)
    return chaves


def leituras_diretas_em_rodar(raiz=None):
    """Chaves lidas DIRETO pelo rodar_galpao em `params` (por AST).

    Coleta `params["chave"]` (Subscript sobre o Name `params` com slice
    literal), `params.get/setdefault/pop("chave", ...)` (primeiro arg
    literal) e `"chave" in params` (Compare). So AST: string em mensagem
    de erro nao e leitura (o mesmo rigor do scan de imports do G126).
    `raiz` (molde G51-rev): diretorio a varrer, default o proprio
    galpao_fw; existe para o teste-guarda provar o VERMELHO num diretorio
    temporario.
    """
    arvore = _ast_de(_caminho(raiz, "rodar_galpao.py"))
    if arvore is None:
        return set()
    lidas = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Subscript):
            if isinstance(no.value, ast.Name) and no.value.id == "params":
                sl = no.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    lidas.add(sl.value)
        elif isinstance(no, ast.Call):
            f = no.func
            if (isinstance(f, ast.Attribute)
                    and isinstance(f.value, ast.Name)
                    and f.value.id == "params"
                    and f.attr in ("get", "setdefault", "pop")
                    and no.args
                    and isinstance(no.args[0], ast.Constant)
                    and isinstance(no.args[0].value, str)):
                lidas.add(no.args[0].value)
        elif isinstance(no, ast.Compare):
            for op, comp in zip(no.ops, no.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    alvo = comp
                    if isinstance(alvo, ast.Constant) \
                            and isinstance(alvo.value, str):
                        # `"chave" in params`: o outro lado tem de ser o
                        # Name `params` (esquerda ou comparadores).
                        lados = [no.left] + list(no.comparators)
                        if any(isinstance(l, ast.Name) and l.id == "params"
                               for l in lados):
                            lidas.add(alvo.value)
    return lidas


def usa_leitura_declarada(raiz=None, chave="norma_6118_edicao"):
    """A leitura indireta declarada da chave e usada de verdade?

    True quando rodar_galpao.py IMPORTA a funcao do modulo declarado (com ou
    sem alias, `from ... import f` / `from ... import f as g` / `import mod`
    + `mod.f`) E a CHAMA no corpo. So AST; nome em string de mensagem de
    erro nao e dependencia nem chamada.
    """
    decl = LEITURAS_DECLARADAS.get(chave)
    if decl is None:
        return False
    modulo, funcao = decl
    arvore = _ast_de(_caminho(raiz, "rodar_galpao.py"))
    if arvore is None:
        return False
    # Nomes locais que apontam para a funcao declarada (alias de import).
    apelidos = set()
    modulo_importado = False
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom) and (no.module or "").split(".")[0] == modulo.split(".")[0]:
            for a in no.names:
                if a.name == funcao:
                    apelidos.add(a.asname or a.name)
        elif isinstance(no, ast.Import):
            for a in no.names:
                if (a.name or "").split(".")[0] == modulo.split(".")[0]:
                    modulo_importado = True
    if not apelidos and not modulo_importado:
        return False
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        f = no.func
        if isinstance(f, ast.Name) and f.id in apelidos:
            return True
        if isinstance(f, ast.Attribute) and f.attr == funcao:
            if isinstance(f.value, ast.Name):
                # `mod.funcao(...)` ou alias de modulo.
                return True
    return False


def chaves_sem_leitor(raiz=None):
    """Chaves escritas por to_rodar_params sem leitor no rodar_galpao.

    Leitor = acesso direto a `params` (leituras_diretas_em_rodar) OU
    leitura indireta declarada e usada (LEITURAS_DECLARADAS +
    usa_leitura_declarada). O `cimento` reinjetado cai aqui (zero
    leitores); `norma_6118_edicao` com o import/call removido cai aqui
    tambem. Ordem estavel.
    """
    escritas = chaves_escritas_por_to_rodar(raiz)
    diretas = leituras_diretas_em_rodar(raiz)
    sem = []
    for chave in sorted(escritas):
        if chave in diretas:
            continue
        if chave in LEITURAS_DECLARADAS and usa_leitura_declarada(
                raiz, chave):
            continue
        sem.append(chave)
    return sem


def confere_censo(raiz=None, esperado=None):
    """Portao do censo: zero chaves sem leitor E escritas == esperadas.

    Baseline nos dois sentidos: `sem_leitor` (chave morta ou leitura
    declarada que parou de usar), `extras` (chave nova sem triagem) e
    `faltando` (nome morto) sao os acumuladores que o teste faz disparar;
    OK so quando os tres estao vazios. (Nome confere_censo, molde G129:
    o censo de guardas do D86 so enxerga `def confere_*`.)
    """
    esp = set(CHAVES_ESPERADAS) if esperado is None else set(esperado)
    escritas = chaves_escritas_por_to_rodar(raiz)
    sem = chaves_sem_leitor(raiz)
    extras = sorted(escritas - esp)
    faltando = sorted(esp - escritas)
    return {"OK": not (sem or extras or faltando),
            "escritas": sorted(escritas),
            "sem_leitor": sem,
            "extras": extras,
            "faltando": faltando}


def main() -> int:
    c = confere_censo()
    print("escritas=%d esperadas=%d sem_leitor=%r extras=%r faltando=%r"
          % (len(c["escritas"]), len(CHAVES_ESPERADAS), c["sem_leitor"],
             c["extras"], c["faltando"]))
    print("removida: %s - %s" % (CHAVE_REMOVIDA, MOTIVO_REMOCAO_CIMENTO))
    print("leitura declarada: norma_6118_edicao via edicao_de_spec usada=%s"
          % usa_leitura_declarada())
    return 0 if c["OK"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
