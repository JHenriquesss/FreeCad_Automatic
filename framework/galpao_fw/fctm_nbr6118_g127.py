# ============================================================================
# fctm_nbr6118_g127.py - G127: A FCT,M EM FONTE UNICA. PRODUCAO, NAO LENTE.
# MODULO DE PRODUCAO (fonte unica): a conta da resistencia media a tracao
# mora aqui; os 10 modulos que a calculavam a chamam, e a lente e o teste
# importam daqui. (Uma fonte so - regra do lote.)
# Rodado a mao/CI (python fctm_nbr6118_g127.py) e pelo teste-guarda
# tests/test_fctm_fonte_unica_g127.py. IMPORTADO pela producao
# (base_chumbador, estaca_profunda, fissuracao_nbr6118, fundacao_sapata,
# laje_concreto, pilar_concreto, piso_industrial, premoldado_nbr9062,
# viga_baldrame, viga_protendida) - por isso NAO e script avulso (ver
# test_alcancabilidade).
#
# O que foi MEDIDO (G125, remedido no G127 na funcao real, 2026-09-13):
#   - A expressao do ramo alto (`2,12 ln (1 + 0,11 fck)`) estava escrita em
#     11 linhas de 10 modulos: base_chumbador:99, estaca_profunda:388,
#     fissuracao_nbr6118:59, fundacao_sapata:681, laje_concreto:441,
#     pilar_concreto:407, piso_industrial:73, premoldado_nbr9062:125,
#     viga_baldrame:47,78, viga_protendida:70. Todas com o mesmo limiar
#     e o mesmo numero: fis/pm/vp devolvem 2210,4188991842316
#     kN/m2 em C20, 4071,626424892359 em C50, 4140,418547667256 em C55,
#     4299,674284259645 em C60 e 5064,177113178408 em C90 (medido antes da
#     migracao; o teste-guarda repete estes literais).
#   - Unidades: dois jeitos de entrar e sair, sem divergencia de conta -
#     MPa -> MPa (estaca, fundacao, piso) e kN/m2 -> kN/m2 (fissuracao,
#     premoldado, viga_protendida, viga_baldrame/flecha); os quatro
#     cortantes/ancoragens convertem no contorno (base, laje, pilar,
#     viga_baldrame/cortante). A fonte unica oferece as duas primitivas com
#     o mesmo miolo, e cada modulo usa a do seu sistema.
#   - As copias derivavam fctk,inf inline (`0,7 * fctm`, sem funcao propria;
#     nenhum sitio derivava fctk,sup). A fonte unica expoe fctk,inf/sup nas
#     duas unidades; o fctd (`fctk,inf / gamma_c`, de 9.3.2/17.4/19.4.1)
#     continua nos modulos, que e de outra clausula.
#
# Maquina: fctm_MPa (primitiva, MPa -> MPa) + fctm (kN/m2 -> kN/m2) +
# fctk_inf/sup nas duas unidades + copias_fctm_fora_da_fonte/confere_copias
# (so a fonte pode conter o literal da conta; copia nova fora dela reprova) +
# arquivos_que_importam_fctm/confere_uso_fctm (os 10 chamam a fonte; leitura
# por conta propria ou nome morto reprova). A faixa declarada e guardada e
# o limiar entre os ramos em fctm_MPa; o fckj jovem do icamento, abaixo
# de C20, usa a mesma expressao por extrapolacao declarada (travar a
# producao mudaria veredito de peca real: medido, fckj 13,74 MPa aos 3
# dias no galpao de concreto).
#
# Nao fazer do goal: a expressao e a da edicao 2014 declarada (a mesma que
# as 11 copias calculavam). Virar para a 2023 (`2,12 ln [1 + 0,1 (fck+8)]`)
# e decisao do usuario (G123); o teste-guarda prova que a 2023 nao entrou.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - o miolo simbolico da 8.2.5 na pagina (ver imagem F016 p.23 PDF41);
#   - a migracao para a 2023 (decisao do usuario, G123);
#   - o fctd de cada modulo (outra clausula, conta do chamador).
# ============================================================================
"""fct,m da NBR 6118 8.2.5 em fonte unica (G127): conta + faixas + portao."""

from __future__ import annotations

import ast
import math
import pathlib
import re

GALPAO = pathlib.Path(__file__).resolve().parent

# Limites da 8.2.5 (classes C20 a C90; o limiar entre os dois ramos).
# O icamento avalia fct,m no fckj jovem (ex.: 13,7 MPa aos 3 dias), abaixo
# de C20: a fonte unica aplica a mesma expressao (extrapolacao declarada
# do framework, numero inalterado) em vez de travar a producao.
FCK_LIMIAR_C50_MPA = 50.0

# Modulos de producao que calculam pela fonte unica (baseline nos dois
# sentidos em confere_uso_fctm: chamada nova sem triagem = leitura por
# conta propria; nome que some = nome morto).
MODULOS_VIA_FONTE = (
    "base_chumbador",
    "estaca_profunda",
    "fissuracao_nbr6118",
    "fundacao_sapata",
    "laje_concreto",
    "pilar_concreto",
    "piso_industrial",
    "premoldado_nbr9062",
    "viga_baldrame",
    "viga_protendida",
)

# Arquivos que podem importar esta fonte unica (a fonte + os 10 leitores
# de producao + a lente do G122, que importa o detector unico e a conta
# para o caso C5). Baseline nos dois sentidos em confere_uso_fctm.
LEITORES_ESPERADOS = frozenset(
    {"fctm_nbr6118_g127.py", "confronto_2014_2023_g122.py"}
    | {m + ".py" for m in MODULOS_VIA_FONTE}
)

# O literal da conta do ramo alto (o mesmo das 11 copias; so a fonte o
# tem). Mesma expressao da lente do G122 (`confronto_2014_2023_g122` a
# importa daqui para nao haver dois detectores divergindo).
RE_FCTM_C55 = re.compile(
    r"2\.12\s*\*\s*math\.log\(\s*1(?:\.0)?\s*\+\s*0\.11\s*\*")


def fctm_MPa(fck_MPa):
    """Resistencia media a tracao fct,m em MPa (NBR 6118 8.2.5, 2014).

    Faixa de validade: fck <= 50 MPa no ramo potenciado; acima do limiar,
    no ramo logaritmico. O fckj jovem do icamento, abaixo de C20, usa a
    mesma expressao (extrapolacao declarada, numero inalterado).
    """
    if fck_MPa <= FCK_LIMIAR_C50_MPA:
        return 0.3 * fck_MPa ** (2.0 / 3.0)
    return 2.12 * math.log(1.0 + 0.11 * fck_MPa)


def fctm(fck):
    """Resistencia media a tracao fct,m (NBR 6118 8.2.5, 2014).

    fck em kN/m2 -> retorna kN/m2. O mesmo miolo da primitiva em MPa.
    """
    return fctm_MPa(fck / 1000.0) * 1000.0


def fctk_inf_MPa(fck_MPa):
    """Valor caracteristico inferior fctk,inf = 0,7 fct,m (8.2.5). MPa."""
    return 0.7 * fctm_MPa(fck_MPa)


def fctk_sup_MPa(fck_MPa):
    """Valor caracteristico superior fctk,sup = 1,3 fct,m (8.2.5). MPa."""
    return 1.3 * fctm_MPa(fck_MPa)


def fctk_inf(fck):
    """fctk,inf em kN/m2 (fck em kN/m2)."""
    return fctk_inf_MPa(fck / 1000.0) * 1000.0


def fctk_sup(fck):
    """fctk,sup em kN/m2 (fck em kN/m2)."""
    return fctk_sup_MPa(fck / 1000.0) * 1000.0


def copias_fctm_fora_da_fonte(raiz=None):
    """Modulos com o literal da conta fora da fonte unica.

    Varre `*.py` da raiz (fora de comentario `#`; docstring conta como
    codigo, como na lente do G122) e devolve {modulo: [linhas]} sem a
    fonte unica. Existe para o portao provar o vermelho num diretorio
    temporario sem mutar o repo.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = {}
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "fctm_nbr6118_g127.py":
            continue
        if caminho.name == "confronto_2014_2023_g122.py":
            continue
        try:
            linhas = caminho.read_text(encoding="utf-8",
                                        errors="replace").splitlines()
        except OSError:
            continue
        for i, linha in enumerate(linhas, 1):
            codigo = linha.split("#", 1)[0]
            if RE_FCTM_C55.search(codigo):
                achados.setdefault(caminho.stem, []).append(i)
    return achados


def fonte_tem_a_conta(raiz=None):
    """A fonte unica ainda contem o literal da conta? (contra remocao)."""
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    caminho = base / "fctm_nbr6118_g127.py"
    try:
        texto = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any(RE_FCTM_C55.search(ln.split("#", 1)[0])
               for ln in texto.splitlines())


def confere_copias(raiz=None):
    """Portao 'nenhuma copia fora da fonte'.

    OK so quando ha ZERO copias fora da fonte unica E a fonte contem a
    conta (baseline nos dois sentidos: copia nova = vermelho; conta
    apagada da fonte = vermelho). `copias` e `fonte_apagada` sao os
    acumuladores que o teste faz disparar.
    """
    copias = copias_fctm_fora_da_fonte(raiz)
    apagada = not fonte_tem_a_conta(raiz)
    return {"OK": not (copias or apagada), "copias": copias,
            "fonte_apagada": bool(apagada)}


def arquivos_que_importam_fctm(raiz=None):
    """Arquivos *.py da raiz que importam esta fonte unica (por AST, nunca
    por substring: o nome em mensagem de erro nao e dependencia).

    So raiz (nao tests/): teste que importa a fonte nao e conta de
    producao.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = set()
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "fctm_nbr6118_g127.py":
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
                if any((a.name or "").split(".")[0] == "fctm_nbr6118_g127"
                       for a in no.names):
                    achados.add(caminho.name)
                    break
            elif isinstance(no, ast.ImportFrom):
                if (no.module or "").split(".")[0] == "fctm_nbr6118_g127":
                    achados.add(caminho.name)
                    break
    return achados


def confere_uso_fctm(raiz=None, esperado=None):
    """Portao 'os 10 chamam a fonte; ninguem le por conta propria'.

    Compara quem importa a fonte unica com o baseline LEITORES_ESPERADOS
    nos dois sentidos: extra (chamada nova sem triagem) e faltando (nome
    morto) = vermelho. `extras`/`faltando` sao os acumuladores que o
    teste faz disparar.
    """
    esp = set(LEITORES_ESPERADOS) if esperado is None else set(esperado)
    tem = set(arquivos_que_importam_fctm(raiz))
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
        print("fck=%4.0f fctm=%.6f MPa" % (fck, fctm_MPa(fck)))
    c = confere_copias()
    print("copias fora da fonte=%r fonte_apagada=%s"
          % (c["copias"], c["fonte_apagada"]))
    u = confere_uso_fctm()
    print("uso OK=%s extras=%r faltando=%r" % (u["OK"], u["extras"],
                                               u["faltando"]))
    return 0 if (c["OK"] and u["OK"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
