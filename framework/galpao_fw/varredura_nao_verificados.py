# ============================================================================
# varredura_nao_verificados.py - G33: O QUE E ANALISADO E NUNCA VERIFICADO.
# SCRIPT AVULSO: ferramenta de varredura rodada a mao/CI (python
# varredura_nao_verificados.py) e pelo teste-guarda
# tests/test_varredura_nao_verificados.py. Nao e importada por nenhum
# orquestrador do Loop - e declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de validacao/verificar_amostra.
# Antes de consertar a viga, procurar os irmaos. A ordem que funcionou no
# G6->G7: a varredura achou 21 ilhas, depois o G7 achou 9 bugs reais dentro
# delas. Aqui a classe e nitida e mecanizavel: elemento que recebe esforco
# solicitante CALCULADO e nunca passa por um cheque de resistencia.
#
# Cobertura: as tres tipologias (galpao, casa, edificio) e o mezanino, lidas
# pelos seus orquestradores rodar():
#   galpao   -> rodar_galpao.rodar + galpao_concreto.rodar
#   casa     -> estrutura_casa.rodar
#   edificio -> edificio_multipavimento.rodar
#   mezanino -> galpao_mezanino.rodar
#
# O que NAO entra na lista (declarado aqui para nao virar ilha por acidente):
#   - esforco que CHEGA a verificacao (mesmo que o gate seja frouxo): ex. a
#     reacao da viga que desce ao pilar e a fundacao; o V_w_k que chega ao
#     calice e a sapata; a envoltoria tapered que passa por chk.verifica por
#     segmento (o gate do quadro e outra discussao, nao esta classe).
#   - ausencia honesta (Ask-Do-Not-Invent): fundacao/baldrame/recalque nao
#     declarados saem not_available com o motivo, nao somem em silencio.
#   - carga que nunca e calculada como variavel do orquestrador (ex. reacao
#     da escada, que o modulo calcula por metro mas o rodar nunca soma aos
#     pilares): e omissao de caminho de carga, nao esforco calculado sem
#     cheque. Fica registrada como observacao no teste, fora da lista-guarda.
# ============================================================================
"""Varredura G33: pares (elemento, esforco calculado) sem cheque de resistencia."""

from __future__ import annotations

import ast
import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent

# Orquestradores varridos, por tipologia. Se uma tipologia ganhar um novo
# orquestrador, ele entra aqui - e o teste cobra a cobertura.
TIPOLOGIAS = {
    "galpao": ["rodar_galpao.py", "galpao_concreto.py"],
    "casa": ["estrutura_casa.py"],
    "edificio": ["edificio_multipavimento.py"],
    "mezanino": ["galpao_mezanino.py"],
}

# Lista-guarda: todo par (elemento, esforco) calculado e sem verificacao
# correspondente. Se a varredura achar um par novo, o teste fica vermelho.
# Se um par for CORRIGIDO (passar a ser verificado), atualize a lista e o
# teste - nunca o contrario.
# G34 FECHOU as 3 ilhas de viga do edificio (M_positivo/M_apoios/V_max passam
# por viga_concreto.verifica_viga por tramo via estrutura_casa.verifica_vigas,
# com M_d_neg da envoltoria). Elas SAIRAM da lista e NAO podem voltar em
# silencio: o teste-guia G34 trava a transicao.
NAO_VERIFICADOS = [
    {"tipologia": "galpao", "elemento": "pilar", "esforco": "V (cortante de base V_w_k do vento)",
     "onde_calculado": "galpao_concreto.rodar (V_w_k = w_h * H)",
     "trecho": "V_w_k",
     "cheque_ausente": "pilar_concreto.dimensiona_pilar nao recebe V (so N + M1d); o V chega ao calice e a sapata, nunca ao fuste"},
]

ESFORCOS_VIGA_EDIFICIO = ("M_positivo", "M_apoios", "V_max")


def _ast(caminho):
    return ast.parse(pathlib.Path(caminho).read_text(encoding="utf-8"))


def _rodar_no(arvore, nome="rodar"):
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == nome:
            return no
    return None


def _le_vigas_do_pav(no_rodar):
    """True se o rodar() le pav['vigas_x']/pav['vigas_y'] (ha esforco de viga em maos)."""
    for no in ast.walk(no_rodar):
        if isinstance(no, ast.Subscript):
            seg = ast.unparse(no) if hasattr(ast, "unparse") else ""
            if 'pav["vigas_x"]' in seg or "pav['vigas_x']" in seg:
                return True
            if 'pav["vigas_y"]' in seg or "pav['vigas_y']" in seg:
                return True
    return False


def _verifica_vigas_por_tramo(no_rodar, fonte):
    """True se o rodar() verifica CADA TRAMO contra a envoltoria.

    Conta: (a) helper verifica_vigas(pav, ...) - o padrao da casa; ou
    (b) laco sobre linha['vaos'] com verifica_viga/dimensiona_viga recebendo
    M_d/V_d da envoltoria. NAO conta o verifica_viga isolado da vibracao
    (um so vao L_v para o Anexo L), que nao consome pav['vigas_*'].
    """
    tem_laco_tramo = False
    for no in ast.walk(no_rodar):
        if isinstance(no, ast.Call):
            fn = no.func
            nome = fn.attr if isinstance(fn, ast.Attribute) else (
                fn.id if isinstance(fn, ast.Name) else "")
            if nome == "verifica_vigas":
                return True
    # padrao (b): verifica_viga dentro de laco sobre vaos da linha
    for no in ast.walk(no_rodar):
        if isinstance(no, (ast.For,)):
            corpo = ast.unparse(no) if hasattr(ast, "unparse") else ""
            if 'linha["vaos"]' in corpo and "verifica_viga" in corpo:
                tem_laco_tramo = True
    if tem_laco_tramo:
        return True
    # fallback textual preciso: a casa itera 'for k, L in enumerate(linha["vaos"])'
    # e chama vgc.verifica_viga com M_d/V_d; o edificio nao tem esse laco.
    if 'enumerate(linha["vaos"])' in fonte and "verifica_viga" in fonte:
        return True
    return False


def _arquivos_que_montam_pavimento():
    """Todo .py do pacote que monta pavimento-tipo (potencial produtor de viga)."""
    achados = []
    for p in sorted(GALPAO.glob("*.py")):
        try:
            src = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if "pavimento_tipo" in src and "monta(" in src:
            achados.append(p)
    return achados


def _pilar_concreto_aceita_cortante():
    """True se pilar_concreto.dimensiona_pilar passou a verificar cortante."""
    src = (GALPAO / "pilar_concreto.py").read_text(encoding="utf-8")
    arvore = ast.parse(src)
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == "dimensiona_pilar":
            corpo = ast.unparse(no) if hasattr(ast, "unparse") else ""
            if "cort" in corpo.lower() or "VRd" in corpo or "cisalh" in corpo.lower():
                return True
            # assinatura que recebe V/Vsd/V_d tambem conta como verificacao
            args = [a.arg for a in no.args.args] + [a.arg for a in no.args.kwonlyargs]
            if any(a in ("V", "Vsd", "V_d", "Vd", "Vsd_k") for a in args):
                return True
            return False
    return False


def _galpao_concreto_passa_V_ao_pilar():
    """True se galpao_concreto.rodar passou a entregar V ao pilar."""
    src = (GALPAO / "galpao_concreto.py").read_text(encoding="utf-8")
    return ("V_w_k" in src and "_dimensiona_pilar_secao" in src
            and "V_w_k" in src[src.find("def _dimensiona_pilar_secao"):
                               src.find("def _dimensiona_pilar_secao") + 3000])


def varredura():
    """Reexecuta a varredura e devolve a lista de ilhas encontradas.

    Cada ilha: {tipologia, elemento, esforco, arquivo, detalhe}. A ordem e
    estavel (por tipologia, elemento, esforco) para o teste comparar.
    """
    ilhas = []

    # --- regra 1: viga de pavimento-tipo analisada e nunca verificada ------
    for caminho in _arquivos_que_montam_pavimento():
        try:
            arvore = _ast(caminho)
        except SyntaxError:
            continue
        no = _rodar_no(arvore)
        if no is None:
            continue
        fonte = pathlib.Path(caminho).read_text(encoding="utf-8")
        if _le_vigas_do_pav(no) and not _verifica_vigas_por_tramo(no, fonte):
            tipologia = "edificio" if caminho.stem == "edificio_multipavimento" else caminho.stem
            for esforco in ESFORCOS_VIGA_EDIFICIO:
                ilhas.append({
                    "tipologia": tipologia, "elemento": "viga",
                    "esforco": esforco, "arquivo": caminho.name,
                    "detalhe": "pav['vigas_*'] lido sem verifica_vigas por tramo",
                })

    # --- regra 2: cortante do pilar do galpao de concreto -------------------
    try:
        src_gc = (GALPAO / "galpao_concreto.py").read_text(encoding="utf-8")
    except OSError:
        src_gc = ""
    if ("V_w_k" in src_gc and not _pilar_concreto_aceita_cortante()
            and not _galpao_concreto_passa_V_ao_pilar()):
        ilhas.append({
            "tipologia": "galpao", "elemento": "pilar",
            "esforco": "V (cortante de base V_w_k do vento)",
            "arquivo": "galpao_concreto.py",
            "detalhe": "V_w_k calculado e entregue ao calice/sapata, nunca ao fuste",
        })

    ilhas.sort(key=lambda d: (d["tipologia"], d["elemento"], d["esforco"]))
    return ilhas


def chaves_declaradas():
    return sorted((d["tipologia"], d["elemento"], d["esforco"])
                  for d in NAO_VERIFICADOS)


def chaves_varridas():
    return sorted((d["tipologia"], d["elemento"], d["esforco"])
                  for d in varredura())


def relatorio_pt():
    linhas = ["VARREDURA G33 - ANALISADO E NUNCA VERIFICADO",
              "tipologia | elemento | esforco -> cheque ausente"]
    for d in NAO_VERIFICADOS:
        linhas.append("  %-8s | %-8s | %s -> %s"
                     % (d["tipologia"], d["elemento"], d["esforco"],
                        d["cheque_ausente"][:90]))
    return "\n".join(linhas)


if __name__ == "__main__":
    print(relatorio_pt())
    print()
    for ilha in varredura():
        print("  ENCONTRADA: %(tipologia)s/%(elemento)s/%(esforco)s (%(arquivo)s)" % ilha)
