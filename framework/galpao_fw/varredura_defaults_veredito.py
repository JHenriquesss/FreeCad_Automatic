# ============================================================================
# varredura_defaults_veredito.py - G75: OS DEFAULTS QUE MUDAM VEREDITO.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_defaults_veredito.py) e pelo teste-guarda
# tests/test_defaults_veredito_g75.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_descoberta.
#
# Motivacao (G75): um .get(chave, True) fazia uma parede reprovada passar.
# A nota "a" da Tab.9 troca o teto de esbeltez de 24 para 30 E o gamma de
# 2,0 para 3,0: he/te = 27 sai reprovado sem a nota e aprovado com ela - e
# estrutura_casa assumia habitacao_terrea=True por default (G61), depois
# n == 1 (G67), enquanto a primitiva defaultava False e o cabecalho do G60
# escrevia "opcao declarada, nunca silenciosa". A regra estava escrita e o
# codigo fazia o contrario. Nao e caso isolado por natureza: e um padrao de
# fronteira entre um modulo cuidadoso e o wrapper que o chama.
#
# Maquina: AST (mesma familia da do G48/G51, sem o vocabulario de faixa).
# Percorre os *.py do diretorio, acha chamadas X.get(chave, default) cuja
# chave esta em NORMATIVAS_G75 (opcoes normativas: as que aparecem como
# argumento de funcao de verificacao) e devolve uma linha por sitio, com o
# default normalizado ou OBRIGATORIO quando nao ha default (o padrao
# declara-ou-recusa: cfg.get(chave) is None -> raise nomeado).

# V2: tambem pega o resgate por `or` (cfg.get(chave) or padrao, cfg[chave]
# or padrao), com `via` = get|or em cada linha. Medido: 11 sitios `or` no
# galpao_fw, todos n_pavimentos/n_paineis nas camadas de gestao/BIM (a mesma
# triagem escrita do teste-guarda vale para as duas vias).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - chaves genericas de uma palavra (fyk, bloco, sistema, phi_mm,
#     d0_mm, n_cortes, espacamentos): aparecem em dezenas de modulos sem
#     parentesco e cada uma ja tem porta propria (G60/G66/G73 exigem as
#     partes declaradas; a verga dimensiona e emite na folha, ver triagem
#     no teste-guarda). Alargar a lente a elas custa ruido, como o "teto"
#     sozinho no G64.
#   - defaults de apresentacao (escala de desenho, casas decimais, nome de
#     arquivo): fora do escopo do G75 por declaracao do goal.
# ============================================================================
"""Varredura G75: defaults silenciosos em opcao normativa, sitio a sitio."""

from __future__ import annotations

import ast
import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent

# Opcoes normativas da fronteira casa/alvenaria/madeira/vento: as que
# aparecem como argumento de funcao de verificacao e cujo default
# silencioso no wrapper ja pagou (habitacao_terrea) ou pode pagar.
# Chave nova aqui entra com triagem escrita no teste-guarda; chave
# generica ou de apresentacao nao entra (ver motivo no cabecalho).
NORMATIVAS_G75 = frozenset({
    "habitacao_terrea",
    "combinacao",
    "material",
    "tipo_bloco",
    "s1",
    "s3",
    "forro_fragil",
    "revestimento_cm",
    "altura_m",
    "linhas",
    "n_pavimentos",
    "categoria",
    "n_paineis",
    "redutivel",
    "contraflecha_m",
    "limites_flecha",
    "z_m",
    "alpha_graus",
    "t2_mm",
    "fe2_Nmm2",
    "t_madeira_mm",
    "conifera",
    "penetracao_mm",
    "fa_MPa",
    "As_m2",
    "ranhurado",
    "apoio_m",
    "altura_verga_m",
})

OBRIGATORIO = "OBRIGATORIO"


def _repr_default(no):
    if no is None:
        return OBRIGATORIO
    try:
        return ast.unparse(no).strip()
    except Exception:
        return ast.dump(no)


def _chave_normativa(no):
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) \
            and no.func.attr == 'get':
        args = list(no.args)
        if args and isinstance(args[0], ast.Constant) and isinstance(
                args[0].value, str) and args[0].value in NORMATIVAS_G75:
            return args[0].value
    if isinstance(no, ast.Subscript) and isinstance(no.slice, ast.Constant) \
            and isinstance(no.slice.value, str) \
            and no.slice.value in NORMATIVAS_G75:
        return no.slice.value
    return None


def _mascarados_por_or(arvore):
    alvos = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.BoolOp) and isinstance(no.op, ast.Or):
            vals = list(no.values)
            if len(vals) >= 2 and _chave_normativa(vals[0]) is not None:
                for sub in ast.walk(vals[0]):
                    alvos.add(id(sub))
    return alvos


class _Visita(ast.NodeVisitor):
    def __init__(self, mascarados=None):
        self.sitios = []
        self.mascarados = mascarados or set()

    def visit_Call(self, no):
        if id(no) not in self.mascarados:
            func = no.func
            if isinstance(func, ast.Attribute) and func.attr == 'get':
                args = list(no.args)
                if args and isinstance(args[0], ast.Constant) and isinstance(
                        args[0].value, str):
                    chave = args[0].value
                    if chave in NORMATIVAS_G75:
                        default = _repr_default(args[1] if len(args) > 1 else None)
                        self.sitios.append({
                            'linha': int(getattr(no, 'lineno', 0) or 0),
                            'chave': chave,
                            'default': default,
                            'via': 'get',
                        })
        self.generic_visit(no)

    def visit_BoolOp(self, no):
        if isinstance(no.op, ast.Or):
            vals = list(no.values)
            if len(vals) >= 2:
                chave = _chave_normativa(vals[0])
                if chave is not None:
                    if len(vals) == 2:
                        resto = vals[1]
                    else:
                        resto = ast.BoolOp(op=ast.Or(), values=vals[1:])
                    self.sitios.append({
                        'linha': int(getattr(no, 'lineno', 0) or 0),
                        'chave': chave,
                        'default': _repr_default(resto),
                        'via': 'or',
                    })
        self.generic_visit(no)

def sitios_do_arquivo(caminho):
    """Todos os sitios .get(chave normativa) do arquivo, com defaults.

    Inclui o resgate por `or` (V2): `cfg.get(chave) or padrao` e
    `cfg[chave] or padrao` mascaram a ausencia do mesmo jeito que um
    default no .get - e mascaram ate o zero declarado (falso tambem
    cai no `or`). O .get sem default que vive como primeiro operando
    do `or` nao gera linha propria: ele esta representado pelo sitio
    `or`, que e o default efetivo.
    """
    arvd = ast.parse(pathlib.Path(caminho).read_text(
        encoding='utf-8-sig', errors='replace'))
    visita = _Visita(mascarados=_mascarados_por_or(arvd))
    visita.visit(arvd)
    return visita.sitios

def varredura(raiz=None):
    """Uma linha por sitio: {arquivo, linha, chave, default}."""
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = []
    for arq in sorted(base.glob("*.py")):
        for sitio in sitios_do_arquivo(arq):
            achados.append({"arquivo": arq.name,
                            "via": sitio["via"],
                            "linha": sitio["linha"],
                            "chave": sitio["chave"],
                            "default": sitio["default"]})
    return achados


def _selftest():
    linhas = varredura()
    assert isinstance(linhas, list) and linhas, "lente cega"
    assert all(set(d) == {"arquivo", "linha", "chave", "default", "via"}
               for d in linhas)
    assert {d["chave"] for d in linhas} <= NORMATIVAS_G75
    return {"n_sitios": len(linhas)}


if __name__ == "__main__":
    for item in varredura():
        print("%s:%s:%s=>%s [%s]" % (item["arquivo"], item["linha"],
                                item["chave"], item["default"], item["via"]))
