# -*- coding: utf-8 -*-
"""
G24 — Protocolo de Fonte Externa (bloqueia todos os outros)

Define hierarquia de autoridade, enum fechado de veredito, guarda de
proveniência (pagina + trecho_literal) e regra que só framework_errado
com citacao normativa autoriza mexer no framework.

Este arquivo é a referência normativa do protocolo; seu conteúdo é
escrito ANTES de ver qualquer resultado numérico e é validado por
framework/galpao_fw/tests/test_fontes_externas_protocolo.py.

O rótulo CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA replica-se
em (1) nome do diretório, (2) JSON, (3) README e (4) relatório.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
from datetime import date

# ---------------------------------------------------------------------------
# Hierarquia de autoridade — ordem decrescente (maior primeiro)
# ---------------------------------------------------------------------------
CLASSES_AUTORIDADE = [
    "licitacao_executada",
    "projeto_licitado",
    "livro_exemplo_resolvido",
    "tcc_academico",
    "material_comercial",
]

# mapa para ordenação / comparação: menor índice = maior autoridade
_ORDEM_AUTORIDADE = {cls: i for i, cls in enumerate(CLASSES_AUTORIDADE)}

# ---------------------------------------------------------------------------
# Veredito fechado — enum antes de ver qualquer resultado
# ---------------------------------------------------------------------------
# G31 — acrescenta `concorda`: 0..tolerancia = concordancia entre calculistas
# (mesma premissa ou diferença dentro da tolerância numérica declarada).
# Antes de G31 o bay 7,5 vs 7,5 exato era registrado como hipotese_divergente
# com observação "CONCORDÂNCIA EXATA... não é erro" — sintoma de enum incompleto.
VEREDITOS = [
    "concorda",
    "framework_errado",
    "fonte_errada",
    "hipotese_divergente",
    "nao_comparavel",
    "nao_conclusivo",
]

# descrições humanas (documentam guarda d·sen45 em nao_comparavel)
VEREDITO_DESCRICAO = {
    "concorda": "Concordancia entre calculistas dentro da tolerancia numerica declarada (G31). Nao mexe no framework; valida a entrada/calculo.",
    "framework_errado": "Framework diverge da norma/fisica; fonte defensavel. Unico que autoriza mexer no framework com citacao normativa.",
    "fonte_errada": "Fonte contem erro demonstravel. Nao mexe no framework.",
    "hipotese_divergente": "Ambas defensaveis, premissas diferentes (ex. base rotulada vs engastada) OU erro relativo acima da tolerancia concorda mas ainda defensavel. Nao mexe; registrar hipoteses.",
    "nao_comparavel": "Definicoes diferentes — guarda do d·sen(45): d vs d·sen45, L_rafter inclinado vs projecao, vao livre vs eixo. Nao comparar sem converter.",
    "nao_conclusivo": "Dados insuficientes para decidir. Nao mexe.",
}

# ---------------------------------------------------------------------------
# G31 — Tolerância que separa concorda de hipotese_divergente
# ---------------------------------------------------------------------------
# Regra escrita ANTES de reclassificar (para não calibrar pelo resultado).
# Valores derivados das tolerâncias G15 já existentes (peso 10%, M 15%, V 5%,
# elétrica 2%), não inventados para este caso. Se erro_relativo_pct <=
# tolerancia[grandeza] => concorda; se > tolerancia mas defensável =>
# hipotese_divergente. A viga de tapamento 13 vs 14 kg/m = 7,7% cai em
# concorda porque 7,7% <= 10% (massa_linear); bay 7,5 vs 7,5 = 0% concorda.
# Esta tabela é a resposta à pergunta do goal — regra anterior à reclassificação.
TOLERANCIA_CONCORDA_PCT: dict[str, float] = {
    "geometria": 2.0,       # m, mm — bay, vão, altura, pe-direito, L_rafter (ordem de G15 elétrica 2%)
    "massa_linear": 10.0,   # kg/m — perfil linear, massa por metro (G15 peso 10%)
    "peso_total": 10.0,     # kg — peso total / romaneio (G15 peso 10%)
    "diametro": 10.0,       # mm — barra contraventamento (peso-like)
    "esforco": 15.0,        # kN, kNm — M, N, V (G15 M/H 15%)
    "indice": 10.0,         # m3/m2, kg/m3, m2/m2 — índices de consumo/banda (quantitativo 10%)
    "default": 10.0,        # fallback para grandezas não listadas
}


def tolerancia_concorda_pct(tipo_grandeza: str) -> float:
    """G31 — retorna tolerância (%) que separa concorda de hipotese_divergente.

    tipo_grandeza em TOLERANCIA_CONCORDA_PCT; desconhecido => default.
    Valores espelham G15 (geometria 2%, massa/peso 10%, esforço 15%).
    """
    return TOLERANCIA_CONCORDA_PCT.get(tipo_grandeza, TOLERANCIA_CONCORDA_PCT["default"])


def erro_relativo_pct(valor_fonte: float, valor_framework: float) -> float | None:
    """Calcula erro relativo percentual |fonte-framework|/framework *100.

    Retorna None se framework==0 (divisão indefinida) ou valores não numéricos.
    """
    try:
        vf = float(valor_fonte)
        vc = float(valor_framework)
    except Exception:
        return None
    if vc == 0:
        return None if vf == 0 else float("inf")
    return abs(vf - vc) / abs(vc) * 100.0


def classifica_concorda_ou_hipotese(
    erro_pct: float | None,
    tipo_grandeza: str = "default",
) -> str:
    """G31 — classifica erro já medido na mesma definição.

    Retorna "concorda" se erro_pct <= tolerancia[tipo]; senão "hipotese_divergente".
    Se erro_pct is None (não numérico/indefinido), retorna "nao_conclusivo"
    para não forçar veredito sem base numérica.
    Regra pura: não decide sobre framework_errado/fonte_errada/nao_comparavel —
    apenas separa concorda vs hipotese_divergente quando ambas são defensáveis.
    """
    if erro_pct is None:
        return "nao_conclusivo"
    tol = tolerancia_concorda_pct(tipo_grandeza)
    if erro_pct <= tol:
        return "concorda"
    return "hipotese_divergente"


def tipo_grandeza_para_comparacao(nome_chave: str, definicao: str = "") -> str:
    """Heurística G31: infere tipo_grandeza a partir do nome da chave / definição.

    Usado para aplicar tolerância correta sem exigir campo extra nos JSONs legados.
    """
    n = (nome_chave + " " + definicao).lower()
    if any(k in n for k in ["bay", "vao", "vão", "comprimento", "altura", "pe_direito", "travamento", "geometria", "l_rafter", "ridge"]):
        return "geometria"
    if any(k in n for k in ["massa", "kg/m", "perfil", "tapamento", "terca", "viga", "pilar"]):
        # perfis comparam massa linear quando erro_relativo_massa_pct existe
        return "massa_linear"
    if "peso" in n:
        return "peso_total"
    if any(k in n for k in ["diametro", "diâmetro", "contraventamento", "barra"]):
        return "diametro"
    if any(k in n for k in ["esforco", "esforço", "momento", "cortante", "axial", "reacao", "reação", "mcol", "m_"]):
        return "esforco"
    if any(k in n for k in ["indice", "índice", "m3/m2", "kg/m3", "forma"]):
        return "indice"
    return "default"

# ---------------------------------------------------------------------------
# Rotulagem obrigatória — 4 lugares
# ---------------------------------------------------------------------------
ROTULO_CONCORDANCIA = "CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA"
# sufixo exigido no id/diretório da obra
SUFIXO_DIRETORIO = "__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL"

# ---------------------------------------------------------------------------
# Validadores — G30: guarda que abre o PDF (renderizar-e-olhar da proveniência)
# ---------------------------------------------------------------------------
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# G30: fonte externa deve ser https:// — file:// recusado (só sintaxe antes, agora proveniência)
_URL_RE = re.compile(r"^https://.+")
_URL_FILE_RE = re.compile(r"^file://.+")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validar_classe_autoridade(classe: str) -> tuple[bool, str]:
    if classe not in CLASSES_AUTORIDADE:
        return False, f"classe_autoridade '{classe}' fora do enum {CLASSES_AUTORIDADE}"
    return True, ""


def validar_veredito(veredito: str) -> tuple[bool, str]:
    if veredito not in VEREDITOS:
        return False, f"veredito '{veredito}' fora do enum fechado {VEREDITOS}"
    return True, ""


def validar_sha256(sha: str) -> tuple[bool, str]:
    if not isinstance(sha, str) or not _SHA256_RE.match(sha.lower()):
        return False, f"sha256 deve ser 64 hex chars, veio '{sha}'"
    return True, ""


def validar_url(url: str) -> tuple[bool, str]:
    """G30: fonte externa exige https:// — file:// é recusado (guarda de procedência)."""
    if not isinstance(url, str) or not _URL_RE.match(url):
        if isinstance(url, str) and _URL_FILE_RE.match(url):
            return False, f"url file:// recusado para fonte externa (G30): {url} — use https://"
        return False, f"url deve comecar com https://, veio '{url}'"
    return True, ""


def _normalizar_texto(s: str) -> str:
    """Normaliza para comparação renderizar-e-olhar: colapsa whitespace e lower."""
    return " ".join(s.split()).lower()


def validar_trecho_no_pdf(pdf_path: pathlib.Path, pagina: int, trecho_literal: str) -> tuple[bool, str]:
    """
    G30 — guarda que abre o PDF: verifica que a página existe e que o trecho_literal
    está literalmente na página declarada (renderizar-e-olhar da proveniência).

    Retorna (True, \"\") se ok, ou (False, motivo) se falhar.
    """
    if not isinstance(pagina, int) or pagina <= 0:
        return False, f"pagina deve ser int >0, veio {pagina!r}"
    if not isinstance(trecho_literal, str) or len(trecho_literal.strip()) < 10:
        return False, f"trecho_literal deve ser string >=10 chars, veio {trecho_literal!r}"
    if not pdf_path.is_file():
        return False, f"PDF nao encontrado: {pdf_path}"
    try:
        import fitz  # PyMuPDF
    except ImportError as ex:
        return False, f"PyMuPDF (fitz) nao disponivel para abrir PDF: {ex}"
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as ex:
        return False, f"falha ao abrir PDF {pdf_path}: {ex}"
    n = len(doc)
    if pagina > n:
        return False, f"pagina {pagina} fora do intervalo 1..{n} (PDF de {n} pagina(s)) — fabricacao detectada (G30)"
    try:
        page = doc[pagina - 1]
        texto = page.get_text() or ""
    except Exception as ex:
        return False, f"falha ao extrair texto da pagina {pagina}: {ex}"
    finally:
        try:
            doc.close()
        except Exception:
            pass
    norm_texto = _normalizar_texto(texto)
    norm_trecho = _normalizar_texto(trecho_literal)
    if norm_trecho in norm_texto:
        return True, ""
    # diagnóstico: mostra snippet da página
    snippet = texto[:200].replace("\n", " ").strip()
    return False, (
        f"trecho_literal nao encontrado na pagina {pagina} "
        f"(trecho {trecho_literal[:60]!r}... ausente no texto da pagina com {len(texto)} chars) "
        f"— renderizar-e-olhar G30 | pagina_snippet: {snippet[:120]!r}"
    )


def validar_hash_arquivo(sha_registrado: str, pdf_path: pathlib.Path) -> tuple[bool, str]:
    """G30: recalcula SHA-256 do arquivo guardado e compara com o registrado."""
    if not isinstance(sha_registrado, str) or not _SHA256_RE.match(sha_registrado.lower()):
        return False, f"sha256 registrado invalido: {sha_registrado!r}"
    if not pdf_path.is_file():
        return False, f"arquivo nao encontrado para conferir SHA-256: {pdf_path}"
    h = compute_sha256(pdf_path)
    if h.lower() != sha_registrado.lower():
        return False, f"SHA-256 diverge: registrado {sha_registrado[:12]}... vs arquivo {h[:12]}... (arquivo alterado?) — G30"
    return True, ""


def validar_data_coleta(data: str) -> tuple[bool, str]:
    if not isinstance(data, str) or not _ISO_DATE_RE.match(data):
        return False, f"data_coleta deve ser YYYY-MM-DD, veio '{data}'"
    try:
        y, m, d = map(int, data.split("-"))
        date(y, m, d)
    except Exception as ex:
        return False, f"data_coleta invalida: {ex}"
    return True, ""


def validar_entrada_registro(entry: dict) -> list[str]:
    """Valida uma entrada de fontes_externas/registro.json. Retorna lista de erros (vazia = ok)."""
    erros = []
    for campo in ["id", "url", "sha256", "data_coleta", "autor", "classe_autoridade"]:
        if campo not in entry:
            erros.append(f"campo obrigatorio ausente: {campo}")
    if "id" in entry:
        if not isinstance(entry["id"], str) or not entry["id"]:
            erros.append("id deve ser string nao vazia")
        elif SUFIXO_DIRETORIO not in entry["id"]:
            erros.append(f"id deve conter sufixo '{SUFIXO_DIRETORIO}' (rotulo 4 lugares - diretorio)")
        if ROTULO_CONCORDANCIA not in str(entry.get("rotulo", "")):
            # rotulo pode estar ausente, mas deve conter o aviso quando presente; se ausente, erro
            if "rotulo" not in entry:
                erros.append(f"rotulo ausente: deve ser '{ROTULO_CONCORDANCIA}'")
            elif ROTULO_CONCORDANCIA not in entry["rotulo"]:
                erros.append(f"rotulo deve conter '{ROTULO_CONCORDANCIA}'")
        else:
            # se rotulo existe, verificar conteudo
            pass
        # fallback: se rotulo nao existe a mensagem acima ja cobre
        if "rotulo" in entry and ROTULO_CONCORDANCIA not in entry["rotulo"]:
            # ja adicionado
            pass
    if "url" in entry:
        ok, msg = validar_url(entry["url"])
        if not ok:
            erros.append(msg)
    if "sha256" in entry:
        ok, msg = validar_sha256(entry["sha256"])
        if not ok:
            erros.append(msg)
    if "data_coleta" in entry:
        ok, msg = validar_data_coleta(entry["data_coleta"])
        if not ok:
            erros.append(msg)
    if "autor" in entry:
        if not isinstance(entry["autor"], str) or len(entry["autor"].strip()) < 5:
            erros.append("autor deve ser string com >=5 chars")
    if "classe_autoridade" in entry:
        ok, msg = validar_classe_autoridade(entry["classe_autoridade"])
        if not ok:
            erros.append(msg)
    # rotulo obrigatorio (4 lugares)
    if "rotulo" not in entry:
        erros.append(f"rotulo obrigatorio: '{ROTULO_CONCORDANCIA}'")
    elif ROTULO_CONCORDANCIA not in entry["rotulo"]:
        erros.append(f"rotulo deve ser '{ROTULO_CONCORDANCIA}'")
    return erros


def validar_valor_com_procedencia(nome: str, valor_dict: dict) -> list[str]:
    """
    Guarda contra fabricação: todo número no fixture deve carregar
    pagina + trecho_literal. Valor sem procedência reprova em teste.
    """
    erros = []
    if not isinstance(valor_dict, dict):
        return [f"{nome}: deve ser objeto com pagina+trecho_literal"]
    if "valor" not in valor_dict:
        erros.append(f"{nome}: campo 'valor' ausente")
    # pagina obrigatória
    if "pagina" not in valor_dict:
        erros.append(f"{nome}: campo 'pagina' ausente (procedência obrigatória)")
    else:
        p = valor_dict["pagina"]
        if not isinstance(p, int) or p <= 0:
            erros.append(f"{nome}: pagina deve ser int >0, veio {p!r}")
    # trecho_literal obrigatório
    if "trecho_literal" not in valor_dict:
        erros.append(f"{nome}: campo 'trecho_literal' ausente (procedência obrigatória)")
    else:
        t = valor_dict["trecho_literal"]
        if not isinstance(t, str) or len(t.strip()) < 10:
            erros.append(f"{nome}: trecho_literal deve ser string >=10 chars, veio {t!r}")
    return erros


def validar_fixture(fixture: dict) -> list[str]:
    """Valida um fixture.json completo. Retorna lista de erros."""
    erros = []
    if "_aviso" not in fixture or ROTULO_CONCORDANCIA not in str(fixture["_aviso"]):
        erros.append(f"_aviso deve conter '{ROTULO_CONCORDANCIA}' (rotulo 4 lugares)")
    if "fonte_id" not in fixture:
        erros.append("fonte_id ausente no fixture")
    elif SUFIXO_DIRETORIO not in fixture["fonte_id"]:
        erros.append(f"fonte_id deve conter sufixo '{SUFIXO_DIRETORIO}'")
    if "valores" not in fixture or not isinstance(fixture["valores"], dict):
        erros.append("valores deve ser objeto com entradas pagina+trecho_literal")
        return erros
    if not fixture["valores"]:
        erros.append("valores vazio: fixture deve conter ao menos um numero com procedencia")
    for nome, vdict in fixture["valores"].items():
        erros.extend(validar_valor_com_procedencia(nome, vdict))
    return erros


def localizar_pdf_fonte(fonte_id: str, repo_root: pathlib.Path | None = None) -> pathlib.Path | None:
    """Localiza original.pdf da fonte pelo id. Retorna Path ou None se nao existir."""
    if repo_root is None:
        repo_root = pathlib.Path(__file__).resolve().parents[2]
    candidatos = [
        repo_root / "fontes_externas" / fonte_id / "original.pdf",
        # fallback para dummy legado (exemplo_dummy.pdf na raiz de fontes_externas)
        repo_root / "fontes_externas" / "exemplo_dummy.pdf",
    ]
    for cand in candidatos:
        if cand.is_file():
            # para dummy, só retorna se fonte_id contiver exemplo e cand for exemplo_dummy
            if "exemplo_dummy" in cand.name and "exemplo" not in fonte_id:
                continue
            return cand
    # tenta diretamente o path do dummy se for o id de exemplo
    if "exemplo" in fonte_id:
        p = repo_root / "fontes_externas" / "exemplo_dummy.pdf"
        if p.is_file():
            return p
    return None


def validar_fixture_com_pdf(fixture: dict, pdf_path: pathlib.Path) -> list[str]:
    """
    G30 — guarda que abre o PDF: valida fixture sintaticamente e depois
    exige que cada pagina+trecho_literal esteja literalmente no PDF.
    Retorna lista de erros (vazia = ok). Inclui erros sintáticos + semânticos.
    """
    erros = validar_fixture(fixture)
    # se já tem erro sintático grave (ex. valores ausente), não tenta abrir PDF
    if not isinstance(fixture.get("valores"), dict):
        return erros
    if not pdf_path.is_file():
        erros.append(f"PDF nao encontrado para validar fixture: {pdf_path}")
        return erros
    for nome, vdict in fixture["valores"].items():
        # só verifica se sintaxe já ok para pagina/trecho
        if not isinstance(vdict, dict):
            continue
        pag = vdict.get("pagina")
        trecho = vdict.get("trecho_literal")
        if isinstance(pag, int) and pag > 0 and isinstance(trecho, str) and len(trecho.strip()) >= 10:
            ok, msg = validar_trecho_no_pdf(pdf_path, pag, trecho)
            if not ok:
                erros.append(f"{nome}: {msg}")
    return erros


def validar_fonte_externa_completa(
    entry: dict,
    fixture: dict | None = None,
    repo_root: pathlib.Path | None = None,
) -> list[str]:
    """
    G30 — guarda completa de procedência (renderizar-e-olhar).

    Verifica:
      1) sintaxe do registro (inclui https://, file:// recusado)
      2) SHA-256 recalculado do arquivo guardado bate com o registrado
      3) cada pagina+trecho_literal do fixture está no PDF na página declarada

    Usada por testes G30 para provar que fica vermelha com fabricadas (pagina 45 em PDF 1 pag)
    e verde com reais (https, hash ok, trecho presente).
    """
    erros: list[str] = []
    # 1) sintaxe (já inclui URL https)
    erros.extend(validar_entrada_registro(entry))
    if repo_root is None:
        repo_root = pathlib.Path(__file__).resolve().parents[2]
    fonte_id = str(entry.get("id", ""))
    # localizar PDF
    pdf_path = localizar_pdf_fonte(fonte_id, repo_root)
    # fallback: se entry url é file:// local, tenta resolver o path do file://
    if pdf_path is None and isinstance(entry.get("url"), str) and entry["url"].startswith("file://"):
        import urllib.parse
        parsed = urllib.parse.urlparse(entry["url"])
        raw = urllib.parse.unquote(parsed.path)
        if parsed.netloc:
            raw = f"{parsed.netloc}{raw}"
        cand = repo_root / raw.lstrip("/\\")
        if cand.is_file():
            pdf_path = cand
    if pdf_path is None:
        # se não achou PDF, já é erro para fonte completa (mas não para sintaxe isolada)
        # só adiciona se entry parece real (tem sha e url https)
        if _URL_RE.match(str(entry.get("url", ""))):
            erros.append(f"PDF armazenado nao encontrado para fonte {fonte_id}: {repo_root / 'fontes_externas' / fonte_id / 'original.pdf'}")
        return erros
    # 2) hash
    sha = str(entry.get("sha256", ""))
    if sha:
        ok, msg = validar_hash_arquivo(sha, pdf_path)
        if not ok:
            erros.append(msg)
    # 3) fixture com PDF
    if fixture is not None:
        # validar_fixture_com_pdf já inclui sintaxe, mas evitamos duplicar
        for nome, vdict in fixture.get("valores", {}).items():
            pag = vdict.get("pagina")
            trecho = vdict.get("trecho_literal")
            if isinstance(pag, int) and pag > 0 and isinstance(trecho, str) and len(trecho.strip()) >= 10:
                ok, msg = validar_trecho_no_pdf(pdf_path, pag, trecho)
                if not ok:
                    erros.append(f"fixture[{nome}]: {msg}")
    else:
        # tenta carregar fixture do disco se não fornecido
        fixture_path = repo_root / "fontes_externas" / fonte_id / "fixture.json"
        if fixture_path.is_file():
            try:
                data = json.loads(fixture_path.read_text(encoding="utf-8"))
                for nome, vdict in data.get("valores", {}).items():
                    pag = vdict.get("pagina")
                    trecho = vdict.get("trecho_literal")
                    if isinstance(pag, int) and pag > 0 and isinstance(trecho, str) and len(trecho.strip()) >= 10:
                        ok, msg = validar_trecho_no_pdf(pdf_path, pag, trecho)
                        if not ok:
                            erros.append(f"fixture[{nome}]: {msg}")
            except Exception as ex:
                erros.append(f"falha ao validar fixture com PDF: {ex}")
    return erros


def validar_comparacao(comp: dict) -> list[str]:
    """Valida comparacao.json (veredito + regra framework_errado)."""
    erros = []
    if "_aviso" not in comp or ROTULO_CONCORDANCIA not in str(comp["_aviso"]):
        erros.append(f"_aviso deve conter '{ROTULO_CONCORDANCIA}'")
    if "veredito" not in comp:
        erros.append("veredito ausente")
    else:
        ok, msg = validar_veredito(comp["veredito"])
        if not ok:
            erros.append(msg)
    # regra: se mudou_framework, exige framework_errado + citacao_normativa
    mudou = comp.get("mudou_framework", False)
    veredito = comp.get("veredito", "")
    cit = str(comp.get("citacao_normativa", "")).strip()
    if mudou:
        if veredito != "framework_errado":
            erros.append(f"mudou_framework=True exige veredito='framework_errado', veio '{veredito}'")
        if not cit:
            erros.append("mudou_framework=True exige citacao_normativa nao vazia (ex. NBR 8800 §5.4.3 p.60)")
    # se veredito framework_errado, citacao fortemente recomendada (warn, mas validamos como erro se mudou)
    # concordar com fonte nunca justificativa suficiente: isso é a regra acima
    return erros


def fechar_divergencia(veredito: str, citacao_normativa: str, mudou_framework: bool) -> None:
    """
    Regra que dá sentido ao resto: só pode fechar mexendo no framework quando
    veredito == framework_errado com citação normativa.
    Lança ValueError se violado (usado por testes e por código que altera framework).
    """
    ok, msg = validar_veredito(veredito)
    if not ok:
        raise ValueError(msg)
    if mudou_framework:
        if veredito != "framework_errado":
            raise ValueError(
                f"Divergencia com veredito '{veredito}' nao autoriza mexer no framework. "
                f"So 'framework_errado' autoriza. Regra G24: concordar com a fonte nunca e justificativa suficiente."
            )
        if not str(citacao_normativa).strip():
            raise ValueError(
                "Veredito 'framework_errado' exige citacao_normativa (ex. NBR 8800:2024 §5.4.3 p.60 eq.5.4-10). "
                "Sem citacao normativa, a divergencia nao pode ser fechada mexendo no framework."
            )


def validar_registro(registro: dict) -> list[str]:
    """Valida registro.json completo."""
    erros = []
    if "_aviso" not in registro or ROTULO_CONCORDANCIA not in str(registro["_aviso"]):
        erros.append(f"_aviso deve conter '{ROTULO_CONCORDANCIA}'")
    if "_rotulo_quatro_lugares" not in registro:
        erros.append("_rotulo_quatro_lugares ausente (documentacao do padrao 4 lugares)")
    if "fontes" not in registro or not isinstance(registro["fontes"], list):
        erros.append("fontes deve ser lista")
        return erros
    ids = set()
    for idx, entry in enumerate(registro["fontes"]):
        prefix = f"fontes[{idx}]"
        if not isinstance(entry, dict):
            erros.append(f"{prefix}: deve ser objeto")
            continue
        e = validar_entrada_registro(entry)
        for msg in e:
            erros.append(f"{prefix} ({entry.get('id','?')}): {msg}")
        fid = entry.get("id")
        if fid in ids:
            erros.append(f"{prefix}: id duplicado '{fid}'")
        ids.add(fid)
    return erros


def compute_sha256(path: pathlib.Path) -> str:
    """Calcula SHA-256 hex de um arquivo."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hierarquia_rank(classe: str) -> int:
    """Retorna rank (0 = maior autoridade). Erro se classe invalida."""
    if classe not in _ORDEM_AUTORIDADE:
        raise ValueError(f"classe_autoridade desconhecida: {classe}")
    return _ORDEM_AUTORIDADE[classe]


def assert_registro_existe(repo_root: pathlib.Path | None = None) -> pathlib.Path:
    """
    Guard G24: bloqueia comparacao numerica antes do protocolo existir.
    Lanca FileNotFoundError se fontes_externas/registro.json nao existir.
    """
    if repo_root is None:
        # framework/galpao_fw/fontes_externas_protocolo.py -> parents[2] = repo root
        repo_root = pathlib.Path(__file__).resolve().parents[2]
    reg = repo_root / "fontes_externas" / "registro.json"
    if not reg.is_file():
        raise FileNotFoundError(
            f"Protocolo G24 ausente: {reg} nao encontrado. "
            f"Nada de comparar numero antes disto existir. Crie o registro via tools/extrai_fonte_externa.py "
            f"antes de qualquer comparacao externa."
        )
    return reg
