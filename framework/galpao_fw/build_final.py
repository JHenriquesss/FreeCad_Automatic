import sys, tempfile
sys.path.insert(0, 'D:/dev/FreeCad_Automatic/framework/galpao_fw')
import rodar_projeto as RP, projeto_spec as PS
import relatorio_calculo as RC

s = PS.novo()
s['slug'] = 'galpao_final'
s['terreno'].update(area_lote_m2=1200, to_max=0.6, ca_max=1.0, tp_min=0.2,
                    recuos={'frente': 5, 'lateral': 2, 'fundos': 3})
s['geometria'].update(span=10, comprimento=20, eave=6, ridge=6.5, bay=5, base_fixed=True)
s['cobertura'].update(aguas=2, slope=0.10, telha_tipo='trapezoidal', telha_peso=0.10, calha=True)
s['fechamento'].update(tipo='telha', altura_alvenaria=0, peso=0.05, mesa_interna_travada=True, n_maos_francesas=2)
s['aberturas'] = {'portao_frente': (4000, 4500), 'porta_fundo': (900, 2130), 'janelas_laterais': (4300, 5300)}
s['vento'].update(v0=40, cat='II', classe='B', s3=0.95, z=6.5, abertura_dominante='portao_oitao')
s['ponte'] = None
s['cargas'].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
s['fundacao']['sigma_solo_adm'] = 200.0
s['fundacao']['tipo'] = 'sapata'

out = tempfile.mkdtemp(prefix='final_')
res = RP.calcular(s, out)
print(f'Pipeline: atende={res.get("atende")}')
print(f'Memoriais: {out}')

# PDF unico do memorial de calculo (metodo + calculo) para o Eng. Senior
try:
    g = s['geometria']
    pdf = RC.gerar_pdf(out, titulo=f"GALPAO {g['comprimento']:.0f}x{g['span']:.0f} m")
    print(f'Memorial PDF: {pdf}')
except Exception as ex:
    print(f'Memorial PDF (erro): {ex}')

r = RP.montar_modelo(s, out, 'galpao_final',
                     mf_stride=res.get('mf_stride'),
                     n_tirante_parede=res.get('n_tirante_parede'))
resm = r.get('result') if isinstance(r, dict) else None
fcstd = None
if resm:
    print(f'3D: {resm["elementos"]} objetos, {resm["interferencias"]} interferencias')
    print(f'Aco: {resm["massa_aco_kg"]} kg')
    print(f'FCStd: {resm["fcstd"]}')
    fcstd = resm["fcstd"]
fcstd = fcstd or f'{out}/freecad/galpao_final.FCStd'.replace("\\", "/")

ex = RP.rodar_executivo(s, out, fcstd)
if isinstance(ex, dict) and ex.get('ok'):
    print(f'Executivo: {len(ex["pranchas"])} pranchas em {out}/pranchas')
    for p in ex['pranchas']:
        print(f'  - {p}')
else:
    print(f'Executivo (erro): {ex}')
