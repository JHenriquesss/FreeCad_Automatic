"""G75 - os defaults que mudam veredito viram guarda (casa/alvenaria/madeira/vento).

Contexto: um .get(chave, True) fazia uma parede reprovada passar. A nota "a"
da Tab.9 troca o teto de esbeltez de 24 para 30 E o gamma de 2,0 para 3,0:
he/te = 27 sai reprovado sem a nota e aprovado com ela - e estrutura_casa
assumia habitacao_terrea=True por default (G61), depois n == 1 (G67), enquanto
a primitiva defaultava False e o cabecalho do G60 escrevia "opcao declarada,
nunca silenciosa". A regra estava escrita e o codigo fazia o contrario. Nao e
caso isolado por natureza: e um padrao de fronteira entre um modulo cuidadoso
e o wrapper que o chama.

1. FERRAMENTA (varredura_defaults_veredito.py, mesma familia de AST do
   G48/G51, sem vocabulario de faixa): percorre os *.py do diretorio e casa
   chamadas X.get(chave, default) cuja chave esta em NORMATIVAS_G75 (opcao
   normativa: argumento de funcao de verificacao cujo default silencioso ja
   pagou ou pode pagar). V2 pega tambem o resgate por `or` (cfg.get(chave)
   or padrao mascara a ausencia do mesmo jeito - e mascara ate o zero
   declarado). Sem default, o sitio sai como OBRIGATORIO: e o padrao
   declara-ou-recusa (cfg.get(chave) is None -> raise nomeado).
2. CORRECOES: cada default que muda veredito virou recusa nomeada (testes
   test_10 a test_21, um por fix); cada default conservador ou de escopo
   ficou, com o motivo medido (test_30 em diante + triagem abaixo).
3. TRIAGEM (rigor G10): sitio a sitio, medida. O que virou recusa esta nos
   testes de recusa; o que ficou esta abaixo com o numero que prova que nao
   e bug. O que a lente NAO cobre esta dito no cabecalho da ferramenta
   (molde DIVIDA-LENTE do G51).

Triagem do que FICOU (default conservador ou de escopo, com motivo):
- combinacao='normal': gamma maximo (test_30; els/excepcional/especial
  sao menores). Declarar normal e o piso de resistencia.
- altura_m=pe_direito: carga maxima (test_31; a parede da altura do
  pe-direito inteiro pesa mais que qualquer altura menor).
- redutivel=False: carga cheia (test_32; alpha 1,0, sem reducao 6.12).
- z_m=h_ed: S2 maximo no topo (test_33).
- contraflecha_m=0.0: sem contraflecha declarada nao ha desconto
  (test_34; omitido == 0.0 bit a bit).
- limites_flecha=None: extremo estrito da Tab.21 (guardado pelo G66,
  test_tab21_e_faixa_e_o_limite_sem_declaracao_e_o_estrito).
- As_m2=0.0: sem armadura declarada nao ha aco (o 11.5 so le Ea(tipo_bloco)
  no caminho armado; com As>0 o tipo passa a ser obrigatorio, test_18).
- tipo_bloco='bloco_concreto' (2 sitios): default morto - so e lido onde o
  caminho armado ja exigiu o tipo declarado (test_18); com As=0 o Ea nao
  entra na conta.
- ranhurado=False: sem ranhura declarada nao ha ranhura.
- linhas='contorno' na portante: guardado pela recusa
  laje_apoia_em_linha_sem_parede (a linha sem parede nao recebe carga).
- b/h/cobrimento/continuidade/fck/fyk (secao do baldrame e da viga):
  dimensao de secao, dita na folha; sem elas nao ha numero, nao ha
  veredito trocado em silencio.
- verga fyk/phi/bloco: a verga dimensiona e emite na folha (G70); apoio e
  altura ja eram OBRIGATORIO.
- material em build_*/compat/ifc e categoria em compat: camadas de
  emissao/coordenacao, fora da conta que aprova (o calculo ja recusou
  antes, na fronteira do spec).
- n_pavimentos/n_paineis em gestao/BIM/desenho/tesoura/rodar_galpao/
  projeto_spec/techdraw (via get e via or): camadas de gestao e emissao;
  a conta usa o n declarado do spec (o `or` mascara o zero declarado, mas
  nessas camadas zero nao e numero valido de pavimento/painel).
- projeto_spec s1=1.0 / wizard s3=0.95: o normalizador materializa no spec
  e a sugestao do wizard e materializada antes de calcular; o calculo
  (que agora recusa sem s1/s3) nunca recebe o default.
- puncao alpha=90: Hankinson-minimo (test_35; a 90 graus vale f90).
- embutimento_fek/espacamentos_minimos alpha=0.0: assinatura da primitiva;
  os chamadores da arvore passam o alpha declarado (telhado passa 0.0 no
  apoio e a inclinacao no no).
- hidrantes altura_m / galpao_seguranca H: altura do caso, nao opcao.
- entregaveis linhas=[]: lista de entrega, nao carga.
- fa_MPa/habitacao_terrea/apoio_m/altura_m OBRIGATORIO: recusas anteriores
  (G9/G60/G67), ja sem default.
"""
import copy
import os
import sys
from collections import Counter

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_defaults_veredito as vd


def _contagem():
    return Counter((d["arquivo"], d["chave"], d["default"], d["via"])
                   for d in vd.varredura())


def test_01_ferramenta_enxerga_piso_e_so_chave_normativa():
    tudo = vd.varredura()
    assert len(tudo) >= 152, "piso G75+G84: a varredura tem de enxergar >= 152, viu %d" % len(tudo)
    assert {d["chave"] for d in tudo} <= vd.NORMATIVAS_G75
    assert {d["via"] for d in tudo} <= {"get", "or"}
    assert all(set(d) == {"arquivo", "linha", "chave", "default", "via"}
               for d in tudo)


BASELINE_G75 = Counter({
    (u'alvenaria_estrutural.py', u's1', u'OBRIGATORIO', u'get'): 1,
    (u'alvenaria_estrutural.py', u's3', u'OBRIGATORIO', u'get'): 1,
    (u'bim_edificio.py', u'n_pavimentos', u'1', u'or'): 1,
    (u'bim_instalacoes_casa.py', u'n_pavimentos', u'1', u'or'): 1,
    (u'bim_telhado_madeira.py', u'n_paineis', u'2', u'or'): 2,
    (u'build_concreto.py', u'material', u"'Concreto'", u'get'): 2,
    (u'build_eletrico.py', u'material', u"'Aco'", u'get'): 1,
    (u'build_galpao.py', u'n_paineis', u'8', u'get'): 1,
    (u'cargas_nbr6120.py', u'redutivel', u'padrao_redutivel', u'get'): 1,
    (u'compatibilizacao.py', u'categoria', u'CAT_CONFLITO', u'get'): 2,
    (u'compatibilizacao.py', u'categoria', u'OBRIGATORIO', u'get'): 4,
    (u'desenho_alvenaria.py', u'altura_m', u'0.1', u'get'): 1,
    (u'desenho_alvenaria.py', u'altura_verga_m', u'0.0', u'get'): 1,
    (u'desenho_alvenaria.py', u'altura_verga_m', u'0.2', u'get'): 1,
    (u'desenho_alvenaria.py', u'apoio_m', u'0.2', u'get'): 2,
    (u'desenho_alvenaria.py', u'n_pavimentos', u'1', u'or'): 1,
    (u'edificio_multipavimento.py', u'redutivel', u'False', u'get'): 1,
    (u'entregaveis_projeto.py', u'linhas', u'[]', u'get'): 1,
    (u'estabilidade_edificio.py', u's1', u'OBRIGATORIO', u'get'): 1,
    (u'estabilidade_edificio.py', u's3', u'OBRIGATORIO', u'get'): 1,
    (u'estrutura_casa.py', u'As_m2', u'0.0', u'get'): 1,
    (u'estrutura_casa.py', u'altura_m', u'OBRIGATORIO', u'get'): 1,
    (u'estrutura_casa.py', u'altura_m', u'pe_direito', u'get'): 2,
    (u'estrutura_casa.py', u'apoio_m', u'OBRIGATORIO', u'get'): 1,
    (u'estrutura_casa.py', u'combinacao', u"'normal'", u'get'): 2,
    (u'estrutura_casa.py', u'fa_MPa', u'OBRIGATORIO', u'get'): 2,
    (u'estrutura_casa.py', u'habitacao_terrea', u'OBRIGATORIO', u'get'): 2,
    (u'estrutura_casa.py', u'linhas', u"'contorno'", u'get'): 2,
    (u'estrutura_casa.py', u'linhas', u'OBRIGATORIO', u'get'): 1,
    (u'estrutura_casa.py', u'material', u'OBRIGATORIO', u'get'): 2,
    (u'estrutura_casa.py', u'n_pavimentos', u'0', u'get'): 2,
    (u'estrutura_casa.py', u'n_pavimentos', u'1', u'get'): 5,
    (u'estrutura_casa.py', u'n_pavimentos', u'n', u'get'): 1,
    (u'estrutura_casa.py', u'ranhurado', u'False', u'get'): 1,
    (u'estrutura_casa.py', u'redutivel', u'False', u'get'): 1,
    (u'estrutura_casa.py', u'revestimento_cm', u'OBRIGATORIO', u'get'): 1,
    (u'estrutura_casa.py', u'tipo_bloco', u"'bloco_concreto'", u'get'): 2,
    (u'estrutura_casa.py', u'tipo_bloco', u'OBRIGATORIO', u'get'): 1,
    (u'galpao_concreto.py', u's1', u'OBRIGATORIO', u'get'): 1,
    (u'galpao_concreto.py', u's3', u'OBRIGATORIO', u'get'): 1,
    (u'galpao_seguranca_incendio.py', u'altura_m', u'H', u'get'): 1,
    (u'gestao_casa.py', u'n_pavimentos', u'0', u'or'): 1,
    (u'gestao_casa.py', u'n_pavimentos', u'1', u'or'): 3,
    (u'gestao_casa.py', u'n_pavimentos', u'OBRIGATORIO', u'get'): 2,
    (u'gestao_edificio.py', u'n_pavimentos', u'1', u'or'): 2,
    # G87/G89: o "or" do mesmo par (totais do incendio caindo para a
    # estrutura). Nao e default: os dois lados sao dado declarado, e o
    # resultado so entra no texto do motivo. Caso (a), fica.
    (u'gestao_edificio.py', u'n_pavimentos', u"est.get('n_pavimentos')", u'or'): 1,
    # G87/G89: 1 -> 2. A ocorrencia nova e' `totais.get('n_pavimentos') or
    # est.get('n_pavimentos')` na quantificacao do incendio, e alimenta SO o
    # texto do `motivo` ("sem contagem nos totais ... n_pavimentos=%s").
    # Sem default e sem veredito: caso (a) da triagem, fica.
    (u'gestao_edificio.py', u'n_pavimentos', u'OBRIGATORIO', u'get'): 2,
    (u'hidrantes_nbr13714.py', u'altura_m', u"caso.get('pe_direito', 6.0)", u'get'): 1,
    (u'ifc_emit.py', u'material', u'OBRIGATORIO', u'get'): 1,
    (u'madeira_nbr7190.py', u'conifera', u'OBRIGATORIO', u'get'): 1,
    (u'madeira_nbr7190.py', u'fe2_Nmm2', u'OBRIGATORIO', u'get'): 1,
    (u'madeira_nbr7190.py', u'penetracao_mm', u'OBRIGATORIO', u'get'): 2,
    (u'madeira_nbr7190.py', u't2_mm', u'OBRIGATORIO', u'get'): 1,
    (u'pavimento_tipo.py', u'revestimento_cm', u'OBRIGATORIO', u'get'): 1,
    (u'projeto_spec.py', u'n_paineis', u'8', u'get'): 2,
    (u'projeto_spec.py', u's1', u'1.0', u'get'): 1,
    (u'puncao_nbr6118.py', u'alpha_graus', u'90.0', u'get'): 2,
    (u'relatorio_calculo.py', u's1', u'OBRIGATORIO', u'get'): 2,
    (u'relatorio_calculo.py', u's3', u'OBRIGATORIO', u'get'): 2,
    (u'rodar_galpao.py', u'n_paineis', u'8', u'get'): 1,
    (u'rodar_galpao.py', u's1', u'OBRIGATORIO', u'get'): 1,
    (u'rodar_galpao.py', u's3', u'OBRIGATORIO', u'get'): 1,
    (u'techdraw_exec.py', u'n_paineis', u'0', u'get'): 1,
    (u'telhado_casa_madeira.py', u'contraflecha_m', u'0.0', u'get'): 1,
    (u'telhado_casa_madeira.py', u'limites_flecha', u'OBRIGATORIO', u'get'): 1,
    (u'telhado_casa_madeira.py', u'z_m', u'h_ed', u'get'): 2,
    (u'tesoura.py', u'n_paineis', u'8', u'get'): 2,
    (u'vibracao_piso.py', u'As_m2', u'0.0', u'get'): 3,
    (u'viga_baldrame_edificio.py', u'linhas', u'OBRIGATORIO', u'get'): 1,
    (u'wizard.py', u's3', u'0.95', u'get'): 1,
    (u'wizard.py', u'n_maos_francesas', u'0', u'or'): 2,
    # G84: a lente passa nos 4 modulos com mais A CONFIRMAR. Triagem com
    # numero em tests/test_declara_ou_recusa_g84.py (a = fica, b = vira
    # calculo, c = vira recusa). O que ja era OBRIGATORIO segue OBRIGATORIO.
    (u'bim_instalacoes_casa.py', u'n_condutores', u'0', u'or'): 1,
    (u'galpao_concreto.py', u'cbr_pct', u'OBRIGATORIO', u'get'): 1,
    (u'galpao_concreto.py', u'k_MN_m3', u'OBRIGATORIO', u'get'): 1,
    (u'galpao_hidraulica.py', u'area_telhado_m2', u'L * W', u'get'): 1,
    (u'galpao_hidraulica.py', u'decl_calha_pct', u'1.0', u'get'): 1,
    (u'galpao_hidraulica.py', u'decl_esgoto_pct', u'1.0', u'get'): 1,
    (u'galpao_hidraulica.py', u'decl_pluvial_pct', u'1.0', u'get'): 1,
    (u'galpao_hidraulica.py', u'i_pluvial_mm_h', u'hp.I_PLUVIAL_PADRAO_MM_H', u'get'): 1,
    (u'galpao_hidraulica.py', u'metodo_agua', u"'soma'", u'get'): 1,
    (u'galpao_hidraulica.py', u'n_condutores', u'N_CONDUTORES_PADRAO', u'get'): 2,
    (u'galpao_hidraulica.py', u'p_alim_kPa', u'100.0', u'get'): 2,
    (u'hidraulica_residencial.py', u'decl_calha_pct', u'1.0', u'get'): 1,
    (u'hidraulica_residencial.py', u'decl_esgoto_pct', u'1.0', u'get'): 1,
    (u'hidraulica_residencial.py', u'decl_pluvial_pct', u'1.0', u'get'): 1,
    (u'hidraulica_residencial.py', u'metodo_agua', u"'soma'", u'get'): 1,
    (u'hidraulica_residencial.py', u'n_condutores', u'2', u'get'): 1,
    (u'hidraulica_residencial.py', u'p_alim_kPa', u'OBRIGATORIO', u'get'): 1,
    (u'montagem.py', u'peso_unit_kg', u'0.0', u'or'): 1,
    (u'pilar_continuo.py', u'peso_proprio', u'True', u'get'): 1,
    (u'piso_industrial.py', u'cbr_pct', u'OBRIGATORIO', u'get'): 1,
    (u'piso_industrial.py', u'k_MN_m3', u'OBRIGATORIO', u'get'): 1,
    (u'piso_industrial.py', u'posicoes', u"['interior', 'borda']", u'get'): 1,
    (u'piso_industrial.py', u'sigma_solo_adm_kN_m2', u'OBRIGATORIO', u'get'): 1,
    (u'piso_industrial.py', u'udl_kN_m2', u'OBRIGATORIO', u'get'): 1,
    (u'ponte_rolante.py', u'Cb', u'1.0', u'get'): 1,
    (u'ponte_rolante.py', u'Lb', u'L', u'get'): 1,
    (u'ponte_rolante.py', u'Lb', u"cfg['vao_viga']", u'get'): 1,
    (u'projeto_spec.py', u'mesa_interna_travada', u'False', u'get'): 1,
    (u'projeto_spec.py', u'n_maos_francesas', u'OBRIGATORIO', u'get'): 1,
    (u'rodar_galpao.py', u'n_tirantes', u'2', u'get'): 1,
    (u'secundarios_nbr8800.py', u'Cb', u'1.0', u'get'): 2,
    (u'secundarios_nbr8800.py', u'Lb', u'H', u'get'): 1,
    (u'secundarios_nbr8800.py', u'Lb', u'vao', u'get'): 1,
    (u'secundarios_nbr8800.py', u'Nsd', u'5.0', u'get'): 1,
    (u'secundarios_nbr8800.py', u'continua', u'OBRIGATORIO', u'get'): 1,
    (u'secundarios_nbr8800.py', u'gamma_G', u'1.25', u'get'): 1,
    (u'secundarios_nbr8800.py', u'gamma_W', u'1.4', u'get'): 1,
    (u'secundarios_nbr8800.py', u'mesa_interna_travada', u'False', u'get'): 1,
    (u'secundarios_nbr8800.py', u'n_maos_francesas', u'n_t', u'get'): 1,
    (u'secundarios_nbr8800.py', u'n_tirantes', u'1', u'get'): 1,
    (u'secundarios_nbr8800.py', u'peso_proprio', u'0.1', u'get'): 1,
    (u'secundarios_nbr8800.py', u'peso_proprio', u'0.31', u'get'): 1,
    (u'techdraw_exec.py', u'peso_unit_kg', u'OBRIGATORIO', u'get'): 1,
    (u'tercas_nbr14762.py', u'continua', u'False', u'get'): 2,
    (u'viga_baldrame.py', u'continua', u'OBRIGATORIO', u'get'): 1,
})


def test_02_baseline_nos_dois_sentidos():
    """Regra do G33 aplicada a esta varredura (molde do test_08 do G51).
    Sem o baseline a ferramenta e RELATORIO, nao guarda."""
    agora = _contagem()
    novas = sorted(set(agora) - set(BASELINE_G75))
    sumidas = sorted(set(BASELINE_G75) - set(agora))
    for chave in sorted(set(agora) | set(BASELINE_G75)):
        if agora[chave] != BASELINE_G75[chave]:
            raise AssertionError(
                "contagem mudou em %r: baseline %d, agora %d" % (chave, BASELINE_G75[chave], agora[chave]))
    assert not novas, (
        "default em opcao normativa que nao estava triado: %r. Ou vira "
        "recusa nomeada (declarar-ou-recusar), ou entra no BASELINE_G75 com "
        "o motivo medido pelo qual NAO e bug (rigor G10)." % (novas,))
    assert not sumidas, (
        "sitios que a varredura nao acha mais: %r. Se viraram recusa, o "
        "baseline tem de MUDAR junto (senao protege nome morto)." % (sumidas,))


_GAP_GET = [
    "def verifica_algo(cfg):",
    "    s1 = float(cfg.get(\"s1\", 1.0))",
    "    return s1",
    "",
    "def verifica_outro(cfg):",
    "    v = cfg.get(\"s3\")",
    "    if v is None:",
    "        raise ValueError(\"s3 nao declarado\")",
    "    return float(v)",
    "",
]

_GAP_OR = [
    "def conta(spec):",
    "    n = spec.get(\"n_paineis\") or 8",
    "    return n",
    "",
    "def conta2(spec):",
    "    m = spec[\"n_paineis\"] or 8",
    "    return m",
    "",
]


def test_03_vermelho_por_injecao_nos_dois_sentidos(tmp_path):
    """Prova por injecao em diretorio temporario (licao do D81: sem mutar o
    repo). Sentido get: default silencioso e visto; padrao declara-ou-recusa
    sai como OBRIGATORIO, nao como default. Sentido or: o resgate por `or`
    ( inclusive cfg[chave] or padrao) e visto como sitio `or`."""
    gap = tmp_path / "zz_get.py"
    gap.write_text(chr(10).join(_GAP_GET) + chr(10), encoding="utf-8")
    achados = {(d["arquivo"], d["chave"], d["default"], d["via"])
               for d in vd.varredura(raiz=str(tmp_path))}
    assert ("zz_get.py", "s1", "1.0", "get") in achados, achados
    assert ("zz_get.py", "s3", "OBRIGATORIO", "get") in achados, achados
    limpo = tmp_path / "zz_limpo.py"
    limpo.write_text("def soma(a, b):\n    return a + b\n", encoding="utf-8")
    so_get = [d for d in vd.varredura(raiz=str(tmp_path))
              if d["arquivo"] == "zz_limpo.py"]
    assert so_get == [], so_get
    gap_or = tmp_path / "zz_or.py"
    gap_or.write_text(chr(10).join(_GAP_OR) + chr(10), encoding="utf-8")
    achados_or = {(d["arquivo"], d["chave"], d["default"], d["via"])
                  for d in vd.varredura(raiz=str(tmp_path))}
    assert ("zz_or.py", "n_paineis", "8", "or") in achados_or, achados_or
    n_or = [d for d in vd.varredura(raiz=str(tmp_path))
            if d["arquivo"] == "zz_or.py"]
    assert len(n_or) == 2, n_or


# --- recusas: um teste por fix (o default que mudava veredito) ---------------

PAREDE_G75 = {"tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14,
              "altura": 2.7, "revestimento_cm": 2.0}

VENTO_SEM_S = {"v0": 40.0, "cat": "II", "classe": "B",
               "ca": {"x": 1.1, "y": 1.1}}


def _terrea_g75(**mud):
    spec = {
        "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                      "pe_direito": 2.7},
        "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
        "parede_sobre_vigas": dict(PAREDE_G75),
        "baldrame": {"b": 0.15, "h": 0.40, "linhas": "contorno",
                     "parede": dict(PAREDE_G75)},
    }
    spec.update(copy.deepcopy(mud))
    return spec


def _sobrado_vento_g75():
    spec = _terrea_g75(
        pavimentos=[{"nome": "Cobertura", "uso": "cobertura_manutencao"},
                    {"nome": "Terreo", "uso": "residencial_dormitorio"}],
        vento=dict(VENTO_SEM_S))
    return spec


def _portante_g75(**mud):
    spec = _terrea_g75()
    spec["alvenaria_portante"] = {
        "fpk": 4000.0, "material": "bloco", "te": 0.14,
        "combinacao": "normal", "habitacao_terrea": True,
        "parede_6120": {"tipo": "bloco_concreto_estrutural",
                        "espessura_cm": 14.0, "revestimento_cm": 2.0},
        "linhas": "todas"}
    for k, v in mud.items():
        spec["alvenaria_portante"][k] = v
    return spec


VENTO_G75 = {"v0": 35.0, "cat": "II", "classe": "B", "s1": 1.0,
             "s3": 1.0, "ca": {"x": 0.9, "y": 1.1}}


def _sobrado_portante_g75(vento=None, **mud):
    spec = {
        "geometria": {"vaos_x": [4.0], "vaos_y": [5.0], "pe_direito": 2.7},
        "pavimentos": [{"nome": "Sup", "uso": "residencial_dormitorio"},
                       {"nome": "Ter", "uso": "residencial_dormitorio"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
        "alvenaria_portante": {
            "fpk": 4000.0, "material": "bloco", "te": 0.14,
            "combinacao": "normal", "habitacao_terrea": False,
            "parede_6120": {"tipo": "bloco_concreto_estrutural",
                            "espessura_cm": 14.0, "revestimento_cm": 2.0},
            "linhas": "todas", "fa_MPa": 5.0},
        "vento": dict(VENTO_G75) if vento is None else vento,
        "baldrame": {"b": 0.15, "h": 0.40, "linhas": "contorno",
                     "q_parede": 5.0},
        "fundacao": {"tipo": "sapata_corrida", "sigma_solo_adm": 150.0,
                     "cota_apoio_m": 1.0},
    }
    for k, v in mud.items():
        spec["alvenaria_portante"][k] = v
    return spec


def _msgs_alvenaria(r):
    g = r["gates"]
    txt = " ".join(g["alvenaria_portante"].get("reprovadas", []))
    return txt + " " + str(g["fechamento_carga"].get("erro"))


def _telhado_g75():
    return {
        "vao": 8.0, "inclinacao_graus": 25.0, "extensao": 10.4,
        "espacamento": 2.0, "n_paineis": 2, "forro_fragil": False,
        "telha": {"tipo": "ondulada", "peso": 0.55},
        "sobrecarga_kNm2": 0.25,
        "madeira": {"classe": "C24", "carregamento": "curta", "umidade": 2,
                    "categoria": "serrada"},
        "secoes": {"banzo_sup": {"b": 0.08, "h": 0.16},
                   "banzo_inf": {"b": 0.06, "h": 0.16},
                   "diagonal": {"b": 0.06, "h": 0.12},
                   "montante": {"b": 0.06, "h": 0.12},
                   "terca": {"b": 0.06, "h": 0.16}},
        "apoio": "viga",
        "travamento_borda_comprimida_m": 2.0,
        "contraventamento_banzo_inf_m": 2.0,
        "apoio_comprimento_m": 0.2,
        "ligacao": {"tipo_pino": "parafuso", "d_mm": 12.0, "fu_MPa": 415.0,
                    "t_chapa_mm": 6.3, "n_pinos": 4,
                    "config_73": "chapa_central_dupla",
                    "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                                     "a3c": 80, "a4t": 60, "a4c": 60},
                    "he_mm": 90.0},
    }


def test_10_vento_concreto_sem_s1_recusa_nomeando():
    """s1/s3 no caminho do sobrado de concreto: sem eles nao ha Vk."""
    import estrutura_casa as ec
    with pytest.raises(ec.EntradaEstrutura) as erro:
        ec.rodar(_sobrado_vento_g75())
    assert "vento_concreto_rejeitado" in str(erro.value), str(erro.value)
    assert "s1" in str(erro.value)
    cheio = _sobrado_vento_g75()
    cheio["vento"] = dict(VENTO_SEM_S, s1=1.0, s3=1.0)
    assert ec.rodar(cheio)["ATENDE"] is True


def test_11_vento_portante_sem_s1_recusa_nomeando():
    """s1/s3 no caminho do sobrado em alvenaria: sem eles nao ha Fa."""
    import estrutura_casa as ec
    sem_s = {k: v for k, v in VENTO_G75.items() if k not in ("s1", "s3")}
    r = ec.rodar(_sobrado_portante_g75(vento=sem_s))
    assert r["ATENDE"] is False
    txt = _msgs_alvenaria(r)
    assert "vento.s1 nao declarado" in txt, txt
    assert ec.rodar(_sobrado_portante_g75())["ATENDE"] is True


def test_12_vento_alvenaria_direto_recusa_e_completo_roda():
    import alvenaria_estrutural as alv
    try:
        alv.vento_fa_por_nivel(2, 2.7, 8.0, dict(VENTO_SEM_S, ca=1.0))
        raise AssertionError("vento sem s1/s3 devia recusar")
    except alv.EntradaAlvenaria as exc:
        assert "vento.s1/s3 nao declarados" in str(exc)
    w = alv.vento_fa_por_nivel(
        2, 2.7, 8.0, dict(VENTO_SEM_S, ca=1.0, s1=1.0, s3=1.0))
    assert len(w["niveis"]) == 2 and w["F_total_kN"] > 0


def test_13_vento_estabilidade_direto_recusa_e_completo_roda():
    import estabilidade_edificio as ee
    spec = {"geometria": {"vaos_x": [3.5], "vaos_y": [4.0],
                          "pe_direito": 2.7},
            "n_pavimentos": 2, "vento": dict(VENTO_SEM_S)}
    try:
        ee.vento_por_pavimento(spec, "x")
        raise AssertionError("vento sem s1/s3 devia recusar")
    except ValueError as exc:
        assert "vento.s1/s3 nao declarados" in str(exc)
    spec["vento"] = dict(VENTO_SEM_S, s1=1.0, s3=1.0)
    r = ee.vento_por_pavimento(spec, "x")
    assert len(r["pavimentos"]) == 2 and r["F_total_kN"] > 0


def test_14_telhado_categoria_sem_default():
    """serrada x recomposta troca o kmod e as resistencias: sem categoria
    declarada nao ha numero (molde test_telhado_sem_peso_e_sem_classe_recusa
    do G66)."""
    import telhado_casa_madeira as tmad
    assert tmad.rodar(_telhado_g75())["ATENDE"] is True
    sem = _telhado_g75()
    del sem["madeira"]["categoria"]
    try:
        tmad.rodar(sem)
        raise AssertionError("telhado sem categoria devia recusar")
    except tmad.EntradaTelhado as exc:
        assert "categoria" in str(exc), str(exc)


def test_15_material_portante_sem_declaracao_recusa():
    """bloco (0,70) x tijolo (0,60): o fator troca fd e muda o veredito."""
    import estrutura_casa as ec
    spec = _portante_g75()
    del spec["alvenaria_portante"]["material"]
    r = ec.rodar(spec)
    assert r["ATENDE"] is False
    txt = _msgs_alvenaria(r)
    assert "alvenaria_portante.material nao declarado" in txt, txt
    assert ec.rodar(_portante_g75())["ATENDE"] is True


def test_16_revestimento_sem_declaracao_recusa_nos_quatro_caminhos():
    """O peso da parede (NBR 6120) entra em N em quatro caminhos; sem o
    revestimento nao ha carga - e sem carga nao ha veredito."""
    import estrutura_casa as ec
    import pavimento_tipo as pt
    import viga_baldrame_edificio as vb
    sem = dict(PAREDE_G75)
    del sem["revestimento_cm"]
    r = ec.rodar(_terrea_g75(baldrame={"b": 0.15, "h": 0.40,
                                       "linhas": "contorno",
                                       "parede": sem}))
    assert "baldrame.parede.revestimento_cm nao declarado" in str(
        r.get("baldrame_erro")), r.get("baldrame_erro")
    spec_p = _portante_g75()
    spec_p["alvenaria_portante"]["parede_6120"] = {
        "tipo": "bloco_concreto_estrutural", "espessura_cm": 14.0}
    r2 = ec.rodar(spec_p)
    assert r2["ATENDE"] is False
    txt = _msgs_alvenaria(r2)
    assert "parede_6120.revestimento_cm nao declarado" in txt, txt
    cfg = {"vaos_x": [5.0], "vaos_y": [4.5], "h_laje": 0.10,
           "uso": "residencial_dormitorio", "fck": 30e3,
           "parede_sobre_vigas": {"tipo": "bloco_ceramico_furo_horizontal",
                                  "espessura_cm": 14}}
    try:
        pt.monta(cfg)
        raise AssertionError("parede sem revestimento devia recusar")
    except ValueError as exc:
        assert "parede_sobre_vigas.revestimento_cm nao declarado" in str(exc)
    try:
        vb._valida({"viga_baldrame": {"parede": dict(sem)}})
        raise AssertionError("parede sem revestimento devia recusar")
    except vb.EntradaBaldrame as exc:
        assert "revestimento_cm" in str(exc), str(exc)


def test_17_linhas_sem_declaracao_recusa_nos_dois_baldrames():
    """contorno x todas decide quais linhas recebem viga e muda as reacoes."""
    import estrutura_casa as ec
    import viga_baldrame_edificio as vb
    r = ec.rodar(_terrea_g75(baldrame={"b": 0.15, "h": 0.40,
                                       "parede": dict(PAREDE_G75)}))
    assert "baldrame.linhas nao declarado" in str(
        r.get("baldrame_erro")), r.get("baldrame_erro")
    try:
        vb._valida({"viga_baldrame": {"b": 0.20, "h": 0.40,
                                      "q_parede": 5.0}})
        raise AssertionError("baldrame sem linhas devia recusar")
    except vb.EntradaBaldrame as exc:
        assert "viga_baldrame.linhas deve ser declarado" in str(exc)
    vb._valida({"viga_baldrame": {"b": 0.20, "h": 0.40, "linhas": "contorno",
                                  "q_parede": 5.0}})


def test_18_tipo_bloco_so_e_obrigatorio_com_armadura():
    """A 11.5/Anexo C so le Ea(tipo_bloco) no caminho armado: com As>0 sem
    tipo RECUSA; com As=0 o default nunca entra na conta (teste_18b)."""
    import estrutura_casa as ec
    spec = _sobrado_portante_g75(As_m2=4e-4, fyk=500e3)
    r = ec.rodar(spec)
    assert r["ATENDE"] is False
    assert "alvenaria_portante.tipo_bloco nao declarado" in _msgs_alvenaria(
        r), _msgs_alvenaria(r)
    com_tipo = _sobrado_portante_g75(As_m2=4e-4, fyk=500e3,
                                     tipo_bloco="bloco_concreto")
    r2 = ec.rodar(com_tipo)
    assert "alvenaria_portante.tipo_bloco nao declarado" not in (
        _msgs_alvenaria(r2))


def test_18b_sem_armadura_o_tipo_nunca_entra_na_conta():
    """Com As = 0 (default) o caminho e gravitacional puro e o default
    'bloco_concreto' nunca e lido: a terrea atende igual com e sem tipo."""
    import estrutura_casa as ec
    assert ec.rodar(_portante_g75())["ATENDE"] is True
    assert "tipo_bloco nao declarado" not in _msgs_alvenaria(
        ec.rodar(_portante_g75()))


def test_19_telhado_forro_e_paineis_sem_default():
    """forro_fragil decide os limites da Tab.21 e n_paineis a geometria."""
    import telhado_casa_madeira as tmad
    assert tmad.rodar(_telhado_g75())["ATENDE"] is True
    sem_forro = _telhado_g75()
    del sem_forro["forro_fragil"]
    try:
        tmad.rodar(sem_forro)
        raise AssertionError("telhado sem forro_fragil devia recusar")
    except tmad.EntradaTelhado as exc:
        assert "forro_fragil" in str(exc)
    sem_n = _telhado_g75()
    del sem_n["n_paineis"]
    try:
        tmad.rodar(sem_n)
        raise AssertionError("telhado sem n_paineis devia recusar")
    except tmad.EntradaTelhado as exc:
        assert "n_paineis" in str(exc)


def _cfg_mm_g75(**kw):
    import madeira_nbr7190 as mad
    fe = mad.embutimento_fek(12.0, 350.0, True, True, 0.0)["fe_k_Nmm2"]
    base = {"tipo_pino": "parafuso", "d_mm": 12.0, "d0_mm": 12.5,
            "fu_MPa": 415.0, "t1_mm": 160.0, "t2_mm": 160.0,
            "fe1_Nmm2": fe, "fe2_Nmm2": fe, "n_pinos": 4,
            "n_cortes": 2, "kmod1": 0.9, "kmod2": 0.9,
            "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                             "a3c": 80, "a4t": 60, "a4c": 60},
            "alpha_graus": 0.0, "t_madeira_mm": 80.0,
            "penetracao_mm": 80.0}
    base.update(kw)
    return base


def _cfg_73_g75(**kw):
    import madeira_nbr7190 as mad
    fe = mad.embutimento_fek(12.0, 350.0, True, True, 0.0)["fe_k_Nmm2"]
    base = {"config_73": "chapa_central_dupla", "tipo_pino": "parafuso",
            "d_mm": 12.0, "fu_MPa": 415.0, "t1_mm": 160.0, "t2_mm": 160.0,
            "fe1_Nmm2": fe, "fe2_Nmm2": fe, "n_pinos": 4, "n_planos": 2,
            "kmod1": 0.9, "kmod2": 0.9,
            "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                             "a3c": 80, "a4t": 60, "a4c": 60},
            "alpha_graus": 0.0, "t_madeira_mm": 80.0,
            "penetracao_mm": 80.0, "t_chapa_mm": 6.3}
    base.update(kw)
    return base


def test_20_ligacao_72_sem_espessura_ou_alpha_recusa():
    """7.2: t2/fe2 entram em todos os modos (beta e r), t_madeira nos
    portoes a-f e alpha na Tab.14. Sem eles nao ha FvRk."""
    import madeira_nbr7190 as mad
    assert mad.verifica_ligacao_madeira_madeira(10.0, _cfg_mm_g75())["OK"] is True
    for chave in ("t2_mm", "fe2_Nmm2", "t_madeira_mm", "alpha_graus"):
        cfg = _cfg_mm_g75()
        del cfg[chave]
        try:
            mad.verifica_ligacao_madeira_madeira(10.0, cfg)
            raise AssertionError("7.2 sem %s devia recusar" % chave)
        except mad.EntradaMadeira as exc:
            assert "ligacao 7.2 precisa de" in str(exc), str(exc)
            assert chave in str(exc)


def test_21_ligacao_73_simples_nao_pede_t2_lateral_pede():
    """7.3: chapa simples/central usa fe1/t1; so chapas laterais usam
    fe2/t2. alpha e t_madeira valem sempre (portoes 7.2 a-f e Tab.14)."""
    import madeira_nbr7190 as mad
    cheio = _cfg_73_g75()
    r_cheio = mad.verifica_ligacao(10.0, cheio)
    assert r_cheio["OK"] is True
    sem_t2 = _cfg_73_g75()
    del sem_t2["t2_mm"]
    del sem_t2["fe2_Nmm2"]
    r_simples = mad.verifica_ligacao(10.0, sem_t2)
    assert r_simples["OK"] is True
    assert r_simples["FvRk_por_plano_N"] == r_cheio["FvRk_por_plano_N"]
    for config in ("chapas_laterais_finas_dupla",
                   "chapas_laterais_grossas_dupla"):
        cfg = _cfg_73_g75(config_73=config)
        del cfg["t2_mm"]
        try:
            mad.verifica_ligacao(10.0, cfg)
            raise AssertionError("%s sem t2 devia recusar" % config)
        except mad.EntradaMadeira as exc:
            assert "t2_mm" in str(exc) and "fe2_Nmm2" in str(exc)
    for chave in ("alpha_graus", "t_madeira_mm"):
        cfg = _cfg_73_g75()
        del cfg[chave]
        try:
            mad.verifica_ligacao(10.0, cfg)
            raise AssertionError("7.3 sem %s devia recusar" % chave)
        except mad.EntradaMadeira as exc:
            assert chave in str(exc)


# --- triagem medida do que FICOU --------------------------------------------

def test_30_combinacao_normal_e_o_gamma_maximo():
    import alvenaria_estrutural as alv
    gammas = {c: g["alvenaria"] for c, g in alv.GAMMA_M.items()}
    assert gammas["normal"] == 2.0
    assert gammas["normal"] == max(gammas.values())


def test_31_altura_default_e_a_carga_maxima():
    import cargas_nbr6120 as cg
    tipo, esp, rev = "bloco_ceramico_furo_horizontal", 14, 2.0
    assert cg.carga_linear_parede(tipo, esp, 2.0, rev) < cg.carga_linear_parede(
        tipo, esp, 2.7, rev)


def test_32_nao_redutivel_e_carga_cheia():
    import cargas_nbr6120 as cn
    pavs = [{"nome": "P%d" % k, "uso": "residencial_dormitorio", "area": 50.0}
            for k in range(5)]
    pavs[2]["redutivel"] = False
    saida = cn.multiplicadores_pavimentos(pavs, elemento="pilar")
    assert saida[2]["alpha"] == 1.0
    assert saida[2]["qk_reduzido"] == saida[2]["qk"]
    assert any(s["alpha"] < 1.0 for s in saida)


def test_33_s2_no_topo_e_o_maximo():
    import vento_nbr6123 as vt
    assert vt.s2_factor("II", "B", 10.0)[3] >= vt.s2_factor("II", "B", 5.0)[3]


def test_34_contraflecha_omitida_e_zero():
    import madeira_nbr7190 as mad
    base = dict(wG_kN_m=2.0, wQ_kN_m=1.0, L_m=3.0, E0m=11e6, I_m4=2e-5,
                classe_umidade=2)
    r1 = mad.verifica_els_terca(forro_fragil=False, **base)
    r2 = mad.verifica_els_terca(forro_fragil=False, contraflecha_m=0.0,
                                **base)
    assert r1 == r2


def test_35_hankinson_a_90_e_o_minimo():
    import madeira_nbr7190 as mad
    assert mad.hankinson(10.0, 3.0, 90.0) == 3.0
    assert mad.hankinson(10.0, 3.0, 0.0) == 10.0
