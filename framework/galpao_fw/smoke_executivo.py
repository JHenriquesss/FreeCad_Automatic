# ============================================================================
# smoke_executivo.py - Smoke test do gerador de pranchas (techdraw_exec).
# Constroi varias configuracoes GEOMETRICAS de galpao de ponta a ponta, TODAS
# headless (calculo em python; 3D via freecadcmd; pranchas via freecad.exe),
# e verifica que cada uma produz as 9 pranchas sem erro. NAO precisa do MCP.
#
# Cobre o espaco de geometria que o build_galpao gera:
#   - padrao (comprimento > vao)
#   - vao > comprimento (inverte os eixos)  [regressao do bug comp_x]
#   - baixo e largo
#   - com ponte rolante (console + viga de rolamento)
#   - fundacao PROFUNDA (estaca + bloco de coroamento + viga de baldrame no 3D)
# (escada / plataforma sao calc-only: nao mudam o 3D.)
#
# Uso:  python smoke_executivo.py
# ============================================================================
import os
import sys
import json
import tempfile
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rodar_projeto as RP
import projeto_spec as PS
import framework as FW
import techdraw_exec as TD
import relatorio_calculo as RC

FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


_PERFIL_SPT = [                     # sondagem exemplo (dado de sitio) topo->ponta
    {"tipo": "argila_siltosa", "N": 5, "dz": 3.0},
    {"tipo": "silte_arenoso", "N": 12, "dz": 4.0},
    {"tipo": "areia_siltosa", "N": 25, "dz": 5.0},
]


def _spec(slug, span, comp, eave, ridge, ponte=None, fundacao="sapata",
          tipo_portico="prismatico", tapered=None, trelica=None):
    s = PS.novo()
    s['slug'] = slug
    s['terreno'].update(area_lote_m2=4000, to_max=0.6, ca_max=1.0, tp_min=0.2,
                        recuos={'frente': 5, 'lateral': 3, 'fundos': 3})
    s['geometria'].update(span=span, comprimento=comp, eave=eave, ridge=ridge,
                          bay=5, base_fixed=True)
    s['cobertura'].update(aguas=2, slope=0.10, telha_tipo='trapezoidal',
                          telha_peso=0.10, calha=True)
    s['fechamento'].update(tipo='telha', altura_alvenaria=0, peso=0.05,
                          mesa_interna_travada=True, n_maos_francesas=2)
    s['aberturas'] = {'portao_frente': (4000, 4500), 'porta_fundo': (900, 2130),
                      'janelas_laterais': (4300, 5300)}
    s['vento'].update(v0=40, cat='II', classe='B', s3=0.95, z=eave + 0.5,
                      abertura_dominante='portao_oitao')
    s['ponte'] = ponte
    s['cargas'].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
    s['fundacao']['sigma_solo_adm'] = 200.0
    s['fundacao']['tipo'] = fundacao
    if fundacao == 'estaca':                 # fundacao profunda (SPT da sondagem)
        s['fundacao']['estaca'] = {
            'perfil_spt': [dict(c) for c in _PERFIL_SPT],
            'tipo_estaca': 'pre_moldada', 'D': 0.30, 'L': 10.0, 'FS': 3.0,
            'bloco': {'a_pilar': 0.30, 'fck': 25e3, 'fyk': 500e3}}
        s['baldrame'] = {'b': 0.20, 'h': 0.40, 'q_parede': 0.0,
                         'continuidade': 'simples'}
    s['estrutura']['tipo_portico'] = tipo_portico
    if tapered is not None:
        s['estrutura']['tapered'] = tapered
    if trelica is not None:
        s['estrutura']['trelica'] = trelica
    return s


def _build_3d(spec, out, doc_name):
    """3D via freecadcmd (headless, sem MCP). Retorna path do FCStd."""
    bk = PS.to_build_kwargs(spec)
    bk['export_dir'] = str(out).replace('\\', '/')
    bk['doc_name'] = doc_name
    import rodar_projeto as _RP
    _bgp = FW.raiz_repo() / 'framework' / 'galpao_fw' / 'build_galpao.py'
    # build_galpao vai como FONTE p/ o FreeCAD -> seus imports de irmaos
    # (mao_francesa_geom) exigem o dir no sys.path (senao ModuleNotFound). Helper unico.
    src = _RP._ship_build_src(_bgp)
    stf = os.path.join(str(out), '_build.json').replace('\\', '/')
    boot = (src + "\nimport json\nreset()\nconfigurar(**%r)\n_r = run()\n"
            "open(%r, 'w', encoding='utf-8').write(json.dumps(_r, default=str))\n"
            % (bk, stf))
    bp = tempfile.NamedTemporaryFile(mode='w', suffix='_b.py', delete=False,
                                     encoding='utf-8')
    bp.write(boot); bp.close()
    subprocess.run([FREECADCMD, bp.name], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=600)
    os.unlink(bp.name)
    if not os.path.exists(stf):
        return None
    r = json.load(open(stf, encoding='utf-8'))
    if isinstance(r, dict) and r.get('por_grupo'):
        spec.setdefault('estrutura', {})['takeoff'] = r['por_grupo']
    return r.get('fcstd') if isinstance(r, dict) else None


PONTE = {'Q': 50.0, 'peso_ponte': 30.0, 'peso_trole': 8.0, 'aprox_min': 1.0,
         'n_rodas_lado': 2, 'n_rodas_motoras': 2, 'phi': 1.10, 'frac_lateral': 0.10,
         'frac_long': 0.10, 'Hvr': 4.5, 'excentricidade': 0.3}

CASOS = [
    ("padrao",   dict(span=10, comp=20, eave=6, ridge=6.5)),
    ("vao_maior", dict(span=18, comp=12, eave=7, ridge=7.9)),
    ("baixo_largo", dict(span=8, comp=30, eave=4, ridge=4.4)),
    ("ponte",    dict(span=15, comp=20, eave=7, ridge=7.75, ponte=PONTE)),
    # fundacao PROFUNDA: estaca + bloco de coroamento + viga de baldrame no 3D.
    ("estaca",   dict(span=10, comp=20, eave=6, ridge=6.5, fundacao="estaca")),
    # PORTICO de alma variavel (misula tapered): rafter em loft + analise variavel.
    ("alma_var", dict(span=10, comp=20, eave=6, ridge=6.5, tipo_portico="alma_variavel",
                      tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "bf": 0.20,
                               "tw": 0.008, "tf": 0.0125})),
    # PORTICO trelicado (tesoura): analise por metodo dos nos + barras no 3D.
    ("tesoura",  dict(span=20, comp=30, eave=6, ridge=8, tipo_portico="tesoura",
                      trelica={"h": 2.5, "n_paineis": 8, "tipo": "warren",
                               "perfil_banzo": (0.150, 0.100, 0.006, 0.009),
                               "perfil_diagonal": (0.100, 0.075, 0.005, 0.008)})),
]


def _acha_pendente(v, caminho="cfg"):
    """Anda no cfg e retorna o 1o caminho cujo valor string seja PENDENTE."""
    if isinstance(v, str):
        return caminho if v == PS.PENDENTE else None
    if isinstance(v, dict):
        for k, sub in v.items():
            r = _acha_pendente(sub, "%s.%s" % (caminho, k))
            if r:
                return r
    elif isinstance(v, (list, tuple)):
        for i, sub in enumerate(v):
            r = _acha_pendente(sub, "%s[%d]" % (caminho, i))
            if r:
                return r
    return None


def checar_carimbo():
    """Pre-flight SEM freecad: garante que nenhum campo do cfg vaza
    __PENDENTE__ para as pranchas (regressao do carimbo). Instantaneo."""
    print("\n===== pre-flight carimbo (sem freecad) =====")
    ok = True
    for nome, kw in CASOS:
        s = _spec(nome, **kw)      # spec crua: descricao/slug ficam PENDENTE
        cfg = TD.config_de_spec(s, "x.FCStd", "out")
        p = _acha_pendente(cfg)
        if p:
            print("  %-14s VAZOU PENDENTE em %s" % (nome, p)); ok = False
        else:
            print("  %-14s limpo" % nome)
    return ok


def rodar():
    if not checar_carimbo():
        print("  pre-flight FALHOU: __PENDENTE__ vazando no carimbo")
        return False
    resultados = []
    for nome, kw in CASOS:
        print("\n===== %s =====" % nome)
        s = _spec(nome, **kw)
        out = tempfile.mkdtemp(prefix='smoke_%s_' % nome)
        ok = False
        try:
            r = RP.calcular(s, out)
            print("  calc: atende=%s" % r.get('atende'))
            # callouts de fabricacao (me-4): cfg deve carregar a spec de ligacao
            # do calculo (joelho/gusset sempre; console so ponte). Se presente,
            # _callout_fab desenha os numeros -> todo callout rastreia ao calculo.
            cfg = TD.config_de_spec(s, 'x.FCStd', out)
            for k in ('joelho', 'gusset'):
                assert cfg.get(k), "cfg sem spec de ligacao '%s' (callout)" % k
            if kw.get('ponte'):
                assert cfg.get('console'), "cfg sem console (callout)"
            fcstd = _build_3d(s, out, nome)
            assert fcstd and os.path.exists(fcstd), "3D nao gerou FCStd"
            ex = RP.rodar_executivo(s, out, fcstd, timeout=900)
            assert isinstance(ex, dict) and ex.get('ok'), "executivo falhou: %s" % ex
            n = len(ex['pranchas'])
            assert n >= 9, "esperado >=9 pranchas, veio %d" % n
            # guard de cobertura: nenhum TIPO de solido do modelo pode ficar
            # de fora de todas as pranchas (nem virar invisivel silenciosamente).
            nc = ex.get('cobertura', {}).get('nao_cobertos', [])
            assert not nc, "solidos nao cobertos por nenhuma prancha: %s" % nc
            # detalhes de ligacao (PE10+): presentes e com traço real (nao
            # silhueta chapada). LIMIAR de arestas calibrado na fase de prova.
            LIMIAR = 15
            edges = ex.get('detalhes_edges', {})
            baixos = {k: v for k, v in edges.items() if v < LIMIAR}
            assert not baixos, "detalhe de ligacao com poucas arestas: %s" % baixos
            base_lig = {'VLIG_ELEV_GUSSET_COB', 'VLIG_ELEV_GUSSET_PAR',
                        'VLIG_ELEV_CLIPE_GIRT'}
            # cumeeira (no de momento) so existe no portico solido; a tesoura e
            # biapoiada rotulada (sem joelho/cumeeira).
            if kw.get('tipo_portico') != 'tesoura':
                base_lig.add('VLIG_ELEV_CUMEEIRA')
            faltam = base_lig - set(edges)
            assert not faltam, "faltam detalhes de ligacao: %s" % faltam
            # CORTE SECCIONADO (fase 5): pelo menos 1 secao hachurada gerada, e
            # nenhuma secao vazia (corte com arestas reais).
            secoes = ex.get('detalhes_secoes', {})
            assert secoes, "nenhum corte seccionado gerado (VLIG_SEC_*)"
            vazias = {k: v for k, v in secoes.items() if v <= 0}
            assert not vazias, "corte seccionado vazio: %s" % vazias
            if kw.get('ponte'):
                assert 'VLIG_ELEV_CONSOLE' in edges, "falta detalhe do console"
            # PDF do memorial de calculo: gera sem erro e sai um arquivo != vazio
            pdf = RC.gerar_pdf(out, titulo="SMOKE %s" % nome)
            assert os.path.exists(pdf) and os.path.getsize(pdf) > 2000, \
                "PDF de calculo nao gerou (%s)" % pdf
            print("  OK: %d pranchas + memorial PDF, cobertura completa -> %s"
                  % (n, out))
            ok = True
        except Exception as ex:
            print("  FALHOU: %r" % ex)
        resultados.append((nome, ok))
    print("\n===== RESUMO =====")
    for nome, ok in resultados:
        print("  %-14s %s" % (nome, "OK" if ok else "FALHOU"))
    n_ok = sum(1 for _, ok in resultados if ok)
    print("  %d/%d casos OK" % (n_ok, len(resultados)))
    return n_ok == len(resultados)


if __name__ == '__main__':
    sys.exit(0 if rodar() else 1)
