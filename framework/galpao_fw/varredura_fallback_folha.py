# ============================================================================
# varredura_fallback_folha.py - G145: OS 47 FALLBACKS or 0 / or 1 DOS EMISSORES.
# + G150: OS 64 .get(chave, 0/1) NOS EMISSORES + 3 DO ADAPTADOR DO MEZANINO.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_fallback_folha.py) e pelos testes-guardas
# tests/test_fallback_folha_g145.py (or) e tests/test_fallback_get_g150.py
# (.get). Nao e importada por nenhum orquestrador do Loop - declarada em
# SCRIPTS_AVULSOS no tests/test_alcancabilidade.py, no mesmo molde de
# varredura_faixa_validade.
# (Uma fonte so: as lentes e os testes importam daqui, nunca copiadas.)
#
# Motivacao (G145, auditoria D172): um `or 0` / `or 1` no emissor decide o
# DESENHO quando o dado falta. `int(N_hidrantes or 0) or 1` desenhava hidrante
# inventado quando o emissor do predio passou a receber o galpao (D172).
# Motivacao (G150, auditoria D176): o mesmo fallback escrito como
# `.get(chave, 0|0.0|1|1.0)` nao entra na lente do G145 (BoolOp Or). AST nos
# 10 emissores do G145 + techdraw_mezanino, techdraw_incendio, techdraw_concreto:
# 64 ocorrencias. A maquina e AST (nao grep): cada Call .get(chave, constante)
# com constante 0/0.0/1/1.0 nos 13 emissores. A classificacao e contra o
# PRODUTOR (convencao 9):
#   (a) MORTO - o produtor sempre entrega a chave (funcao + teste que garante);
#   (b) VIVO  - o dado pode faltar ou valer zero numa rodada real; a folha
#       DECLARA a ausencia em texto (nunca um numero) e o teste do goal cobre
#       ausente/zero/presente um por um (convencao 13).
# Os 3 do adaptador do mezanino entram na triagem pelo nome (nao sao achados
# pelo AST numerico puro): rp.get("hy"|"hx", mz.get(...)) em
# desenho_pavimento.adaptar_galpao_mezanino (o default externo e outra Call, nao
# constante) e mz.get("fyk", 500e3) em techdraw_mezanino.config_de_spec
# (constante fora de 0/1). Os 3 sao MORTOS hoje (D176 mediu fyk, hx, hy
# presentes no resultado do mezanino) com baseline que acusa quando o produtor
# mudar.
# Chave do baseline: (arquivo, funcao, expressao normalizada, fallback).
# Ocorrencias duplicadas na mesma funcao levam sufixo #2, #3 (ordem por linha):
# remover uma renumera a seguinte e o confere REPROVA nos dois sentidos -
# fails closed, pede retriagem escrita. Linha nao entra na chave (muda a cada
# edicao). Renomear para escapar nao adianta: a entrada vira resolvida e
# reprova (licao do G98).
# ============================================================================
"""Varredura G145+G150: fallbacks or 0/or 1 e .get(chave, 0/1) nos emissores."""

from __future__ import annotations

import ast
import pathlib
import re

GALPAO = pathlib.Path(__file__).resolve().parent

EU = "varredura_fallback_folha.py"

ALVOS = [
    "desenho_incendio.py",
    "desenho_fundacao_edificio.py",
    "desenho_escada_edificio.py",
    "desenho_alvenaria.py",
    "desenho_eletrico.py",
    "desenho_hidraulica.py",
    "desenho_coordenacao.py",
    "desenho_casa_residencial.py",
    "techdraw_eletrico.py",
    "desenho_pavimento.py",
]

# G150: os 10 do G145 + 3 (mezanino, incendio, concreto). O AST dos 13 com
# .get(chave, 0|0.0|1|1.0) acha 64 (D176). techdraw_mezanino/techdraw_incendio
# nao tem .get 0/1 (0 ocorrencias) mas entram no ALVO para congelar.
ALVOS_GET = sorted(set(ALVOS) | {
    "techdraw_mezanino.py",
    "techdraw_incendio.py",
    "techdraw_concreto.py",
})

_GET_FALLBACKS = (0, 0.0, 1, 1.0)

_FALLBACKS = (0, 0.0, 1, 1.0)


def _norm_expr(texto):
    """Normaliza o segmento fonte: colapsa whitespace para a chave estavel."""
    return re.sub(r"\s+", " ", (texto or "").strip())[:220]


def _func_dona(arvore, lineno):
    """Funcao de menor escopo que contem a linha (ou <modulo>)."""
    dona = None
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fim = getattr(no, "end_lineno", no.lineno)
            if no.lineno <= lineno <= fim:
                if dona is None or no.lineno >= dona.lineno:
                    dona = no
    return dona.name if dona is not None else "<modulo>"


def varredura(raiz=None):
    """Cada fallback or 0/or 1 nos emissores: [{arquivo, funcao, linha, coluna,
    expressao, fallback}]. Ordem estavel por (arquivo, linha, coluna).

    `raiz`: diretorio a varrer (default o proprio galpao_fw). Existe para o
    teste-guarda provar o VERMELHO num diretorio temporario sem mutar o repo.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = []
    alvos = sorted(p.name for p in base.glob("*.py") if p.name in ALVOS) if raiz is None else ALVOS
    for nome in alvos:
        caminho = base / nome
        if not caminho.is_file():
            continue
        if caminho.name == EU and raiz is None:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        try:
            arvore = ast.parse(texto)
        except SyntaxError:
            continue
        for no in ast.walk(arvore):
            if not isinstance(no, ast.BoolOp):
                continue
            if not isinstance(no.op, ast.Or):
                continue
            for val in no.values[1:]:
                if isinstance(val, ast.Constant) and val.value in _FALLBACKS and type(val.value) in (int, float):
                    # `or 0` vs `or False`: False == 0 em Python; exige int/float
                    # literal para nao acusar `or False` / `or None`.
                    if isinstance(val.value, bool):
                        continue
                    seg = ast.get_source_segment(texto, no) or ""
                    achados.append({
                        "arquivo": nome,
                        "funcao": _func_dona(arvore, getattr(no, "lineno", 1)),
                        "linha": getattr(no, "lineno", 1),
                        "coluna": getattr(no, "col_offset", 0),
                        "expressao": _norm_expr(seg),
                        "fallback": repr(val.value),
                    })
    achados.sort(key=lambda d: (d["arquivo"], d["linha"], d["coluna"]))
    return achados


def chaves(raiz=None):
    """Chaves estaveis (arquivo, funcao, expressao, fallback) com sufixo #k
    para duplicadas na mesma funcao (ordem por linha)."""
    tot = {}
    for d in varredura(raiz):
        bk = (d["arquivo"], d["funcao"], d["expressao"], d["fallback"])
        tot[bk] = tot.get(bk, 0) + 1
    final = []
    vista = {}
    for d in varredura(raiz):
        bk = (d["arquivo"], d["funcao"], d["expressao"], d["fallback"])
        if tot[bk] == 1:
            final.append(bk)
        else:
            k = vista.get(bk, 0) + 1
            vista[bk] = k
            final.append(bk + ("#%d" % k,))
    final.sort()
    return final


def _e_get_com_default_numerico(no):
    """True se Call x.get(chave, const) com const numerica 0/0.0/1/1.0.

    Exclui bool (True == 1 em Python) e default nao-constante (outra Call,
    Name, etc.). So o AST, nunca grep: `rp.get("hy", mz.get(...))` (default
    Call) nao entra aqui - vai para a triagem do adaptador pelo nome (G150).
    """
    if not isinstance(no, ast.Call):
        return None
    func = getattr(no, "func", None)
    if not (isinstance(func, ast.Attribute) and func.attr == "get"):
        return None
    if len(getattr(no, "args", [])) < 2:
        return None
    dflt = no.args[1]
    if not (isinstance(dflt, ast.Constant) and type(dflt.value) in (int, float)):
        return None
    if isinstance(dflt.value, bool):
        return None
    if dflt.value not in _GET_FALLBACKS:
        return None
    return repr(dflt.value)


def varredura_get(raiz=None):
    """Cada .get(chave, 0/1) nos 13 emissores (G150).

    Mesma forma da varredura do G145: [{arquivo, funcao, linha, coluna,
    expressao, fallback}], ordem estavel por (arquivo, linha, coluna).
    `raiz` existe para o teste-guarda provar o VERMELHO em tmp_path.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = []
    alvos = (sorted(p.name for p in base.glob("*.py") if p.name in ALVOS_GET)
             if raiz is None else list(ALVOS_GET))
    for nome in alvos:
        caminho = base / nome
        if not caminho.is_file():
            continue
        if caminho.name == EU and raiz is None:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        try:
            arvore = ast.parse(texto)
        except SyntaxError:
            continue
        for no in ast.walk(arvore):
            fb = _e_get_com_default_numerico(no)
            if fb is None:
                continue
            seg = ast.get_source_segment(texto, no) or ""
            achados.append({
                "arquivo": nome,
                "funcao": _func_dona(arvore, getattr(no, "lineno", 1)),
                "linha": getattr(no, "lineno", 1),
                "coluna": getattr(no, "col_offset", 0),
                "expressao": _norm_expr(seg),
                "fallback": fb,
            })
    achados.sort(key=lambda d: (d["arquivo"], d["linha"], d["coluna"]))
    return achados


def chaves_get(raiz=None):
    """Chaves estaveis do G150 (mesmo esquema do G145, sufixo #k)."""
    tot = {}
    for d in varredura_get(raiz):
        bk = (d["arquivo"], d["funcao"], d["expressao"], d["fallback"])
        tot[bk] = tot.get(bk, 0) + 1
    final = []
    vista = {}
    for d in varredura_get(raiz):
        bk = (d["arquivo"], d["funcao"], d["expressao"], d["fallback"])
        if tot[bk] == 1:
            final.append(bk)
        else:
            k = vista.get(bk, 0) + 1
            vista[bk] = k
            final.append(bk + ("#%d" % k,))
    final.sort()
    return final


# ---------------------------------------------------------------------------
# FALLBACKS_TRIADOS (G145). Cada fallback ou esta aqui, com destino, motivo e
# produtor - ou a suite fica vermelha. Destinos:
#   MORTO - o produtor sempre entrega a chave (prova: funcao + teste que
#           garante); o fallback nunca decide desenho em rodada real.
#   VIVO  - o dado pode faltar ou valer zero; a folha DECLARA a ausencia em
#           texto (nunca numero) e o teste do goal cobre ausente/zero/presente.
# Entrada com motivo vazio reprova (sem_motivo); com produtor vazio reprova
# (sem_produtor); triado que sumiu vira resolvida e reprova (nome morto).
# ---------------------------------------------------------------------------
FALLBACKS_TRIADOS = {
    # --- desenho_incendio.py: guardas geometricas (MORTO) ---
    ("desenho_incendio.py", "_sym_seta_rota", "math.hypot(dx, dy) or 1.0", "1.0"): (
        "MORTO",
        "guarda aritmetica anti-divisao-zero: so dispara com vetor (dx,dy)=(0,0); "
        "produtor = args da chamada, sempre presentes; nunca dado ausente.",
        "desenho_incendio.py:48-51 (_sym_seta_rota); prova: test_fallback_folha_g145 guarda-geometrica"),
    ("desenho_incendio.py", "_pontos_perimetro", "2.0 * (pw + ph) or 1.0", "1.0"): (
        "MORTO",
        "guarda aritmetica: perimetro degenerado (pw=ph=0) evita divisao por zero; "
        "produtor = geometria do canvas, sempre presente.",
        "desenho_incendio.py:149-156 (_pontos_perimetro); prova: test_fallback_folha_g145 guarda-geometrica"),
    # --- desenho_incendio.py: VIVOS (D172 + reserva/populacao) ---
    ("desenho_incendio.py", "detalhes_hidrantes_rotas_svg", "n_decl or 0", "0"): (
        "VIVO",
        "N_hidrantes pode ser None (galpao sem hidrantes no spec; predio sem "
        "hidrantes: incendio_edificio.py:642-643 hidr=None); a folha declara "
        "'hidrantes nao calculados' e desenha 0 simbolos.",
        "galpao_seguranca_incendio.py:128; incendio_edificio.py:642-663; prova: test_fallback_folha_g145 ausente/zero/presente"),
    ("desenho_incendio.py", "detalhes_hidrantes_rotas_svg", "int(n_decl or 0) or 1", "1"): (
        "VIVO",
        "o `or 1` desenhava HID-1 inventado com N=None (D172); corrigido nos "
        "dois ramos (nivel_unico + predio): None vira texto declarado + 0 "
        "simbolos; 0 vira 0 simbolos; presente vira N.",
        "galpao_seguranca_incendio.py:128 (None); prova: test_fallback_folha_g145 ausente/zero/presente"),
    # FIXOS no G145 (fallback removido, declaracao em texto + teste congela):
    # - detalhes_hidrantes_rotas_svg `reserva or 0` -> `None => 'nao calculada'`
    # - detalhes_hidrantes_rotas_svg `inc.get("populacao_total") or 0` -> `None => 'nao calculada'`
    # - planta_pavimento_edificio_svg `hid.get("N_hidrantes") or 0` -> `_hid_raw is None => 'nao dimensionados'`
    ("desenho_incendio.py", "planta_seguranca_svg", 'g["hidrantes"]["N_hidrantes"] or 0', "0"): (
        "VIVO",
        "galpao sem hidrantes => gates.hidrantes.N_hidrantes=None "
        "(galpao_seguranca_incendio.py:128); a folha declara 'Hidrantes: nao "
        "calculados' no RESUMO e omite o simbolo da legenda.",
        "galpao_seguranca_incendio.py:122-130; prova: test_fallback_folha_g145 ausente/zero/presente"),
    # --- desenho_incendio.py: MORTOS (produtor sempre entrega) ---
    ("desenho_incendio.py", "planta_pavimento_edificio_svg", 'det.get("N_detectores") or 0', "0"): (
        "MORTO",
        "alarme sempre dimensionado (incendio_edificio.py:637-640 da.dimensiona); "
        "N_detectores sempre int; fallback nunca dispara em rodada real.",
        "incendio_edificio.py:637-640; deteccao_alarme_nbr17240.py:105; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_incendio.py", "planta_pavimento_edificio_svg", 'det.get("N_acionadores") or 0', "0"): (
        "MORTO",
        "idem N_detectores: alarme sempre dimensionado, N_acionadores sempre int.",
        "incendio_edificio.py:637-640; deteccao_alarme_nbr17240.py:106; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_incendio.py", "planta_pavimento_edificio_svg", 'sin.get("N_total") or 0', "0"): (
        "MORTO",
        "sinalizacao sempre dimensionada (incendio_edificio.py:633-635); N_total sempre int.",
        "incendio_edificio.py:633-635; sinalizacao_nbr16820.py:125; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_incendio.py", "planta_pavimento_edificio_svg", 'ilu.get("N_aclaramento") or 0', "0", "#1"): (
        "MORTO",
        "iluminacao sempre dimensionada (incendio_edificio.py:629-631); N_aclaramento "
        "sempre int; duas ocorrencias na mesma funcao (loop + resumo).",
        "incendio_edificio.py:629-631; iluminacao_emergencia_nbr10898.py:107; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_incendio.py", "planta_pavimento_edificio_svg", 'ilu.get("N_aclaramento") or 0', "0", "#2"): (
        "MORTO",
        "segunda ocorrencia (resumo) do mesmo produtor sempre-presente; ver #1.",
        "incendio_edificio.py:629-631; iluminacao_emergencia_nbr10898.py:107; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_incendio.py", "planta_pavimento_edificio_svg", 'inc.get("populacao_total") or 0', "0"): (
        "MORTO",
        "predio sempre produz populacao_total (incendio_edificio.py:945 pop_total); "
        "o VIVO e o irmao de detalhes_hidrantes (galpao, None).",
        "incendio_edificio.py:944-945; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_incendio.py", "planta_seguranca_svg", 'g["iluminacao_emergencia"]["N_aclaramento"] or 0', "0"): (
        "MORTO",
        "galpao sempre dimensiona iluminacao (galpao_seguranca_incendio.rodar); "
        "N_aclaramento sempre int; [] indica presenca obrigatoria (KeyError se sumir).",
        "galpao_seguranca_incendio.py:105; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_incendio.py", "planta_seguranca_svg", 'g["iluminacao_emergencia"]["N_balizamento"] or 0', "0"): (
        "MORTO",
        "idem N_aclaramento: N_balizamento sempre int no gate do galpao.",
        "galpao_seguranca_incendio.py:106; prova: test_fallback_folha_g145 mortos-produzem"),
    # --- desenho_fundacao_edificio.py: MORTOS (ramo guardado + produtor garante) ---
    ("desenho_fundacao_edificio.py", "_geometria_desenho", "h or 0.0", "0.0"): (
        "MORTO",
        "h = g.get('h_m'); sapata sempre produz h_m (fundacao_edificio.py:357); "
        "ausente vira 0.0 no float() do ramo sapata, nunca desenho inventado.",
        "fundacao_edificio.py:357; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'g.get("n_estacas") or 0', "0", "#1"): (
        "MORTO",
        "ramo guardado por 'n_estacas' in g (planta_fundacao_svg:310,69-70); "
        "estaca sempre produz n_estacas int (fundacao_edificio.py:429).",
        "fundacao_edificio.py:429; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'g.get("n_estacas") or 0', "0", "#2"): (
        "MORTO",
        "segunda ocorrencia (quadro) do mesmo ramo guardado; ver #1.",
        "fundacao_edificio.py:429; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'g.get("D_m") or 0.0', "0.0"): (
        "MORTO",
        "estaca sempre produz D_m (fundacao_edificio.py:430 capacidade.D); "
        "ramo estaca; fallback nunca dispara.",
        "fundacao_edificio.py:429-430; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'g.get("D_m") or 0', "0"): (
        "MORTO",
        "ocorrencia do quadro (D*100) do mesmo produtor; ver anterior.",
        "fundacao_edificio.py:429-430; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'g.get("L_m") or 0.0', "0.0"): (
        "MORTO",
        "estaca sempre produz L_m (fundacao_edificio.py:430); ramo estaca.",
        "fundacao_edificio.py:429-430; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'g.get("L_m") or 0', "0"): (
        "MORTO",
        "ocorrencia do quadro do mesmo produtor; ver anterior.",
        "fundacao_edificio.py:429-430; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'g.get("h_m") or 0', "0"): (
        "MORTO",
        "sapata sempre produz h_m (fundacao_edificio.py:357); ramo B_m is not None.",
        "fundacao_edificio.py:357; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "adaptar_galpao_para_locacao", 'est.get("N_pilar", 0.0) or 0.0', "0.0"): (
        "MORTO",
        "G145: morto hoje - estaca do galpao sempre entrega N_pilar "
        "(galpao_concreto.py:367 N_base); congela para acusar se o produtor mudar.",
        "galpao_concreto.py:367; fundacao_edificio.py:406; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "adaptar_galpao_para_locacao", 'cap.get("D", 0.0) or 0.0', "0.0"): (
        "MORTO",
        "G145: morto hoje - capacidade da estaca sempre entrega D "
        "(fundacao_edificio.py:403 default 0.30); congela.",
        "fundacao_edificio.py:403; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "adaptar_galpao_para_locacao", 'cap.get("L", 0.0) or 0.0', "0.0"): (
        "MORTO",
        "G145: morto hoje - capacidade sempre entrega L (fundacao_edificio.py:404); congela.",
        "fundacao_edificio.py:404; prova: test_fallback_folha_g145 mortos-produzem"),
    # --- desenho_escada_edificio.py ---
    ("desenho_escada_edificio.py", "planta_escada_svg", '_num(escada.get("patamar_m"), 0.0) or 0.0', "0.0"): (
        "MORTO",
        "escada_concreto sempre produz patamar_m (escada_concreto.py:235); "
        "0.0 legitimo (sem patamar) == fallback; nunca esconde ausencia.",
        "escada_concreto.py:235; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_escada_edificio.py", "planta_escada_svg", "largura or 0.0", "0.0"): (
        "MORTO",
        "largura = _num(escada.get('largura_m')); produtor sempre entrega "
        "largura_m (escada_concreto.py:234); escala usa max() em seguida.",
        "escada_concreto.py:234; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_escada_edificio.py", "planta_escada_svg", "largura or 1.0", "1.0"): (
        "MORTO",
        "guarda de escala (max(largura or 1.0, 1e-9)): so dispara com largura "
        "degenerada; produtor sempre presente.",
        "escada_concreto.py:234; prova: test_fallback_folha_g145 guarda-geometrica"),
    ("desenho_escada_edificio.py", "confere_desenho_escada", 'geo.get("n_degraus") or 0', "0"): (
        "MORTO",
        "funcao de conferencia (nao decide desenho): n_esperado para diagnostico; "
        "geometria sempre produz n_degraus (escada_concreto.py:85).",
        "escada_concreto.py:85; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_escada_edificio.py", "confere_desenho_escada", 'escada.get("patamar_m") or 0.0', "0.0"): (
        "MORTO",
        "funcao de conferencia (nao decide desenho); produtor sempre entrega.",
        "escada_concreto.py:235; prova: test_fallback_folha_g145 mortos-produzem"),
    # --- desenho_alvenaria.py ---
    ("desenho_alvenaria.py", "confere_vergas", 'r.get("data-verga-comp", 0.0) or 0.0', "0.0"): (
        "MORTO",
        "funcao de conferencia drawing-vs-data (nao decide desenho); o float() "
        "compara desenho x calculo para diagnostico.",
        "desenho_alvenaria.py:363-368; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_alvenaria.py", "confere_vergas", 'r.get("data-verga-h", 0.0) or 0.0', "0.0"): (
        "MORTO",
        "idem: conferencia, nao desenho.",
        "desenho_alvenaria.py:363-368; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_alvenaria.py", "confere_vergas", 'r.get("data-contraverga-comp", 0.0) or 0.0', "0.0"): (
        "MORTO",
        "idem: conferencia, nao desenho.",
        "desenho_alvenaria.py:367-368; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_alvenaria.py", "gerar_pranchas_alvenaria", 'estrutura.get("n_pavimentos") or 1', "1"): (
        "MORTO",
        "pe = H_total/max(n_pav,1); estrutura do predio sempre produz n_pavimentos "
        "(edificio_multipavimento.py:343); max() blinda o degenerado.",
        "edificio_multipavimento.py:343; prova: test_fallback_folha_g145 mortos-produzem"),
    # --- desenho_eletrico.py ---
    ("desenho_eletrico.py", "diagrama_prumada_edificio_svg", 'ele.get("pavimentos_servidos") or 0', "0"): (
        "MORTO",
        "recusa nomeada: int(...or 0) e `if n<1: raise ValueError('eletrica sem "
        "pavimentos servidos')`; ausencia nunca desenha silencioso. Produtor "
        "sempre int>=1 (eletrica_edificio.py:587-594).",
        "eletrica_edificio.py:587-594; desenho_eletrico.py:349-351; prova: test_fallback_folha_g145 recusa-nomeada"),
    ("desenho_eletrico.py", "infra_aterramento_edificio_svg", 'ele.get("pavimentos_servidos") or 0', "0"): (
        "MORTO",
        "idem: recusa nomeada antes de desenhar (infra:442-444).",
        "eletrica_edificio.py:587-594; desenho_eletrico.py:442-444; prova: test_fallback_folha_g145 recusa-nomeada"),
    ("desenho_eletrico.py", "qdc_edificio_svg", 'ele.get("pavimentos_servidos") or 0', "0"): (
        "MORTO",
        "idem: recusa nomeada (qdc:475-477).",
        "eletrica_edificio.py:587-594; desenho_eletrico.py:475-477; prova: test_fallback_folha_g145 recusa-nomeada"),
    ("desenho_eletrico.py", "planta_eletrica_pavimento_svg", 'ele.get("carga_areas_comuns_VA") or 0', "0"): (
        "MORTO",
        "produtor sempre entrega float (eletrica_edificio.py:598 get or 0.0); "
        "legenda 'carga comum: %.0f VA' com 0 legitimo quando sem areas comuns.",
        "eletrica_edificio.py:598; prova: test_fallback_folha_g145 mortos-produzem"),
    # --- desenho_hidraulica.py (produtor sempre entrega) ---
    ("desenho_hidraulica.py", "planta_rede_edificio_svg", 'hid.get("pavimentos_servidos") or 0', "0"): (
        "MORTO",
        "servidos sempre int (hidraulica_edificio.py:390-395, deriva do contexto "
        "quando ausente no spec); compoe o `or 1` abaixo, tambem morto.",
        "hidraulica_edificio.py:390-395; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_hidraulica.py", "planta_rede_edificio_svg", 'int(hid.get("pavimentos_servidos") or 0) or 1', "1"): (
        "MORTO",
        "servidos>=1 sempre (mesmo produtor); o `or 1` nunca dispara; n so conta "
        "pavimentos para escala do corte, nunca inventa equipamento.",
        "hidraulica_edificio.py:390-395; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_hidraulica.py", "planta_rede_edificio_svg", '(hid.get("reservacao") or {}).get("total_L") or 0', "0"): (
        "MORTO",
        "_reservacao sempre devolve total_L (hidraulica_edificio.py:399); "
        "legenda 'RESERVACAO %.0f L' com produtor garantido.",
        "hidraulica_edificio.py:399; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_hidraulica.py", "planta_rede_edificio_svg", 'plv.get("n_descidas") or 1', "1"): (
        "MORTO",
        "n_descidas>=1 sempre (hidraulica_edificio.py:342-344 default 1 + raise "
        "se <1); o `or 1` nunca dispara em rodada real.",
        "hidraulica_edificio.py:342-344; prova: test_fallback_folha_g145 mortos-produzem"),
    # --- desenho_coordenacao.py / casa / techdraw / pavimento ---
    ("desenho_coordenacao.py", "_projecao", "(hi[ejx] - lo[ejx]) or 1.0", "1.0"): (
        "MORTO",
        "guarda de escala do bbox (evita divisao por zero em frame degenerado); "
        "produtor = bbox global, sempre presente.",
        "desenho_coordenacao.py:80-86; prova: test_fallback_folha_g145 guarda-geometrica"),
    ("desenho_coordenacao.py", "_projecao", "(hi[ejy] - lo[ejy]) or 1.0", "1.0"): (
        "MORTO",
        "idem eixo Y.",
        "desenho_coordenacao.py:80-86; prova: test_fallback_folha_g145 guarda-geometrica"),
    ("desenho_casa_residencial.py", "conferencia_svg", '(conferencia.get("totais") or {}).get("pontos_orfaos") or 0', "0"): (
        "MORTO",
        "conferencia sempre produz totais.pontos_orfaos (casa_residencial.py:238); "
        "0 omite o aviso (correto: sem orfaos, sem texto).",
        "casa_residencial.py:238; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_casa_residencial.py", "armacao_vigas_pilares_casa_svg", 'vigas.get("n_tramos") or 0', "0"): (
        "MORTO",
        "vigas da casa sempre produz n_tramos (estrutura_casa.py:421); titulo "
        "'%d tramos VERIFICADOS' com produtor garantido.",
        "estrutura_casa.py:421; prova: test_fallback_folha_g145 mortos-produzem"),
    ("desenho_pavimento.py", "_dados_vigas", '(vigas_verificacao or {}).get("n_tramos") or 0', "0"): (
        "MORTO",
        "vigas_verificacao sempre produz n_tramos (viga_continua.py:435; "
        "edificio_multipavimento.py:623); {} vazio => 0 linhas (correto).",
        "viga_continua.py:435; prova: test_fallback_folha_g145 mortos-produzem"),
    ("techdraw_eletrico.py", "config_de_spec", 'd["queda_pct"] or 0.0', "0.0"): (
        "MORTO",
        "projeto_instalacao sempre produz queda_pct (instalacao_eletrica.py:175 "
        "cond.dv_pct); 0.0 legitimo (queda nula) == fallback.",
        "instalacao_eletrica.py:175; prova: test_fallback_folha_g145 mortos-produzem"),
}


def confere(raiz=None, triados=None):
    """Guarda G145 em forma chamavel: fallbacks nao triados vs triagem."""
    tri = FALLBACKS_TRIADOS if triados is None else triados
    vivas = set(chaves(raiz))
    novas = sorted(k for k in vivas if k not in (tri or {}))
    no_disco = {p.name for p in (pathlib.Path(raiz) if raiz is not None else GALPAO).glob("*.py")}
    resolvidas = sorted(k for k in (tri or {}) if k[0] in no_disco and k not in vivas)
    sem_motivo = sorted(k for k, v in (tri or {}).items() if len(v) < 2 or not (v[1] or "").strip())
    sem_produtor = sorted(k for k, v in (tri or {}).items() if len(v) < 3 or not (v[2] or "").strip())
    ausentes = sorted(k for k in (tri or {}) if k[0] not in no_disco)
    return {"OK": not (novas or resolvidas or sem_motivo or sem_produtor or ausentes),
            "novas": novas, "resolvidas": resolvidas,
            "sem_motivo": sem_motivo, "sem_produtor": sem_produtor,
            "ausentes": ausentes}


def relatorio_pt(res=None):
    res = confere() if res is None else res
    linhas = ["VARREDURA G145 - FALLBACKS DE FOLHA"]
    for lado in ("novas", "resolvidas", "sem_motivo", "sem_produtor", "ausentes"):
        linhas.append("  [%s] %d" % (lado, len(res.get(lado) or [])))
        for k in (res.get(lado) or []):
            linhas.append("    %-12s %s" % (lado, " :: ".join(str(x) for x in k)))
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# GETS_TRIADOS (G150). Os 64 .get(chave, 0/1) + triagem MORTO/VIVO.
# Todos os 64 sao MORTOS (medido no G150): o produtor sempre entrega a chave
# em rodada real; o fallback nunca decide desenho. Prova por grupo no
# tests/test_fallback_get_g150.py (rodada real minima por produtor + presenca
# textual da chave no fonte citado). Nenhum VIVO: nenhuma folha precisou
# declarar ausencia nova (predio e casa byte-identicos; sem PNG de cura).
# ---------------------------------------------------------------------------
GETS_TRIADOS = {
    ("desenho_alvenaria.py", "_painel_elevacao", 'reg.get("N_wall_d_kN", 0.0)', "0.0"): (
        "MORTO",
        "parede sempre produz N_wall_d_kN (estrutura_casa.py:1091,1437); "
        "elevacao so formata o numero do calculo.",
        "estrutura_casa.py:1091; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_alvenaria.py", "confere_vergas", 'd.get("comprimento_m", 0.0)', "0.0"): (
        "MORTO",
        "conferencia drawing-vs-data (nao decide desenho); detalhe sempre "
        "produz comprimento_m (alvenaria_estrutural.py:1325,1567).",
        "alvenaria_estrutural.py:1325; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_alvenaria.py", "confere_vergas", 'g.get("altura_verga_m", 0.0)', "0.0"): (
        "MORTO",
        "conferencia, nao desenho; verga sempre produz altura_verga_m "
        "(alvenaria_estrutural.py:1451,1479).",
        "alvenaria_estrutural.py:1451; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_alvenaria.py", "confere_vergas", 'g.get("comprimento_peca_m", 0.0)', "0.0"): (
        "MORTO",
        "conferencia, nao desenho; produtor sempre entrega comprimento_peca_m "
        "(alvenaria_estrutural.py:1449,1477).",
        "alvenaria_estrutural.py:1449; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_alvenaria.py", "confere_vergas", 'r.get("data-contraverga-comp", 0.0)', "0.0"): (
        "MORTO",
        "conferencia drawing-vs-data (G145 irmao data-verga); o float compara "
        "desenho x calculo para diagnostico, nunca numero na folha.",
        "desenho_alvenaria.py:363-368; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_alvenaria.py", "confere_vergas", 'r.get("data-verga-comp", 0.0)', "0.0"): (
        "MORTO",
        "conferencia, nao desenho (irmao G145).",
        "desenho_alvenaria.py:363-368; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_alvenaria.py", "confere_vergas", 'r.get("data-verga-h", 0.0)', "0.0"): (
        "MORTO",
        "conferencia, nao desenho (irmao G145).",
        "desenho_alvenaria.py:363-368; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_alvenaria.py", "gerar_pranchas_alvenaria", 'estrutura.get("H_total_m", 0.0)', "0.0"): (
        "MORTO",
        "estrutura do predio/casa sempre produz H_total_m "
        "(edificio_multipavimento.py:536; estrutura_casa.py:2311).",
        "edificio_multipavimento.py:536; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", '(telhado.get("descida") or {}).get( "reacao_por_tesoura_kN", {}).get("G_kN", 0.0)', "0.0"): (
        "MORTO",
        "telhado sempre produz descida.reacao_por_tesoura_kN.G_kN "
        "(telhado_casa_madeira.py:1123,1206); {} vazio so em uso avulso.",
        "telhado_casa_madeira.py:1123; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", '(telhado.get("descida") or {}).get( "reacao_por_tesoura_kN", {}).get("Q_kN", 0.0)', "0.0"): (
        "MORTO",
        "idem G_kN: Q_kN sempre presente no mesmo produtor.",
        "telhado_casa_madeira.py:1123; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'arr.get("L_kN", 0.0)', "0.0"): (
        "MORTO",
        "arrancamento so lido no ramo vento_ativo; produtor sempre entrega L/R "
        "quando ha vento (telhado_casa_madeira.py:1140-1141).",
        "telhado_casa_madeira.py:1140; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'arr.get("R_kN", 0.0)', "0.0"): (
        "MORTO",
        "idem L_kN, mesmo produtor e ramo.",
        "telhado_casa_madeira.py:1141; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'contra_folha.get("F1d_kN", 0.0)', "0.0"): (
        "MORTO",
        "contraventamento 6.6 sempre produz F1d (telhado_casa_madeira.py:1099; "
        "madeira_nbr7190.py:451).",
        "telhado_casa_madeira.py:1099; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'contra_folha.get("Fd_extremidade_kN", 0.0)', "0.0"): (
        "MORTO",
        "idem: Fd sempre presente (telhado_casa_madeira.py:1100).",
        "telhado_casa_madeira.py:1100; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'contra_folha.get("Kbrmin_kN_m", 0.0)', "0.0"): (
        "MORTO",
        "idem: Kbrmin sempre presente (telhado_casa_madeira.py:1107).",
        "telhado_casa_madeira.py:1107; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'contra_folha.get("Nd_governante_kN", 0.0)', "0.0"): (
        "MORTO",
        "idem: Nd_governante sempre presente (telhado_casa_madeira.py:1098).",
        "telhado_casa_madeira.py:1098; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'peca.get("L_por_tesoura_m", 0)', "0"): (
        "MORTO",
        "romaneio sempre produz L_por_tesoura_m por peca "
        "(telhado_casa_madeira.py:1046,1053).",
        "telhado_casa_madeira.py:1046; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'peca.get("b_m", 0)', "0"): (
        "MORTO",
        "peca sempre produz b_m/h_m (telhado_casa_madeira.py:1045).",
        "telhado_casa_madeira.py:1045; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'peca.get("h_m", 0)', "0"): (
        "MORTO",
        "idem b_m, mesmo produtor.",
        "telhado_casa_madeira.py:1045; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'peca.get("vol_por_tesoura_m3", 0)', "0"): (
        "MORTO",
        "idem: vol sempre presente (telhado_casa_madeira.py:1048).",
        "telhado_casa_madeira.py:1048; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'telhado.get("n_tesouras", 0)', "0", "#1"): (
        "MORTO",
        "telhado sempre produz n_tesouras (telhado_casa_madeira.py:1095,1206); "
        "tres ocorrencias na mesma funcao (legenda + contraventamento + volume).",
        "telhado_casa_madeira.py:1095; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'telhado.get("n_tesouras", 0)', "0", "#2"): (
        "MORTO",
        "segunda ocorrencia do mesmo produtor; ver #1.",
        "telhado_casa_madeira.py:1095; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'telhado.get("n_tesouras", 0)', "0", "#3"): (
        "MORTO",
        "terceira ocorrencia do mesmo produtor; ver #1.",
        "telhado_casa_madeira.py:1095; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_casa_residencial.py", "telhado_tesoura_svg", 'telhado.get("vao_m", 0.0)', "0.0"): (
        "MORTO",
        "telhado sempre produz vao_m (telhado_casa_madeira.py:1178).",
        "telhado_casa_madeira.py:1178; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_eletrico.py", "diagrama_prumada_edificio_svg", 'ent.get("carga_total_VA", 0)', "0"): (
        "MORTO",
        "entrada sempre produz carga_total_VA (eletrica_edificio.py:541,707); "
        "legenda CARGA TOTAL com produtor garantido.",
        "eletrica_edificio.py:541; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_eletrico.py", "qdc_edificio_svg", 'ent.get("carga_total_VA", 0)', "0"): (
        "MORTO",
        "idem diagrama, mesmo produtor (quadro do QDC).",
        "eletrica_edificio.py:541; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_escada_edificio.py", "confere_desenho_escada", 'geo.get("blondel", 0.0)', "0.0"): (
        "MORTO",
        "conferencia drawing-vs-data (nao decide desenho); geometria sempre "
        "produz blondel (escada_concreto.py:86).",
        "escada_concreto.py:86; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_escada_edificio.py", "confere_desenho_escada", 'geo.get(chave, 0.0)', "0.0"): (
        "MORTO",
        "conferencia com chave variavel (espelho/piso/blondel); geometria sempre "
        "produz as tres (escada_concreto.py:85-86).",
        "escada_concreto.py:85; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_escada_edificio.py", "planta_escada_svg", 'escada.get("h_laje", 0)', "0"): (
        "MORTO",
        "escada sempre produz h_laje (escada_concreto.py:238); sem h_laje o "
        "produtor levanta KeyError antes (cfg[h_laje], :138), nunca chega a folha.",
        "escada_concreto.py:238; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "adaptar_galpao_para_locacao", 'cap.get("D", 0.0)', "0.0"): (
        "MORTO",
        "capacidade da estaca sempre entrega D/L (fundacao_edificio.py:403-404, "
        "padrao 0.30); congela para acusar se o produtor mudar.",
        "fundacao_edificio.py:403; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "adaptar_galpao_para_locacao", 'cap.get("L", 0.0)', "0.0"): (
        "MORTO",
        "idem D, mesmo produtor.",
        "fundacao_edificio.py:404; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "adaptar_galpao_para_locacao", 'est.get("N_pilar", 0.0)', "0.0"): (
        "MORTO",
        "estaca do galpao sempre entrega N_pilar (galpao_concreto.py:367; "
        "fundacao_edificio.py:426).",
        "galpao_concreto.py:367; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "adaptar_galpao_para_locacao", 'rA.get("N_tot", 0.0)', "0.0"): (
        "MORTO",
        "sapata sempre produz N_tot (fundacao_sapata.py:243).",
        "fundacao_sapata.py:243; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "confere_desenho_fundacao", 'reg.get("N_dimensionamento_kN", 0.0)', "0.0", "#1"): (
        "MORTO",
        "conferencia, nao desenho; registro sempre produz N_dimensionamento_kN "
        "(fundacao_edificio.py:797).",
        "fundacao_edificio.py:797; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "confere_desenho_fundacao", 'reg.get("N_dimensionamento_kN", 0.0)', "0.0", "#2"): (
        "MORTO",
        "segunda ocorrencia da mesma conferencia; ver #1.",
        "fundacao_edificio.py:797; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'reg.get("N_dimensionamento_kN", 0.0)', "0.0", "#1"): (
        "MORTO",
        "registro por pilar sempre produz N_dimensionamento_kN "
        "(fundacao_edificio.py:797; casa_residencial.py:506).",
        "fundacao_edificio.py:797; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_fundacao_edificio.py", "planta_fundacao_svg", 'reg.get("N_dimensionamento_kN", 0.0)', "0.0", "#2"): (
        "MORTO",
        "segunda ocorrencia (quadro) do mesmo produtor; ver #1.",
        "fundacao_edificio.py:797; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_hidraulica.py", "esquema_hidraulica_svg", 'redes["esgoto"].get("ventilacao_ramal_mm", 0)', "0"): (
        "MORTO",
        "ramo guardado por ventilacao_coluna_mm (:98): sem coluna o bloco nem "
        "executa; com coluna o produtor sempre entrega ramal "
        "(galpao_hidraulica.py:159).",
        "galpao_hidraulica.py:159; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_chave_trecho", 'lance.get("As_cm2", 0)', "0"): (
        "MORTO",
        "lance de pilar sempre produz As_cm2/b/h/Nd/taxa (pilar_continuo; "
        "adaptar_galpao_mezanino:1034-1038 monta lances com as 5).",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_chave_trecho", 'lance.get("b", 0)', "0"): (
        "MORTO",
        "idem As_cm2, mesmo produtor.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_chave_trecho", 'lance.get("h", 0)', "0"): (
        "MORTO",
        "idem As_cm2, mesmo produtor.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_trecho", 'base.get("As_cm2", 0)', "0"): (
        "MORTO",
        "base do trecho = lance de base, mesmo produtor do _chave_trecho.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_trecho", 'base.get("Nd", 0)', "0"): (
        "MORTO",
        "idem As_cm2, mesmo produtor.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_trecho", 'base.get("b", 0)', "0"): (
        "MORTO",
        "idem As_cm2, mesmo produtor.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_trecho", 'base.get("h", 0)', "0"): (
        "MORTO",
        "idem As_cm2, mesmo produtor.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_trecho", 'base.get("taxa_pct", 0)', "0"): (
        "MORTO",
        "idem As_cm2, mesmo produtor.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'anc.get("lb_nec_mm", 0)', "0"): (
        "MORTO",
        "ancoragem so lida no ramo `if anc` (:370 mostra '-' sem anc); com anc "
        "o produtor sempre entrega lb_nec_mm (fundacao_sapata.py:692; "
        "viga_concreto ancoragem).",
        "fundacao_sapata.py:692; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'els.get("d_comparado_mm", 0)', "0"): (
        "MORTO",
        "ELS so lido no ramo `if els` (:352-354 mostra '-' sem els); com els o "
        "produtor sempre entrega d_comparado/lim (viga_concreto.py:123-124).",
        "viga_concreto.py:123; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'els.get("lim_mm", 0)', "0"): (
        "MORTO",
        "idem d_comparado, mesmo produtor e ramo.",
        "viga_concreto.py:124; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'linha.get("b", 0)', "0"): (
        "MORTO",
        "linha do por_linha sempre produz b/h (desenho_pavimento.py:1007-1014 "
        "monta de rx b/h; galpao_mezanino.py:173).",
        "desenho_pavimento.py:1007; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'linha.get("h", 0)', "0"): (
        "MORTO",
        "idem b, mesmo produtor.",
        "desenho_pavimento.py:1007; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'tramo.get("As_inf_cm2", 0)', "0"): (
        "MORTO",
        "tramo sempre produz L/M/As (viga_concreto.py:170; estrutura_casa.py:385-389; "
        "galpao_concreto.py:280 para protendida).",
        "viga_concreto.py:170; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'tramo.get("As_sup_cm2", 0)', "0"): (
        "MORTO",
        "idem As_inf, mesmo produtor.",
        "viga_concreto.py:170; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'tramo.get("L", 0)', "0"): (
        "MORTO",
        "idem As_inf, mesmo produtor (vao do tramo).",
        "estrutura_casa.py:385; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'tramo.get("M_d_kNm", 0)', "0"): (
        "MORTO",
        "idem As_inf, mesmo produtor.",
        "estrutura_casa.py:385; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "_vals_fileira_viga", 'tramo.get("M_d_neg_envoltoria_kNm", 0)', "0"): (
        "MORTO",
        "idem As_inf, mesmo produtor (estrutura_casa.py:387).",
        "estrutura_casa.py:387; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "adaptar_galpao_mezanino", 'mz.get("hx", 0.0)', "0.0"): (
        "MORTO",
        "mezanino sempre produz hx/hy (galpao_mezanino.py:143-144,144); fallback "
        "0.0 nunca dispara em rodada real (D176 mediu presentes).",
        "galpao_mezanino.py:144; prova: test_fallback_get_g150 adaptador-morto"),
    ("desenho_pavimento.py", "adaptar_galpao_mezanino", 'mz.get("hy", 0.0)', "0.0"): (
        "MORTO",
        "idem hx, mesmo produtor.",
        "galpao_mezanino.py:144; prova: test_fallback_get_g150 adaptador-morto"),
    ("desenho_pavimento.py", "confere_armacao_pilares", 'base.get("As_cm2", 0)', "0"): (
        "MORTO",
        "conferencia drawing-vs-data (nao decide desenho); base sempre produz "
        "As/b/h (mesmo produtor da fileira).",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "confere_armacao_pilares", 'base.get("b", 0)', "0"): (
        "MORTO",
        "idem As_cm2, mesma conferencia.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "confere_armacao_pilares", 'base.get("h", 0)', "0"): (
        "MORTO",
        "idem As_cm2, mesma conferencia.",
        "desenho_pavimento.py:1034; prova: test_fallback_get_g150 mortos-produzem"),
    ("desenho_pavimento.py", "confere_armacao_vigas", 'esperado_por_viga.get(viga, 0)', "0"): (
        "MORTO",
        "conferencia (contagem esperada vs desenhada); dict montado no mesmo "
        "laco que desenha, chave sempre presente quando a viga existe.",
        "desenho_pavimento.py:462; prova: test_fallback_get_g150 mortos-produzem"),
    ("techdraw_concreto.py", "config_de_spec", 'r["viga"].get("As_inf_cm2", 0.0)', "0.0", "#1"): (
        "MORTO",
        "viga do galpao sempre produz As_inf_cm2 (galpao_concreto.py:280 poe 0.0 "
        "na protendida; viga_concreto.py:170 no armado); duas ocorrencias "
        "(rotulo + quadro).",
        "galpao_concreto.py:280; prova: test_fallback_get_g150 mortos-produzem"),
    ("techdraw_concreto.py", "config_de_spec", 'r["viga"].get("As_inf_cm2", 0.0)', "0.0", "#2"): (
        "MORTO",
        "segunda ocorrencia do mesmo produtor; ver #1.",
        "galpao_concreto.py:280; prova: test_fallback_get_g150 mortos-produzem"),
}


# ---------------------------------------------------------------------------
# ADAPTADOR_MEZANINO_TRIADOS (G150, pelo nome). Os 3 defaults do adaptador novo
# que o AST numerico puro nao acha: o default externo de rp.get(hy|hx, ...) e
# outra Call (nao constante) e o fyk tem constante fora de 0/1. Todos MORTOS
# hoje (D176 mediu fyk, hx, hy presentes); o confere_get acusa se sumirem do
# fonte ou se o produtor parar de entregar (teste adaptador-morto).
# Chave: (arquivo, funcao, nome). `nome` e estavel (nao e linha).
# ---------------------------------------------------------------------------
ADAPTADOR_MEZANINO_TRIADOS = {
    ("desenho_pavimento.py", "adaptar_galpao_mezanino", 'rp.get("hy", mz.get("hy", 0.0))'): (
        "MORTO",
        "rp sempre entrega hy (echo do dimensiona_pilar, medido 0.30); o externo "
        "nunca cai no mz e o interno nunca cai no 0.0; o try levanta sem pilar.",
        "pilar_concreto.dimensiona_pilar; galpao_mezanino.py:144; desenho_pavimento.py:1027; prova: test_fallback_get_g150 adaptador-morto"),
    ("desenho_pavimento.py", "adaptar_galpao_mezanino", 'rp.get("hx", mz.get("hx", 0.0))'): (
        "MORTO",
        "idem hy, eixo X.",
        "pilar_concreto.dimensiona_pilar; galpao_mezanino.py:144; desenho_pavimento.py:1028; prova: test_fallback_get_g150 adaptador-morto"),
    ("techdraw_mezanino.py", "config_de_spec", 'mz.get("fyk", 500e3)'): (
        "MORTO",
        "mezanino sempre produz fyk (galpao_mezanino.py:107,143); 500e3 so "
        "repete o padrao de entrada, nunca decide desenho em rodada real.",
        "galpao_mezanino.py:107; prova: test_fallback_get_g150 adaptador-morto"),
}


def _adaptador_presente_no_disco(raiz=None):
    """Os 3 nomes do adaptador existem no fonte? Lista os que sumiram."""
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    faltando = []
    try:
        dp = (base / "desenho_pavimento.py").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        dp = ""
    try:
        tm = (base / "techdraw_mezanino.py").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        tm = ""
    if 'rp.get("hy"' not in dp:
        faltando.append(("desenho_pavimento.py", "adaptar_galpao_mezanino", 'rp.get("hy", mz.get("hy", 0.0))'))
    if 'rp.get("hx"' not in dp:
        faltando.append(("desenho_pavimento.py", "adaptar_galpao_mezanino", 'rp.get("hx", mz.get("hx", 0.0))'))
    if 'mz.get("fyk"' not in tm:
        faltando.append(("techdraw_mezanino.py", "config_de_spec", 'mz.get("fyk", 500e3)'))
    return sorted(faltando)


def confere_get(raiz=None, triados=None, adaptador=None):
    """Guarda G150 em forma chamavel: .gets nao triados vs triagem + adaptador."""
    tri = GETS_TRIADOS if triados is None else triados
    adp = ADAPTADOR_MEZANINO_TRIADOS if adaptador is None else adaptador
    vivas = set(chaves_get(raiz))
    novas = sorted(k for k in vivas if k not in (tri or {}))
    no_disco = {p.name for p in (pathlib.Path(raiz) if raiz is not None else GALPAO).glob("*.py")}
    resolvidas = sorted(k for k in (tri or {}) if k[0] in no_disco and k not in vivas)
    sem_motivo = sorted(k for k, v in (tri or {}).items() if len(v) < 2 or not (v[1] or "").strip())
    sem_produtor = sorted(k for k, v in (tri or {}).items() if len(v) < 3 or not (v[2] or "").strip())
    ausentes = sorted(k for k in (tri or {}) if k[0] not in no_disco)
    adp_sem_motivo = sorted(k for k, v in (adp or {}).items() if len(v) < 2 or not (v[1] or "").strip())
    adp_sem_produtor = sorted(k for k, v in (adp or {}).items() if len(v) < 3 or not (v[2] or "").strip())
    if raiz is None:
        # _adaptador_presente_no_disco retorna os FALTANTES no fonte; um triado
        # que esta nos faltantes sumiu do fonte e vira resolvida (fails closed).
        faltantes = set(_adaptador_presente_no_disco(None))
        adp_resolvidas = sorted(k for k in (adp or {}) if k in faltantes)
    else:
        # Em tmp_path o teste monta o cenario: so verifica motivo/produtor.
        adp_resolvidas = []
    ok = not (novas or resolvidas or sem_motivo or sem_produtor or ausentes
              or adp_sem_motivo or adp_sem_produtor or adp_resolvidas)
    return {"OK": ok,
            "novas": novas, "resolvidas": resolvidas,
            "sem_motivo": sem_motivo, "sem_produtor": sem_produtor,
            "ausentes": ausentes,
            "adp_sem_motivo": adp_sem_motivo, "adp_sem_produtor": adp_sem_produtor,
            "adp_resolvidas": adp_resolvidas}


def relatorio_get(res=None):
    res = confere_get() if res is None else res
    linhas = ["VARREDURA G150 - GETS DE FOLHA"]
    for lado in ("novas", "resolvidas", "sem_motivo", "sem_produtor", "ausentes",
                 "adp_sem_motivo", "adp_sem_produtor", "adp_resolvidas"):
        linhas.append("  [%s] %d" % (lado, len(res.get(lado) or [])))
        for k in (res.get(lado) or []):
            linhas.append("    %-16s %s" % (lado, " :: ".join(str(x) for x in k)))
    return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    res = confere()
    print(relatorio_pt(res))
    print("fallbacks=%d triados=%d OK=%s" % (len(chaves()), len(FALLBACKS_TRIADOS), res["OK"]))
    resg = confere_get()
    print(relatorio_get(resg))
    print("gets=%d triados=%d adaptador=%d OK=%s"
          % (len(chaves_get()), len(GETS_TRIADOS), len(ADAPTADOR_MEZANINO_TRIADOS), resg["OK"]))
