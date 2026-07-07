# Barras tracionadas (contraventamento, tirantes, mao-francesa) - contraventamento.py

Arquivo: `framework/galpao_fw/contraventamento.py`
Gerado: 2026-07-05
Base: NBR 8800:2008 item 5.2 (barra tracionada) + 5.2.8 (esbeltez). Pendente revisao.

## Problema que resolve
As barras tracionadas do galpao (contraventamento so-tracao, tirantes/correntes
de terca, barra da mao-francesa) eram modeladas mas nao verificadas. Este modulo
fecha, consumindo a forca de arrasto Fa do vento longitudinal (vento_nbr6123).

## Metodo
- **Tracao (5.2):** `Nt,Rd = min(Ag*fy/1,10 ; Ct*An*fu/1,35)` - escoamento da
  secao bruta vs ruptura da secao liquida. Barra redonda rosqueada: `An=0,75*Ag`
  (area efetiva na rosca), `Ct=1,0`.
- **Esbeltez (5.2.8):** `L/r <= 300` recomendado. Barra so-tracao com esticador
  (turnbuckle) PRE-TENSIONADA e dispensada do limite -> sinaliza `pretensionada`.
- **Forca da diagonal:** `N = F_painel/cos(theta)`, do vao horizontal e altura.
- **Mao-francesa:** forca de estabilizacao = 2% da forca de compressao da mesa
  (`0,02*Msd/braco`), fechando o elo com o espacamento do modulo [[mao_francesa]].

## Integracao (rodar_galpao, Gate 7)
Contravento de parede e de cobertura recebem Fa/lado; a mao-francesa recebe 2%
do Msd da viga; o tirante recebe a componente do peso na agua (A CONFIRMAR).
Salva `gate7-contraventamento.txt`.

## Codigo completo

```python
# ============================================================================
# contraventamento.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica as BARRAS TRACIONADAS do galpao pela ABNT NBR 8800:2008:
#   - Contraventamento (barras redondas so-tracao): diagonal que leva a forca do
#     vento longitudinal (arrasto Fa, do vento_nbr6123) ate a fundacao.
#   - Tirantes (correntes de terca / sag rods): componente do peso paralela a
#     agua, acumulada ate a cumeeira.
#   - Barra da mao-francesa: forca de estabilizacao (regra dos 2% da forca de
#     compressao da mesa).
# Verificacao de barra tracionada (item 5.2):
#   Nt,Rd = min( Ag*fy/ga1 ; Ct*An*fu/ga2 )  (escoamento da bruta / ruptura da
#   liquida). Barra redonda rosqueada: An = 0,75*Ag (area efetiva na rosca),
#   Ct = 1,0. ga1=1,10 ; ga2=1,35.
# Esbeltez (5.2.8): L/r <= 300 recomendado; barra so-tracao com esticador
# (turnbuckle) pre-tensionada e DISPENSADA do limite - reporta e sinaliza.
# Generico e parametrico. NAO calcula esforcos globais (Fa vem do vento).
# Calcula apenas; pendente revisao do eng. responsavel.
# ============================================================================
"""Barras tracionadas (contraventamento, tirantes, mao-francesa) - NBR 8800."""

from __future__ import annotations

import math

GA1 = 1.10
GA2 = 1.35


def tracao_barra_Rd(d, fy, fu, ct=1.0, k_rosca=0.75):
    """Nt,Rd (kN) de uma barra redonda de diametro d (m). k_rosca = An/Ag
    (~0,75 na regiao da rosca). Retorna (Nt_Rd, escoamento_Rd, ruptura_Rd)."""
    Ag = math.pi * d ** 2 / 4.0
    An = k_rosca * Ag
    esc = Ag * fy / GA1
    rup = ct * An * fu / GA2
    return min(esc, rup), esc, rup


def n_diagonal(F_painel, dx, dy):
    """Forca de tracao numa diagonal que resiste a F_painel (kN), vao horizontal
    dx e altura dy (m). N = F_painel / cos(theta), theta = angulo com a horizontal."""
    L = math.hypot(dx, dy)
    cos_t = dx / L                                  # componente horizontal
    return F_painel / cos_t, L


def forca_estabilizacao_2pct(Msd, braco):
    """Forca de estabilizacao (2% da forca de compressao da mesa). braco = altura
    do perfil (m); forca da mesa ~ Msd/braco. Retorna 0,02 * (Msd/braco) (kN)."""
    return 0.02 * Msd / braco


def verifica_barra(nome, d, fy, fu, Nsd, L, limite_esbeltez=300.0,
                   pretensionada=False):
    """Verifica uma barra tracionada: tracao (5.2) + esbeltez (5.2.8)."""
    Nt_Rd, esc, rup = tracao_barra_Rd(d, fy, fu)
    r_gir = d / 4.0                                 # raio de giracao da secao cheia
    lam = L / r_gir
    u = Nsd / Nt_Rd
    esbeltez_ok = pretensionada or lam <= limite_esbeltez
    return {"nome": nome, "d": d, "Nsd": Nsd, "L": L, "Nt_Rd": Nt_Rd,
            "escoamento_Rd": esc, "ruptura_Rd": rup, "u": u, "lambda": lam,
            "limite_esbeltez": limite_esbeltez, "pretensionada": pretensionada,
            "esbeltez_ok": esbeltez_ok, "OK": u <= 1.0 and esbeltez_ok,
            "gov": "escoamento" if esc < rup else "ruptura (rosca)"}


def relatorio_pt(rs):
    L = ["=" * 68, "BARRAS TRACIONADAS (ABNT NBR 8800:2008 item 5.2)",
         "  Nt,Rd = min(Ag*fy/1,10 ; 0,75*Ag*fu/1,35) ; esbeltez L/r <= 300",
         "=" * 68]
    for r in rs:
        L += [f"  --- {r['nome']} (d={r['d']*1000:.0f} mm ; L={r['L']:.2f} m) ---",
              f"    Nt,Rd = {r['Nt_Rd']:.1f} kN (gov {r['gov']}: esc={r['escoamento_Rd']:.1f} "
              f"; rup={r['ruptura_Rd']:.1f})",
              f"    Nsd = {r['Nsd']:.1f} kN -> u = {r['u']:.2f}",
              f"    Esbeltez L/r = {r['lambda']:.0f} (limite {r['limite_esbeltez']:.0f}"
              f"{' ; pre-tensionada -> dispensa' if r['pretensionada'] else ''}) "
              f"-> {'OK' if r['esbeltez_ok'] else 'NAO'}",
              f"    >> {'OK' if r['OK'] else 'NAO PASSA'}"]
    L.append("=" * 68)
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    fy, fu = 250e3, 400e3                            # aco MR250 (barra comum)
    # Contraventamento de parede: resiste Fa/lado=29,5 kN; diagonal 5 m (bay) x
    # 6 m (pe-direito). Barra d20.
    Nd, Ld = n_diagonal(29.5, 5.0, 6.0)
    r1 = verifica_barra("Contravento parede (d20)", 0.020, fy, fu, Nd, Ld,
                        pretensionada=True)
    # Tirante de cobertura d16: componente do peso na agua (ex.: 8 kN).
    r2 = verifica_barra("Tirante de cobertura (d16)", 0.016, fy, fu, 8.0, 1.68,
                        pretensionada=True)
    # Barra da mao-francesa d16: 2% da forca da mesa (Msd=61,3 ; braco=0,17 m).
    Nmf = forca_estabilizacao_2pct(61.3, 0.171)
    r3 = verifica_barra("Mao-francesa (d16)", 0.016, fy, fu, Nmf, 0.40)
    print(relatorio_pt([r1, r2, r3]))
    assert r1["OK"] and r2["OK"] and r3["OK"]
    assert r1["Nsd"] > 29.5                          # diagonal amplifica pelo cos
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
```

## Resultado da execucao (`python contraventamento.py`)

```
====================================================================
BARRAS TRACIONADAS (ABNT NBR 8800:2008 item 5,2)
  Nt,Rd = min(Ag*fy/1,10 ; 0,75*Ag*fu/1,35) ; esbeltez L/r <= 300
====================================================================
  --- Contravento parede (d20) (d=20 mm ; L=7,81 m) ---
    Nt,Rd = 69,8 kN (gov ruptura (rosca): esc=71,4 ; rup=69,8)
    Nsd = 46,1 kN -> u = 0,66
    Esbeltez L/r = 1562 (limite 300 ; pre-tensionada -> dispensa) -> OK
    >> OK
  --- Tirante de cobertura (d16) (d=16 mm ; L=1,68 m) ---
    Nt,Rd = 44,7 kN (gov ruptura (rosca): esc=45,7 ; rup=44,7)
    Nsd = 8,0 kN -> u = 0,18
    Esbeltez L/r = 420 (limite 300 ; pre-tensionada -> dispensa) -> OK
    >> OK
  --- Mao-francesa (d16) (d=16 mm ; L=0,40 m) ---
    Nt,Rd = 44,7 kN (gov ruptura (rosca): esc=45,7 ; rup=44,7)
    Nsd = 7,2 kN -> u = 0,16
    Esbeltez L/r = 100 (limite 300) -> OK
    >> OK
====================================================================

[selftest] OK
```
