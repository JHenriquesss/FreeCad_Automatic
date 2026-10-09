"""Fase 1 do plano de 2026-10-08 - a camada LENTA da suite (infra de teste).

O plano pede duas camadas: a RAPIDA (motores e modelo, roda a cada alteracao,
poucos minutos na maquina de 8 GB) e a LENTA (integracao, pranchas, FreeCAD,
roda antes de entrega). A fronteira e' MEDIDA, nao escolhida por nome: entra
aqui o arquivo de teste que somou 10 s ou mais na corrida inteira de
2026-10-08 (`tools/suite_paralela.py -n 2`, 4020 testes, 1535 s de parede,
3044 s somados, maquina carregada). Quem sobe o FreeCAD e' lento por
definicao e vem de `censo_freecad.GRUPO_FREECAD` (fonte unica, nao copiado).

`tests/conftest.py` marca `slow` nos arquivos daqui; a camada rapida e'
`pytest -m "not slow"` (runner: `tools/suite_rapida.py`).

Remedir: `tools/suite_paralela.py --junitxml=...`, somar `time` por arquivo.
"""
CORTE_S = 10.0

# arquivo (relativo a framework/galpao_fw) -> segundos somados na corrida medida
LENTOS_MEDIDOS = {
    "tests/branches/g15/test_validacao_sistema.py": 319.5,
    "tests/test_edificio_multipavimento.py": 148.8,
    "tests/branches/g12/test_incendio_edificio.py": 144.8,
    "tests/test_ifc_secundarios_xcheck.py": 108.8,
    "tests/test_fase6c_tesoura.py": 101.5,
    "tests/branches/g12/test_hidraulica_eletrica_edificio.py": 93.0,
    "tests/branches/g9/test_g9_fundacao_no_loop.py": 89.8,
    "tests/test_fase6b_alma_variavel.py": 80.0,
    "tests/test_fase65_zona_painel.py": 79.3,
    "tests/branches/g9/test_fundacao_edificio.py": 74.6,
    "tests/test_edicao_tipologias_g128.py": 73.5,
    "tests/test_alcancabilidade.py": 73.1,
    "tests/test_techdraw_concreto.py": 69.9,
    "tests/test_fase64_coluna_tapered.py": 69.6,
    "tests/branches/g14/test_gestao_edificio.py": 66.6,
    "tests/test_colisoes_censo_g129.py": 55.0,
    "tests/test_fase3_fundacao_profunda.py": 54.7,
    "tests/branches/g34/test_vigas_edificio_fechadas.py": 43.3,
    "tests/test_edicao_carimbo_fonte_unica_g135.py": 39.7,
    "tests/test_executivo_eletrico.py": 38.5,
    "tests/branches/g8/test_g8_entregaveis_no_loop.py": 37.5,
    "tests/test_build_federado.py": 35.4,
    "tests/test_auditoria_g143_g148_d176.py": 34.6,
    "tests/test_piso_memoria_g148.py": 33.4,
    "tests/test_exigencias_nao_verificadas_g130.py": 32.2,
    "tests/test_build_concreto.py": 29.7,
    "tests/test_desenho_concreto.py": 29.6,
    "tests/test_fontes_externas_g30_procedencia.py": 29.3,
    "tests/test_veredito_folha_g152.py": 27.6,
    "tests/test_varredura_faixa_validade_g51.py": 26.9,
    "tests/branches/g8/test_g8_ifc_renderiza.py": 25.8,
    "tests/test_turnkey_bim.py": 24.9,
    "tests/test_executivo_concreto.py": 24.2,
    "tests/test_terraplenagem_rodada_g95.py": 23.4,
    "tests/test_cimento_nbr6118_g126.py": 23.2,
    "tests/branches/edificio/test_edificio_adapter.py": 21.8,
    "tests/test_hidraulica_contrato_g82.py": 20.4,
    "tests/branches/g8/test_bim_edificio.py": 20.4,
    "tests/test_indice_disco_rodada_g102.py": 19.7,
    "tests/test_varredura_constantes_orfas_g124.py": 19.1,
    "tests/test_folhas_g77.py": 18.9,
    "tests/test_galpao_concreto_bim.py": 18.6,
    "tests/branches/g8/test_g8_xcheck_freecad.py": 17.5,
    "tests/test_galpao_concreto.py": 17.3,
    "tests/test_turnkey_clash.py": 17.2,
    "tests/test_edificio_g57_spda_emergencia.py": 17.0,
    "tests/test_asserts_sequencia_g97.py": 16.9,
    "tests/test_protensao_fck_g133.py": 16.8,
    "tests/test_bim_instalacoes_edificio.py": 16.7,
    "tests/branches/g4/test_casa_residencial_adapter.py": 15.6,
    "tests/test_edificio_pranchas_g56.py": 15.3,
    "tests/test_edicao_nbr6118_g123.py": 13.4,
    "tests/branches/project_loop/test_project_loop_execution.py": 13.3,
    "tests/test_piso_memoria_g153.py": 12.7,
    "tests/test_defaults_veredito_g75.py": 12.5,
    "tests/test_casa_g58_nivelamento.py": 12.3,
    "tests/test_fallback_get_g150.py": 12.2,
    "tests/branches/edificio/test_g11_vibracao_desempenho.py": 11.2,
    "tests/test_chaves_to_rodar_g134.py": 11.0,
    "tests/test_veredito_folha_g155.py": 10.7,
    "tests/test_geotecnia_spt.py": 10.0,
}


def arquivos_lentos(grupo_freecad):
    """Camada lenta = medidos acima do corte + todo arquivo que sobe o FreeCAD
    (`grupo_freecad` = `censo_freecad.GRUPO_FREECAD`, passado por quem chama:
    este modulo e' carregado por caminho, sem `tests/` no sys.path)."""
    return set(LENTOS_MEDIDOS) | set(grupo_freecad)
