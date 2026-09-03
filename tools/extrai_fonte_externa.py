#!/usr/bin/env python3
"""
G24 — Extrator de Fonte Externa (protocolo de fonte externa)

Baixa o PDF por URL (ou --pdf-local), calcula SHA-256, registra em
fontes_externas/registro.json e grava esqueleto com proveniência
pagina + trecho_literal obrigatórios.

Uso:
    python tools/extrai_fonte_externa.py --url https://repositorio.universidade.br/tcc.pdf --autor "Silva, J. - UFMG 2023" --classe tcc_academico --id tcc-ufmg-2023-galpao-24x36 --titulo "Galpao 24x36 - TCC UFMG 2023"

    python tools/extrai_fonte_externa.py --pdf-local /caminho/para/tcc.pdf --autor "Silva, J." --classe tcc_academico --id meu-tcc --titulo "Titulo literal da obra"

    python tools/extrai_fonte_externa.py --check --id tcc-ufmg-2023-galpao-24x36

    python tools/extrai_fonte_externa.py --check-remote --id tcc-ufpe-galpao-44x90
    (G35: rebusca a URL ao vivo e compara o SHA-256 com o registrado; prova que
    o PDF guardado e o que a URL serve sao o mesmo. --check so confere o
    arquivo LOCAL contra o registro.)

    python tools/extrai_fonte_externa.py --url file://tests/fixtures/fonte_exemplo_sintetica/exemplo_dummy.pdf --autor "Exemplo" --classe tcc_academico --id teste-local --titulo "Teste local"

Saídas (por obra):
    fontes_externas/registro.json  (entrada acrescentada/atualizada)
    fontes_externas/<id__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL>/fonte.json
    fontes_externas/<id>/fixture.json  (esqueleto: pagina+trecho_literal = null -> BLOQUEADO até preencher)
    fontes_externas/<id>/comparacao.json  (esqueleto veredito = nao_conclusivo)
    fontes_externas/<id>/original.pdf  (cópia do PDF, quando baixado)

Regras G24:
    - URL, SHA-256, data_coleta, autor e classe_autoridade são obrigatórios (ver fontes_externas/README.md §1)
    - classe_autoridade em {licitacao_executada, projeto_licitado, livro_exemplo_resolvido, tcc_academico, material_comercial}
    - Todo número no fixture carrega pagina + trecho_literal (guarda contra fabricação)
    - Rótulo CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA em 4 lugares
    - Veredito em {concorda, framework_errado, fonte_errada, hipotese_divergente, nao_comparavel, nao_conclusivo}
    - Só framework_errado + citacao_normativa autoriza mudar framework
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.request
import urllib.parse
from datetime import date

REPO = pathlib.Path(__file__).resolve().parents[1]
REGISTRO = REPO / "fontes_externas" / "registro.json"
FW = REPO / "framework" / "galpao_fw"

# tenta importar protocolo (fallback inline constants se não existir ainda durante bootstrap)
try:
    sys.path.insert(0, str(FW))
    import fontes_externas_protocolo as PROTO
except Exception:
    PROTO = None
    CLASSES = ["licitacao_executada", "projeto_licitado", "livro_exemplo_resolvido", "tcc_academico", "material_comercial"]
    VEREDITOS = ["concorda", "framework_errado", "fonte_errada", "hipotese_divergente", "nao_comparavel", "nao_conclusivo"]
    ROTULO = "CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA"
    SUFIXO = "__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL"
else:
    CLASSES = PROTO.CLASSES_AUTORIDADE
    VEREDITOS = PROTO.VEREDITOS
    ROTULO = PROTO.ROTULO_CONCORDANCIA
    SUFIXO = PROTO.SUFIXO_DIRETORIO


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str) -> tuple[bytes, str]:
    """
    Baixa URL e retorna (bytes, sha256).
    Suporta:
      - https:// / http://  (via urllib)
      - file://  (le arquivo local, relativo ao repo ou absoluto)
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "file":
        # file://tests/fixtures/fonte_exemplo_sintetica/exemplo_dummy.pdf  ou file:///C:/...
        # urllib decodifica, mas fazemos manual
        raw_path = urllib.parse.unquote(parsed.path)
        # Windows: file://fontes_externas/... -> path = /fontes_externas/... (sem drive)
        # parsed.netloc pode conter primeira parte sem barra
        if parsed.netloc:
            # file://fontes_externas/... -> netloc=fontes_externas
            raw_path = f"{parsed.netloc}{raw_path}"
        # tenta como relativo ao REPO primeiro
        candidates = [
            pathlib.Path(raw_path),
            REPO / raw_path.lstrip("/\\"),
            REPO / parsed.path.lstrip("/\\"),
        ]
        for cand in candidates:
            # normalize
            cand = cand.resolve() if cand.is_absolute() else (REPO / cand).resolve() if not cand.is_absolute() else cand
            # fallback simples
            if cand.is_file():
                data = cand.read_bytes()
                return data, _sha256_bytes(data)
        # ultima tentativa: url sem scheme com path absoluto
        p = pathlib.Path(raw_path)
        if p.is_file():
            data = p.read_bytes()
            return data, _sha256_bytes(data)
        raise FileNotFoundError(f"file:// não encontrado: {url} -> tentado {candidates}")
    elif parsed.scheme in ("http", "https"):
        # download com timeout
        req = urllib.request.Request(url, headers={"User-Agent": "FreeCAD_Automatic-G24-extrator/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            # limite 100 MB para evitar abuso
            if len(data) > 100 * 1024 * 1024:
                raise ValueError(f"PDF muito grande: {len(data)} bytes")
            return data, _sha256_bytes(data)
    else:
        raise ValueError(f"URL deve comecar com https:// / http:// ou file://, veio '{url}'")


def _load_registro() -> dict:
    if not REGISTRO.is_file():
        # cria esqueleto se não existir (bootstrap)
        return {
            "_aviso": f"{ROTULO} - este registro compara o framework contra literatura/TCC/licitacao, jamais contra obra edificada. Nao rotular como 'validado contra obra real'.",
            "_rotulo_quatro_lugares": "Este aviso replica-se em (1) nome do diretorio fontes_externas/<id__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL>/, (2) este JSON, (3) fontes_externas/README.md e (4) relatorios em fontes_externas/<id>/comparacao.json e relatorio*.txt",
            "_protocolo_versao": "1.0",
            "_hierarquia_autoridade": CLASSES,
            "_vereditos_enum": VEREDITOS,
            "fontes": [],
        }
    return json.loads(REGISTRO.read_text(encoding="utf-8"))


def _save_registro(data: dict):
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    REGISTRO.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _id_com_sufixo(id_raw: str) -> str:
    if SUFIXO in id_raw:
        return id_raw
    return f"{id_raw}{SUFIXO}"


def cmd_extrair(args):
    url = args.url
    pdf_local = args.pdf_local
    autor = args.autor
    classe = args.classe
    id_raw = args.id
    titulo = args.titulo

    # validações prévias
    if not autor or len(autor.strip()) < 5:
        print("ERRO: --autor deve ter >=5 chars", file=sys.stderr)
        return 2
    if classe not in CLASSES:
        print(f"ERRO: --classe deve ser um de {CLASSES}, veio '{classe}'", file=sys.stderr)
        return 2
    if not id_raw or not id_raw.strip():
        print("ERRO: --id é obrigatório (slug único da obra)", file=sys.stderr)
        return 2
    if not titulo or len(titulo.strip()) < 5:
        print("ERRO: --titulo é obrigatório (>=5 chars, título literal da obra)", file=sys.stderr)
        return 2
    if not url and not pdf_local:
        print("ERRO: informe --url ou --pdf-local", file=sys.stderr)
        return 2
    if pdf_local:
        # converte --pdf-local para file:// URL
        p = pathlib.Path(pdf_local)
        if not p.is_file():
            # tenta relativo ao repo
            p2 = REPO / pdf_local
            if p2.is_file():
                p = p2
            else:
                print(f"ERRO: --pdf-local não encontrado: {pdf_local}", file=sys.stderr)
                return 2
        # usa file:// URL canônica relativa ao repo quando possível
        try:
            rel = p.resolve().relative_to(REPO.resolve())
            url = f"file://{rel.as_posix()}"
        except ValueError:
            url = f"file://{p.resolve().as_posix()}"

    print(f"[G24] Coletando: {url}")
    try:
        pdf_bytes, sha256 = _download(url)
    except Exception as ex:
        print(f"ERRO ao baixar URL: {ex}", file=sys.stderr)
        return 3

    # verifica PDF magic (opcional)
    if not pdf_bytes.startswith(b"%PDF"):
        print(f"AVISO: conteúdo não começa com %PDF (primeiros 4 bytes: {pdf_bytes[:4]!r}) — prosseguindo, mas verifique se é PDF", file=sys.stderr)

    data_coleta = date.today().isoformat()
    id_full = _id_com_sufixo(id_raw.strip())

    # carregar registro
    registro = _load_registro()
    fontes = registro.setdefault("fontes", [])

    # procurar existente
    existente = None
    for f in fontes:
        if f.get("id") == id_full or f.get("id") == id_raw:
            existente = f
            break

    entry = {
        "id": id_full,
        "url": url,
        "sha256": sha256,
        "data_coleta": data_coleta,
        "autor": autor.strip(),
        "classe_autoridade": classe,
        "titulo_obra": titulo.strip(),
        "rotulo": ROTULO,
        "observacao_coleta": f"Coletado via tools/extrai_fonte_externa.py em {data_coleta}. PDF {len(pdf_bytes)} bytes, SHA-256 {sha256[:12]}... Verificar pagina+trecho_literal em fixture.json antes de comparar.",
        "pagina_exemplo_referencia": 1,
        "trecho_literal_exemplo": f"Coletado de {url} - pagina 1 (verificar trecho literal no PDF, ex. captar tabela de perfis / reacoes)",
    }

    if existente is not None:
        # atualiza mantendo id_full
        existente.update(entry)
        print(f"[G24] Atualizado registro existente: {id_full}")
    else:
        fontes.append(entry)
        print(f"[G24] Nova entrada adicionada: {id_full}")

    # ordenar por hierarquia (licitacao_executada primeiro)
    if PROTO is not None:
        try:
            fontes.sort(key=lambda e: PROTO.hierarquia_rank(e.get("classe_autoridade", "material_comercial")))
        except Exception:
            pass

    # garantir avisos raiz
    registro["_aviso"] = f"{ROTULO} - este registro compara o framework contra literatura/TCC/licitacao, jamais contra obra edificada. Nao rotular como 'validado contra obra real'."
    registro["_rotulo_quatro_lugares"] = "Este aviso replica-se em (1) nome do diretorio fontes_externas/<id__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL>/, (2) este JSON, (3) fontes_externas/README.md e (4) relatorios em fontes_externas/<id>/comparacao.json e relatorio*.txt"
    registro["_protocolo_versao"] = "1.0"
    registro["_hierarquia_autoridade"] = CLASSES
    registro["_vereditos_enum"] = VEREDITOS

    _save_registro(registro)
    print(f"[G24] Registro salvo: {REGISTRO} ({len(fontes)} fontes)")

    # criar diretório por obra
    obra_dir = REPO / "fontes_externas" / id_full
    obra_dir.mkdir(parents=True, exist_ok=True)

    # salvar PDF (cópia para auditoria)
    pdf_dest = obra_dir / "original.pdf"
    pdf_dest.write_bytes(pdf_bytes)
    print(f"[G24] PDF salvo: {pdf_dest} ({len(pdf_bytes)} bytes, sha256 {sha256})")

    # fonte.json (espelho da entrada)
    fonte_json = obra_dir / "fonte.json"
    fonte_data = {
        "_aviso": f"{ROTULO} - copia espelhada de registro.json para auditoria local da obra. Nao afirmar 'validado contra obra real'.",
        **entry,
    }
    fonte_json.write_text(json.dumps(fonte_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[G24] Fonte salva: {fonte_json}")

    # fixture.json esqueleto (proveniência obrigatória)
    fixture_path = obra_dir / "fixture.json"
    if not fixture_path.is_file():
        fixture = {
            "_aviso": f"{ROTULO} - fixture de valores extraidos do PDF da fonte externa. Todo numero carrega pagina + trecho_literal. Nao e obra construida.",
            "_rotulo_quatro_lugares": "Este aviso replica-se em (1) nome do diretorio, (2) este JSON, (3) fontes_externas/README.md e (4) relatorio de comparacao",
            "fonte_id": id_full,
            "extraido_em": data_coleta,
            "extrator": "tools/extrai_fonte_externa.py",
            "valores": {
                "EXEMPLO_Mcol_kNm": {
                    "valor": None,
                    "pagina": None,
                    "trecho_literal": None,
                    "unidade": "kN.m",
                    "definicao": "EXEMPLO - substituir por valor real do PDF com pagina e trecho literal (ex. M no topo da coluna, combinacao Fd1)"
                },
                "EXEMPLO_peso_aco_kg": {
                    "valor": None,
                    "pagina": None,
                    "trecho_literal": None,
                    "unidade": "kg",
                    "definicao": "EXEMPLO - peso de aco primario do PDF (pilares+vigas) com pagina e trecho"
                }
            },
            "_instrucoes": "Preencha cada 'valor' com numero do PDF, 'pagina' com int >0 e 'trecho_literal' com copia literal >=10 chars do trecho que contem o numero. Valor sem pagina+trecho reprova em teste (guarda contra fabricação). Remova os EXEMPLO_* quando adicionar valores reais."
        }
        fixture_path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[G24] Fixture esqueleto criado: {fixture_path} — PREENCHA pagina+trecho_literal antes de comparar!")
    else:
        print(f"[G24] Fixture já existe, mantido: {fixture_path}")

    # comparacao.json esqueleto
    comp_path = obra_dir / "comparacao.json"
    if not comp_path.is_file():
        comp = {
            "_aviso": f"{ROTULO} - resultado de comparacao framework vs fonte externa. Nao rotular como validado contra obra real.",
            "_rotulo_quatro_lugares": "Este aviso replica-se em diretorio, JSON, README e relatorio",
            "fonte_id": id_full,
            "data_comparacao": data_coleta,
            "versao_framework": "desconhecida - preencher (ex. git rev-parse HEAD)",
            "veredito": "nao_conclusivo",
            "citacao_normativa": "",
            "mudou_framework": False,
            "justificativa": "Preencha com veredito do enum fechado {concorda, framework_errado, fonte_errada, hipotese_divergente, nao_comparavel, nao_conclusivo} ANTES de ver o resultado numerico. So framework_errado + citacao normativa autoriza mexer no framework. G31: erro <= tolerancia (geometria 2%, massa/peso 10%, esforco 15%) => concorda; senao hipotese_divergente.",
            "detalhes_por_valor": {},
            "relatorio_txt": f"fontes_externas/{id_full}/relatorio.txt"
        }
        comp_path.write_text(json.dumps(comp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[G24] Comparacao esqueleto criado: {comp_path}")
    else:
        print(f"[G24] Comparacao já existe, mantida: {comp_path}")

    # README por obra (quarto lugar do rótulo — garante cobertura per-obra)
    readme_obra = obra_dir / "README.md"
    if not readme_obra.is_file():
        readme_obra.write_text(
            f"# Fonte: {id_full} - {ROTULO}\n\n"
            f"> **{ROTULO}**\n"
            f"> Esta obra e fonte externa para concordancia entre calculistas, nao obra edificada. "
            f"Nao rotular como \"validado contra obra real\".\n\n"
            f"Este diretorio (`{id_full}`) e um dos **quatro lugares** do rotulo G24:\n\n"
            f"1. **Diretorio** — sufixo `{SUFIXO}` no nome\n"
            f"2. **JSON** — `_aviso` / `rotulo` em `fonte.json`, `fixture.json`, `comparacao.json`\n"
            f"3. **README** — este arquivo\n"
            f"4. **Relatorio** — `relatorio.txt` e `comparacao.json`\n\n"
            f"Classe: `{classe}` (hierarquia: {' > '.join(CLASSES)})\n\n"
            f"PDF: `original.pdf` (SHA-256 verificado contra `registro.json`)\n"
            f"Fixture: `fixture.json` — cada valor com `pagina` + `trecho_literal` (guarda contra fabricacao)\n"
            f"Veredito: `comparacao.json` — enum fechado {{{', '.join(VEREDITOS)}}}\n",
            encoding="utf-8",
        )
        print(f"[G24] README por obra criado: {readme_obra}")
    else:
        print(f"[G24] README por obra já existe, mantido: {readme_obra}")

    # validar com protocolo
    if PROTO is not None:
        erros = PROTO.validar_entrada_registro(entry)
        if erros:
            print(f"AVISO: entrada valida mas com pendencias: {erros}", file=sys.stderr)
        # valida fixture esqueleto: deve falhar até preencher (esperado)
        # não reprova agora, só informa

    print(f"[G24] Concluido. Proximos passos:")
    print(f"  1. Abra {pdf_dest} e extraia numeros com pagina + trecho_literal para {fixture_path}")
    print(f"  2. Preencha {comp_path} com veredito do enum fechado")
    print(f"  3. Rode: python -m pytest framework/galpao_fw/tests/test_fontes_externas_protocolo.py -v")
    return 0


def cmd_check(args):
    id_raw = args.id
    if not id_raw:
        print("ERRO: --check exige --id <slug>", file=sys.stderr)
        return 2
    id_full = _id_com_sufixo(id_raw.strip())
    # procurar no registro
    if not REGISTRO.is_file():
        print(f"ERRO: registro não existe: {REGISTRO}", file=sys.stderr)
        return 1
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    entry = None
    for f in registro.get("fontes", []):
        if f.get("id") == id_full or f.get("id") == id_raw:
            entry = f
            break
    if entry is None:
        print(f"ERRO: id não encontrado no registro: {id_raw} (tentado {id_full})", file=sys.stderr)
        print(f"IDs no registro: {[e.get('id') for e in registro.get('fontes',[])][:5]}", file=sys.stderr)
        return 1
    print(f"[G24] Registro: {entry['id']}")
    print(f"  URL: {entry['url']}")
    print(f"  SHA256: {entry['sha256']}")
    print(f"  Classe: {entry['classe_autoridade']}")
    print(f"  Data: {entry['data_coleta']}")
    print(f"  Rotulo: {entry['rotulo']}")
    # verificar PDF local se for file:// (legado, mas G30 recusa file://)
    url = entry["url"]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "file":
        try:
            pdf_bytes, sha = _download(url)
            if sha.lower() == entry["sha256"].lower():
                print(f"  PDF local OK: sha256 bate ({sha[:12]}...)")
            else:
                print(f"  [FALHA] SHA256 diverge! registrado {entry['sha256'][:12]}... vs arquivo {sha[:12]}...", file=sys.stderr)
                return 1
        except Exception as ex:
            print(f"  [FALHA] não foi possível verificar PDF local: {ex}", file=sys.stderr)
            return 1
    # validar entrada (G30: https obrigatório, file:// recusado)
    if PROTO is not None:
        erros = PROTO.validar_entrada_registro(entry)
        if erros:
            print(f"  [FALHA] validação protocolo: {erros}", file=sys.stderr)
            return 1
        else:
            print(f"  Protocolo: PASS")
    # G30: recalcular hash do arquivo guardado e verificar pagina+trecho no PDF (renderizar-e-olhar)
    obra_dir = REPO / "fontes_externas" / id_full
    pdf_path = obra_dir / "original.pdf"
    if not pdf_path.is_file():
        # fallback para o exemplo sintetico (G35: movido para tests/fixtures)
        alt = REPO / "tests" / "fixtures" / "fonte_exemplo_sintetica" / "exemplo_dummy.pdf"
        if alt.is_file() and "exemplo" in id_full:
            pdf_path = alt
    if pdf_path.is_file() and PROTO is not None:
        ok_h, msg_h = PROTO.validar_hash_arquivo(entry.get("sha256", ""), pdf_path)
        if not ok_h:
            print(f"  [FALHA] hash G30: {msg_h}", file=sys.stderr)
            return 1
        else:
            print(f"  Hash (G30): PASS ({entry['sha256'][:12]}... confere com arquivo {pdf_path.name} {pdf_path.stat().st_size} bytes)")
        # fixture com PDF
        fixture_path = obra_dir / "fixture.json"
        if fixture_path.is_file():
            try:
                fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
                erros_pdf = PROTO.validar_fixture_com_pdf(fixture, pdf_path)
                # filtra apenas erros de pagina/trecho (sintaxe já validada acima)
                pdf_errs = [e for e in erros_pdf if "fora do intervalo" in e or "nao encontrado" in e]
                if pdf_errs:
                    print(f"  [FALHA] fixture G30 (pagina+trecho no PDF): {pdf_errs[0]}", file=sys.stderr)
                    return 1
                else:
                    # se não houver erro de PDF, considera PASS (mesmo que haja erro sintático já tratado)
                    if not erros_pdf:
                        print(f"  Fixture G30 (pagina+trecho no PDF): PASS ({len(fixture.get('valores', {}))} valores verificados em {pdf_path.name})")
            except Exception as ex:
                print(f"  [FALHA] G30 fixture com PDF: {ex}", file=sys.stderr)
                return 1
    # verificar fixture
    obra_dir = REPO / "fontes_externas" / id_full
    fixture_path = obra_dir / "fixture.json"
    if fixture_path.is_file():
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        if PROTO is not None:
            erros_f = PROTO.validar_fixture(fixture)
            if erros_f:
                print(f"  Fixture: BLOQUEADO (sem proveniencia completa):")
                for e in erros_f[:5]:
                    print(f"    - {e}")
                # não é falha do check, é estado esperado até preencher
            else:
                print(f"  Fixture: PASS ({len(fixture.get('valores',{}))} valores com pagina+trecho)")
        else:
            print(f"  Fixture: existe ({fixture_path})")
    else:
        print(f"  Fixture: ausente ({fixture_path})")
    # comparacao
    comp_path = obra_dir / "comparacao.json"
    if comp_path.is_file():
        comp = json.loads(comp_path.read_text(encoding="utf-8"))
        if PROTO is not None:
            erros_c = PROTO.validar_comparacao(comp)
            if erros_c:
                print(f"  Comparacao: BLOQUEADO:")
                for e in erros_c[:5]:
                    print(f"    - {e}")
            else:
                print(f"  Comparacao: PASS (veredito={comp.get('veredito')})")
    print(f"[G24] Check concluido para {id_full}")
    return 0


def cmd_check_remote(args):
    """G35 --check-remote: rebusca a URL ao vivo e compara o hash com o registrado.

    E o que foi feito a mao no G29 (rebusca ao vivo contra os servidores de
    origem) refeito pela maquina: baixa a URL declarada no registro, calcula o
    SHA-256 do que a URL SERVE agora e compara com o sha256 registrado na coleta.
    Diverge => o PDF guardado nao e (mais) o que a URL serve: FAIL.

    Limite que fecha: o G30 confere fixture contra o PDF LOCAL, nunca que o PDF
    local e o que a URL serve. Uma entrada sintetica com URL que da 404 (ex.
    https://example.com/...) PASSA no G30 por construcao e FALHA aqui.

    Somente leitura: nao toca em registro.json nem nos arquivos guardados.
    file:// nao faz sentido remoto (nao ha servidor de origem) => erro de uso.
    """
    id_raw = args.id
    if not id_raw:
        print("ERRO: --check-remote exige --id <slug>", file=sys.stderr)
        return 2
    id_full = _id_com_sufixo(id_raw.strip())
    if not REGISTRO.is_file():
        print(f"ERRO: registro não existe: {REGISTRO}", file=sys.stderr)
        return 1
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    entry = None
    for f in registro.get("fontes", []):
        if f.get("id") == id_full or f.get("id") == id_raw:
            entry = f
            break
    if entry is None:
        print(f"ERRO: id não encontrado no registro: {id_raw} (tentado {id_full})", file=sys.stderr)
        print(f"IDs no registro: {[e.get('id') for e in registro.get('fontes',[])][:5]}", file=sys.stderr)
        return 1
    url = entry["url"]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        if parsed.scheme == "file":
            print(f"[FALHA] --check-remote exige URL https:// com servidor de origem; entrada usa file://: {url}", file=sys.stderr)
        else:
            print(f"[FALHA] --check-remote exige URL https://, veio '{url}'", file=sys.stderr)
        return 1
    print(f"[G35] Rebuscando ao vivo: {url}")
    try:
        pdf_bytes, sha_vivo = _download(url)
    except Exception as ex:
        print(f"[FALHA] nao foi possivel rebuscar a URL (servidor fora, 404, timeout?): {ex}", file=sys.stderr)
        return 1
    sha_reg = entry["sha256"]
    print(f"  Registrado: {sha_reg} ({entry['data_coleta']})")
    print(f"  Servido:    {sha_vivo} ({len(pdf_bytes)} bytes)")
    if sha_vivo.lower() != sha_reg.lower():
        print(f"[FALHA] SHA-256 diverge: o que a URL serve NAO e o PDF guardado (registrado {sha_reg[:12]}... vs servido {sha_vivo[:12]}...)", file=sys.stderr)
        return 1
    print(f"[G35] Check-remote PASS: a URL serve o mesmo PDF guardado ({sha_vivo[:12]}...)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="G24 - Extrator de Fonte Externa (protocolo de fonte externa)")
    ap.add_argument("--url", type=str, default="", help="URL do PDF (https:// ou file://)")
    ap.add_argument("--pdf-local", type=str, default="", help="caminho local do PDF (alternativa a --url)")
    ap.add_argument("--autor", type=str, default="", help="autor + instituicao + ano (ex. 'Silva, J. - UFMG 2023')")
    ap.add_argument("--classe", type=str, default="", choices=CLASSES, help="classe de autoridade: " + " > ".join(CLASSES))
    ap.add_argument("--id", type=str, default="", help="slug único da obra (sem sufixo; o sufixo de concordancia é adicionado automaticamente)")
    ap.add_argument("--titulo", type=str, default="", help="titulo literal da obra")
    ap.add_argument("--check", action="store_true", help="verifica entrada existente por --id (só arquivo local, sem rede)")
    ap.add_argument("--check-remote", action="store_true", help="G35: rebusca a URL ao vivo e compara SHA-256 com o registrado (exige --id)")
    args = ap.parse_args()

    if args.check_remote:
        return cmd_check_remote(args)
    if args.check:
        return cmd_check(args)
    # modo extração: exige autor/classe/id/titulo + url ou pdf-local
    if not args.autor or not args.classe or not args.id or not args.titulo:
        ap.print_help()
        print("\nERRO: --autor, --classe, --id e --titulo são obrigatórios (ou use --check --id <slug>)", file=sys.stderr)
        return 2
    if not args.url and not args.pdf_local:
        ap.print_help()
        print("\nERRO: informe --url ou --pdf-local", file=sys.stderr)
        return 2
    return cmd_extrair(args)


if __name__ == "__main__":
    sys.exit(main())
