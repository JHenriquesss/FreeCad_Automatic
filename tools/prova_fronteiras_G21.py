#!/usr/bin/env python3
"""
prova_fronteiras_G21.py — G21/G22: Prova de que o fronteiras.py pega

Injeta deliberadamente os três defeitos do G8 e confirma que test_fronteiras.py
fica VERMELHO em cada um. Barato, rápido, sem mocks irreais — mutação em disco
e subprocesso real de pytest.

G22 (higiene): a mutação NÃO toca o repositório vivo. Cada defeito é
injetado numa CÓPIA do pacote (framework/galpao_fw) num diretório temporário.
O pytest roda contra essa cópia (cwd = tmp). Se o processo morrer no meio
(Ctrl+C, kill, disco cheio), o repositório permanece com os dois módulos
intactos — a classe de acidente do G21 (finally que não roda) está eliminada.
Mecanismo idêntico, isolamento por cópia.

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
import shutil
import subprocess
import sys
import tempfile

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

def _run_pytest_in_temp(tmp_root: pathlib.Path, selector: str) -> subprocess.CompletedProcess:
    """Roda pytest contra a cópia temporária (cwd = tmp_root)."""
    # Mantém o mesmo seletor relativo: framework/galpao_fw/tests/test_fronteiras.py::...
    test_ref = f"{TEST}::{selector}"
    return subprocess.run(
        [sys.executable, "-m", "pytest", test_ref, "-v"],
        capture_output=True, text=True, cwd=str(tmp_root)
    )

def _copiar_pacote(tmp_root: pathlib.Path) -> pathlib.Path:
    """
    Copia framework/galpao_fw para tmp_root/framework/galpao_fw preservando
    estrutura para que framework.raiz_repo() aponte para tmp_root.
    Ignora caches e venv para ser rápido.
    Retorna o Path do pacote copiado.
    """
    dest = tmp_root / "framework" / "galpao_fw"
    # Garante que tmp_root/framework existe
    dest.parent.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", ".venv", "*.pyc", "*.pyo",
        ".git", "saida_*", "out_*", "*.log"
    )
    shutil.copytree(FW, dest, ignore=ignore)
    return dest

def main():
    ap = argparse.ArgumentParser(description="G21/G22 prova que fronteiras pega os 3 bugs do G8 (cópia isolada)")
    ap.add_argument("--keep-green", action="store_true", help="só verifica baseline verde")
    args = ap.parse_args()

    print("="*78)
    print("G21/G22 — Prova de que o fronteiras.py pega (3 defeitos do G8) [ISOLADA]")
    print("="*78)

    # Baseline verde (repositório vivo, sem mutação)
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

    # Guarda hash do vivo para provar que nunca foi tocado
    hashes_vivo = {}
    for m in MUTACOES:
        p = m["arquivo"]
        # pode haver duplicata (G21-1 e G21-2 no mesmo arquivo)
        if p not in hashes_vivo:
            hashes_vivo[p] = p.read_text(encoding="utf-8")

    falhas = 0
    for m in MUTACOES:
        print(f"\n[{m['id']}] {m['nome']}")
        print(f"  arquivo: {m['arquivo'].name}  |  teste: {m['teste']}")
        print(f"  motivo G8: {m['explicacao']}")

        p_real = m["arquivo"]
        orig_real = hashes_vivo[p_real]
        # sanidade: string ainda existe no vivo?
        if m["velho"] not in orig_real:
            print(f"  SKIP: string '{m['velho']}' não encontrada no vivo (já corrigido de outro jeito?)")
            falhas += 1
            continue

        # Cópia isolada — mutação nunca toca o vivo
        with tempfile.TemporaryDirectory(prefix="g22_prova_") as tmpdir:
            tmp_root = pathlib.Path(tmpdir)
            tmp_fw = _copiar_pacote(tmp_root)
            # arquivo mutado dentro da cópia (mesmo nome)
            p_tmp = tmp_fw / p_real.name
            orig_tmp = p_tmp.read_text(encoding="utf-8")
            if m["velho"] not in orig_tmp:
                print(f"  SKIP: string '{m['velho']}' não encontrada na cópia (inconsistente)")
                falhas += 1
                continue
            mutated = orig_tmp.replace(m["velho"], m["novo"])
            assert mutated != orig_tmp, "mutação não alterou arquivo"
            p_tmp.write_text(mutated, encoding="utf-8")

            # prova de isolamento: vivo intacto imediatamente após escrever cópia
            assert p_real.read_text(encoding="utf-8") == orig_real, \
                "G22 isolamento quebrado: repositório vivo foi modificado!"

            res = _run_pytest_in_temp(tmp_root, m["teste"])

            # prova de isolamento pós-pytest
            assert p_real.read_text(encoding="utf-8") == orig_real, \
                "G22 isolamento quebrado após pytest: vivo tocado!"

            if res.returncode == 0:
                print(f"  [FALHA] guarda NÃO ficou vermelho — contrato furado!")
                print(res.stdout[-2000:])
                falhas += 1
            else:
                # confirma que foi AssertionError do guarda, não erro de import
                if "AssertionError" in res.stdout and ("FAILED" in res.stdout or "failed" in res.stdout):
                    print(f"  -> GUARDA VERMELHO (ok) — teste falhou como esperado (cópia isolada)")
                    # mostra a linha do AssertionError (preferindo a mensagem, não o trecho do código)
                    printed = False
                    for line in res.stdout.splitlines():
                        if "AssertionError" in line:
                            print(f"     {line.strip()}")
                            printed = True
                            break
                    if not printed:
                        for line in res.stdout.splitlines():
                            if "assert" in line.lower():
                                print(f"     {line.strip()}")
                                break
                else:
                    print(f"  [SUSPEITO] returncode !=0 mas sem AssertionError esperado")
                    print(res.stdout[-2000:])
                    print(res.stderr[-1000:])
                    falhas += 1
        # TemporaryDirectory limpo aqui; vivo segue intacto por construção
        assert p_real.read_text(encoding="utf-8") == orig_real, \
            "G22 isolamento final: vivo diverge após cleanup!"

    # Verifica que todos os arquivos vivos continuam idênticos ao baseline
    for p, h in hashes_vivo.items():
        assert p.read_text(encoding="utf-8") == h, f"G22: {p.name} foi alterado!"

    # Baseline verde depois (vivo nunca tocado, deve permanecer verde)
    print("\n[RESTAURAÇÃO] verificando que baseline (vivo) segue verde…")
    base2 = subprocess.run([sys.executable, "-m", "pytest", TEST, "-q"],
                           capture_output=True, text=True, cwd=str(REPO))
    if base2.returncode != 0:
        print("ERRO: baseline não voltou ao verde após prova isolada!")
        print(base2.stdout[-2000:])
        sys.exit(3)
    print("  -> baseline VERDE novamente (20 passed) — vivo nunca mutado (G22)")

    print("\n" + "="*78)
    if falhas == 0:
        print("G21/G22 PROVADO: 3/3 mutações deixaram o guarda vermelho (cópia isolada).")
        print("G16 de 'escrito' -> 'provado', sem tocar o repositório vivo.")
        print("="*78)
        return 0
    else:
        print(f"G21/G22 FALHOU: {falhas}/3 mutações NÃO ficaram vermelhas.")
        print("="*78)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
