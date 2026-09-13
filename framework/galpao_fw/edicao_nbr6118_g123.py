# ============================================================================
# edicao_nbr6118_g123.py - G123: O PROJETO DECLARA POR QUAL EDICAO DA NORMA
# FOI CALCULADO. DECLARACAO + CHAVE DESLIGADA. NAO MIGRA NADA SOZINHO.
# MODULO DE PRODUCAO (fonte unica): o carimbo que o cliente recebe mora
# aqui; a lente e o teste importam daqui. (Uma fonte so - regra do lote.)
# Rodado a mao/CI (python edicao_nbr6118_g123.py) e pelo teste-guarda
# tests/test_edicao_nbr6118_g123.py. IMPORTADO pela producao (premoldado,
# compatibilizacao, desenho_concreto, techdraw_concreto, pacote_legal,
# relatorio_calculo, executivo_concreto, projeto_spec, galpao_concreto,
# rodar_galpao, entregaveis_projeto, desenho_pavimento,
# desenho_fundacao_edificio + G128: casa_residencial, edificio_adapter,
# galpao_adapter, desenho_casa_residencial, caderno_encargos) - por isso
# NAO e script avulso (ver test_alcancabilidade).
#
# O que foi MEDIDO (G116/G122, enderecos verificados naquelas entregas):
#   - O framework calcula pela NBR 6118:2014 (F016) e nenhuma folha, pacote
#     legal ou relatorio diz isso (G123, medido G116/G119).
#   - 2 pontos NUMERO-MUDA (G116 Tabela 1): 13.2.5.1-b (furo circular
#     12,1-12,5 cm passa a dispensar verificacao; o framework hoje pede a
#     mais, conservador) e 12.3.3 (s = 0,20 para todo C60+: C60 CPIII a 7 d
#     da 41032 kN/m2 em 2014 contra 49124 kN/m2 em 2023+Em1, +19,7 %).
#   - 8.2.5 (G122 item 52, fct,m C55+: 4,300 MPa em 2014 contra 4,355 MPa em
#     2023) NAO entra nesta chave: este goal entrega os 2 pontos do G116;
#     o 8.2.5 segue 2014 declarado (migrar e decisao do usuario, item a item).
#   - 2 PROCESSO-NOVO (5.3 ATP, 20.6 marquise/balanco) NAO entram: sao gate
#     novo, nao troca de conta (Nao fazer do G123).
#
# Maquina: resolver_edicao (sem default silencioso) + carimbo_edicao (o que
# a folha diz) + s_cimento/limite_furo (os 2 numeros que leem a chave) +
# contem_declaracao/confere_pecas (o portao: peca sem declaracao reprova) +
# MODULOS_COM_TROCA/USO_ESPERADO (o portao: nenhum modulo troca por conta
# propria) + casos C1/C4 que chamam as funcoes REAIS (contra assercao
# tautologica: o numero 2014 vem da funcao real com a chave em 2014; o
# 2023+Em1 vem da MESMA funcao real com a chave em 2023+Em1).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - 2014 -> 2023 fora dos 2 pontos (inclui 8.2.5, 6 REGRA-MUDA, EDITORIAL,
#     FIGURA): segue 2014 declarado, sem troca silenciosa;
#   - figuras/tabelas/miolo simbolico: ver pagina renderizada (regra 3);
#   - a MIGRACAO em si (virar a chave): decisao do usuario, com este numero
#     na mao. Sem o parametro, o comportamento e o de hoje (2014) e a folha
#     diz qual e (chave DESLIGADA, sem default silencioso).
# ============================================================================
"""Edicao da NBR 6118 declarada pelo projeto (G123): carimbo + chave."""

from __future__ import annotations

import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent

# Edicoes que o projeto pode declarar. So estas duas; qualquer outra e erro
# (nao default silencioso, nao "2023" sem Emenda: 2023 sem Em1 nao e edicao
# de projeto neste goal).
EDICOES_VALIDAS = ("2014", "2023+Em1")

# Comportamento de hoje (o que o framework faz sem o parametro).
EDICAO_PADRAO = "2014"

# Rotulos que a folha carimba. Substrings estaveis que o portao confere por
# substring (nunca regex sobre a folha: convencao 3 do lote e parse, mas o
# carimbo e texto corrido, nao norma).
DECLARACAO_2014 = "NBR 6118:2014"
DECLARACAO_2023_EM1 = "NBR 6118:2023 + Emenda 1:2026"

# s do cimento em 2014 (NBR 6118 12.3.3, medido em premoldado_nbr9062:53).
# Fonte unica a partir deste goal: premoldado importa daqui (uma fonte so).
# G126: a identidade valida e o piso moram em cimento_nbr6118_g126 (fonte
# unica da identidade); desconhecido LEVANTA la, ausente vira o piso.
S_CIMENTO_2014 = {
    "CPIII": 0.38, "CPIV": 0.38,
    "CPI": 0.25, "CPII": 0.25,
    "CPV": 0.20, "CPV-ARI": 0.20,
}

# Limites de dispensa do furo em viga (NBR 6118 13.2.5.1-b).
# 2014 = 2023 pre-Em1: 12 cm e h/3 (qualquer forma).
# 2023+Em1: 12 cm x 12 cm (retangular) e 12,5 cm (circular), ambos <= h/3.
LIMITE_FURO_2014_MM = 120.0
LIMITE_FURO_RETANGULAR_2023_EM1_MM = 120.0
LIMITE_FURO_CIRCULAR_2023_EM1_MM = 125.0

# Os 2 pontos NUMERO-MUDA que leem a chave (baseline congelado nos dois
# sentidos: ponto novo sem triagem = vermelho; ponto que some = vermelho).
MODULOS_COM_TROCA = (
    ("premoldado_nbr9062", "12.3.3"),
    ("compatibilizacao", "13.2.5.1"),
)

# Arquivos de producao que podem importar esta fonte unica (baseline nos
# dois sentidos: import novo sem triagem = troca por conta propria; import
# que some = nome morto). So raiz *.py (nao tests/): teste que importa a
# lente nao e troca de edicao.
USO_ESPERADO = frozenset({
    "edicao_nbr6118_g123.py",
    "premoldado_nbr9062.py",
    "compatibilizacao.py",
    "desenho_concreto.py",
    "techdraw_concreto.py",
    "pacote_legal.py",
    "relatorio_calculo.py",
    "executivo_concreto.py",
    "projeto_spec.py",
    "galpao_concreto.py",
    "rodar_galpao.py",
    "entregaveis_projeto.py",
    # G125 (auditoria do G123): as folhas de concreto da casa e do predio.
    "desenho_pavimento.py",
    "desenho_fundacao_edificio.py",
    # G128 (a declaracao chega as tres tipologias): quem resolve a chave
    # fora do galpao (os 3 hooks de compatibilizacao + os 2 de desenho),
    # o wrapper das folhas da casa e o caderno de encargos. Triagem: cada
    # um so LE a chave via edicao_de_spec/edicao_de_normalized e a repassa
    # (nenhum troca conta por conta propria: MODULOS_COM_TROCA intacto).
    "casa_residencial.py",
    "edificio_adapter.py",
    "galpao_adapter.py",
    "desenho_casa_residencial.py",
    "caderno_encargos.py",
})


def normaliza_edicao(edicao):
    """Canoniza '2014' ou '2023+Em1' (aceita variacao de escrita da segunda).

    Levanta ValueError para qualquer outra coisa (inclui '2023' sem Emenda:
    sem a Emenda nao e edicao de projeto). None nunca chega aqui (ver
    resolver_edicao): parametro ausente nao e edicao invalida, e comportamento
    de hoje declarado.
    """
    if not isinstance(edicao, str):
        raise ValueError("edicao da NBR 6118 deve ser '2014' ou '2023+Em1' "
                         "(recebido %r)" % (edicao,))
    t = edicao.strip()
    if t == "2014":
        return "2014"
    junto = t.replace(" ", "").replace("_", "").replace("-", "+").upper()
    if junto in ("2023+EM1", "2023+EMENDA1", "2023+EMENDA1:2026",
                 "2023+EM1:2026"):
        return "2023+Em1"
    raise ValueError("edicao da NBR 6118 invalida %r (use '2014' ou '2023+Em1')"
                     % (edicao,))


def resolver_edicao(edicao=None):
    """Resolve a edicao do projeto sem default silencioso.

    edicao=None (parametro ausente) -> 2014 (comportamento de hoje) com
    origem declarada 'padrao_hoje_sem_parametro' (a folha diz qual e).
    edicao='2014'/'2023+Em1' -> a edicao, com origem 'declarada_no_projeto'.
    Qualquer outra string -> ValueError ( migrar e decisao do usuario; valor
    inventado nao vira edicao).
    """
    if edicao is None:
        return {"edicao": EDICAO_PADRAO,
                "origem": "padrao_hoje_sem_parametro",
                "explicita": False}
    canon = normaliza_edicao(edicao)
    return {"edicao": canon, "origem": "declarada_no_projeto",
            "explicita": True}


def rotulo_edicao(edicao=None):
    """'NBR 6118:2014' ou 'NBR 6118:2023 + Emenda 1:2026' (o que a folha diz)."""
    r = resolver_edicao(edicao)
    if r["edicao"] == "2023+Em1":
        return DECLARACAO_2023_EM1
    return DECLARACAO_2014


def carimbo_edicao(edicao=None):
    """Linha completa que a peca de concreto carimba (vem desta fonte so).

    Sem o parametro, o comportamento e o de hoje (2014) E a folha diz qual
    e (sem default silencioso: a ausencia do parametro fica escrita).
    """
    r = resolver_edicao(edicao)
    rot = rotulo_edicao(r["edicao"])
    if r["explicita"]:
        return ("Projeto calculado pela %s (edicao declarada no projeto)"
                % rot)
    return ("Projeto calculado pela %s (comportamento atual; edicao nao "
            "declarada no projeto — assumida 2014)" % rot)


def sufixo_folha_edicao(edicao=None):
    """Sufixo curto para o titulo da folha SVG (cabe na mesma linha)."""
    return " (%s)" % rotulo_edicao(edicao)


def edicao_de_spec(spec):
    """Edicao declarada num spec dict (projeto ou galpao_concreto).

    Procura 'norma_6118_edicao' (canonico do ProjetoSpec), 'edicao_6118' e
    'edicao' (atalhos do spec pequeno do galpao_concreto). Ausente/None ->
    None (comportamento de hoje, 2014 declarado na folha). Valor invalido ->
    ValueError (nao vira edicao em silencio).
    """
    if not isinstance(spec, dict):
        return None
    for chave in ("norma_6118_edicao", "edicao_6118", "edicao",
                  "nbr6118_edicao"):
        if chave in spec and spec[chave] not in (None, ""):
            return normaliza_edicao(spec[chave])
    # Fundacao aninhada do ProjetoSpec pode carregar a chave (compat).
    fund = spec.get("fundacao")
    if isinstance(fund, dict):
        for chave in ("norma_6118_edicao", "edicao_6118", "edicao"):
            if chave in fund and fund[chave] not in (None, ""):
                return normaliza_edicao(fund[chave])
    return None


def edicao_de_resultado(res):
    """Edicao que um resultado de calculo carrega (galpao_concreto.rodar)."""
    if not isinstance(res, dict):
        return None
    for chave in ("edicao_6118", "norma_6118_edicao", "edicao"):
        if res.get(chave) not in (None, ""):
            try:
                return normaliza_edicao(res[chave])
            except ValueError:
                raise
    spec = res.get("spec")
    if isinstance(spec, dict):
        ed = edicao_de_spec(spec)
        if ed is not None:
            return ed
        # Spec pequeno do galpao_concreto guarda a edicao resolvida em
        # spec['edicao_6118_resolvida'] quando presente (ver rodar()).
        for chave in ("edicao_6118_resolvida", "norma_6118_edicao_resolvida"):
            if spec.get(chave) not in (None, ""):
                try:
                    return normaliza_edicao(spec[chave])
                except ValueError:
                    raise
    return None


def edicao_de_normalized(normalized):
    """Edicao declarada no normalized do project_loop (G128, as 3 tipologias).

    Le `raw_spec` e, na falta, `turnkey_spec` (o loop os deriva do mesmo
    project-spec.json; a chave mora na raiz, `norma_6118_edicao`). Ausente
    em ambos -> None (comportamento de hoje, 2014 declarado na peca).
    Valor invalido -> ValueError (nao vira edicao em silencio).
    """
    if not isinstance(normalized, dict):
        return None
    for fonte in (normalized.get("raw_spec"),
                  normalized.get("turnkey_spec")):
        if not isinstance(fonte, dict):
            continue
        ed = edicao_de_spec(fonte)
        if ed is not None:
            return ed
    return None


def s_cimento(edicao, cimento, fck_kNm2):
    """s do cimento para fckj (12.3.3) lendo a chave.

    2014: tabela por cimento (S_CIMENTO_2014).
    2023+Em1: 0,20 para todo concreto C60 ou superior (fck >= 60 MPa),
    qualquer cimento; abaixo de 60, a mesma tabela de 2014.
    edicao=None -> 2014 (comportamento de hoje).
    G126: cimento ausente (None/"") -> piso conservador
    (cimento_nbr6118_g126.PISO_S, o maior `s`); cimento desconhecido ->
    ValueError com a lista dos validos (nunca mais 0,25 em silencio).
    """
    r = resolver_edicao(edicao)
    try:
        fck_MPa = float(fck_kNm2) / 1000.0
    except (TypeError, ValueError):
        fck_MPa = 0.0
    if r["edicao"] == "2023+Em1" and fck_MPa >= 60.0:
        return 0.20
    if cimento is None or (isinstance(cimento, str) and not cimento.strip()):
        from cimento_nbr6118_g126 import PISO_S as _piso
        return _piso
    from cimento_nbr6118_g126 import normaliza_cimento as _norm_cim
    return S_CIMENTO_2014[_norm_cim(cimento)]


def limite_furo_viga_mm(edicao=None, forma_furo=None):
    """Limite de dispensa da dimensao do furo (13.2.5.1-b) lendo a chave.

    2014: 120 mm (qualquer forma). 2023+Em1: 125 mm SO para circular;
    retangular (ou forma nao declarada) fica em 120 mm (conservador: liberar
    125 retangular seria nao-conservador). edicao=None -> 120 (hoje).
    forma_furo=None -> 120 (sem a forma nao ha dispensa maior).
    """
    r = resolver_edicao(edicao)
    if r["edicao"] == "2023+Em1":
        forma = str(forma_furo or "").strip().lower()
        if forma == "circular":
            return LIMITE_FURO_CIRCULAR_2023_EM1_MM
        return LIMITE_FURO_RETANGULAR_2023_EM1_MM
    return LIMITE_FURO_2014_MM


def contem_declaracao(texto):
    """A peca declara por qual edicao foi calculada? (portao por substring).

    True quando o texto contem 'NBR 6118:2014' ou 'NBR 6118:2023 + Emenda
    1:2026' (a forma curta 'NBR 6118' sem edicao NAO conta: e a ausencia que
    o G123 achou). Devolve {'tem', 'edicao'}; edicao=None quando nao tem.
    """
    t = str(texto or "")
    tem_2023 = (DECLARACAO_2023_EM1 in t) or ("2023+Em1" in t)
    tem_2014 = DECLARACAO_2014 in t
    if tem_2023 and tem_2014:
        return {"tem": True, "edicao": "ambas"}
    if tem_2023:
        return {"tem": True, "edicao": "2023+Em1"}
    if tem_2014:
        return {"tem": True, "edicao": "2014"}
    return {"tem": False, "edicao": None}


def confere_peca(texto):
    """Portao de uma peca: OK quando declara a edicao; senao reprova nomeando.

    O acumulador e 'sem_declaracao' em confere_pecas (convencao 7: o teste o
    faz disparar).
    """
    c = contem_declaracao(texto)
    if c["tem"]:
        return {"OK": True, "edicao": c["edicao"], "motivo": ""}
    return {"OK": False, "edicao": None,
            "motivo": "peca sem declaracao da edicao da NBR 6118 "
                      "(exigido G123: '%s' ou '%s')"
                      % (DECLARACAO_2014, DECLARACAO_2023_EM1)}


def confere_pecas(pecas):
    """Portao de N pecas: {nome: texto} -> OK global + por peca.

    OK global so quando TODA peca declara (cada OK chega ao veredito global,
    contra a saturacao silenciosa do G113). 'sem_declaracao' e o acumulador
    que o teste faz disparar (convencao 7).
    """
    if pecas is None or not isinstance(pecas, dict):
        raise TypeError("pecas tem de ser dict nome->texto")
    por_peca = {}
    sem = []
    for nome, texto in pecas.items():
        r = confere_peca(texto)
        por_peca[str(nome)] = r
        if not r["OK"]:
            sem.append(str(nome))
    sem.sort()
    return {"por_peca": por_peca, "sem_declaracao": sem,
            "OK": not sem}


def arquivos_que_importam_edicao(raiz=None):
    """Arquivos *.py da raiz que importam esta fonte unica (por AST, nunca
    substring: o nome em string de SEM_FAIXA/isencao nao e dependencia).

    Le por ast.parse (nunca substring): `import edicao_nbr6118_g123` ou
    `from edicao_nbr6118_g123 import ...`, em qualquer nivel (inclusive
    dentro de funcao, como premoldado/compatibilizacao fazem para evitar
    ciclo). O proprio modulo conta (fonte unica). So raiz (nao tests/).
    """
    import ast

    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = set()
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "edicao_nbr6118_g123.py":
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
                if any((a.name or "").split(".")[0] == "edicao_nbr6118_g123"
                       for a in no.names):
                    achados.add(caminho.name)
                    break
            elif isinstance(no, ast.ImportFrom):
                if (no.module or "").split(".")[0] == "edicao_nbr6118_g123":
                    achados.add(caminho.name)
                    break
    return achados


def confere_uso_edicao(raiz=None, esperado=None):
    """Portao 'nenhum modulo troca por conta propria' (lado dos imports).

    Compara quem importa a fonte unica com o baseline USO_ESPERADO nos dois
    sentidos: extra (import novo sem triagem) e faltando (nome morto) =
    vermelho. 'extras'/'faltando' sao os acumuladores que o teste faz
    disparar.
    """
    esp = set(USO_ESPERADO) if esperado is None else set(esperado)
    tem = set(arquivos_que_importam_edicao(raiz))
    extras = sorted(tem - esp)
    faltando = sorted(esp - tem)
    # Arquivos do esperado que sumiram do disco nao sao "faltando" de uso:
    # sao ausencia (o teste de baseline os acusa como ausentes).
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    try:
        no_disco = {p.name for p in base.glob("*.py")}
    except OSError:
        no_disco = set(tem) | esp
    ausentes = sorted(a for a in esp if a not in no_disco)
    # faltando de verdade: esperado, no disco, mas sem importar
    faltando = sorted(a for a in faltando if a not in ausentes)
    return {"OK": not (extras or faltando or ausentes),
            "extras": extras, "faltando": faltando, "ausentes": ausentes,
            "tem": sorted(tem)}


def caso_c1_furo_circular():
    """13.2.5.1-b no mesmo caso do repo pelas duas edicoes (funcao REAL).

    Caso C1 do inventario (G116): furo circular d = 125 mm em viga h = 600
    mm (h/3 = 200 mm), zona de tracao, demais condicoes atendidas.
    2014 (limite 120) -> a_confirmar; 2023+Em1 circular (limite 125) ->
    admissivel. A forma 'circular' e explicita (sem ela nao ha 125).
    """
    import compatibilizacao as co

    base = {"d_furo_mm": 125.0, "h_viga_mm": 600.0, "dist_apoio_mm": 1300.0,
            "zona_tracao": True, "dist_face_mm": 60.0, "cobrimento_mm": 25.0,
            "furo_unico": True, "armadura_seccionada": False}
    r2014 = co.avalia_furo_viga(edicao="2014", forma_furo="circular", **base)
    r2023 = co.avalia_furo_viga(edicao="2023+Em1", forma_furo="circular",
                                **base)
    return {"veredito_2014": r2014["veredito"],
            "motivos_2014": list(r2014["motivos"]),
            "clausulas_2014": list(r2014["clausulas"]),
            "veredito_2023_em1": r2023["veredito"],
            "motivos_2023_em1": list(r2023["motivos"]),
            "clausulas_2023_em1": list(r2023["clausulas"])}


def caso_c4_fckj_c60():
    """12.3.3 no mesmo caso do repo pelas duas edicoes (funcao REAL).

    Caso C4 do inventario (G116): fckj aos 7 dias, C60 CPIII.
    2014 (s = 0,38) -> 41032 kN/m2; 2023+Em1 (s = 0,20 p/ todo C60+) ->
    49124 kN/m2 (+19,7 %). Os dois numeros saem da MESMA funcao real
    (premoldado_nbr9062.fckj_idade) com a chave em cada posicao (contra
    assercao tautologica: a lente nao reimplementa a formula).
    """
    import premoldado_nbr9062 as pm

    f2014 = float(pm.fckj_idade(60e3, 7, cimento="CPIII", edicao="2014"))
    f2023 = float(pm.fckj_idade(60e3, 7, cimento="CPIII", edicao="2023+Em1"))
    return {"fckj_2014_kNm2": float(f2014),
            "fckj_2023_em1_kNm2": float(f2023)}


def main() -> int:
    print("edicoes=%s padrao=%s pontos=%d uso=%d"
          % (list(EDICOES_VALIDAS), EDICAO_PADRAO, len(MODULOS_COM_TROCA),
             len(USO_ESPERADO)))
    print("carimbo (sem parametro): %s" % carimbo_edicao(None))
    print("carimbo (2023+Em1): %s" % carimbo_edicao("2023+Em1"))
    c1 = caso_c1_furo_circular()
    print("C1 furo125 circular: 2014=%s 2023+Em1=%s"
          % (c1["veredito_2014"], c1["veredito_2023_em1"]))
    c4 = caso_c4_fckj_c60()
    print("C4 fckj C60/CPIII/7d: 2014=%.0f 2023+Em1=%.0f kN/m2"
          % (c4["fckj_2014_kNm2"], c4["fckj_2023_em1_kNm2"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
