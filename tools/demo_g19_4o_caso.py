#!/usr/bin/env python3
"""
Demo G19 - 4o caso sem obra real.

Roda o harness G15+G19 em dois modos:
1. Real: python -m validacao_sistema_g15 (21 checks, SJB blocked => 2 SKIP)
2. Demo: python tools/demo_g19_4o_caso.py (usa project-spec-framework-teste.json como proxy de SJB ready
   + docs/validacao_g15/exemplo-sintetico-valores-referencia.json como sidecar sintético)

O demo prova que o caminho de comparacao numero-a-numero do harness funciona ponta-a-ponta
quando houver obra real, sem precisar inventar que o exemplo sintético e obra.

Uso:
    python tools/demo_g19_4o_caso.py
    python tools/demo_g19_4o_caso.py --verbose
"""
from __future__ import annotations
import json
import pathlib
import sys
import tempfile
import shutil

REPO = pathlib.Path(__file__).resolve().parents[1]
FW = REPO / "framework" / "galpao_fw"
SPEC_TESTE = REPO / "projects" / "galpao-sjb" / "project-spec-framework-teste.json"
SIDECAR_EXEMPLO = REPO / "docs" / "validacao_g15" / "exemplo-sintetico-valores-referencia.json"
SIDECAR_TEMPLATE = REPO / "docs" / "validacao_g15" / "galpao-sjb-valores-referencia.json.template"

def _run_framework_teste():
    sys.path.insert(0, str(FW))
    import project_loop, builtin_adapters
    try:
        builtin_adapters.register_builtin_adapters()
    except Exception:
        pass
    spec = json.loads(SPEC_TESTE.read_text(encoding="utf-8"))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="demo_g19_"))
    try:
        manifest = project_loop.run_project(spec, str(tmp), options={"generate_3d": False, "generate_2d": False})
        dis_path = tmp / "reports" / "disciplinas.json"
        dis = json.loads(dis_path.read_text(encoding="utf-8")) if dis_path.is_file() else {}
        aco_raw = dis.get("aco", {}).get("native", {}).get("raw", {})
        peso = aco_raw.get("romaneio_peso_primario_kg")
        # extrair Mcol se disponivel
        esf_col = aco_raw.get("esf_coluna", {})
        return {
            "manifest_status": manifest.get("status"),
            "disciplines": {k: v.get("status") for k, v in manifest.get("disciplines", {}).items()},
            "peso_aco_primario_kg": peso,
            "Mcol_kNm": esf_col.get("M_kNm"),
            "perfis": {"coluna": aco_raw.get("perfil_col_adotado"), "viga": aco_raw.get("perfil_raf_adotado")},
            "tmp": tmp,
        }, tmp
    except Exception as ex:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

def main():
    verbose = "--verbose" in sys.argv
    print("="*70)
    print("DEMO G19 - 4o caso (sintetico, NAO e obra real)")
    print("="*70)
    print(f"SPEC proxy : {SPEC_TESTE.relative_to(REPO)}")
    print(f"  -> {json.loads(SPEC_TESTE.read_text(encoding='utf-8')).get('test_assumptions',{}).get('mode')} / {json.loads(SPEC_TESTE.read_text(encoding='utf-8')).get('test_assumptions',{}).get('status')}")
    print(f"SIDECAR    : {SIDECAR_EXEMPLO.relative_to(REPO)}")
    print(f"  -> {json.loads(SIDECAR_EXEMPLO.read_text(encoding='utf-8')).get('_aviso','')[:90]}...")
    print()

    # 1. Mostrar que SJB real ainda bloqueado
    sys.path.insert(0, str(FW))
    import validacao_sistema_g15 as G15
    print("[1] Harness real (SJB bloqueado) — deve dar 21/21 PASS com 2 SKIP")
    ok_real, res_real = G15.rodar(verbose=verbose)
    # filtrar SJB
    sjb_checks = [r for r in res_real if "SJB" in r[0]]
    print(f"    -> SJB checks: {len(sjb_checks)} | ok_real={ok_real}")
    for nome, ok, err, det in sjb_checks:
        print(f"       [{ 'PASS' if ok else 'FAIL'}] {nome}: {det[:120]}...")

    print()
    print("[2] Demo com SPEC teste como proxy de obra pronta")
    info, tmp = _run_framework_teste()
    print(f"    manifest status: {info['manifest_status']} (esperado needs_review/failed por A CONFIRMAR, nao por bloqueio)")
    print(f"    disciplinas: {info['disciplines']}")
    print(f"    peso_aco_primario_kg framework: {info['peso_aco_primario_kg']}")
    sidecar = json.loads(SIDECAR_EXEMPLO.read_text(encoding="utf-8"))
    ref_peso = sidecar["valores_referencia"]["peso_aco_primario_kg"]
    ref_mcol = sidecar["valores_referencia"]["Mcol_kNm"]
    print(f"    sidecar peso_aco_primario_kg: {ref_peso} | Mcol: {ref_mcol}")
    print("    AVISO (G23/G36, circular por construcao): o sidecar foi gerado PELO")
    print("    PROPRIO framework — 0.00% PASS prova que o harness compara numero-a-")
    print("    numero, NAO que o calculo esta certo. Validacao real exige memorial externo.")
    # comparar com tolerancias G19
    def rel_err(a,b):
        return abs(a-b)/max(abs(b),1e-9)
    err_peso = rel_err(info["peso_aco_primario_kg"], ref_peso) if info["peso_aco_primario_kg"] and ref_peso else None
    err_mcol = rel_err(info["Mcol_kNm"], ref_mcol) if info["Mcol_kNm"] and ref_mcol else None
    print(f"    err peso: {err_peso*100:.2f}% (tol 10%) -> {'PASS' if err_peso is not None and err_peso<=0.10 else 'FAIL/SKIP'}")
    print(f"    err Mcol: {err_mcol*100:.2f}% (tol 15%) -> {'PASS' if err_mcol is not None and err_mcol<=0.15 else 'FAIL/SKIP'}")
    # limpar
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("[3] Conclusao")
    print("    - Caminho real G19: AGUARDANDO OBRA REAL (SJB blocked 9 campos) — correto.")
    print("    - Caminho demo: prova que, quando SJB ficar ready + memorial real, o harness")
    print("      compara numero-a-numero com tolerancias G15 e que o framework ja produz valores.")
    print("    - Para validacao real: preencher projects/galpao-sjb/project-spec.json (9 campos)")
    print("      + anexar docs/validacao_g15/galpao-sjb-memorial.pdf + sidecar do template.")
    print("="*70)
    print("Demo OK — nao afirma que exemplo sintetico e obra. G19 continua AGUARDANDO OBRA REAL.")
    print("AVISO: numeros acima sao CIRCULARES (framework x framework) — o PASS valida o harness, nao a engenharia.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
