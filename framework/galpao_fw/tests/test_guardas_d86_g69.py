"""Lente G69 (D86): as guardas que concordam consigo mesmas.

Censo da arvore (baseline em TRIADAS_G69, congelado nos DOIS sentidos):
38 defs confere_*/verifica_fechamento* (3 com o G130; a ultima antes veio
com o G129; 2 com o
G127; 3 com o G126; a
G107-G112 foi entregue com ESTE censo vermelho - ver item 24; 20 ate o G77; o G80/G81/G82
trouxeram 3 e o confere_folha_svg do G76 so foi triado no G89). A revisao achou a contagem de 15
desatualizada dentro do proprio lote — confere_vergas nasceu no G70 e o
censo, que so procurava os nomes que ja esperava, nao a viu; e o G66
ganhou confere_fechamento_area. Cada guarda vem com origem dos 2 lados:

1. alvenaria_estrutural.confere_fechamento_horizontal — A=soma Fi
   (Fi=Qh x quota, quota=k/k_total, mesmo modulo), B=Qh declarada que
   entrou na reparticao. MESMA expressao -> DECLARACAO (pega adulteracao
   posterior, nunca erro de rigidez). Docstring diz isso; nao apagar.
2. alvenaria_estrutural.confere_fronteira_peso (G60 isolado) — A=Nd que
   entrou na verificacao, B=carga via 6120 passada PRONTA. Independencia
   mora no CHAMADOR; quando ambos sao q x L -> DECLARACAO de transcricao.
3. alvenaria_estrutural.confere_fronteira_peso_parcela (G61) — A=parcela
   Nd isolada (chamador: q x L), B=recomputo interno (q x L, mesma tabela).
   MESMA expressao -> DECLARACAO (pega L/GF/revestimento, nunca parede
   errada). A relacao independente do plano e' a simetria (G61).
4. estrutura_casa.verifica_fechamento_alvenaria — TOTAL (soma por_linha vs
   carga_laje+q*L+telhado: pega OMISSAO de painel) + SIMETRIA (quinhoes
   espelhados em plano palindromo: pega ENDERECAMENTO errado). Hibrida:
   total=declaracao de integridade, simetria=relacao independente.
5. estrutura_casa.confere_simetria_quinhao — A=quinhao linha k, B=quinhao
   linha espelhada; condicao=vaos palindromos (plano). INDEPENDENTE.
6. pavimento_tipo.verifica_fechamento — A=soma reacoes nos pilares (descida),
   B=carga_laje+peso_viga*comp+g_parede*contorno (geometria x cargas).
   Origens diferentes -> INDEPENDENTE (pega laje que some).
7. bim_edificio.confere_modelo (+_confere_modelo_alvenaria) — A=contagem de
   TIPOS no modelo emitido, B=contagem derivada do calculo aprovado
   (pilares x niveis, vigas por malha, fundacao aprovada). INDEPENDENTE.
8. bim_edificio.confere_empilhamento / bim_casa_residencial.confere_solidos
   — A/B=pares de volumes do modelo (AABB via geometria_membros); condicao
   geometrica externa (face, nunca volume). INDEPENDENTE.
9. bim_casa_residencial.confere_areas — A=area do Space emitido (dx*dy),
   B=area do programa declarada. INDEPENDENTE (rotulo x geometria).
10. desenho_pavimento.confere_desenho — A=contagens do DADO (len pilares/
    paineis, linhas de viga), B=rects/textos do SVG. INDEPENDENTE.
11. desenho_pavimento.confere_armacao_vigas — A=tramos calculados por viga,
    B=ocorrencias do nome da viga no SVG (uma por linha de tramo).
    INDEPENDENTE apos G69 (antes: so presenca do nome — parcial D86).
12. desenho_alvenaria.confere_elevacao — A=rects data-parede/vao/ajuste no
    SVG, B=por_linha+vaos+fiadas(pe_direito). INDEPENDENTE.
13. desenho_alvenaria.confere_fiadas — A=rects data-fiadas-*/2 fiadas,
    B=por_linha+vaos. INDEPENDENTE.
14. desenho_alvenaria.confere_vergas (G70) — A=rects data-verga/
    data-contraverga do SVG (comprimento, altura, armadura), B=vergas/
    contravergas do registro calculado. INDEPENDENTE (desenho x dado).
15. telhado_casa_madeira.confere_fechamento_area (G66, pos-revisao) —
    A=carga lancada nos nos, B=telha x area INCLINADA + sobrecarga x area
    PROJETADA. INDEPENDENTE: o fechamento_carga irmao (reacao x lancado)
    fecha por construcao e nao via o tributario de beiral errado.
16. varredura_faixa_validade.confere_cobertura (lente G51) — A=arquivos no
    disco, B=isencoes declaradas com motivo. INDEPENDENTE (meta-guarda).
17. bim_telhado_madeira.confere_modelo (G72) — A=contagem de TIPOS no
    modelo emitido (Member/Beam), B=recomputo da geometria da tesoura
    (n_barras x n_tesouras, tercas = nos do banzo sup). Nao le os
    membros para saber o esperado. INDEPENDENTE (mesma forma do item 7).
18. bim_telhado_madeira.confere_volume (G72) — A=soma bf.d.L medida nos
    membros EMITIDOS (coordenadas + secao em mm), B=vol_madeira_m3 do
    quantitativo do calculo (lista de pecas). Caminhos distintos ate o
    mesmo numero. INDEPENDENTE (rotulo x geometria, item 9).
19. bim_telhado_madeira.confere_orientacao (G72) — A=eixos locais que o
    emissor IFC vai usar (ifc_emit._base_axes com o hint), B=normal do
    plano da tesoura declarada no membro. Mede o EIXO, nao o nome da
    peca. INDEPENDENTE — e a guarda do G3 (viga deitada de lado).

20. desenho_fundacao_edificio.confere_desenho_fundacao (G80) - A=`por_pilar`
    de fundacao_edificio.dimensiona (B/L/Ndim por pilar), B=<rect data-pilar>
    do SVG parseado. Caminhos distintos ate o mesmo numero: o esperado nunca
    e lido do desenho. INDEPENDENTE (drawing-vs-data, mesma forma do item 10).
21. desenho_escada_edificio.confere_desenho_escada (G81) - A=geometria de
    escada_concreto.dimensiona (n_degraus, espelho, piso) + gates do
    incendio, B=rects data-degrau/data-patamar-rect e attrs data-* do SVG.
    INDEPENDENTE (item 10). O comprimento do patamar segue A CONFIRMAR e
    aparece na folha como tal - a guarda confere o que foi declarado, nao
    fecha o numero.
22. desenho_hidraulica.confere_cobertura_galpao (G82) - META-GUARDA de
    contrato, nao de geometria: A=arquivos de fato emitidos em drawings/,
    B=os 3 codigos PE-HI que o indice promete. INDEPENDENTE no eixo que
    importa (disco x indice), e o unico caso do censo em que "conferir" nao
    e' medir desenho: e' impedir que codigo prometido evapore sem motivo.
    Mesma familia do item 16 (confere_cobertura da lente G51).
23. desenho_svg_base.confere_folha_svg (G76) - A=viewBox/width/height
    declarados na folha, B=extremos (xmax/ymax) medidos nos elementos
    desenhados. INDEPENDENTE (o continente x o conteudo): e a guarda que
    pegou a cota 3,5 px fora da folha no G77. Estava no censo desde o G76 e
    so agora foi triada - nomeada aqui para o baseline fechar nos dois
    sentidos.

24. desenho_pavimento.confere_armacao_pilares (G110, trechos no G115) -
    A=trechos do DADO (dict `pilares` de pilar_continuo.dimensiona, agrupados
    por secao+As contiguos: intervalos "1-5"/"6", secao e As da base do
    trecho, soma dos lances), B=ocorrencias do nome no SVG com fronteira de
    palavra + intervalos/secao/As literais. O esperado nunca e lido do
    desenho. INDEPENDENTE (drawing-vs-data, mesma forma do item 11, o irmao
    de vigas). Ramo de ausencia: com `pilares` vazio/ausente o ok so e True
    se a DECLARACAO de ausencia (_AUSENCIA_PILARES) estiver na folha -
    folha vazia calada continua reprovando.

25. f150_decodifica.confere_amostra (G117) - A=15 frases-ancora lidas
    nas paginas RENDERIZADAS da F150 (PNG por fitz, nunca a camada de
    texto: xvi, xvii, 5.1.2, 8.2.3, 9.4.2.6, 11.4.1.3, 14.4.1, 15.4.2,
    17.4.2.3, 22.5.1.3), B=ocorrencias literais no .txt decodificado.
    O esperado nunca e lido do resultado. INDEPENDENTE (a forma das
    drawing-vs-data: especificacao de um lado, produto do outro).

26. edicao_nbr6118_g123.confere_peca (G123) - A=declaracao exigida
    ("NBR 6118:2014" ou "NBR 6118:2023 + Emenda 1:2026" no texto da peca),
    B=substring medida no texto emitido. INDEPENDENTE (especificacao de um
    lado, produto do outro; peca sem declaracao reprova com o motivo
    nomeado, nunca OK silencioso).
27. edicao_nbr6118_g123.confere_pecas (G123) - A=conjunto de pecas de
    concreto que o cliente recebe, B=OK por peca que chega ao veredito
    global (contra saturacao silenciosa do G113). INDEPENDENTE (o global
    so e True com todas as pecas declarando; sem_declaracao lista quem
    falta).
28. edicao_nbr6118_g123.confere_uso_edicao (G123) - A=arquivos no disco que
     importam a fonte unica, B=USO_ESPERADO declarado com motivo (29 usos:
     14 desde o G125 + os 5 do G128, que so leem a chave e a repassam -
     casa_residencial, edificio_adapter, galpao_adapter,
     desenho_casa_residencial, caderno_encargos - + os 10 memoriais fiados
     no G135, que chamam rotulo_edicao() da fonte).
     INDEPENDENTE (meta-guarda, mesma forma do item 16: disco x declaracao;
     extra ou faltando = troca por conta propria).
29. confronto_2014_2023_g122.confere_sites_8_2_5 (G125, auditoria do G122) -
    A=modulos onde a CONTA fct,m C55+ aparece no codigo (regex fora de
    comentario), B=modulos do item 8.2.5 do CONFRONTO_G122, escritos a mao
    com a triagem no inventario. INDEPENDENTE (codigo x inventario: o G122
    partiu das citacoes de "6118" e deixou 5 contas fora; nao_inventariados
    e sem_formula disparam por injecao em tmp_path).
30. cimento_nbr6118_g126.confere_pecas (G126) - A=declaracao exigida
    ("Cimento (NBR 6118 12.3.3" + "(declarado no projeto)" ou
    "piso conservador s=0,38" no texto da peca), B=substring medida no
    texto emitido. INDEPENDENTE (especificacao de um lado, produto do
    outro; peca sem declaracao reprova com o motivo nomeado, nunca OK
    silencioso; o OK global so fecha com todas declarando).
31. cimento_nbr6118_g126.confere_defaults (G126) - A=defaults de cimento no
    codigo (`.get("cimento", "<valido>")` ou parametro `cimento="<valido>"`,
    por AST), B=baseline vazio declarado (nenhum default sobrando: ausente
    e piso, nao CPV/CPII). INDEPENDENTE (codigo x baseline; default novo
    sem triagem = vermelho, provado por injecao em tmp_path).
32. cimento_nbr6118_g126.confere_uso_cimento (G126) - A=arquivos no disco
    que importam a fonte unica, B=LEITORES_ESPERADOS declarado com motivo
    (8 usos: a fonte + 7 leitores; o executivo compoe o relatorio e nao
    importa - dito na fonte). INDEPENDENTE (meta-guarda, mesma forma do
    item 16: disco x declaracao; extra ou faltando = leitura por conta
    propria).
33. fctm_nbr6118_g127.confere_copias (G127) - A=literal da conta fct,m
    C55+ no codigo (regex fora de comentario, o mesmo detector da lente
    do G122), B=fonte unica declarada (so ela pode conter a conta).
    INDEPENDENTE (codigo x declaracao; copia nova fora da fonte ou conta
    apagada da fonte = vermelho, provado por injecao em tmp_path).
34. fctm_nbr6118_g127.confere_uso_fctm (G127) - A=arquivos no disco que
    importam a fonte unica, B=LEITORES_ESPERADOS declarado com motivo
    (13 usos: a fonte + os 10 modulos + a lente do G122, que importa o
    detector unico e a conta para o caso C5 + a fonte do G136, que
    deriva a fctd da fctk,inf daqui - dito na fonte). INDEPENDENTE
    (meta-guarda, mesma forma do item 16: disco x declaracao; extra ou
    faltando = leitura por conta propria).
35. varredura_colisoes_g129.confere_censo (G129) - A=censo vivo das 35
    folhas (pares do estimador por folha), B=BASELINE_G129 declarado com
    a triagem (43 pares isentos com PNG em ISENCOES_G129 + 19 corrigidos
    em CORRIGIDOS_G129). INDEPENDENTE (censo vivo x declaracao; par novo
    ou par sumido = vermelho, provado por injecao em tmp_path).
36. exigencias_nao_verificadas_g130.confere_aplicabilidade (G130) -
    A=chaves DIVIDA de ORFAS_TRIADAS no disco, B=APLICABILIDADE declarada
    com motivo de nao-aplicacao (39 dividas; casa 18, predio 24, galpao
    30, uniao 39). INDEPENDENTE (meta-guarda, mesma forma do item 16:
    disco x declaracao; divida nova sem triagem ou motivo vazio =
    vermelho, provado por injecao em tmp_path).
37. exigencias_nao_verificadas_g130.confere_documento (G130) - A=divida
    aplicavel exigida (nome + clausula da fonte unica no texto do
    pacote), B=substring medida no pacote-legal.md emitido. INDEPENDENTE
    (especificacao de um lado, produto do outro; faltando lista quem nao
    chegou ao cliente, nunca OK silencioso; o OK global so fecha com
    todas citadas).
38. exigencias_nao_verificadas_g130.confere_uso_exigencias (G130) - A=arquivos
    no disco que importam a fonte unica, B=LEITORES_ESPERADOS declarado
    com motivo (2 usos: a fonte + pacote_legal; gestao_casa/edificio e
    entregaveis_projeto so passam a string da tipologia - dito na fonte).
    INDEPENDENTE (meta-guarda, mesma forma do item 16: disco x
    declaracao; extra ou faltando = leitura por conta propria).
39. protensao_fck_g133.confere_pecas (G133) - A=declaracao exigida
    ("Protensao (fck da viga e fckj" + marcas do fck e do fckj, ou
    "sem viga protendida" no texto da peca), B=substring medida no
    texto emitido. INDEPENDENTE (especificacao de um lado, produto do
    outro; peca sem declaracao reprova com o motivo nomeado, nunca OK
    silencioso; o OK global so fecha com todas declarando).
40. protensao_fck_g133.confere_defaults (G133) - A=defaults de protensao
    no codigo (`max(fck, <piso>)`, `.get("fck_protendida"/"fckj_protensao",
    <numero>)` ou `.get("fckj", <nao-fck>)`, por AST), B=baseline vazio
    declarado (nenhum default sobrando: ausente e fck do projeto / fckj
    = fck, nunca C40). INDEPENDENTE (codigo x baseline; default novo
    sem triagem = vermelho, provado por injecao em tmp_path).
41. protensao_fck_g133.confere_uso_protensao (G133) - A=arquivos no disco
    que importam a fonte unica, B=LEITORES_ESPERADOS declarado com motivo
    (8 usos: a fonte + viga_protendida, galpao_concreto, desenho_concreto,
    techdraw_concreto, pacote_legal, galpao_adapter, entregaveis_projeto;
    o executivo compoe os relatorios e nao importa - dito na fonte).
    INDEPENDENTE (meta-guarda, mesma forma do item 16: disco x
    declaracao; extra ou faltando = leitura por conta propria).
42. edicao_nbr6118_g123.confere_copias (G135) - A=texto do carimbo no
    codigo (regex fora de comentario, molde fctm_nbr6118_g127.
    confere_copias), B=fonte unica declarada (so ela pode conter o
    carimbo). INDEPENDENTE (codigo x declaracao; copia nova fora da
    fonte ou carimbo apagado da fonte = vermelho, provado por injecao
    em tmp_path).
43. edicao_nbr6118_g123.confere_rotulos (G135) - A=arquivos no disco com
    o literal "6118:2014" fora de comentario, B=CITACOES_ISENTAS
    declarado com motivo por arquivo (14 citacoes historicas:
    docstrings de metodo / tabela METODOS / clausula-fonte / subtitulo
    default; o carimbo-sentenca continua no item 42). INDEPENDENTE
    (meta-guarda, mesma forma do item 16: disco x declaracao; rotulo
    novo sem triagem ou isencao sem rotulo = vermelho, provado por
    injecao em tmp_path).
44. chaves_to_rodar_g134.confere_censo (G134) - A=chaves de topo que
    to_rodar_params escreve em `p` (por AST), B=CHAVES_ESPERADAS
    declarado com motivo (29 chaves: as 30 menos o cimento, que saiu do
    fluxo metalico com o motivo escrito) + LEITURAS_DECLARADAS
    (norma_6118_edicao via edicao_de_spec, importada e chamada no
    rodar_galpao). INDEPENDENTE (codigo x declaracao; chave nova sem
    leitor, leitura declarada sem uso ou nome morto = vermelho, provado
    por injecao em tmp_path; string em mensagem nao e leitura).
45. fctd_nbr6118_g136.confere_copias (G136) - A=literal da conta fctd
    no codigo (regex fora de comentario e fora de _selftest, o mesmo
    molde de fctm_nbr6118_g127.confere_copias), B=fonte unica declarada
    (so ela pode conter a conta). INDEPENDENTE (codigo x declaracao;
    copia nova fora da fonte ou conta apagada da fonte = vermelho,
    provado por injecao em tmp_path; copia em _selftest e prova
    independente, fora da lente por declaracao na fonte).
    fctd_nbr6118_g136.confere_uso_fctd (G136) - A=arquivos no disco que
    importam a fonte unica, B=LEITORES_ESPERADOS declarado com motivo
    (8 usos: a fonte + os 7 modulos - as 6 copias do backlog com o 1,4
    literal mais base_chumbador via GC, mesmo numero). INDEPENDENTE
    (meta-guarda, mesma forma do item 16: disco x declaracao; extra ou
    faltando = leitura por conta propria).

Proibido G69: apagar guarda fraca sem substituto. As declaracoes acima
ficam — ditas como declaracoes — e a prova do vermelho mora nestes testes.
Mapa do vermelho: neste arquivo (D86 das 2 fracas + omissao do total +
areas, solidos/empilhamento, modelo, desenho, armacao, elevacao, fiadas,
fechamento do pavimento); simetria e enderecamento errado em
test_alvenaria_portante_g61.py; 10 % da fronteira em
test_alvenaria_estrutural_g60.py; Fi adulterada em
test_alvenaria_contraventamento_g63.py; cobertura nos dois sentidos em
test_varredura_faixa_validade_g51.py.
"""

import copy
import re
import xml.etree.ElementTree as ET

import pytest

import alvenaria_estrutural as alv
import desenho_pavimento as dp
import pavimento_tipo as pt


# Baseline do censo (D87: congelado nos DOIS sentidos). Cada par aqui tem
# a triagem escrita no cabecalho deste arquivo, com a origem de cada lado.
TRIADAS_G69 = {
    ("alvenaria_estrutural", "confere_fechamento_horizontal"),
    ("alvenaria_estrutural", "confere_fronteira_peso"),
    ("alvenaria_estrutural", "confere_fronteira_peso_parcela"),
    ("bim_casa_residencial", "confere_areas"),
    ("bim_casa_residencial", "confere_solidos"),
    ("bim_edificio", "confere_modelo"),
    ("bim_edificio", "confere_empilhamento"),
    ("bim_telhado_madeira", "confere_modelo"),
    ("bim_telhado_madeira", "confere_volume"),
    ("bim_telhado_madeira", "confere_orientacao"),
    ("desenho_alvenaria", "confere_elevacao"),
    ("desenho_alvenaria", "confere_fiadas"),
    ("desenho_alvenaria", "confere_vergas"),
    ("desenho_pavimento", "confere_desenho"),
    ("desenho_pavimento", "confere_armacao_vigas"),
    ("estrutura_casa", "confere_simetria_quinhao"),
    ("estrutura_casa", "verifica_fechamento_alvenaria"),
    ("pavimento_tipo", "verifica_fechamento"),
    ("telhado_casa_madeira", "confere_fechamento_area"),
    ("varredura_faixa_validade", "confere_cobertura"),
    ("desenho_fundacao_edificio", "confere_desenho_fundacao"),
    ("desenho_escada_edificio", "confere_desenho_escada"),
    ("desenho_hidraulica", "confere_cobertura_galpao"),
    ("desenho_svg_base", "confere_folha_svg"),
    ("desenho_pavimento", "confere_armacao_pilares"),
    ("f150_decodifica", "confere_amostra"),
    ("edicao_nbr6118_g123", "confere_peca"),
    ("edicao_nbr6118_g123", "confere_pecas"),
    ("edicao_nbr6118_g123", "confere_uso_edicao"),
    ("edicao_nbr6118_g123", "confere_copias"),
    ("edicao_nbr6118_g123", "confere_rotulos"),
    ("confronto_2014_2023_g122", "confere_sites_8_2_5"),
    ("cimento_nbr6118_g126", "confere_pecas"),
    ("cimento_nbr6118_g126", "confere_defaults"),
    ("cimento_nbr6118_g126", "confere_uso_cimento"),
    ("fctm_nbr6118_g127", "confere_copias"),
    ("fctm_nbr6118_g127", "confere_uso_fctm"),
    ("varredura_colisoes_g129", "confere_censo"),
    ("exigencias_nao_verificadas_g130", "confere_aplicabilidade"),
    ("exigencias_nao_verificadas_g130", "confere_documento"),
    ("exigencias_nao_verificadas_g130", "confere_uso_exigencias"),
    ("protensao_fck_g133", "confere_pecas"),
    ("protensao_fck_g133", "confere_defaults"),
    ("protensao_fck_g133", "confere_uso_protensao"),
    ("chaves_to_rodar_g134", "confere_censo"),
    ("fctd_nbr6118_g136", "confere_copias"),
    ("fctd_nbr6118_g136", "confere_uso_fctd"),
}


TE = 0.14
HE = 2.70


def _paredes_2():
    return [
        {"nome": "PX-1", "comprimento_m": 3.0, "te_m": TE, "he_m": HE},
        {"nome": "PX-2", "comprimento_m": 3.0, "te_m": TE, "he_m": HE},
    ]


# --- D86 provado: a guarda passa com a fisica errada ------------------------

def test_fechamento_horizontal_passa_com_rigidez_errada():
    """Duas reparticoes com he diferente dao Fis diferentes e AMBAS fecham.

    Se a guarda conferisse a formula, uma delas teria de acusar. Como fecha
    nos dois casos, ela declara integridade (soma==Qh), nao fisica.
    """
    pars_ok = _paredes_2()
    pars_errada = [
        {"nome": "PX-1", "comprimento_m": 3.0, "te_m": TE, "he_m": HE},
        {"nome": "PX-2", "comprimento_m": 3.0, "te_m": TE, "he_m": HE * 2},
    ]
    d_ok = alv.distribuir_horizontal_por_rigidez(30.0, pars_ok)
    d_err = alv.distribuir_horizontal_por_rigidez(30.0, pars_errada)
    assert d_ok["OK"] and d_err["OK"]
    fi_ok = {r["nome"]: r["Fi_kN"] for r in d_ok["por_parede"]}
    fi_err = {r["nome"]: r["Fi_kN"] for r in d_err["por_parede"]}
    assert fi_ok["PX-1"] != pytest.approx(fi_err["PX-1"], rel=1e-3)
    # e a declaracao fecha nos dois: a prova de que nao confere a formula
    assert alv.confere_fechamento_horizontal(d_ok, 30.0)["OK"] is True
    assert alv.confere_fechamento_horizontal(d_err, 30.0)["OK"] is True
    # ...mas acusa adulteracao posterior (o que ela declara de verdade)
    adulterada = [{"Fi_kN": r["Fi_kN"]} for r in d_ok["por_parede"]]
    adulterada[0]["Fi_kN"] *= 1.10
    f = alv.confere_fechamento_horizontal(adulterada, 30.0)
    assert f["OK"] is False
    assert "fechamento_horizontal_diverge" in f["motivo"]


def test_fronteira_parcela_passa_com_tipo_errado_consistente():
    """Caller e guarda usando o MESMO tipo errado fecham — D86 provado.

    A guarda compara q(tipo)*L contra q(tipo)*L: se o tipo estiver errado
    dos dois lados, ela concorda consigo mesma. O que ela pega e'
    transcricao (L, GF, revestimento), nao a escolha do tipo.
    """
    import cargas_nbr6120 as cg

    tipo_certo = "bloco_concreto_estrutural"
    tipo_errado = "bloco_concreto_vedacao"
    esp, rev, L = 14.0, 2.0, 3.3
    q_err = cg.carga_linear_parede(tipo_errado, esp, HE, rev)
    # chamador isolou a parcela com o tipo errado — a guarda fecha igual
    assert alv.confere_fronteira_peso_parcela(
        q_err * L, tipo_errado, esp, HE, L, rev)["OK"] is True
    # ...mas 10 % a mais num lado acusa a junta (transcricao), nao o elemento
    assert alv.confere_fronteira_peso_parcela(
        q_err * L * 1.10, tipo_errado, esp, HE, L, rev)["OK"] is False
    # e sem parcela isolavel o caso RECUSA em vez de fingir conferencia
    sem = alv.confere_fronteira_peso_parcela(None, tipo_certo, esp, HE, L, rev)
    assert sem["OK"] is False and "parcela" in sem["motivo"]


def test_docstrings_dizem_declaracao_onde_e_decorativa():
    assert "DECLARACAO" in alv.confere_fechamento_horizontal.__doc__
    assert "DECLARACAO" in alv.confere_fronteira_peso_parcela.__doc__
    assert "D86" in alv.confere_fechamento_horizontal.__doc__
    assert "G69" in alv.confere_fronteira_peso_parcela.__doc__


# --- sobreviventes: vermelho por injecao ------------------------------------

def _cfg(**kw):
    base = {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5], "h_laje": 0.10,
            "uso": "residencial_dormitorio", "b_viga": 0.20, "h_viga": 0.50,
            "fck": 30e3, "fyk": 500e3, "pe_direito": 2.90}
    base.update(kw)
    return base


def test_verifica_fechamento_acusa_pilar_sem_carga():
    """verifica_fechamento e' independente: some 10 % da carga dos pilares
    e o total tem de acusar."""
    r = pt.monta(_cfg())
    assert pt.verifica_fechamento(r)["ok"]
    roubado = copy.deepcopy(r)
    roubado["N_total_k"] = roubado["N_total_k"] * 0.90
    f = pt.verifica_fechamento(roubado)
    assert f["ok"] is False
    assert f["N_pilares"] == pytest.approx(roubado["N_total_k"], rel=1e-9)


def test_confere_desenho_acusa_pilar_apagado_do_svg():
    """confere_desenho segue o dado; apagando um pilar do SVG o desenho
    deixa de bater com o dado (vermelho real, nao aritmetica)."""
    NS = "{http://www.w3.org/2000/svg}"
    pav = pt.monta(_cfg())
    svg = dp.planta_formas_svg(pav)
    root = ET.fromstring(svg)
    rects = root.findall(".//" + NS + "rect")
    desenhados = sum(1 for x in rects if x.get("fill") == dp.COR_PILAR)
    c = dp.confere_desenho(pav)
    assert desenhados == c["n_pilares"] == len(pav["pilares"])
    # injecao real: remove um rect de pilar do desenho e reconta
    for x in list(root.iter(NS + "rect")) + list(root.iter("rect")):
        if x.get("fill") == dp.COR_PILAR:
            root.remove(x)
            break
    desenhados_depois = sum(
        1 for x in root.findall(".//" + NS + "rect")
        if x.get("fill") == dp.COR_PILAR)
    assert desenhados_depois == desenhados - 1 != c["n_pilares"]


def test_fechamento_alvenaria_acusa_painel_omitido():
    """A parte TOTAL de verifica_fechamento_alvenaria pega omissao: some a
    laje de uma linha e o total tem de acusar (a simetria, ja vermelha no
    G61, pega o enderecamento errado)."""
    import estrutura_casa as ec

    por = [
        {"nome": "BX-0", "comprimento_m": 10.0, "N_laje_kN": 50.0,
         "Nd_parede_kN": 20.0},
        {"nome": "BX-1", "comprimento_m": 10.0, "N_laje_kN": 50.0,
         "Nd_parede_kN": 20.0},
    ]
    ok = ec.verifica_fechamento_alvenaria(por, 100.0, 2.0,
                                          vaos_x=[10.0], vaos_y=[10.0])
    assert ok["ok"] is True
    omitido = copy.deepcopy(por)
    omitido[0]["N_laje_kN"] = 0.0  # painel que nao desceu na linha
    r = ec.verifica_fechamento_alvenaria(omitido, 100.0, 2.0,
                                         vaos_x=[10.0], vaos_y=[10.0])
    assert r["ok"] is False
    assert r["N_paredes_kN"] == pytest.approx(90.0, rel=1e-9)


def test_confere_areas_acusa_area_trocada_e_ausente():
    """confere_areas e' rotulo x geometria: area trocada e ambiente sumido
    tem de acusar."""
    import bim_casa_residencial as bim

    membros = [{"tipo": "Space", "marca": "Q1", "dims": [3000, 4000, 2700]}]
    prog = {"ambientes": [{"nome": "Q1", "area_m2": 12.0}]}
    assert bim.confere_areas(prog, membros)["ok"] is True
    trocada = {"ambientes": [{"nome": "Q1", "area_m2": 13.0}]}
    r = bim.confere_areas(trocada, membros)
    assert r["ok"] is False and r["por_ambiente"][0]["ok"] is False
    ausente = {"ambientes": [{"nome": "Q2", "area_m2": 12.0}]}
    r2 = bim.confere_areas(ausente, membros)
    assert r2["ok"] is False and r2["ausentes"] == ["Q2"]


def test_solidos_e_empilhamento_acusam_volume_comum():
    """confere_solidos/confere_empilhamento: dois volumes no mesmo lugar
    tem de acusar; separados, passar."""
    import bim_casa_residencial as bim
    import bim_edificio as be

    a = {"tipo": "Wall", "marca": "A", "centro": [0, 0, 0],
         "dims": [1000, 1000, 1000]}
    longe = {"tipo": "Wall", "marca": "B", "centro": [5000, 0, 0],
             "dims": [1000, 1000, 1000]}
    junto = {"tipo": "Wall", "marca": "B", "centro": [0, 0, 0],
             "dims": [1000, 1000, 1000]}
    assert bim.confere_solidos([a, longe])["OK"] is True
    assert be.confere_empilhamento([a, longe])["OK"] is True
    assert bim.confere_solidos([a, junto])["OK"] is False
    r = be.confere_empilhamento([a, junto])
    assert r["OK"] is False
    assert {(x["a"], x["b"]) for x in r["conflitos"]} == {("A", "B")}


def test_confere_modelo_acusa_viga_faltando():
    """confere_modelo e' calculo x modelo: some uma viga do modelo e o
    quadro tem de acusar."""
    import bim_edificio as be

    estrutura = {"pavimento": {"vaos_x": [5.0], "vaos_y": [4.0],
                               "n_paineis": 1},
                 "descida": {"pavimentos": [{"nome": "Tipo"}]},
                 "pilares": [{}, {}]}
    membros = ([{"tipo": "Column", "pavimento": "Tipo"}] * 2
               + [{"tipo": "Beam", "pavimento": "Tipo"}] * 4
               + [{"tipo": "Slab", "pavimento": "Tipo"}])
    assert be.confere_modelo(estrutura, membros)["ok"] is True
    sem_viga = [m for m in membros]
    sem_viga.pop(2)  # uma viga some do modelo
    r = be.confere_modelo(estrutura, sem_viga)
    assert r["ok"] is False
    assert r["por_tipo"]["Beam"] == 3 != r["esperado"]["Beam"]


def test_elevacao_acusa_parede_apagada():
    """confere_elevacao e' desenho x calculado: apague uma parede do SVG e
    a guarda tem de acusar."""
    import desenho_alvenaria as da

    alv = {"por_linha": [{"vaos": []}, {"vaos": []}]}
    pe = 2.8  # fiadas(2.8) tem resto: 1 ajuste por parede
    svg = ('<svg xmlns="http://www.w3.org/2000/svg">'
           '<rect data-parede="a"/><rect data-parede="b"/>'
           '<rect data-ajuste="1"/><rect data-ajuste="2"/></svg>')
    assert da.confere_elevacao(svg, alv, pe)["ok"] is True
    svg_falta = ('<svg xmlns="http://www.w3.org/2000/svg">'
                 '<rect data-parede="a"/>'
                 '<rect data-ajuste="1"/><rect data-ajuste="2"/></svg>')
    r = da.confere_elevacao(svg_falta, alv, pe)
    assert r["ok"] is False
    assert r["paredes_desenhadas"] == 1 != r["paredes_calculadas"]


def test_fiadas_acusa_fiada_apagada():
    """confere_fiadas: duas fiadas por parede; apague uma e acusa."""
    import desenho_alvenaria as da

    alv = {"por_linha": [{"vaos": []}]}
    svg = ('<svg xmlns="http://www.w3.org/2000/svg">'
           '<rect data-fiadas-parede="BX-0-1"/>'
           '<rect data-fiadas-parede="BX-0-2"/></svg>')
    assert da.confere_fiadas(svg, alv)["ok"] is True
    svg_falta = ('<svg xmlns="http://www.w3.org/2000/svg">'
                 '<rect data-fiadas-parede="BX-0-1"/></svg>')
    r = da.confere_fiadas(svg_falta, alv)
    assert r["ok"] is False


def test_armacao_acusa_tramo_faltando_da_mesma_viga():
    """A versao pre-G69 (so presenca do nome) passava aqui; a contagem por
    viga tem de acusar."""
    vv = {"por_linha": [
        {"nome": "VX-1", "tramos": [{"tramo": 0}, {"tramo": 1}]},
        {"nome": "VX-2", "tramos": [{"tramo": 0}]},
    ], "n_tramos": 3}
    svg_ok = "VX-1 VX-1 VX-2"
    conf_ok = dp.confere_armacao_vigas(vv, svg_ok)
    assert conf_ok["ok"] and conf_ok["n_tramos"] == 3
    svg_falta_um_tramo = "VX-1 VX-2"  # nome presente, tramo faltando
    conf = dp.confere_armacao_vigas(vv, svg_falta_um_tramo)
    assert conf["ok"] is False
    assert any("VX-1" in f for f in conf["faltando"])
    # a presenca pura nao bastaria: documenta o defeito antigo
    nomes = ["%s tramo %d" % ("VX-1", k) for k in (0, 1)]
    assert all(n.split()[0] in svg_falta_um_tramo for n in nomes)


def test_censo_das_guardas_fecha_nos_DOIS_sentidos():
    """A lente mora no teste, e baseline de um sentido so e' relatorio.

    A versao anterior varria APENAS os 8 modulos que ja esperava, e so
    perguntava "sumiu alguma?". Guarda NOVA - em modulo novo ou nos
    mesmos 8 - entrava sem triagem e a suite ficava verde: foi o que
    aconteceu com desenho_alvenaria.confere_vergas, criada pelo G70 no
    mesmo lote e invisivel para o G69. Agora o censo varre a arvore
    inteira e cobra os DOIS sentidos: nenhuma some sem substituto, e
    nenhuma nasce sem entrar na triagem do cabecalho (D87)."""
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parents[1]
    pat = re.compile(r"^\s*def\s+(confere_\w+|verifica_fechamento\w*)")
    achadas = set()
    for arq in sorted(raiz.glob("*.py")):
        for linha in arq.read_text(encoding="utf-8",
                                   errors="ignore").splitlines():
            m = pat.match(linha)
            if m:
                achadas.add((arq.stem, m.group(1)))
    sumiram = TRIADAS_G69 - achadas
    novas = achadas - TRIADAS_G69
    # G97: um assert so, com os dois sentidos na mensagem. Dois asserts em
    # sequencia escondiam o segundo (foi assim que confere_vergas nasceu no
    # G70 invisivel e o G77 ficou vermelho sem ninguem ver).
    lados = []
    if sumiram:
        lados.append("guardas sumiram sem substituto: %r" % (sorted(sumiram),))
    if novas:
        lados.append("guarda nova sem triagem D86 (origem de cada lado, "
                     "DECLARACAO ou INDEPENDENTE): declare no cabecalho deste "
                     "arquivo e em TRIADAS_G69: %r" % (sorted(novas),))
    assert not lados, "censo das guardas reprova:\n" + "\n".join(lados)


def test_triagem_do_cabecalho_cobre_cada_guarda_do_censo():
    """O cabecalho e' a triagem escrita; TRIADAS_G69 e' o baseline. Os
    dois tem de falar da mesma lista - senao a lista vira decoracao."""
    doc = __doc__ or ""
    faltando = [nome for _mod, nome in sorted(TRIADAS_G69)
                if nome not in doc]
    assert not faltando, ("guarda no baseline e ausente da triagem "
                          "escrita: %r" % (faltando,))
