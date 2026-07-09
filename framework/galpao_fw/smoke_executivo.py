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
# (estaca profunda / escada / plataforma sao calc-only: nao mudam o 3D.)
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

FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


def _spec(slug, span, comp, eave, ridge, ponte=None):
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
    return s


def _build_3d(spec, out, doc_name):
    """3D via freecadcmd (headless, sem MCP). Retorna path do FCStd."""
    bk = PS.to_build_kwargs(spec)
    bk['export_dir'] = str(out).replace('\\', '/')
    bk['doc_name'] = doc_name
    src = (FW.raiz_repo() / 'framework' / 'galpao_fw' / 'build_galpao.py'
           ).read_text(encoding='utf-8').replace('_result_ = run()', '')
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
         'n_rodas_lado': 2, 'phi': 1.10, 'frac_lateral': 0.10,
         'frac_long': 0.10, 'Hvr': 4.5, 'excentricidade': 0.3}

CASOS = [
    ("padrao",   dict(span=10, comp=20, eave=6, ridge=6.5)),
    ("vao_maior", dict(span=18, comp=12, eave=7, ridge=7.9)),
    ("baixo_largo", dict(span=8, comp=30, eave=4, ridge=4.4)),
    ("ponte",    dict(span=15, comp=20, eave=7, ridge=7.75, ponte=PONTE)),
]


def rodar():
    resultados = []
    for nome, kw in CASOS:
        print("\n===== %s =====" % nome)
        s = _spec(nome, **kw)
        out = tempfile.mkdtemp(prefix='smoke_%s_' % nome)
        ok = False
        try:
            r = RP.calcular(s, out)
            print("  calc: atende=%s" % r.get('atende'))
            fcstd = _build_3d(s, out, nome)
            assert fcstd and os.path.exists(fcstd), "3D nao gerou FCStd"
            ex = RP.rodar_executivo(s, out, fcstd, timeout=900)
            assert isinstance(ex, dict) and ex.get('ok'), "executivo falhou: %s" % ex
            n = len(ex['pranchas'])
            assert n == 9, "esperado 9 pranchas, veio %d" % n
            print("  OK: 9 pranchas -> %s/pranchas" % out)
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
