# ============================================================================
# fctd_nbr6118_g136.py - G136: A FCTD EM FONTE UNICA. PRODUCAO, NAO LENTE.
# MODULO DE PRODUCAO (fonte unica): a conta da resistencia de calculo a
# tracao mora aqui; os 7 modulos que a calculavam a chamam, e a lente e o
# teste importam daqui. (Uma fonte so - regra do lote.)
# Rodado a mao/CI (python fctd_nbr6118_g136.py) e pelo teste-guarda
# tests/test_fctd_fonte_unica_g136.py. IMPORTADO pela producao
# (base_chumbador, estaca_profunda, fundacao_sapata, laje_concreto,
# pilar_concreto, viga_baldrame, viga_protendida) - por isso NAO e script
# avulso (ver test_alcancabilidade).
#
# O que foi MEDIDO (remedicao por AST + regex antes de mudar, 2026-09-13):
#   - A conta `0,7 * fctm / gamma_c` estava escrita em 7 sitios de
#     producao: base_chumbador:99 (`/ GC`, constante propria 1,40),
#     estaca_profunda:387, fundacao_sapata:683, laje_concreto:440,
#     pilar_concreto:440, viga_baldrame:46, viga_protendida:127 (as 6 com
#     o `1.4` literal que o backlog contou + a 7a via GC, mesmo numero).
#     Todas com o mesmo numero (o teste-guarda repete estes literais).
#   - A Tab. 12.1 da NBR 6118 foi lida na PAGINA RENDERIZADA da F016
#     (NBR 6118:2014, p. 71, 12.4.1): combinacoes normais gamma_c = 1,4 /
#     gamma_s = 1,15; especiais ou de construcao 1,2 / 1,15;
#     excepcionais 1,2 / 1,0 (convencao 3: substring -> parse ->
#     renderizar; ver o PNG em Temp/opencode/f016_tab121.png e o verbete
#     D163). O valor da combinacao normal (1,4) e o que as 7 copias
#     gravavam; nenhum caso do repo chama estes modulos em combinacao
#     que nao a normal (remedido nos chamadores: ancoragem_tirante,
#     comprimento_ancoragem, cortante_laje, verifica_cortante_pilar,
#     _verifica_cortante, verifica_cortante_protendida e
#     ancoragem_chumbador so aparecem em caminho ELU normal; nenhum
#     recebe gamma_c - dito no teste-guarda test_07).
#   - Unidades: dois jeitos de entrar e sair, sem divergencia de conta -
#     MPa -> MPa (estaca, fundacao, pilar, baldrame) e kN/m2 -> kN/m2
#     (base, laje, protendida), no mesmo molde da fonte do G127. A
#     primitiva kN/m2 deriva da MPa (`fctd_MPa(fck/1000) * 1000`),
#     nunca `fctk_inf(fck) / gamma_c`: a ordem trocada difere em 1 ulp
#     em C55 (medido; o teste-guarda test_06 prova o vermelho).
#
# Maquina: fctd_MPa (primitiva, MPa -> MPa, gamma_c como parametro com o
# normal por omissao) + fctd (kN/m2 -> kN/m2, mesmo miolo) +
# copias_fctd_fora_da_fonte/confere_copias (so a fonte pode conter o
# literal da conta; copia nova fora dela reprova) +
# arquivos_que_importam_fctd/confere_uso_fctd (os 7 chamam a fonte;
# leitura por conta propria ou nome morto reprova). A faixa do fck vive
# na fonte do G127 (a fctd deriva da fctk,inf dela); sem faixa propria
# (ver SEM_FAIXA_DECLARADA em varredura_faixa_validade).
#
# Nao fazer do goal: mudar o gamma_c de caso nenhum (todos os 7 chamam
# com a omissao = normal 1,4, numero bit a bit igual; o teste-guarda
# test_07 trava por AST que nenhum passa gamma_c).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - os corpos de `def _selftest` / `def test_*` nos *.py da raiz: os
#     asserts ali RECOMPUTAM a formula como prova independente
#     (anti-tautologia, G119; ex. estaca_profunda:672); a prova da
#     migracao mora no teste-guarda com literais escritos a mao;
#   - o miolo simbolico da 12.4.1/Tab. 12.1 na pagina (ver imagem F016
#     p. 71, citada acima);
#   - combinacoes especiais/excepcionais: o parametro existe e e
#     exercitado no teste-guarda, mas nenhum caso do repo o usa (todos
#     os chamadores sao ELU normal, medido acima).
# ============================================================================
"""fctd da NBR 6118 9.3.2/12.4.1 em fonte unica (G136): conta + portao."""

from __future__ import annotations

import ast
import pathlib
import re

import fctm_nbr6118_g127

GALPAO = pathlib.Path(__file__).resolve().parent

# Tab. 12.1 da NBR 6118:2014, 12.4.1 (ELU), lida na pagina renderizada da
# F016 (p. 71): combinacoes normais / especiais ou de construcao /
# excepcionais. O que as 7 copias gravavam e o da combinacao normal.
GAMMA_C_NORMAL = 1.4
GAMMA_C_ESPECIAL_CONSTRUCAO = 1.2
GAMMA_C_EXCEPCIONAL = 1.2

# Modulos de producao que calculam pela fonte unica (baseline nos dois
# sentidos em confere_uso_fctd: chamada nova sem triagem = leitura por
# conta propria; nome que some = nome morto). As 6 do backlog com o 1.4
# literal + base_chumbador, que usava a constante propria GC (= 1,40,
# mesmo numero; migrada junto para a fonte unica nao ter dois miolos).
MODULOS_VIA_FONTE = (
    "base_chumbador",
    "estaca_profunda",
    "fundacao_sapata",
    "laje_concreto",
    "pilar_concreto",
    "viga_baldrame",
    "viga_protendida",
)

# Arquivos que podem importar esta fonte unica (a fonte + os 7 leitores
# de producao). Baseline nos dois sentidos em confere_uso_fctd.
LEITORES_ESPERADOS = frozenset(
    {"fctd_nbr6118_g136.py"}
    | {m + ".py" for m in MODULOS_VIA_FONTE}
)

# O literal da conta (o mesmo das 7 copias; so a fonte o tem): 0,7 vezes
# um nome de fctm dividido pelo gamma (`1.4`, `GC`, `GAMMA_C*` ou
# `gamma_c*`), ou fctk,inf dividido pelo gamma (o desvio pela fonte do
# G127 com literal: mesma conta, fora da fonte). O nome tem de ser
# identificador (recompute numerico de selftest como `0.7 * 0.3 * ...`
# nao e copia de producao; e os corpos de _selftest/test_* estao fora
# da lente, dito no cabecalho).
RE_FCTD_COPIA = re.compile(
    r"0\.7\s*\*\s*[A-Za-z_]\w*\s*/\s*(1\.4|GC\b|GAMMA_C\w*|gamma_c\w*)"
    r"|fctk_inf\w*\s*\([^)]*\)\s*/\s*(1\.4|GC\b|GAMMA_C\w*|gamma_c\w*)")


def fctd_MPa(fck_MPa, gamma_c=GAMMA_C_NORMAL):
    """Resistencia de calculo a tracao fctd = fctk,inf / gamma_c (MPa).

    fctk,inf vem da fonte unica do G127 (8.2.5); gamma_c e o da Tab.
    12.1 (12.4.1), com a combinacao normal por omissao. A ordem e a das
    7 copias (`(0,7 * fctm) / gamma_c`), para o numero sair bit a bit.
    """
    return fctm_nbr6118_g127.fctk_inf_MPa(fck_MPa) / gamma_c


def fctd(fck, gamma_c=GAMMA_C_NORMAL):
    """Resistencia de calculo a tracao fctd (NBR 6118 9.3.2/12.4.1).

    fck em kN/m2 -> retorna kN/m2. Deriva da primitiva em MPa (mesmo
    molde do G127); a ordem `fctd_MPa(fck/1000) * 1000` e a das copias
    em kN/m2 (a ordem trocada difere em 1 ulp em C55, medido).
    """
    return fctd_MPa(fck / 1000.0, gamma_c) * 1000.0


def _linhas_producao(caminho):
    """[(n, codigo)] fora de comentario e fora de _selftest/test_*.

    Os corpos de selftest recomputam a formula como prova independente
    (dito no cabecalho); a lente mira a producao, o que o cliente
    recebe. Arquivo que nao compila: tudo e producao (estrito).
    """
    try:
        texto = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    try:
        arvore = ast.parse(texto, filename=str(caminho))
    except SyntaxError:
        arvore = None
    excluidas = set()
    if arvore is not None:
        for no in ast.walk(arvore):
            if (isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and (no.name == "_selftest"
                         or no.name.startswith("test_"))):
                excluidas.update(range(no.lineno,
                                       (no.end_lineno or no.lineno) + 1))
    saidas = []
    for i, linha in enumerate(texto.splitlines(), 1):
        if i not in excluidas:
            saidas.append((i, linha.split("#", 1)[0]))
    return saidas


def copias_fctd_fora_da_fonte(raiz=None):
    """Modulos com o literal da conta fora da fonte unica.

    Varre `*.py` da raiz (linhas de producao, ver _linhas_producao) e
    devolve {modulo: [linhas]} sem a fonte unica. Existe para o portao
    provar o vermelho num diretorio temporario sem mutar o repo.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = {}
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "fctd_nbr6118_g136.py":
            continue
        for i, codigo in _linhas_producao(caminho):
            if RE_FCTD_COPIA.search(codigo):
                achados.setdefault(caminho.stem, []).append(i)
    return achados


def fonte_tem_a_conta(raiz=None):
    """A fonte unica ainda contem o literal da conta? (contra remocao)."""
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    caminho = base / "fctd_nbr6118_g136.py"
    try:
        texto = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any(RE_FCTD_COPIA.search(ln.split("#", 1)[0])
               for ln in texto.splitlines())


def confere_copias(raiz=None):
    """Portao 'nenhuma copia fora da fonte'.

    OK so quando ha ZERO copias fora da fonte unica E a fonte contem a
    conta (baseline nos dois sentidos: copia nova = vermelho; conta
    apagada da fonte = vermelho). `copias` e `fonte_apagada` sao os
    acumuladores que o teste faz disparar.
    """
    copias = copias_fctd_fora_da_fonte(raiz)
    apagada = not fonte_tem_a_conta(raiz)
    return {"OK": not (copias or apagada), "copias": copias,
            "fonte_apagada": bool(apagada)}


def arquivos_que_importam_fctd(raiz=None):
    """Arquivos *.py da raiz que importam esta fonte unica (por AST, nunca
    por substring: o nome em mensagem de erro nao e dependencia).

    So raiz (nao tests/): teste que importa a fonte nao e conta de
    producao.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = set()
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "fctd_nbr6118_g136.py":
            achados.add(caminho.name)
            continue
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            arvore = ast.parse(texto, filename=str(caminho))
        except SyntaxError:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                if any((a.name or "").split(".")[0] == "fctd_nbr6118_g136"
                       for a in no.names):
                    achados.add(caminho.name)
                    break
            elif isinstance(no, ast.ImportFrom):
                if (no.module or "").split(".")[0] == "fctd_nbr6118_g136":
                    achados.add(caminho.name)
                    break
    return achados


def confere_uso_fctd(raiz=None, esperado=None):
    """Portao 'os 7 chamam a fonte; ninguem le por conta propria'.

    Compara quem importa a fonte unica com o baseline LEITORES_ESPERADOS
    nos dois sentidos: extra (chamada nova sem triagem) e faltando (nome
    morto) = vermelho. `extras`/`faltando` sao os acumuladores que o
    teste faz disparar.
    """
    esp = set(LEITORES_ESPERADOS) if esperado is None else set(esperado)
    tem = set(arquivos_que_importam_fctd(raiz))
    extras = sorted(tem - esp)
    faltando = sorted(esp - tem)
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    try:
        no_disco = {p.name for p in base.glob("*.py")}
    except OSError:
        no_disco = set(tem) | esp
    ausentes = sorted(a for a in esp if a not in no_disco)
    faltando = sorted(a for a in faltando if a not in ausentes)
    return {"OK": not (extras or faltando or ausentes),
            "extras": extras, "faltando": faltando, "ausentes": ausentes,
            "tem": sorted(tem)}


def main() -> int:
    for fck in (20.0, 50.0, 55.0, 60.0, 90.0):
        print("fck=%4.0f fctd=%.6f MPa (gamma_c normal %s)"
              % (fck, fctd_MPa(fck), GAMMA_C_NORMAL))
    c = confere_copias()
    print("copias fora da fonte=%r fonte_apagada=%s"
          % (c["copias"], c["fonte_apagada"]))
    u = confere_uso_fctd()
    print("uso OK=%s extras=%r faltando=%r" % (u["OK"], u["extras"],
                                              u["faltando"]))
    return 0 if (c["OK"] and u["OK"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
