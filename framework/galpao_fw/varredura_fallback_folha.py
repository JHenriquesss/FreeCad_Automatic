# ============================================================================
# varredura_fallback_folha.py - G145: OS 47 FALLBACKS or 0 / or 1 DOS EMISSORES.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_fallback_folha.py) e pelo teste-guarda
# tests/test_fallback_folha_g145.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_faixa_validade.
# (Uma fonte so: a lente e o teste importam daqui, nunca copiada.)
#
# Motivacao (G145, auditoria D172): um `or 0` / `or 1` no emissor decide o
# DESENHO quando o dado falta. `int(N_hidrantes or 0) or 1` desenhava hidrante
# inventado quando o emissor do predio passou a receber o galpao (D172).
# A maquina e AST (nao grep): cada BoolOp Or cujo fallback e constante
# 0/0.0/1/1.0 nos 10 emissores de folha. A classificacao e contra o PRODUTOR
# (convencao 9):
#   (a) MORTO - o produtor sempre entrega a chave (funcao + teste que garante);
#   (b) VIVO  - o dado pode faltar ou valer zero numa rodada real; a folha
#       DECLARA a ausencia em texto (nunca um numero) e o teste do goal cobre
#       ausente/zero/presente um por um (convencao 13).
# Chave do baseline: (arquivo, funcao, expressao normalizada, fallback).
# Ocorrencias duplicadas na mesma funcao levam sufixo #2, #3 (ordem por linha):
# remover uma renumera a seguinte e o confere REPROVA nos dois sentidos -
# fails closed, pede retriagem escrita. Linha nao entra na chave (muda a cada
# edicao). Renomear para escapar nao adianta: a entrada vira resolvida e
# reprova (licao do G98).
# ============================================================================
"""Varredura G145: fallbacks or 0 / or 1 nos emissores de folha."""

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


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    res = confere()
    print(relatorio_pt(res))
    print("fallbacks=%d triados=%d OK=%s" % (len(chaves()), len(FALLBACKS_TRIADOS), res["OK"]))
