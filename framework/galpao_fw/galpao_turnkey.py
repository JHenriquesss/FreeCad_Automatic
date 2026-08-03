# ============================================================================
# galpao_turnkey.py - O QUE ESTE SCRIPT FAZ / CALCULA
# ORQUESTRADOR-MESTRE "turnkey" do galpao industrial: um unico rodar(spec)
# dispara TODOS os verticais do sistema e consolida os vereditos numa unica
# saida. Nao recalcula nada - apenas DESPACHA para os orquestradores de cada
# disciplina e AGREGA os gates/ATENDE:
#   - "concreto"  -> galpao_concreto.rodar(spec)          (NBR 6118/6123/6122)
#   - "aco"       -> rodar_projeto.calcular(spec, out_dir) (NBR 8800/6123) *
#   - "eletrico"  -> galpao_eletrico.rodar(spec)          (NBR 5410/14039/5419)
#   - "incendio"  -> galpao_seguranca_incendio.rodar(spec)(NBR 10898/16820/17240/10897)
#   * o vertical de aco usa spec de PROJETO proprio (geometria.spans / secoes /
#     cargas) e ESCREVE arquivos; so roda quando um out_dir e' fornecido; senao e'
#     pulado com nota (nunca inventa um veredito). O MESMO shape de spec alimenta o
#     caderno_turnkey (rodar_tudo -> pranchas A1).
# PRINCIPIOS (herdados dos verticais): STATELESS (spec explicito, sem estado
# global); imports PREGUICOSOS dentro de cada adaptador -> o modulo-mestre nao
# carrega FreeCAD nem nada pesado, e uma disciplina que quebre NAO derruba as
# outras (fica isolada com 'erro'). Geometria comum e propagada a cada disciplina
# no formato que ela espera (concreto usa comprimento/vao/pe_direito; eletrico e
# incendio usam geometria={L,W,H}). Dados de projeto ausentes seguem a regra dos
# verticais (A CONFIRMAR nos proprios modulos) - o mestre nao preenche premissa.
# Veredito GLOBAL = todas as disciplinas EXECUTADAS atendem.
# CONSOLIDACAO BIM: emitir_bim(R, out_dir, spec) escreve um IFC por disciplina
# (frame nativo) + turnkey_federado.ifc com AS 4 DISCIPLINAS num frame comum
# (X=comprimento, Y=largura, Z=altura): concreto TRANSFORMADO (X=vao centrado ->
# comum) e eletrico/incendio/aco ja no frame comum (aco via ifc_emit.membros_do_spec,
# modelo_neutro X=comprimento/Y=vao). Tesoura/prismatico sem perfil -> aco so via FreeCAD.
# Unidades: as de cada vertical (sem conversao aqui).
# ============================================================================
"""Orquestrador-mestre turnkey do galpao: um rodar(spec) despacha todos os
verticais (concreto/aco/eletrico/incendio) e consolida gates + ATENDE global +
modelo BIM/IFC federado (emitir_bim)."""

from __future__ import annotations

import math


# ordem canonica de apresentacao das disciplinas no relatorio consolidado
DISCIPLINAS = ("concreto", "aco", "eletrico", "incendio", "climatizacao", "hidraulica")


def _geometria(g):
    """Normaliza a geometria comum aceitando os dois dialetos de chave usados pelos
    verticais: {comprimento, vao, pe_direito} (concreto) ou {L, W, H} (eletrico/
    incendio). Devolve o formato canonico {comprimento, vao, pe_direito} em metros."""
    g = g or {}
    comp = g.get("comprimento", g.get("L", 40.0))
    vao = g.get("vao", g.get("W", g.get("largura", 20.0)))
    pd = g.get("pe_direito", g.get("H", 6.0))
    return {"comprimento": float(comp), "vao": float(vao), "pe_direito": float(pd)}


def _norm(r):
    """Normaliza a saida de um vertical de contrato moderno (rodar(spec) ->
    {gates, reprovados, ATENDE}) para o registro consolidado do mestre."""
    return {"rodou": True, "ATENDE": bool(r["ATENDE"]),
            "reprovados": list(r.get("reprovados", [])),
            "gates": r.get("gates", {}), "raw": r}


# ------------------------------------------------------------------ adaptadores
# Cada adaptador recebe (sub_spec, geo_canonica, out_dir) e devolve um registro
# {rodou, ATENDE, reprovados, gates, raw|erro|nota}. Import preguicoso.

def _run_concreto(sub, geo, out_dir):
    import galpao_concreto as gc
    s = dict(sub)
    s.setdefault("comprimento", geo["comprimento"])
    s.setdefault("vao", geo["vao"])
    s.setdefault("pe_direito", geo["pe_direito"])
    return _norm(gc.rodar(s))


def _run_eletrico(sub, geo, out_dir):
    import galpao_eletrico as ge
    s = dict(sub)
    return _norm(ge.rodar(_com_geometria_LWH(s, geo)))


def _run_incendio(sub, geo, out_dir):
    import galpao_seguranca_incendio as gi
    s = dict(sub)
    return _norm(gi.rodar(_com_geometria_LWH(s, geo)))


def _run_climatizacao(sub, geo, out_dir):
    import galpao_climatizacao as gcl
    s = dict(sub)
    return _norm(gcl.rodar(_com_geometria_LWH(s, geo)))


def _run_hidraulica(sub, geo, out_dir):
    import galpao_hidraulica as ghi
    s = dict(sub)
    return _norm(ghi.rodar(_com_geometria_LWH(s, geo)))


def _run_aco(sub, geo, out_dir):
    """Vertical de aco: usa spec de PROJETO proprio (geometria.spans/secoes/cargas) e
    ESCREVE arquivos -> so roda com out_dir. Sem out_dir, e' pulado com nota (nao
    inventa). Usa rodar_projeto.calcular (que valida via exigir_completo, converte com
    to_rodar_params e chama rodar_galpao) -> MESMO shape de spec que o caderno usa p/
    gerar as pranchas (rodar_tudo). O res traz atende_global/falhas_verificacao."""
    if not out_dir:
        return {"rodou": False, "ATENDE": None, "reprovados": [], "gates": {},
                "nota": "vertical de aco requer out_dir (gera arquivos) - nao executado"}
    import os
    import copy
    import rodar_projeto as RP
    s_enr = copy.deepcopy(sub)                            # calcular ENRIQUECE s_enr in-place
    res = RP.calcular(s_enr, os.path.join(out_dir, "aco"))  # grava estrutura.perfil_*_adotado
    falhas = res.get("falhas_verificacao", [])            # [(nome, util), ...]
    atende = res.get("atende_global", res.get("atende"))
    gates = {nome: {"util": float(u), "OK": float(u) <= 1.001} for nome, u in falhas}
    return {"rodou": True, "ATENDE": bool(atende) if atende is not None else None,
            "reprovados": [nome for nome, u in falhas if float(u) > 1.001],
            "gates": gates, "raw": res, "spec_enriquecido": s_enr}


def _com_geometria_LWH(s, geo):
    """Preenche s['geometria'] = {L, W, H} a partir da geometria canonica, sem
    sobrescrever o que o usuario ja informou."""
    g = dict(s.get("geometria", {}))
    g.setdefault("L", geo["comprimento"])
    g.setdefault("W", geo["vao"])
    g.setdefault("H", geo["pe_direito"])
    s["geometria"] = g
    return s


_ADAPTADORES = {"concreto": _run_concreto, "aco": _run_aco,
                "eletrico": _run_eletrico, "incendio": _run_incendio,
                "climatizacao": _run_climatizacao, "hidraulica": _run_hidraulica}


# ------------------------------------------------------------------- mestre
def rodar(spec, out_dir=None):
    """Despacha todos os verticais presentes no spec e consolida os vereditos.
    spec: {
      'geometria': {comprimento/L, vao/W, pe_direito/H} (m) - comum a todas as
                   disciplinas; cada uma usa o que precisa,
      'concreto' : sub-spec de galpao_concreto.rodar   (opc),
      'aco'      : spec de PROJETO de aco (rodar_projeto)(opc; requer out_dir),
      'eletrico' : sub-spec de galpao_eletrico.rodar    (opc),
      'incendio' : sub-spec de galpao_seguranca_incendio.rodar (opc),
    }
    out_dir (opc): pasta de saida do vertical de aco (que escreve arquivos).
    Retorna R com R['disciplinas'][nome] = {rodou, ATENDE, reprovados, gates, ...},
    R['executadas'], R['reprovados'] (disciplinas que reprovam) e R['ATENDE']
    (todas as executadas atendem). Uma disciplina que lance excecao fica ISOLADA
    com 'erro' e reprova, sem derrubar as demais."""
    geo = _geometria(spec.get("geometria", {}))
    disciplinas = {}
    for nome in DISCIPLINAS:
        if nome not in spec:
            continue
        try:
            disciplinas[nome] = _ADAPTADORES[nome](spec[nome], geo, out_dir)
        except Exception as e:                            # isola a falha da disciplina
            disciplinas[nome] = {"rodou": False, "ATENDE": False, "reprovados": ["ERRO"],
                                 "gates": {}, "erro": "%s: %s" % (type(e).__name__, e)}

    executadas = [n for n in DISCIPLINAS if disciplinas.get(n, {}).get("rodou")]
    puladas = [n for n in disciplinas if not disciplinas[n].get("rodou")]
    reprovados = [n for n in disciplinas
                  if disciplinas[n].get("ATENDE") is False]
    R = {"geometria": geo, "disciplinas": disciplinas, "executadas": executadas,
         "puladas": puladas, "reprovados": reprovados,
         "ATENDE": len(executadas) > 0 and len(reprovados) == 0}
    return R


# ============================== BIM / IFC FEDERADO ===========================
# Consolida os modelos BIM das disciplinas apos rodar(): (1) um IFC por disciplina
# no frame NATIVO de cada uma (garantidamente correto) e (2) um IFC FEDERADO com
# concreto+eletrico+incendio num frame COMUM. Frame comum = X=comprimento[0..],
# Y=largura[0..vao], Z=altura (o de eletrico/incendio). O concreto usa X=vao(centrado
# em 0), Y=comprimento -> e' transformado p/ o comum: [x,y,z] -> [y, x+vao/2, z] (e as
# dims de caixa trocam B<->L, rotacao de 90). O aco vem de outro pipeline (spec de
# projeto -> ifc puro FreeCAD-free) e sai como arquivo SEPARADO (nao entra no federado,
# que exige o contrato membros_bim(raw)) - declarado no manifesto, nunca fingido.

def _concreto_no_frame_comum(membros, vao_concreto_m):
    """Transforma membros do concreto (X=vao centrado, Y=comprimento) p/ o frame comum
    (X=comprimento, Y=largura>=0). Ponto [x,y,z]->[y, x+vao/2*1000, z]; caixa troca as
    dims de planta B<->L (a rotacao de 90 leva a extensao em X para Y)."""
    dy = vao_concreto_m / 2.0 * 1000.0
    out = []
    for m in membros:
        mm = dict(m)
        for chave in ("p1", "p2", "centro"):
            if chave in mm:
                x, y, z = mm[chave]
                mm[chave] = [y, x + dy, z]
        if "dims" in mm:
            B, Lp, h = mm["dims"]
            mm["dims"] = [Lp, B, h]
        mm["marca"] = "C-" + str(mm.get("marca", ""))
        out.append(mm)
    return out


def _membros_federados(R, spec=None):
    """Reune os membros das disciplinas no frame comum (X=comprimento, Y=largura, Z=
    altura). concreto (TRANSFORMADO) + eletrico + incendio + aco. Aco vem de
    ifc_emit.membros_do_spec(spec['aco']) e ja esta no frame comum (modelo_neutro:
    X=comprimento, Y=vao) -> sem transformacao. Marca prefixada por disciplina
    (C-/E-/I-/A-). Retorna (membros, disciplinas_contribuintes)."""
    membros = []
    disc = []
    d = R["disciplinas"]
    if d.get("concreto", {}).get("rodou"):
        import galpao_concreto as gc
        raw = d["concreto"]["raw"]
        membros += _concreto_no_frame_comum(gc.membros_bim(raw), raw["spec"]["vao"])
        disc.append("concreto")
    if d.get("eletrico", {}).get("rodou"):
        import galpao_eletrico as ge
        for m in ge.membros_bim(d["eletrico"]["raw"]):
            m = dict(m); m["marca"] = "E-" + str(m.get("marca", "")); membros.append(m)
        disc.append("eletrico")
    if d.get("incendio", {}).get("rodou"):
        import galpao_seguranca_incendio as gi
        for m in gi.membros_bim(d["incendio"]["raw"]):
            m = dict(m); m["marca"] = "I-" + str(m.get("marca", "")); membros.append(m)
        disc.append("incendio")
    if d.get("climatizacao", {}).get("rodou"):
        import galpao_climatizacao as gcl
        for m in gcl.membros_bim(d["climatizacao"]["raw"]):
            m = dict(m); m["marca"] = "H-" + str(m.get("marca", "")); membros.append(m)
        disc.append("climatizacao")
    if d.get("hidraulica", {}).get("rodou"):
        import galpao_hidraulica as ghi
        for m in ghi.membros_bim(d["hidraulica"]["raw"]):
            m = dict(m); m["marca"] = "P-" + str(m.get("marca", "")); membros.append(m)
        disc.append("hidraulica")
    # aco: mesmo frame (modelo_neutro X=comprimento, Y=vao) -> sem transformar. Prefere o
    # spec ENRIQUECIDO pelo calculo (perfil_col/raf_adotado); senao o spec['aco'] cru (so
    # federa se o usuario ja o enriqueceu). None se tesoura/prismatico sem perfil.
    spec_aco = ((d.get("aco") or {}).get("spec_enriquecido")
                or (spec.get("aco") if spec else None))
    if spec_aco:
        import ifc_emit
        mem_aco = ifc_emit.membros_do_spec(spec_aco)
        if mem_aco:
            for m in mem_aco:
                m = dict(m); m["marca"] = "A-" + str(m.get("marca", "")); membros.append(m)
            disc.append("aco")
    return membros, disc


def emitir_bim(R, out_dir, spec=None, nome="GalpaoTurnkey"):
    """Emite os modelos BIM/IFC do projeto turnkey a partir de rodar(spec)=R.
    Escreve em out_dir/bim/: um IFC por disciplina (frame nativo) + turnkey_federado.ifc
    (concreto+eletrico+incendio no frame comum). O aco (se spec['aco'] dado) sai como
    aco.ifc por seu proprio pipeline (nao entra no federado). Retorna um MANIFESTO
    {dir, arquivos:{disc->path}, federado, disciplinas_federadas, nota_aco}. Sem
    ifcopenshell -> {erro}. Nao levanta por disciplina: registra o que saiu."""
    import os
    import ifc_emit
    if not ifc_emit.disponivel():
        return {"erro": "ifcopenshell ausente - IFC nao emitido"}
    bimdir = os.path.join(str(out_dir), "bim")
    os.makedirs(bimdir, exist_ok=True)
    arquivos = {}
    d = R["disciplinas"]

    # 1) um IFC por disciplina no frame NATIVO (via o emitir_bim de cada vertical)
    _mods = {"concreto": "galpao_concreto", "eletrico": "galpao_eletrico",
             "incendio": "galpao_seguranca_incendio"}
    for nome_d, modname in _mods.items():
        if not d.get(nome_d, {}).get("rodou"):
            continue
        try:
            mod = __import__(modname)
            p = os.path.join(bimdir, "%s.ifc" % nome_d)
            if mod.emitir_bim(d[nome_d]["raw"], p):
                arquivos[nome_d] = p
        except Exception as e:
            arquivos[nome_d] = "ERRO: %s: %s" % (type(e).__name__, e)

    # 2) aco: pipeline proprio (spec de projeto -> IFC puro), tambem como arquivo proprio.
    # Prefere o spec ENRIQUECIDO pelo calculo (perfis adotados); senao o spec['aco'] cru.
    nota_aco = None
    spec_aco = ((d.get("aco") or {}).get("spec_enriquecido")
                or (spec.get("aco") if spec else None))
    if spec_aco:
        try:
            p = os.path.join(bimdir, "aco.ifc")
            if ifc_emit.emitir_ifc_do_spec(spec_aco, p):
                arquivos["aco"] = p
            else:
                nota_aco = ("aco nao emitido pelo caminho puro (tesoura/prismatico sem perfil "
                            "adotado -> requer FreeCAD; ou spec['aco'] cru sem calculo)")
        except Exception as e:
            nota_aco = "aco: %s: %s" % (type(e).__name__, e)
    elif "aco" in d:
        nota_aco = "spec['aco'] nao fornecido a emitir_bim -> aco.ifc nao gerado"

    # 3) modelo FEDERADO (frame comum) - todas as disciplinas com membros no frame comum
    federado = None
    membros, disc_fed = _membros_federados(R, spec)
    if membros:
        federado = os.path.join(bimdir, "turnkey_federado.ifc")
        ifc_emit.emitir_ifc(membros, federado, nome=nome, secao_em_metros=True)

    return {"dir": bimdir, "arquivos": arquivos, "federado": federado,
            "disciplinas_federadas": disc_fed, "n_membros_federados": len(membros),
            "nota_aco": nota_aco}


def montar_3d_federado(R, out_dir, spec=None, doc_name="galpao_federado",
                       headless=None, host="http://localhost:9875", timeout=600):
    """Constroi o MODELO 3D SOLIDO FEDERADO (FreeCAD) das disciplinas num UNICO doc e
    roda a interferencia REAL (OCCT) ENTRE disciplinas. Envia build_federado.py como
    FONTE + os membros federados (frame comum) como PAYLOAD DE DADOS - reusa o despacho
    bridge/headless do rodar_projeto (fallback automatico + kill de zumbi). Exporta
    FCStd+STEP+IFC. Retorna o dict de rodar_projeto._montar_* ({result:{...}} | {erro}).
    None-membros -> {erro}. headless: None tenta bridge e cai p/ freecadcmd."""
    import os
    import rodar_projeto as RP
    import framework as FW
    membros, _ = _membros_federados(R, spec)
    if not membros:
        return {"erro": "sem membros federados (nenhuma disciplina com membros_bim)"}
    bk = {"membros": membros, "export_dir": str(out_dir).replace("\\", "/"),
          "doc_name": doc_name}
    src_path = FW.raiz_repo() / "framework" / "galpao_fw" / "build_federado.py"
    src = RP._ship_build_src(src_path)
    if headless is None:
        headless = os.environ.get("FREECAD_HEADLESS", "").strip() in ("1", "true", "True")
    if headless:
        return RP._montar_headless(src, bk, out_dir, timeout)
    import xmlrpc.client
    try:
        return RP._montar_bridge(src, bk, host, timeout)
    except (OSError, xmlrpc.client.ProtocolError) as e:
        import sys
        print("[montar_3d_federado] bridge indisponivel (%s); caindo p/ headless" % e,
              file=sys.stderr)
        return RP._montar_headless(src, bk, out_dir, timeout)


def render_federado(R, out_dir, spec=None, doc_name="galpao_federado",
                    freecad_exe=None, timeout=600):
    """RENDER-AND-LOOK do modelo federado: lanca o freecad.exe GRAFICO (GuiUp) sobre os
    membros federados e salva PNGs (isometrica/frontal/superior) em out_dir/vistas via
    build_federado._capturar_vistas. Diferente do montar_3d_federado (freecadcmd headless,
    sem GUI -> sem imagem). Retorna {vistas:[png...], n_solidos, ...} | {erro}. Mesma
    mecanica de montar_pranchas (freecad.exe destacado + status json + kill de zumbi)."""
    import os
    import json
    import time
    import tempfile
    import subprocess
    import rodar_projeto as RP
    import framework as FW

    exe = freecad_exe or os.environ.get("FREECAD_EXE") or \
        r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe"
    if not os.path.exists(exe):
        return {"erro": "freecad.exe nao encontrado: %s" % exe}
    membros, _ = _membros_federados(R, spec)
    if not membros:
        return {"erro": "sem membros federados"}

    outp = str(out_dir).replace("\\", "/")
    os.makedirs(str(out_dir), exist_ok=True)
    galpao = str(FW.raiz_repo() / "framework" / "galpao_fw").replace("\\", "/")
    memf = os.path.join(str(out_dir), "_fed_membros.json")
    with open(memf, "w", encoding="utf-8") as f:
        json.dump(membros, f)
    status = os.path.join(str(out_dir), "_fed_render_status.json")
    try:
        os.remove(status)
    except OSError:
        pass

    boot = (
        "# -*- coding: utf-8 -*-\n"
        "import sys, os, json\n"
        "sys.path.insert(0, r'%s')\n" % galpao +
        "import build_federado as B\n"
        "B.reset()\n"
        "mem = json.load(open(r'%s', encoding='utf-8'))\n" % memf.replace("\\", "/") +
        "B.configurar(membros=mem, export_dir=r'%s', doc_name='%s')\n" % (outp, doc_name) +
        "res = B.run()\n"
        "json.dump(res, open(r'%s', 'w', encoding='utf-8'), default=str)\n" % status.replace("\\", "/") +
        "try:\n    import FreeCADGui as G; G.getMainWindow().close()\nexcept Exception: pass\n"
    )
    bf = tempfile.NamedTemporaryFile(mode="w", suffix="_fedrender.py",
                                     delete=False, encoding="utf-8")
    bf.write(boot)
    bf.close()

    proc = subprocess.Popen([exe, bf.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    res = None
    try:
        while time.time() - t0 < timeout:
            if os.path.exists(status):
                time.sleep(0.5)
                with open(status, encoding="utf-8") as f:
                    res = json.load(f)
                break
            if proc.poll() is not None and not os.path.exists(status):
                time.sleep(2)
                if os.path.exists(status):
                    with open(status, encoding="utf-8") as f:
                        res = json.load(f)
                else:
                    res = {"erro": "freecad.exe encerrou sem status"}
                break
            time.sleep(2)
        if res is None:
            res = {"erro": "timeout %ss no render federado" % timeout}
    finally:
        RP._matar_processo_freecad(proc)
        try:
            os.unlink(bf.name)
        except OSError:
            pass
    return res


# ============================ CLASH DETECTION FEDERADO =======================
# Interferencia ENTRE disciplinas sobre o modelo federado (frame comum). Cada vertical
# ja checa a interferencia DENTRO de si (checa_interferencia/AABB); aqui pegamos os
# conflitos ENTRE disciplinas - o payload de engenharia do BIM federado: eletrocalha
# cruzando rafter, chuveiro dentro de viga, hidrante batendo em pilar, descida SPDA na
# terca. Puro-Python (AABB), testavel em CI. Convencao de dims por disciplina:
# ESTRUTURAL (concreto/aco) em metros (x1000); INSTALACOES (eletrico/incendio) em mm.
# Secao de BARRA sempre em metros (x1000) em todas. Sao CANDIDATOS p/ o coordenador
# triar: alguns conflitos sao montagem intencional (ex.: descida SPDA rente ao pilar).

# escala das dims de CAIXA por disciplina p/ mm: concreto guarda em METROS (x1000); aco
# (modelo_neutro), eletrico, incendio e climatizacao ja em MM (x1). Secao de BARRA e'
# sempre m (a parte).
_ESCALA_M = {"concreto": 1000.0, "aco": 1.0, "eletrico": 1.0, "incendio": 1.0,
             "climatizacao": 1.0, "hidraulica": 1.0}
_DISC_DE_MARCA = {"C": "concreto", "E": "eletrico", "I": "incendio", "A": "aco",
                  "H": "climatizacao", "P": "hidraulica"}
_TIPOS_IGNORADOS_CLASH = {"Covering", "Cladding"}   # fechamento/telha: overlap esperado

# Triagem esperado x revisar: o aterramento e o SPDA (cabo de aterramento/anel, descida,
# captacao) sao MONTADOS na estrutura POR NORMA (NBR 5419: descidas nas colunas, malha/
# hastes junto as fundacoes) -> interferencia com pilar/viga/sapata e' montagem
# INTENCIONAL, nao conflito a resolver. Ja eletrocalha (CableCarrier) e equipamentos
# (chuveiro/detector/luminaria/hidrante) sobre a estrutura sao coordenacao REAL.
_TIPOS_ESTRUTURA = {"Column", "Beam", "Member", "Footing", "Pile", "Plate"}
_TIPOS_ATERR_SPDA = {"Cable", "Earthing"}


def _clash_esperado(ta, tb):
    """True se o par de tipos e' montagem INTENCIONAL: aterramento/SPDA fixado a
    estrutura (NBR 5419). Caso contrario e' candidato a REVISAR."""
    s = {ta, tb}
    return bool(s & _TIPOS_ATERR_SPDA) and bool(s & _TIPOS_ESTRUTURA)


def _disc_de_membro(mb):
    """Disciplina de um membro federado pela marca prefixada (C-/E-/I-/A-)."""
    return _DISC_DE_MARCA.get(str(mb.get("marca", ""))[:1])


def _aabb_barra(p1, p2, bf, d):
    """AABB (mm) da CAIXA ORIENTADA de uma barra: prisma de secao bf x d ao longo de
    p1->p2. Engorda a secao nos DOIS eixos PERPENDICULARES a direcao (nao em X/Y fixos)
    -> viga horizontal ganha espessura em Z, nao zero. Consistente com o solido do
    build_federado (OCCT). Pure-Python."""
    L = math.dist(p1, p2)
    if L <= 0:
        return None
    u = tuple((b - a) / L for a, b in zip(p1, p2))         # direcao
    helper = (0.0, 0.0, 1.0) if abs(u[2]) < 0.9 else (1.0, 0.0, 0.0)

    def _cross(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0])

    def _norm(a):
        n = math.sqrt(sum(c * c for c in a)) or 1.0
        return tuple(c / n for c in a)

    v = _norm(_cross(u, helper))                           # 1o eixo da secao
    w = _norm(_cross(u, v))                                # 2o eixo da secao
    xs, ys, zs = [], [], []
    for s in (0.0, L):
        for a in (-bf / 2.0, bf / 2.0):
            for b in (-d / 2.0, d / 2.0):
                pt = tuple(p1[k] + s * u[k] + a * v[k] + b * w[k] for k in range(3))
                xs.append(pt[0]); ys.append(pt[1]); zs.append(pt[2])
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _aabb_federado(mb, disc):
    """AABB (x0,x1,y0,y1,z0,z1) em mm de um membro federado. Caixa: dims escaladas pela
    convencao da disciplina (estrutural m, instalacoes mm). Barra: caixa ORIENTADA
    (secao perpendicular a p1->p2). None p/ painel (poligono) ou membro sem geometria."""
    if "poligono" in mb:
        return None                                     # painel de fechamento: ignorado
    if "dims" in mb and "centro" in mb:
        sc = _ESCALA_M.get(disc, 1.0)
        B, L, h = (mb["dims"][0] * sc, mb["dims"][1] * sc, mb["dims"][2] * sc)
        cx, cy, cz = mb["centro"]
        return (cx - B / 2, cx + B / 2, cy - L / 2, cy + L / 2, cz - h / 2, cz + h / 2)
    if "p1" in mb and "p2" in mb and "secao" in mb:
        s = mb["secao"]
        bf = s.get("bf", s.get("D", 0.02)) * 1000.0     # ROUND usa D nos dois eixos
        d = s.get("d", s.get("D", 0.02)) * 1000.0
        return _aabb_barra(mb["p1"], mb["p2"], bf, d)
    return None


def _overlap_vol(a, b, folga=1.0):
    """Volume de interpenetracao de dois AABB (mm3). folga (mm) ignora toques de face."""
    dx = min(a[1], b[1]) - max(a[0], b[0]) - folga
    dy = min(a[3], b[3]) - max(a[2], b[2]) - folga
    dz = min(a[5], b[5]) - max(a[4], b[4]) - folga
    return dx * dy * dz if (dx > 0 and dy > 0 and dz > 0) else 0.0


def checa_interferencia_federada(R, spec=None, folga=1.0, vol_min=1000.0):
    """Varredura de interferencia ENTRE disciplinas no modelo federado.
    R = rodar(spec); spec (opc) traz o aco. folga (mm) ignora toques; vol_min (mm3)
    despreza grazes triviais. So pares de disciplinas DIFERENTES (o intra-disciplina e'
    responsabilidade de cada vertical). Retorna {n_membros, n_clashes, clashes:[{a,b,
    disciplinas,tipos,vol_mm3}], por_par, OK}. OK=True se nenhum clash > vol_min - mas
    os clashes sao CANDIDATOS (alguns sao montagem intencional), nao reprovacao de
    calculo (nao entra no ATENDE do rodar)."""
    membros, _ = _membros_federados(R, spec)
    caixas = []
    for mb in membros:
        disc = _disc_de_membro(mb)
        if disc is None or mb.get("tipo") in _TIPOS_IGNORADOS_CLASH:
            continue
        box = _aabb_federado(mb, disc)
        if box is not None:
            caixas.append((mb.get("marca", mb.get("tipo")), disc, mb.get("tipo"), box))
    clashes = []
    por_par = {}
    for i in range(len(caixas)):
        ma, da, ta, ba = caixas[i]
        for j in range(i + 1, len(caixas)):
            mb_, db, tb, bb = caixas[j]
            if da == db:                                # intra-disciplina: fora do escopo
                continue
            v = _overlap_vol(ba, bb, folga)
            if v > vol_min:
                par = "x".join(sorted((da, db)))
                por_par[par] = por_par.get(par, 0) + 1
                clashes.append({"a": ma, "b": mb_, "disciplinas": par,
                                "tipos": "%sx%s" % (ta, tb), "vol_mm3": round(v, 0),
                                "esperado": _clash_esperado(ta, tb)})
    clashes.sort(key=lambda c: (c["esperado"], -c["vol_mm3"]))   # revisar primeiro
    revisar = [c for c in clashes if not c["esperado"]]
    esperados = [c for c in clashes if c["esperado"]]
    return {"n_membros": len(caixas), "n_clashes": len(clashes),
            "n_revisar": len(revisar), "n_esperado": len(esperados),
            "clashes": clashes, "revisar": revisar, "esperados": esperados,
            "por_par": por_par, "OK": not clashes, "OK_revisar": not revisar}


def relatorio_clash_pt(rep):
    """Relatorio pt-BR do clash federado com TRIAGEM esperado x revisar."""
    L = ["CLASH FEDERADO - INTERFERENCIA ENTRE DISCIPLINAS (coordenacao)",
         "  %d membros ; %d conflitos = %d A REVISAR + %d esperados (montagem)" %
         (rep["n_membros"], rep["n_clashes"], rep.get("n_revisar", 0),
          rep.get("n_esperado", 0))]
    if rep["por_par"]:
        L.append("  Por par de disciplinas: " +
                 " ; ".join("%s=%d" % (k, v) for k, v in sorted(rep["por_par"].items())))
    rev = rep.get("revisar", [c for c in rep["clashes"] if not c.get("esperado")])
    if rev:
        L.append("  --- A REVISAR (coordenacao real): ---")
        for c in rev[:30]:
            L.append("   ! %-14s x %-14s [%s] %s : %.0f mm3"
                     % (c["a"], c["b"], c["disciplinas"], c["tipos"], c["vol_mm3"]))
        if len(rev) > 30:
            L.append("   ... (+%d a revisar)" % (len(rev) - 30))
    esp = rep.get("esperados", [c for c in rep["clashes"] if c.get("esperado")])
    if esp:
        L.append("  --- ESPERADOS (aterramento/SPDA na estrutura, NBR 5419 - %d): ---"
                 % len(esp))
        for c in esp[:10]:
            L.append("   . %-14s x %-14s %s : %.0f mm3"
                     % (c["a"], c["b"], c["tipos"], c["vol_mm3"]))
        if len(esp) > 10:
            L.append("   ... (+%d esperados)" % (len(esp) - 10))
    if not rep["n_clashes"]:
        L.append("  RESULTADO: nenhuma interferencia entre disciplinas > limite")
    elif not rev:
        L.append("  RESULTADO: %d conflitos, TODOS montagem intencional - nada a revisar"
                 % rep["n_clashes"])
    else:
        L.append("  RESULTADO: %d A REVISAR (+%d esperados) - triar o leiaute real"
                 % (len(rev), len(esp)))
    return "\n".join(L)


def relatorio_pt(R):
    """Quadro-resumo consolidado das disciplinas do galpao turnkey."""
    geo = R["geometria"]
    L = ["PROJETO TURNKEY - GALPAO INDUSTRIAL (quadro-resumo consolidado)",
         "  Geometria comum: %.0f x %.0f m ; pe-direito %.1f m"
         % (geo["comprimento"], geo["vao"], geo["pe_direito"]),
         "  Disciplinas:"]
    rotulo = {"concreto": "Estrutura de concreto (NBR 6118/6122)",
              "aco": "Estrutura de aco (NBR 8800/6123)",
              "eletrico": "Instalacoes eletricas (NBR 5410/14039/5419)",
              "incendio": "Seguranca contra incendio (NBR 10898/16820/17240/10897)",
              "climatizacao": "Climatizacao / HVAC (NBR 16401)",
              "hidraulica": "Hidraulica predial (coordenacao; sizing pendente)"}
    for nome in DISCIPLINAS:
        d = R["disciplinas"].get(nome)
        if d is None:
            continue
        if not d.get("rodou"):
            motivo = d.get("erro") or d.get("nota") or "nao executada"
            L.append("   - %-45s PULADA (%s)" % (rotulo[nome], motivo))
            continue
        if d["ATENDE"]:
            L.append("   - %-45s ATENDE" % rotulo[nome])
        else:
            L.append("   - %-45s REPROVA -> %s"
                     % (rotulo[nome], ", ".join(d["reprovados"]) or "?"))
    if not R["executadas"]:
        L.append("  RESULTADO: nenhuma disciplina executada")
    elif R["ATENDE"]:
        L.append("  RESULTADO GLOBAL: ATENDE (todas as %d disciplinas executadas)"
                 % len(R["executadas"]))
    else:
        L.append("  RESULTADO GLOBAL: REPROVA -> %s" % ", ".join(R["reprovados"]))
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    """Afere a consolidacao com os tres verticais de contrato moderno (puro/CI).
    Nao invoca o vertical de aco (escreve arquivos) nem FreeCAD."""
    spec = {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        # concreto com seu proprio vao/vento/solo (galpao de concreto tipico que
        # ATENDE); a geometria comum so preenche o que a disciplina nao informar.
        "concreto": {"vao": 10.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                     "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                     "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3, "sigma_solo_adm": 250.0},
        "eletrico": {"tensao_V": 380.0,
                     "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2}],
                                "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
        "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                     "deteccao": {"viga_m": 0.0},
                     "sprinklers": {"altura_estoque_m": 3.0}},
    }
    R = rodar(spec)
    # as tres disciplinas modernas executaram
    assert set(R["executadas"]) == {"concreto", "eletrico", "incendio"}, R["executadas"]
    # geometria comum propagada ao incendio (galpao 40x20x6 -> 6 pontos de aclaramento)
    inc = R["disciplinas"]["incendio"]["raw"]
    assert inc["gates"]["iluminacao_emergencia"]["N_aclaramento"] == 6
    # geometria comum propagada ao eletrico via geometria={L,W,H}
    ele = R["disciplinas"]["eletrico"]["raw"]
    assert ele["gates"]["luminotecnica"]["OK"]
    # veredito global = AND dos verticais
    esperado = all(R["disciplinas"][n]["ATENDE"] for n in R["executadas"])
    assert R["ATENDE"] == esperado
    # aco sem out_dir -> pulado, com nota, NUNCA inventado
    R2 = rodar(dict(spec, aco={"qualquer": 1}))
    assert "aco" in R2["puladas"] and R2["disciplinas"]["aco"]["ATENDE"] is None
    assert "requer out_dir" in R2["disciplinas"]["aco"]["nota"]
    # uma disciplina que quebra fica ISOLADA e reprova, sem derrubar as outras
    R3 = rodar({"geometria": spec["geometria"], "incendio": spec["incendio"],
                "eletrico": "spec_invalido_de_proposito"})
    assert R3["disciplinas"]["eletrico"]["rodou"] is False
    assert "erro" in R3["disciplinas"]["eletrico"]
    assert R3["disciplinas"]["incendio"]["rodou"] is True    # a outra seguiu
    assert R3["ATENDE"] is False                             # a quebrada reprova
    print(relatorio_pt(R))
    print("galpao_turnkey self-test PASSED")


if __name__ == "__main__":
    _selftest()
