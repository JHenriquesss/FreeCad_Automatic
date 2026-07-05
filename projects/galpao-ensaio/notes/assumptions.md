# Assumptions - galpao-ensaio (ensaio do loop da skill)

## Gate 0 - Uso e volumetria (respostas do usuario, 2026-07-05)

- Uso: armazenagem/deposito.
- Dimensoes: comprimento 20 m (X) ; vao transversal 10 m (Y) ; pe-direito 6 m.
- Tipologia: portico de alma cheia (perfil I).
- Ponte rolante: SEM ponte neste ensaio (decisao do usuario: validar o fluxo
  primeiro; MODULO DE PONTE fica no backlog para depois - ver notes/backlog.md).

## LACUNA DE ESCOPO DETECTADA (Gate 0) - ponte rolante

O toolkit de calculo (calc/) NAO dimensiona ponte rolante:
- Sem caso de carga da ponte (vertical + impacto vertical ~25% siderurgica +
  frenagem longitudinal + forca lateral/surto transversal).
- Sem viga de rolamento, sem console (misula), sem contraventamento de arrasto
  longitudinal rigido, sem verificacao de FADIGA (ponte pesada = muitos ciclos).
- A skill (constructability-detailing.md) descreve a GEOMETRIA (consoles, batentes,
  enrijecedores, viga de surto) mas nao ha modulo que CALCULE os esforcos.

Consequencia: dimensionar o portico so com permanente+sobrecarga+vento seria
CONTRA A SEGURANCA para um galpao com ponte pesada. E um estado-limite que o
motor atual nao cobre -> deve ir para o engenheiro / modulo futuro (crane).
