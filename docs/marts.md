# Marts analíticos

Os marts são consultas DuckDB sobre o lake Parquet, materializadas no PostgreSQL do
portal, schema `marts`, por `quantilica sql run marts --target-schema marts` (troca
atômica por tabela: `<nome>__new` é carregada, indexada e renomeada numa transação).

O contrato de colunas e tipos está em [`marts_contract.toml`](marts_contract.toml).
`tests/test_marts_duckdb.py` executa cada SQL em DuckDB em memória, com dados
sintéticos, e falha se a saída divergir do contrato. Os tipos são os do DuckDB; no
PostgreSQL viram `bigint`, `integer`, `double precision`, `text`, `date`,
`numeric(p,s)` e `boolean` (`quantilica_sql.lake.duck.pg_type`).

## Marts ativos (no `manifest.toml`)

| Tabela | Chave | Origem no lake |
|---|---|---|
| `marts.macro_series` | `data` | `tesouro_direto.taxas` |
| `marts.comex_fluxos` | `ano, mes, uf, tipo_operacao` | `comex.trade_exp_ncm`, `comex.trade_imp_ncm` |
| `marts.trabalho_saldo` | `competencia, uf, grande_setor` | `pdet.caged_2020_mov` |
| `marts.empresas_ativas` | `uf, porte` | `rfb_cnpj.estabelecimentos`, `rfb_cnpj.empresas` |
| `marts.aviacao_pontualidade` | `aerodromo, ano, mes` | `anac.vra` |

Colunas de cada uma: ver o contrato. Observações:

* `marts.trabalho_saldo.uf` é o código IBGE da UF (`id_uf` do CAGED), não a sigla, e
  `grande_setor` é a letra da seção CNAE (`cnae_2_secao`).
* Toda consulta termina em `ORDER BY` por uma chave completa: a saída é a mesma
  qualquer que seja a ordem das linhas lidas.

## Marts desativados

O SQL e o `transform.toml.disabled` ficam no repositório; o pipeline sai do
`manifest.toml` (a regra do catálogo é nenhum mart ativo lendo view inexistente).
Para reativar: renomear `transform.toml.disabled` para `transform.toml`, descomentar o
bloco no `manifest.toml`, acrescentar os aliases novos em `tests/lake_aliases.toml`,
passar `status = "active"` no contrato e rodar `uv run quantilica sql validate . --strict`.

| Tabela | Motivo (dependência upstream) |
|---|---|
| `marts.fato_short_interest_b3` | O coletor da B3 não baixa o BTC (`b3.btc_posicoes_abertas` não existe no lake); colunas do lado BTC não confirmadas contra dados reais. O lado `b3.cotahist` está correto. |
| `cross.mart_renda_fixa_emissoes` | `b3.indices_carteiras` não tem coleta e `b3.instrumentos` não existe; colunas das views `cvm.*` não confirmadas. |
| `cross.mart_credito_pj_cnae` | `bcb_microdados.scr_carteira_cnae_rating` não existe (o conversor publica `scr`, `estban_*`, `cosif`). |
| `marts.fato_balanca_logistica_portuaria` | Não há coletor da ANTAQ (`antaq.cargas` não existe). O lado `comex.trade_exp_ncm` está correto. |
| `cross.mart_cambio_comercio` | `bcb_microdados.fluxo_cambial_diario` não existe. |

## Os cinco marts do subplano 6 (seção 4)

O plano nomeia cinco tabelas `marts.fato_*`. Estado de cada uma:

| Tabela do plano | Estado |
|---|---|
| `marts.fato_short_interest_b3` | SQL pronto e desativado (BTC). Colunas no contrato. |
| `marts.fato_credito_setorial_inadimplencia` | Sem SQL. O mart `cross.mart_credito_pj_cnae` cobre só carteira por CNAE e modalidade, sem UF nem inadimplência; depende do SCR agregado. |
| `marts.fato_balanca_logistica_portuaria` | SQL pronto e desativado (ANTAQ). Colunas no contrato. |
| `marts.fato_renda_petroleo_fiscal_municipal` | Sem SQL. Não há dataset de receitas fiscais municipais no lake. |
| `marts.fato_pix_atividade_municipal` | Sem SQL. Não há dataset do PIX no lake. |

As colunas só existem no contrato para o que tem SQL; as três tabelas sem SQL não têm
colunas definidas e não devem ser criadas no portal antes de existir coletor e mart.
