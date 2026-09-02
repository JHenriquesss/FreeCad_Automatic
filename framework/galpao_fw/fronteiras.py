# ============================================================================
# fronteiras.py - CONTRATOS EXPLICITOS DE FRONTEIRA ENTRE MODULOS
# Varredura sistematica dos pontos de passagem raw/dims/membros_bim (G16).
# Cada fronteira declara: chave, unidade declarada x esperada, quem escreve x
# quem le. Onde havia contrato implicito (unidade por comentario, default
# silencioso, chave nunca lida), o contrato virou dado importavel.
#
# Treze dos defeitos G6-G8 eram de fronteira, nao de formula: unidade trocada
# (m x mm), chave nunca lida, contrato implicito diferente em cada emissor,
# valor que muda num modulo e nao realimenta o outro. Nenhum aparecia em
# teste unitario. Este modulo fecha a lacuna: a fronteira existe como teste-
# guarda (tests/test_fronteiras.py) e como constante importada pelos dois lados.
# ============================================================================
"""Contratos explicitos de fronteira raw/dims/membros_bim.

Convenções herdadas e agora travadas:

- `dims`  de CAIXA  (Footing/Plate/Earthing/Cable/envoltorio) : MILIMETROS
- `centro` de CAIXA                                           : MILIMETROS
- `p1`/`p2` de BARRA/Painel (poligono)                         : MILIMETROS
- `poligono` cantos 3D                                         : MILIMETROS
- `esp`   espessura de chapa/painel/p oligono                   : MILIMETROS
- `secao` de BARRA  (bf, d, tw, tf, D, t, lip)                  : METROS
- `secao2` idem (alma variavel, fim da barra)                  : METROS
- `ancoragem` enum ``eixo`` (default, linha no centroide) | ``base``
          (linha na face inferior, viga apoiada)
- `tipo` enum Footing/Column/Beam/Member/Plate/Pile/Cable/...
- `marca` string livre (prefixo por disciplina no federado: C-/E-/I-/A-)
"""

from __future__ import annotations

# Unidades canonicas (para quem escreve e quem le importarem o mesmo simbolo)
UNIDADE_DIMS_MM = "mm"
UNIDADE_CENTRO_MM = "mm"
UNIDADE_P1P2_MM = "mm"
UNIDADE_POLIGONO_MM = "mm"
UNIDADE_ESP_MM = "mm"
UNIDADE_SECAO_M = "m"
UNIDADE_ANCORAGEM_ENUM = ("eixo", "base")
UNIDADE_TIPO_ENUM = (
    "Footing", "Column", "Beam", "Member", "Plate", "Pile",
    "Cable", "Earthing", "Luminaire", "Outlet", "Covering", "Cladding",
    "Slab", "Wall", "Space",
)

# Fronteiras medidas (id -> contrato). Cada uma e' consumida por outro modulo:
# a chave tem que existir no produtor e a unidade tem que casar no consumidor.
# "chave" usa notacao de caminho (membro["dims"], raw["piso"]["area_m2"], etc.).
FRONTEIRAS = {
    # ── MEMBRO: caixa ──────────────────────────────────────────────────
    "F01_sapata_dims_mm": {
        "chave": 'membro["dims"]',
        "unidade_declarada": UNIDADE_DIMS_MM,
        "unidade_esperada": UNIDADE_DIMS_MM,
        "escreve": ["galpao_concreto.membros_bim", "modelo_neutro.fundacoes",
                    "modelo_neutro.placas_base", "galpao_eletrico.membros_bim",
                    "galpao_climatizacao.membros_bim", "bim_edificio.membros_bim",
                    "galpao_mezanino.membros_bim"],
        "le": ["geometria_membros.aabb", "geometria_membros.volume",
               "ifc_emit.emitir_ifc", "orcamento._vol_membros_concreto",
               "galpao_turnkey._aabb_federado", "build_concreto", "build_federado"],
        "conversao": "B*1000.0 etc. no produtor; leitor usa cru (mm) -> B*L*h/1e9 p/ m3",
        "nota": "G8: sapata era m no concreto e mm no eletrico -> IFC 1000x menor; _ESCALA_M removido, hoje tudo mm",
    },
    "F02_centro_mm": {
        "chave": 'membro["centro"]',
        "unidade_declarada": UNIDADE_CENTRO_MM,
        "unidade_esperada": UNIDADE_CENTRO_MM,
        "escreve": ["galpao_concreto.membros_bim", "modelo_neutro.fundacoes",
                    "galpao_eletrico.membros_bim"],
        "le": ["geometria_membros.aabb", "ifc_emit.emitir_ifc", "galpao_turnkey._aabb_federado"],
        "nota": "centro da caixa em mm, mesma origem do dims",
    },
    "F03_p1p2_mm": {
        "chave": 'membro["p1"]/["p2"]',
        "unidade_declarada": UNIDADE_P1P2_MM,
        "unidade_esperada": UNIDADE_P1P2_MM,
        "escreve": ["galpao_concreto.membros_bim", "modelo_neutro.frame_primario",
                    "modelo_neutro.tercas", "galpao_eletrico.membros_bim",
                    "modelo_neutro.tirantes_parede", "galpao_mezanino.membros_bim"],
        "le": ["geometria_membros.aabb", "ifc_emit.emitir_ifc", "galpao_turnkey._aabb_federado"],
        "nota": "coordenadas em mm; modelo_neutro.*MM = 1000.0",
    },
    "F04_secao_bf_d_m": {
        "chave": 'membro["secao"]["bf"/"d"/"tw"/"tf"/"D"]',
        "unidade_declarada": UNIDADE_SECAO_M,
        "unidade_esperada": UNIDADE_SECAO_M,
        "escreve": ["perfis.PERFIS", "galpao_concreto.membros_bim (hx,hy,b,h)",
                    "modelo_neutro._I / tercas / girts ( /1000 )",
                    "ifc_emit.membros_do_spec (td/1000)", "galpao_mezanino.membros_bim (hx,hy,b,h)"],
        "le": ["geometria_membros.aabb ( *MM )", "geometria_membros.volume",
               "ifc_emit.emitir_ifc ( * esc )", "orcamento._vol_membros_concreto"],
        "conversao": "produtor guarda m; leitor faz bf*1000.0 p/ mm (aabb) ou esc=1000.0 p/ IFC",
        "nota": "secao sempre m; D (circular) idem",
    },
    "F05_ancoragem_base_eixo": {
        "chave": 'membro["ancoragem"]',
        "unidade_declarada": "enum eixo|base",
        "unidade_esperada": "enum eixo|base",
        "escreve": ["galpao_concreto.membros_bim", "modelo_neutro", "galpao_mezanino.membros_bim"],
        "le": ["geometria_membros.aabb", "ifc_emit._ancorar"],
        "default": "eixo",
        "nota": "G8: build_concreto usava base, ifc_emit usava eixo -> viga 35 cm enterrada; hoje declarado por membro (base p/ viga, omite=eixo)",
    },
    "F06_tipo_enum": {
        "chave": 'membro["tipo"]',
        "unidade_declarada": "enum Footing/Column/Beam/... ",
        "unidade_esperada": "enum Footing/Column/Beam/... ",
        "escreve": ["galpao_concreto.membros_bim", "modelo_neutro.*", "galpao_eletrico.membros_bim",
                    "galpao_mezanino.membros_bim"],
        "le": ["geometria_membros.quantitativo (por_tipo)", "geometria_membros.interpenetracoes",
               "orcamento (Footing separa fundacao)", "ifc_emit (tipo->Ifc*)",
               "galpao_turnkey._disc_de_membro (marca prefixo)"],
        "nota": "Footing vs Beam vs Column define leitura dims vs p1/p2",
    },
    "F07_poligono_esp_mm": {
        "chave": 'membro["poligono"] + ["esp"]',
        "unidade_declarada": UNIDADE_POLIGONO_MM + " / " + UNIDADE_ESP_MM,
        "unidade_esperada": UNIDADE_POLIGONO_MM + " / " + UNIDADE_ESP_MM,
        "escreve": ["modelo_neutro.misulas_joelho", "modelo_neutro.gussets_contrav",
                    "modelo_neutro.tapamentos", "modelo_neutro.nervuras_base"],
        "le": ["ifc_emit.emitir_ifc (poligono + esp -> IfcPlate)"],
        "nota": "painel poligonal em mm + esp mm",
    },
    # ── RAW (disciplinas) ────────────────────────────────────────────
    "F08_raw_spec_vao_m": {
        "chave": 'raw["spec"]["vao"]',
        "unidade_declarada": "m",
        "unidade_esperada": "m",
        "escreve": ["galpao_concreto.rodar (spec.vao -> res.spec.vao)"],
        "le": ["galpao_turnkey._concreto_no_frame_comum (raw['spec']['vao'] p/ dy=vao/2*1000)"],
        "nota": "vao em m; leitor converte p/ mm (*1000)",
    },
    "F09_raw_piso_area_m2": {
        "chave": 'raw["piso"]["area_m2"]',
        "unidade_declarada": "m2",
        "unidade_esperada": "m2",
        "escreve": ["galpao_concreto.rodar (piso_industrial.verifica_piso -> area_m2)",
                    "piso_industrial.verifica_piso"],
        "le": ["orcamento.quantitativos_de_turnkey (piso['area_m2'] -> q[piso_industrial])",
               "caderno_encargos.caderno_de_turnkey (piso existence -> secao piso)"],
        "nota": "G7: piso Nao dimensionado (None) nao vira clausula nem quantitativo",
    },
    "F10_raw_piso_h_cm": {
        "chave": 'raw["piso"]["h_cm"]',
        "unidade_declarada": "cm",
        "unidade_esperada": "cm",
        "escreve": ["piso_industrial.verifica_piso (h_cm)"],
        "le": ["galpao_concreto.gates['piso']['h_cm']", "orcamento (via membros? piso volume)"],
        "nota": "h em cm, nao m",
    },
    "F11_raw_romaneio_kg": {
        "chave": 'raw["romaneio_peso_primario_kg"]',
        "unidade_declarada": "kg",
        "unidade_esperada": "kg",
        "escreve": ["rodar_galpao", "romaneio", "rodar_projeto"],
        "le": ["orcamento.quantitativos_de_turnkey"],
        "nota": "G7: galpao metalico 28.5x20 orçado R$72k sem este peso (19.7 t -> R$355k); hoje lido com NOTA_ACO_PRIMARIO",
    },
    "F12_terca_dims_mm_para_sec_m": {
        "chave": 'spec["estrutura"]["terca_dims"] [h,bf,lip,t] mm -> secao m',
        "unidade_declarada": "mm (lista)",
        "unidade_esperada": "m (secao dict)",
        "escreve": ["rodar_galpao (res.terca_dims = [...] mm)", "rodar_projeto (spec.estrutura.terca_dims)"],
        "le": ["ifc_emit.membros_do_spec (td[0]/1000.0 ... -> terca_sec m)",
               "modelo_neutro.tercas (terca_sec m)"],
        "conversao": "/1000.0 no leitor (ifc_emit, modelo_neutro indireto)",
        "nota": "fronteira mm->m explícita; antes carga usava trib do REF (1,675 vs 2,022 = -21%)",
    },
    "F13_longarina_dims_mm_para_sec_m": {
        "chave": 'spec["estrutura"]["longarina_dims"] [h,bf,tw,tf] mm -> secao m',
        "unidade_declarada": "mm (lista)",
        "unidade_esperada": "m (secao dict)",
        "escreve": ["rodar_galpao (longarina_dims mm)", "rodar_projeto (spec.estrutura.longarina_dims)"],
        "le": ["ifc_emit.membros_do_spec (ld[0]/1000.0 ...)"],
        "conversao": "/1000.0",
    },
    "F14_sapata_adotada_m": {
        "chave": 'spec["estrutura"]["sapata_adotada"] {B,L,h} m',
        "unidade_declarada": "m",
        "unidade_esperada": "m (fronteira m->mm no modelo_neutro)",
        "escreve": ["rodar_galpao (sapata_adotada m)"],
        "le": ["ifc_emit.membros_do_spec (B,L,h m -> fund_sec m -> modelo_neutro.fundacoes B*MM mm)"],
        "conversao": "modelo_neutro.fundacoes faz B*MM",
        "nota": "sapata em m no spec, vira dims mm no membro",
    },
    "F15_volume_m3_de_mm3": {
        "chave": 'membro["dims"] mm -> volume m3',
        "unidade_declarada": "mm (dims) -> m3",
        "unidade_esperada": "m3",
        "escreve": ["galpao_concreto.membros_bim (dims mm)", "modelo_neutro.* (dims mm)",
                    "galpao_mezanino.membros_bim (Slab dims mm)"],
        "le": ["orcamento._vol_membros_concreto (B*L*h/1e9)", "geometria_membros.volume (aabb/1e9)",
               "geometria_membros.quantitativo (vol_m3)"],
        "conversao": "/1e9",
        "nota": "mm3 -> m3; B*L*h/1e9",
    },
    "F16_laje_h_adotada_cm_feedback": {
        "chave": 'laje["h"] cm (h*100) / spec laje h_cm',
        "unidade_declarada": "cm",
        "unidade_esperada": "cm",
        "conversao": "h_m*100 = h_cm; realimenta carga g_kN_m2",
        "escreve": ["laje_concreto.dimensiona_laje", "laje_concreto.verifica_laje"],
        "le": ["edificio_multipavimento.rodar", "bim_edificio.membros_bim"],
        "nota": "G8: laje 10->12 cm sem realimentar carga -> 0.5 kN/m2 sub-carga em 126 m2 x9 pav; hoje laço até convergir + gate laje_compatibilizada",
    },
    "F17_pilar_hx_hy_orientacao": {
        "chave": 'pilar["hx"] // vento X / ["hy"] Y m',
        "unidade_declarada": "m",
        "unidade_esperada": "m",
        "escreve": ["galpao_concreto.rodar", "pilar_concreto"],
        "le": ["galpao_concreto.membros_bim", "desenho_concreto", "geometria_membros.aabb"],
        "nota": "G7: pilar 25x50 aparecia 25 na direcao do vao -> eixo fraco no portico (Ix/Iy=4x); hoje bf=hx (X) e d=hy (Y)",
    },
    # ── G20 — MEZANINO NO GALPAO (costura concreto x metalico dentro do envelope) ─
    "F18_mezanino_geometria_m": {
        "chave": 'spec["mezanino"]["x0"/"y0"/"Lx"/"Ly"/"h"] m',
        "unidade_declarada": "m",
        "unidade_esperada": "m (fronteira m->mm no modelo)",
        "escreve": ["galpao_mezanino.rodar (spec mezanino em m)", "galpao_turnkey._run_mezanino"],
        "le": ["galpao_mezanino.membros_bim ( *MM -> mm )", "geometria_membros.aabb",
               "ifc_emit.emitir_ifc", "galpao_turnkey._aabb_federado", "build_concreto"],
        "conversao": "produtor guarda m; leitor faz x*MM (1000.0) p/ mm (p1/p2/dims/centro)",
        "nota": "G20: mezanino DENTRO do envelope do galpao metalico (X=compr, Y=vao, Z=altura) em m; valida posicao x0+Lx<=comp etc.",
    },
    "F19_mezanino_laje_h_cm": {
        "chave": 'mezanino laje["h"] cm (h_m*100) // laje.h m -> slab dims mm',
        "unidade_declarada": "cm",
        "unidade_esperada": "cm",
        "conversao": "h_m*100 = h_cm; realimenta carga g_kN_m2 via laje_concreto",
        "escreve": ["laje_concreto.dimensiona_laje", "galpao_mezanino.rodar (h_adotada)"],
        "le": ["galpao_mezanino.membros_bim (dims mm: h_laje*MM)", "orcamento._vol_membros_concreto",
               "geometria_membros.aabb", "geometria_membros.volume"],
        "nota": "G20: mesma realimentacao de F16 mas no mezanino (concreto sobre vigas de concreto, dentro do galpao metalico)",
    },
    "F20_mezanino_viga_pilar_secao_m": {
        "chave": 'membro mezanino ["secao"]["bf"/"d"] m (viga/pilar)',
        "unidade_declarada": UNIDADE_SECAO_M,
        "unidade_esperada": UNIDADE_SECAO_M,
        "escreve": ["galpao_mezanino.rodar (b_viga/h_viga/hx/hy m)", "viga_concreto.verifica_viga",
                     "pilar_concreto.dimensiona_pilar", "galpao_mezanino.membros_bim (bf/hx, d/hy)"],
        "le": ["geometria_membros.aabb ( *MM )", "geometria_membros.volume",
               "ifc_emit.emitir_ifc ( *MM )", "orcamento._vol_membros_concreto"],
        "conversao": "produtor guarda m; leitor faz bf*MM p/ mm",
        "nota": "G20: secao de viga/pilar de concreto do mezanino (bf transversal, d vertical) em m; orientacao hx//X, hy//Y como F17",
    },
}

# Validador rapido (importavel pelos testes)
def validar_unidade(fronteira_id, valor, unidade_informada=None):
    """Valida se a unidade de um valor casa com a fronteira declarada.
    Para dims/secao: checa magnitude (mm vs m). Retorna (ok, motivo)."""
    f = FRONTEIRAS[fronteira_id]
    # heuristica de magnitude para detectar m x mm trocado
    if fronteira_id in ("F01_sapata_dims_mm", "F02_centro_mm", "F03_p1p2_mm", "F07_poligono_esp_mm"):
        # mm: valores tipicos 100 .. 50000
        if isinstance(valor, (list, tuple)) and len(valor) >= 1:
            # pega primeiro valor numerico
            v = float(valor[0]) if isinstance(valor, (list, tuple)) else float(valor)
        elif isinstance(valor, (int, float)):
            v = float(valor)
        else:
            return True, "nao numerico"
        if 10 < abs(v) < 1e6:
            return True, "magnitude compativel com mm"
        if 0 < abs(v) < 10:
            return False, "valor %.3f parece estar em m, esperado mm (x1000)" % v
        return True, "fora de faixa tipica mas nao conclusivo"
    if fronteira_id in ("F04_secao_bf_d_m", "F20_mezanino_viga_pilar_secao_m"):
        # m: tipicos 0.1 .. 1.5
        v = float(valor) if isinstance(valor, (int, float)) else 0.0
        if 0.05 < abs(v) < 5.0:
            return True, "magnitude compativel com m"
        if abs(v) > 100:
            return False, "valor %.1f parece estar em mm, esperado m (/1000)" % v
        return True, "fora de faixa"
    if fronteira_id == "F18_mezanino_geometria_m":
        # m: envelope 1..50 m tipico
        try:
            v = float(valor) if isinstance(valor, (int, float)) else float(valor[0]) if isinstance(valor, (list, tuple)) else 0.0
        except Exception:
            return True, "nao numerico"
        if 0.5 < abs(v) < 100.0:
            return True, "magnitude compativel com m (mezanino dentro do galpao)"
        if abs(v) > 500:
            return False, "valor %.1f parece estar em mm, esperado m (/1000)" % v
        return True, "fora de faixa"
    if fronteira_id == "F19_mezanino_laje_h_cm":
        try:
            v = float(valor) if isinstance(valor, (int, float)) else 0.0
        except Exception:
            return True, "nao numerico"
        if 5 < abs(v) < 50:
            return True, "magnitude compativel com cm (laje mezanino)"
        if 0 < abs(v) < 0.5:
            return False, "valor %.3f parece estar em m, esperado cm (x100)" % v
        if abs(v) > 500:
            return False, "valor %.1f parece estar em mm, esperado cm (/10)" % v
        return True, "fora de faixa"
    return True, "sem heuristica"

def lista_ids():
    return sorted(FRONTEIRAS.keys())
