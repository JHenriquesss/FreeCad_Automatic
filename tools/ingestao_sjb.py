#!/usr/bin/env python3
"""
Ingestao guiada do galpao SJB - G19.

Ajuda a preencher os 9 campos pendentes de projects/galpao-sjb/ENTRADAS-PENDENTES.md
sem inventar dados. Valida a cada passo com project_loop.preflight_project.

Uso:
    python tools/ingestao_sjb.py                 # modo interativo (pergunta cada campo)
    python tools/ingestao_sjb.py --check         # so mostra status atual do preflight
    python tools/ingestao_sjb.py --set-geometria 40 20 6   # preenche geometria e valida
    python tools/ingestao_sjb.py --from-teste    # copia o SPEC de teste como ponto de partida (marca como sintetico, nao como obra)

O modo interativo nao escreve sem confirmar e nunca substitui valores por estimativa.
Para cada disciplina, ele pede o caminho de um JSON parcial ou abre editor.
"""
from __future__ import annotations
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SPEC = REPO / "projects" / "galpao-sjb" / "project-spec.json"
TEMPLATE = REPO / "projects" / "galpao-sjb" / "project-spec.template.json"
SPEC_TESTE = REPO / "projects" / "galpao-sjb" / "project-spec-framework-teste.json"
FW = REPO / "framework" / "galpao_fw"

def _preflight_status():
    sys.path.insert(0, str(FW))
    import project_loop
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    rep = project_loop.preflight_project(spec, options={"require_source_refs": True})
    return rep

def cmd_check():
    rep = _preflight_status()
    print(f"status: {rep['status']}")
    print(f"ok: {rep['preflight']['ok']}")
    errs = rep['preflight']['errors']
    print(f"errors: {len(errs)}")
    for e in errs:
        print(f"  - {e['code']}: {e.get('path','')} {e.get('discipline','')} {e.get('detail','')[:90]}")
    if rep['status'] == 'blocked':
        print("\nAGUARDANDO OBRA REAL — 9 campos pendentes (3 geometria + 6 disciplinas).")
        print("Preencha project-spec.json a partir do template; ver docs/validacao_g15/README.md")
    elif rep['status'] == 'ready':
        print("\nREADY — pode rodar Loop 2: python framework/galpao_fw/project_loop_cli.py --spec projects/galpao-sjb/project-spec.json --out-dir projects/galpao-sjb/run-001 --require-source-refs")
    return 0 if rep['status'] in ('blocked','ready','needs_review') else 1

def cmd_set_geometria(args):
    if len(args) < 3:
        print("uso: --set-geometria <comprimento> <vao> <pe_direito>  (metros, >0)")
        return 2
    try:
        comp, vao, pe = map(float, args[:3])
    except ValueError:
        print("valores devem ser numericos")
        return 2
    if not (comp>0 and vao>0 and pe>0):
        print("valores devem ser >0")
        return 2
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec.setdefault("turnkey", {}).setdefault("geometria", {})["comprimento"] = comp
    spec["turnkey"]["geometria"]["vao"] = vao
    spec["turnkey"]["geometria"]["pe_direito"] = pe
    SPEC.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"geometria gravada: comprimento={comp} vao={vao} pe_direito={pe}")
    return cmd_check()

def cmd_from_teste():
    print("Copiando SPEC de teste como PONTO DE PARTIDA SINTETICO (NAO e obra real).")
    print(f"Origem: {SPEC_TESTE.relative_to(REPO)} -> {SPEC.relative_to(REPO)}")
    data = json.loads(SPEC_TESTE.read_text(encoding="utf-8"))
    # Marcar claramente que nao e obra
    data["project"]["slug"] = "galpao-sjb-demo-sintetico"
    data["project"]["description"] = "DEMO SINTETICO - COPIA DO TESTE - NAO E OBRA REAL - substituir por dados reais"
    data.setdefault("test_assumptions", {})["ingestao_helper"] = "copiado via tools/ingestao_sjb.py --from-teste em modo demo"
    SPEC.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Feito. Agora rode --check e substitua cada disciplina por dados reais; nao commitar como obra.")
    return cmd_check()

def cmd_interativo():
    print("Ingestao interativa SJB - G19 (9 campos)")
    print("Este assistente NAO estima. Deixe em branco para manter __PENDENTE__.")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    geo = spec.get("turnkey", {}).get("geometria", {})
    print(f"\nGeometria atual: comprimento={geo.get('comprimento')} vao={geo.get('vao')} pe_direito={geo.get('pe_direito')}")
    try:
        comp = input("comprimento (m) >0 ou <enter> manter: ").strip()
        vao = input("vao (m) >0 ou <enter> manter: ").strip()
        pe = input("pe_direito (m) >0 ou <enter> manter: ").strip()
        for k,v in [("comprimento", comp), ("vao", vao), ("pe_direito", pe)]:
            if v:
                try:
                    fv = float(v)
                    if fv<=0: raise ValueError
                    spec["turnkey"]["geometria"][k] = fv
                except ValueError:
                    print(f"  ! {k} ignorado (precisa numero >0)")
        # disciplinas: apenas informar que precisam de JSON parcial
        print("\nDisciplinas pendentes: concreto, aco, eletrico, incendio, climatizacao, hidraulica")
        print("Cada uma deve virar objeto (nao string __PENDENTE__).")
        print("Dica: veja spec_amostra_engenheiro.json (aco) e project-spec-framework-teste.json (todas) como referencia de FORMA,")
        print("      mas preencha com dados REAIS da sua obra (sondagem sigma_solo_adm, cargas G/Q, ENEL, CBMERJ, etc).")
        print("      Use --from-teste para copiar a forma completa e depois substituir campo a campo.")
        ans = input("\nGravar alteracoes em project-spec.json? (s/N): ").strip().lower()
        if ans == "s":
            SPEC.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("Gravado.")
        else:
            print("Nao gravado.")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado.")
        return 1
    return cmd_check()

def main():
    if "--check" in sys.argv:
        return cmd_check()
    if "--set-geometria" in sys.argv:
        idx = sys.argv.index("--set-geometria")
        return cmd_set_geometria(sys.argv[idx+1:])
    if "--from-teste" in sys.argv:
        return cmd_from_teste()
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    return cmd_interativo()

if __name__ == "__main__":
    sys.exit(main())
