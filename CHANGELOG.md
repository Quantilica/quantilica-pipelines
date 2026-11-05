# Changelog

Todas as alterações notáveis deste catálogo serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Adicionado
- `docs/marts.md` e `docs/marts_contract.toml`: contrato de colunas e tipos das tabelas `marts.*`, com os marts ativos, os desativados (e o motivo) e o estado dos cinco marts do plano.
- `tests/test_marts_duckdb.py`: executa cada mart em DuckDB em memória com dados sintéticos e confere compilação, esquema de saída contra o contrato, chave única e resultado idêntico para qualquer ordem de entrada.
- Pipeline `tesouro_direto/marts` (`engine = "duckdb"`): agregados dos microdados do Tesouro Direto (investidores e operações) calculados sobre o lake de Parquet e materializados no PostgreSQL (`mv_investor_*`, `mv_investors_*`, `mv_operations_monthly`, `mv_dashboard_stats`), com os mesmos nomes e índices das materialized views que substituem.
- `manifest.toml` passa a listar todos os pipelines do catálogo (eram 11 de 30; entraram 19 de IBGE, macro e setorial) e declara o `engine` de cada um (`postgres` ou `duckdb`).
- Validação em CI (`quantilica-sql validate . --strict`): falha se um `transform.toml` ficar fora do manifest ou se o `engine` for inválido.

### Corrigido
- `marts.trabalho_saldo` lia colunas inexistentes no lake (`uf`, `secao`, `tipomovimentacao`, `saldomovimentacao`, `salario`); passou a ler `id_uf`, `cnae_2_secao`, `tipo_movimentacao`, `saldo_movimento` e `salario_mensal`, e a competência converte `ano` e `mes` para inteiro.
- Ordenação de `marts.comex_fluxos` e `marts.trabalho_saldo` passou a incluir toda a chave, o que torna a saída determinística (antes, linhas empatadas saíam em ordem indefinida).
- Marts desativados do diretório `cross/`: o lado de comércio exterior lê `co_mes` (a coluna `mes` não existe em `comex.*`), as datas de B3 passam pela macro `b3_date`, e `marts.fato_short_interest_b3` e `marts.fato_balanca_logistica_portuaria` assumem os nomes de destino do plano.

## [1.0.0] - 2026-10-25

### Adicionado
- Catálogo declarativo unificado de pipelines ETL e modelos analíticos para o motor `quantilica-sql`, que substitui os catálogos `sidra-pipelines` e `bcb-sgs-pipelines`.
- Pipelines por domínio: `macro/` (juros, câmbio, atividade, crédito, preços e outros), `ibge/` (pesquisas estruturais e agregadas), `setorial/` e `cross/` (modelos que cruzam domínios, como macro e trabalho).
- `manifest.toml` com o índice de pipelines (tema, caminho e descrição).
