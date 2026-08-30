# Casa residencial elétrica sintética

Fixture de integração da vertical elétrica residencial BT/Enel. Ela registra
um caso sintético para o loop universal; não representa aprovação da Enel,
ART, vistoria ou liberação para construção.

Os campos locais `status: 2` são um snapshot das fontes. Depois de autenticar,
o primeiro comando abaixo produz a verificação viva das fontes antes da
execução; o segundo usa o readiness aprovado.

```powershell
nlm login
python framework/galpao_fw/project_loop_cli.py --spec projects/casa-residencial-eletrica-sintetica/project-spec.json --out-dir projects/casa-residencial-eletrica-sintetica/readiness --verify-source-refs --preflight-only --require-source-refs
python framework/galpao_fw/project_loop_cli.py --spec projects/casa-residencial-eletrica-sintetica/project-spec.json --out-dir projects/casa-residencial-eletrica-sintetica/run --readiness projects/casa-residencial-eletrica-sintetica/readiness --require-source-refs --generate-2d
```

A cobertura de motores desta fase é deliberadamente limitada à combinação
`1 CV trifásico, quantidade 1`. O resultado usa o campo `demand_kva`; motores
fora dessa linha exigem revisão explícita e não são interpolados.

Use uma pasta de saída nova para cada execução. O resultado esperado da
fixture é `needs_review`: `circuits.points` declara as cargas e
`circuits.designs` declara as entradas de engenharia sem defaults.
`circuits.designs` é obrigatório para executar o dimensionamento; quando
faltar, a disciplina fica `blocked` com `missing_circuit_designs`. Nesta fase
a vertical dimensiona condutor/proteção e indica DR/DPS, mas a ausência de
`short_circuit` mantém `short_circuit_evaluation: not_evaluated` e o status
geral em `needs_review`. O fixture continua sendo apenas integração; não
representa aprovação da Enel, ART, vistoria ou liberação para obra.

## Entregáveis (fase 6B)

Com `--generate-2d` o adaptador emite, a partir do MESMO JSON já validado,
`drawings/unifilar.svg`, `drawings/quadro-cargas.svg` e — só quando há layout —
`drawings/planta-eletrica.svg`. Com IFC habilitado sai também
`bim/eletrico-residencial.ifc` (quadro, luminárias, tomadas e condutores). Todos
entram no manifesto com `sha256`. Continua sem FCStd, DXF, PDF e sem prancha
formatada em folha A1.

`circuits.layout` é a entrada OPCIONAL de geometria e não tem default:

- `units` (`"m"`), `board` (`id`, `x_m`, `y_m`, `z_m`), `rooms`
  (`id`, `name`, `x_m`, `y_m`, `width_m`, `depth_m`) e `points`
  (`id`, `x_m`, `y_m`, `z_m`), um para cada ponto de `circuits.points`;
- sem `layout`, `executive_deliverables` fica `schematic_only`: saem só o
  unifilar e o quadro de cargas, e a planta some do manifesto com o motivo
  `layout_not_declared` — nenhuma posição é inventada;
- com `layout` declarado porém incoerente (ponto fora do cômodo que ele mesmo
  declara, cômodos sobrepostos, quadro fora da planta, ponto sem posição), a
  disciplina fica `blocked` — o layout não é reparado.

O emissor BIM compara o comprimento declarado de cada circuito com a distância
reta quadro→ponto do layout. Se o comprimento usado na queda de tensão for
menor que essa distância mínima, o entregável IFC carrega
`declared_length_shorter_than_layout_distance` no manifesto.
