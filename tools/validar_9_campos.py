#!/usr/bin/env python3
"""
Validador G19 - 9 campos (esquema + gate).

Verifica se projects/galpao-sjb/project-spec.json tem os 9 campos que destravam o Loop 2,
usando tanto o esquema docs/validacao_g15/ESQUEMA-9-CAMPOS.json quanto o gate real
framework/galpao_fw/project_loop.py:584 preflight_project.

Uso:
    python tools/validar_9_campos.py
    python tools/validar_9_campos.py --spec projects/galpao-sjb/proposta-obra-conhecida-AGENTE-36x24.json
    python tools/validar_9_campos.py --spec projects/galpao-sjb/project-spec.json --json
"""
from __future__ import annotations
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SPEC = REPO / "projects" / "galpao-sjb" / "project-spec.json"
ESQUEMA = REPO / "docs" / "validacao_g15" / "ESQUEMA-9-CAMPOS.json"
FW = REPO / "framework" / "galpao_fw"

def _check_esquema(spec: dict) -> list[str]:
    faltas = []
    turnkey = spec.get("turnkey")
    if not isinstance(turnkey, dict):
        return ["turnkey ausente ou não é objeto"]
    # geometria 3 campos
    geo = turnkey.get("geometria", {})
    for k in ["comprimento", "vao", "pe_direito"]:
        v = geo.get(k) if isinstance(geo, dict) else None
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
            faltas.append(f"turnkey.geometria.{k} deve ser número >0 (atual: {v!r})")
    # 6 disciplinas
    for disc in ["concreto", "aco", "eletrico", "incendio", "climatizacao", "hidraulica"]:
        val = turnkey.get(disc)
        if not isinstance(val, dict):
            faltas.append(f"turnkey.{disc} deve ser objeto (atual: {val!r})")
            continue
        if val.get("_status") == "__PENDENTE__":
            faltas.append(f"turnkey.{disc} ainda contém _status=__PENDENTE__")
        # também detectar string direta __PENDENTE__
        if val == "__PENDENTE__":
            faltas.append(f"turnkey.{disc} == '__PENDENTE__'")
    return faltas

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Validador 9 campos G19")
    ap.add_argument("--spec", type=str, default=str(DEFAULT_SPEC), help="caminho do project-spec.json")
    ap.add_argument("--json", action="store_true", help="saída JSON")
    args = ap.parse_args()
    spec_path = pathlib.Path(args.spec)
    if not spec_path.is_file():
        print(f"spec não encontrado: {spec_path}", file=sys.stderr)
        sys.exit(2)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    faltas_esquema = _check_esquema(spec)
    # gate real
    sys.path.insert(0, str(FW))
    import project_loop
    rep = project_loop.preflight_project(spec, options={"require_source_refs": True})
    status = rep["status"]
    errs = rep["preflight"]["errors"]
    warns = rep["preflight"]["warnings"]
    ok = len(faltas_esquema) == 0 and status == "ready"
    out = {
        "spec": str(spec_path.relative_to(REPO)) if spec_path.is_absolute() else str(spec_path),
        "esquema_ok": len(faltas_esquema) == 0,
        "faltas_esquema": faltas_esquema,
        "gate_status": status,
        "gate_ok": rep["preflight"]["ok"],
        "gate_errors": errs,
        "gate_warnings": warns,
        "can_start_loop2": rep.get("can_start_project_loop", status == "ready"),
        "checklist": "docs/validacao_g15/CHECKLIST-9-CAMPOS.md",
        "esquema": "docs/validacao_g15/ESQUEMA-9-CAMPOS.json",
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"spec: {out['spec']}")
        print(f"esquema 9 campos: {'OK' if out['esquema_ok'] else 'FALTAM ' + str(len(faltas_esquema))}")
        for f in faltas_esquema:
            print(f"  - {f}")
        print(f"gate: {status} (errors {len(errs)}, warnings {len(warns)})")
        for e in errs[:6]:
            print(f"  - {e['code']}: {e.get('path','')}{e.get('discipline','')} {e.get('detail','')[:80]}")
        print(f"can_start_loop2: {out['can_start_loop2']}")
        if status == "blocked":
            print("G19: AGUARDANDO OBRA REAL - preencher 9 campos (ver CHECKLIST-9-CAMPOS.md)")
        elif status == "ready":
            print("G19: READY - pode rodar Loop 2 e depois validacao_sistema_g15 como 4o caso")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
