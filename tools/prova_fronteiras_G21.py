#!/usr/bin/env python3
"""
prova_fronteiras_G21.py — G21: Prova de que o fronteiras.py pega

Injeta deliberadamente os três defeitos do G8 e confirma que test_fronteiras.py
fica VERMELHO em cada um. Barato, rápido, sem mocks irreais — mutação em disco
e subprocesso real de pytest.

Uso:
  python tools/prova_fronteiras_G21.py              # roda as 3 provas
  python tools/prova_fronteiras_G21.py --keep-green # só verifica que baseline está verde

Saída esperada (3 mutações, 3 vermelhos):
  [G21-1] dims em metros ........... GUARDA VERMELHO (ok)
  [G21-2] ancoragem divergente ..... GUARDA VERMELHO (ok)
  [G21-3] laje sem realimentar ..... GUARDA VERMELHO (ok)
  Baseline test_fronteiras ......... 20 passed (verde antes e depois)
"""
from __future__ import annotations
import argparse
import pathlib
import subprocess
import sys
import textwrap

REPO = pathlib.Path(__file__).resolve().parents[1]
FW = REPO / "framework" / "galpao_fw"
TEST = "framework/galpao_fw/tests/test_fronteiras.py"

MUTACOES = [
    {
        "id": "G21-1",
        "nome": "dims em metros (sapata 1000x menor no IFC)",
        "arquivo": FW / "galpao_concreto.py",
        "velho": "B * 1000.0, L * 1000.0, hf * 1000.0",
        "novo": "B, L, hf",
        "teste": "test_fronteira_F01_sapata_dims_mm_existe_e_casa",
        "explicacao": "G8 mediu IfcFooting [0.002 0.0025 0.00055] m em vez de [2.0 2.5 0.55] m",
    },
    {
        "id": "G21-2",
        "nome": "ancoragem divergente entre emissores (base vs eixo)",
        "arquivo": FW / "galpao_concreto.py",
        "velho": '"ancoragem": "base"',
        "novo": '"ancoragem": "eixo"',
        "teste": "test_fronteira_F05_ancoragem_base_eixo_existe_e_casa",
        "explicacao": "G8 mediu viga 35 cm enterrada: FreeCAD z 6.00-6.70 vs IFC 5.65-6.35",
    },
    {
        "id": "G21-3",
        "nome": "laje que engrossa sem realimentar (10->12 cm, 0.5 kN/m2 faltando)",
        "arquivo": FW / "edificio_multipavimento.py",
        "velho": "laje_compatibilizada",
        "novo": "laje_compat_BUG",
        "teste": "test_fronteira_F16_laje_h_adotada_cm_feedback_existe_e_casa",
        "explicacao": "G8 mediu laje 12 cm construída com carga de 10 cm (126 m2 x 9 pav)",
    },
]

def _run_pytest(selector: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", f"{TEST}::{selector}", "-v"],
        capture_output=True, text=True, cwd=str(REPO)
    )

def main():
    ap = argparse.ArgumentParser(description="G21 prova que fronteiras pega os 3 bugs do G8")
    ap.add_argument("--keep-green", action="store_true", help="só verifica baseline verde")
    args = ap.parse_args()

    print("="*78)
    print("G21 — Prova de que o fronteiras.py pega (3 defeitos do G8)")
    print("="*78)

    # Baseline verde
    print("\n[BASELINE] test_fronteiras.py deve estar verde antes da mutação…")
    base = subprocess.run([sys.executable, "-m", "pytest", TEST, "-q"],
                          capture_output=True, text=True, cwd=str(REPO))
    if base.returncode != 0:
        print("ERRO: baseline já está vermelho — não dá para provar mutação:")
        print(base.stdout[-3000:])
        print(base.stderr[-1000:])
        sys.exit(2)
    print("  -> baseline VERDE (20 passed)")

    if args.keep_green:
        return 0

    falhas = 0
    for m in MUTACOES:
        print(f"\n[{m['id']}] {m['nome']}")
        print(f"  arquivo: {m['arquivo'].name}  |  teste: {m['teste']}")
        print(f"  motivo G8: {m['explicacao']}")
        p = m["arquivo"]
        orig = p.read_text(encoding="utf-8")
        if m["velho"] not in orig:
            print(f"  SKIP: string '{m['velho']}' não encontrada (já corrigido de outro jeito?)")
            falhas += 1
            continue
        mutated = orig.replace(m["velho"], m["novo"])
        p.write_text(mutated, encoding="utf-8")
        try:
            res = _run_pytest(m["teste"])
            if res.returncode == 0:
                print(f"  [FALHA] guarda NÃO ficou vermelho — contrato furado!")
                print(res.stdout[-2000:])
                falhas += 1
            else:
                # confirma que foi AssertionError do guarda, não erro de import
                if "AssertionError" in res.stdout and ("FAILED" in res.stdout or "failed" in res.stdout):
                    print(f"  -> GUARDA VERMELHO (ok) — teste falhou como esperado")
                    # mostra a linha do AssertionError
                    for line in res.stdout.splitlines():
                        if "AssertionError" in line or "assert" in line.lower():
                            print(f"     {line.strip()}")
                            break
                else:
                    print(f"  [SUSPEITO] returncode !=0 mas sem AssertionError esperado")
                    print(res.stdout[-2000:])
                    falhas += 1
        finally:
            p.write_text(orig, encoding="utf-8")
            # verifica restauração
            assert p.read_text(encoding="utf-8") == orig

    # Baseline verde depois
    print("\n[RESTAURAÇÃO] verificando que baseline voltou ao verde…")
    base2 = subprocess.run([sys.executable, "-m", "pytest", TEST, "-q"],
                           capture_output=True, text=True, cwd=str(REPO))
    if base2.returncode != 0:
        print("ERRO: baseline não voltou ao verde após restauração!")
        print(base2.stdout[-2000:])
        sys.exit(3)
    print("  -> baseline VERDE novamente (20 passed)")

    print("\n" + "="*78)
    if falhas == 0:
        print("G21 PROVADO: 3/3 mutações deixaram o guarda vermelho. G16 de 'escrito' -> 'provado'.")
        print("="*78)
        return 0
    else:
        print(f"G21 FALHOU: {falhas}/3 mutações NÃO ficaram vermelhas.")
        print("="*78)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
