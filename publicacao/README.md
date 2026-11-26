# publicacao/

Conjuntos tabulares publicados no portal Quantilica. Cada pasta `publicacao/<fonte>/<conjunto>/`
declara **um conjunto**: de onde vêm os dados no lake, como viram uma tabela por visão
(UF, município, companhia...), em que unidade, sob qual licença e com que conferências.
O carregador valida a declaração, calcula as consultas em DuckDB sobre o lake e grava o
resultado no portal; o portal serve os cortes (`cs:`) e painéis (`panel:`) lendo só o que o
carregador espelhou. O desenho está no ADR de 25/11/2026 ("Publicação genérica de dados
tabulares no portal").

```
publicacao/
  pdet/caged/        conjunto.toml  caged_base.sql  caged_uf.sql  caged_mun.sql  ...
  cvm/dfp/           conjunto.toml  dfp_base.sql    dfp_cia.sql
  _exemplo/          declaração fictícia com todos os campos (não é publicada)
  _exemplo.json      o espelho do exemplo: contrato com o portal (ver "Espelho")
```

Conjunto novo = `conjunto.toml` + `.sql` + um teste com Parquet sintético. Nada de migração,
adapter, escopo ou lista no portal. O que não cabe na declaração fica **na SQL** (regra de
negócio, por exemplo mov + fora do prazo − exclusões) e não vira campo novo sem ADR.

## Validar e testar

```bash
uv run python infra/publicacao/declaracao.py publicacao --registro infra/registry.json
uv run pytest quantilica-pipelines/tests/test_publicacao.py
```

O validador (`infra/publicacao/declaracao.py` do monorepo, só biblioteca padrão) é estrito:
campo desconhecido, tipo errado, nome fora de `^[a-z][a-z0-9_]{0,40}$`, consulta que escreve ou
lê arquivo por caminho literal e licença que restringe obra derivada sem parecer são erros, e
todos aparecem de uma vez, com o caminho do campo. O teste do repositório roda cada consulta
em DuckDB sobre Parquet sintético e confere colunas, tipos e unicidade da chave.

## O `conjunto.toml`

`schema_versao = 1` é obrigatório. Campos desconhecidos são erro.

| Bloco | Campo | Regra |
|---|---|---|
| raiz | `id` | `<fonte>/<conjunto>`, minúsculas, dígitos e hífen; a fonte é um id do registro de fetchers e o QSID fica `cs:<fonte>/<conjunto>/<medida>` |
| | `titulo`, `titulo_curto`, `descricao` | `titulo_curto` (opcional) prefixa o rótulo do corte ("DFP: Ativo total") |
| | `estado` | `rascunho`, `publicado` ou `aposentado`; `publicado` exige `[[conferencia]]`; `rascunho` não aparece em nenhuma listagem |
| | `catalogo` | id do dataset do catálogo (`fonte/dataset`), liga o conjunto à ficha |
| | `preparo` | `.sql` que cria a tabela temporária `base` (ver "Consultas") |
| | `notas` | textos fixos que acompanham todo frame |
| `[fonte]` | `orgao`, `licenca`, `atribuicao` | obrigatórios; `atribuicao` é o crédito que o portal exibe |
| | `redistribuicao` | `livre` ou `restrita` (`restrita` recusa a carga) |
| | `url`, `[fonte.parecer_licenca]` | `parecer_licenca` (`data`, `por`, `nota`) é obrigatório quando a licença restringe obra derivada (por exemplo CC BY-ND) |
| `[entidade]` | `tipo` | `territorio` (liga ao mapa; qualifier `geo`) ou `identificador` (companhia, estação) |
| | `rotulo`, `qualifier` | nome da entidade e do filtro (`geo`, `cia`, `estacao`) |
| | `chaves_alternativas` | só `identificador`: outras chaves aceitas no filtro (por exemplo `cd_cvm`) |
| `[[entrada]]` | `nome`, `glob` | Parquet do lake que a SQL lê como `$nome`; `glob` relativo à raiz do lake e começando pela pasta da fonte |
| `[[visao]]` | `nivel`, `consulta` | uma tabela gerada por visão: `c_<fonte>_<conjunto>_<nivel>` |
| | `chave` | só `territorio`: `UF`→`sigla`, `MUN`→`ibge6`/`ibge7`, `REGIAO`→`ibge1` |
| | `cabecalhos` | `[cabeçalho da chave, cabeçalho do nome]` da tabela da página |
| | `descartes` | opcional: `.sql` que conta o que a visão deixou de fora (vai para o registro da carga) |
| `[tempo]` | `tipo`, `frequencia` | `dia`/`daily`, `mes`/`monthly`, `trimestre`/`quarterly`, `ano`/`yearly` |
| | `alinhamento_painel` | `inicio` ou `fim`: data do período no painel |
| | `padrao`, `fracao` | `ultimo`, ou `ultimo_com_cobertura` com `fracao` (o período mais recente com ao menos essa fração das entidades do anterior) |
| `[[medida]]` | `id`, `rotulo`, `unidade`, `tipo` | `tipo` = `bigint`, `double` ou `numeric`; coluna `m_<id>` |
| | `aditiva` | somar entre entidades é válido; `descricao` e `nota` opcionais |
| `[[dimensao]]` | `id`, `rotulo`, `valores`, `padrao` | vira coluna `d_<id>` e qualifier (`?tipo_registro=fatal`); sem `valores` a dimensão é aberta |
| `[[atributo]]` | `id`, `rotulo`, `tipo` | coluna da observação fora da chave (`text`, `date`, `boolean`, `integer`); coluna `a_<id>` |
| `[preliminar]` | `ultimos_periodos`, `nota` | os últimos N períodos carregados ganham a nota |
| `[limites]` | `max_linhas_cs`, `max_entidades_painel`, `max_linhas_painel`, `max_linhas_tabela` | padrão 10.000 / 50 / 100.000 / 1.000.000; teto duro 10.000 / 50 / 100.000 / 5.000.000 |
| `[guardas]` | ver abaixo | recusam a troca da tabela quando o cálculo parece errado |
| `[[conferencia]]` | `nivel`, `medida`, `periodo`, `entidade`, `dimensoes`, `valor`, `tolerancia_relativa`, `referencia` | valor conhecido da fonte; sem `entidade`, é a soma das entidades da visão; `dimensoes = {<dimensão> = "<valor>"}` fixa o valor de uma dimensão em vez de somar todos; a primeira carga falha se não bater |

Períodos são textos por `tempo.tipo`: `AAAA-MM-DD`, `AAAA-MM`, `AAAA-T1` e `AAAA`.

### Guardas

Todas valem para cada visão. Padrões entre parênteses.

| Campo | Efeito |
|---|---|
| `queda_maxima_linhas` (0,10) | recusa se a tabela nova tiver menos de `1 − x` das linhas atuais |
| `periodos_nao_somem` (`true`) | recusa se um período já carregado desaparecer, ou se o período máximo recuar |
| `periodos_continuos`, `periodo_inicial` | recusa buracos entre `periodo_inicial` e o último período (vale já na primeira carga) |
| `cobertura_minima_entidades` | recusa se algum período tiver menos entidades que isso (vale já na primeira carga) |
| `queda_maxima_entidades_por_periodo` | recusa se as entidades de um período já carregado caírem mais que isso |
| `revisao_maxima_total`, `revisao_medidas` | recusa se o total de uma medida aditiva num período já carregado variar mais que isso (padrão das medidas: todas as aditivas) |
| `queda_maxima_valores` | recusa se, num período já carregado, a quantidade de valores não nulos de uma medida cair mais que isso (padrão 0,10); uma medida que vira toda nula conta como revisão de 100% |

## Consultas `.sql`

Uma instrução `SELECT`/`WITH` por arquivo, em DuckDB. O lake entra só por `read_parquet($entrada, ...)`;
caminho literal, escrita e `;` no meio são recusados. Os nomes de coluna são fixos:

| Coluna | Tipo | Quando |
|---|---|---|
| `entidade` | texto | sempre; a chave da entidade (sigla da UF, IBGE do município, CNPJ) |
| `entidade_rotulo` | texto | obrigatória em `identificador`; o nome mais recente da entidade |
| `entidade_<chave>` | texto | uma por `chaves_alternativas` |
| `periodo` | data | sempre; **primeiro dia** do período (`AAAA-MM-01`, `AAAA-01-01`) |
| `d_<dimensao>` | texto | uma por dimensão |
| `a_<atributo>` | `text`/`date`/`boolean`/inteiro | uma por atributo |
| `m_<medida>` | inteiro, `DOUBLE` ou `DECIMAL` | uma por medida; `sum()` do DuckDB devolve `HUGEINT`, aceito para `bigint` |

A chave `(entidade, periodo, dimensões)` não se repete. Medida sem valor é `NULL`.
Colunas a mais ou a menos são erro; a ordem não importa.

- **`preparo`:** quando várias visões leem o mesmo agregado caro, ele vira a tabela temporária `base`
  (`CREATE TEMP TABLE base AS <preparo>`) e cada visão lê `FROM base`, sem reler o lake.
- **`descartes`:** devolve `periodo` (texto) mais colunas `m_<medida>` com o que a consulta da visão
  deixou de fora (registros sem localização, por exemplo). Auditoria, não dado servido.
- **Registros sem localização** (UF ou município ignorados) ficam de fora da visão territorial e
  a `notas` do conjunto diz isso; a soma das UFs não é o total divulgado pela fonte.

## Espelho

`Declaracao.espelho()` é o JSON que o carregador grava em `publicacao.conjunto.declaracao`
no portal, na mesma transação da troca dos dados: a declaração com os padrões preenchidos,
o nome de cada tabela gerada e as listas no plural (`visoes`, `medidas`, `dimensoes`,
`atributos`, `conferencias`), **sem** o layout do lake (`entrada`) e sem o texto das consultas.
O portal valida esse JSON com modelo próprio e tolerante (aceita `schema_versao` N e N−1) e
guarda o mesmo exemplo em `tests/fixtures/publicacao_exemplo.json`. O arquivo `_exemplo.json` daqui
é o espelho de `_exemplo/conjunto.toml`; para regravá-lo (e o do portal, igual byte a byte):

```bash
uv run python infra/publicacao/declaracao.py --espelho publicacao/_exemplo/conjunto.toml > publicacao/_exemplo.json
cp publicacao/_exemplo.json quantilica-portal/tests/fixtures/publicacao_exemplo.json
```

`tests/test_publicacao.py` falha se os dois divergirem do que o validador gera.
