# Changelog

Todas as alterações notáveis deste catálogo serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Adicionado
- `publicacao/`: declaração de conjuntos tabulares publicados no portal (`conjunto.toml` mais consultas `.sql` por conjunto), com o formato versionado (`schema_versao = 1`) documentado em `publicacao/README.md`. Primeiros conjuntos: `pdet/caged` (Novo CAGED por UF e município, com competências preliminares, descartes dos registros sem localização e conferência do saldo nacional) e `cvm/dfp` (contas principais da DFP por companhia e exercício, ODbL-1.0), mais o exemplo fictício `publicacao/_exemplo` e o espelho dele (`publicacao/_exemplo.json`).
- `tests/test_publicacao.py`: valida cada declaração, executa as consultas sobre Parquet sintético (`tests/lake_sintetico.py`) e confere colunas, chave e aritmética (mov + fora do prazo − exclusões; consolidada, escala MIL e versão mais nova), o espelho do exemplo e a ausência de termos de operação interna no catálogo.

- Testes de contrato com o `quantilica-sql`: `tests/test_ibge_contrato.py` roda `EXPLAIN` de cada SQL de `ibge/**` que lê o esquema do SIDRA (51 de 55, descobertas por varredura, não listadas à mão) contra o esquema que `quantilica sql load sidra` cria vazio; `tests/test_bcb_contrato.py` faz o mesmo com as 13 SQL de `macro/**` e `setorial/**` que leem `series_data` do BCB SGS. As 4 SQL de `ibge/**` que leem `analytics.*` (`populacao`, `inflacao`, `inflacao_difusao`, `inflacao_hierarquia_subitem`) ficam fora, com o motivo em `tests/_catalogo.py`; `tests/test_catalogo_descoberta.py` confere a varredura e as exclusões. O catálogo não muda: ganhou teste.
- `tests/test_ibge_resultado.py`: cinco SQL (`ipca`, `leite`, `estimativa_populacao`, `pib_municipal`, `lavouras_temporarias`) rodam sobre fixtures reais do IBGE carregadas pelo `quantilica-sql` (`tests/data/sidra`, cortes de respostas públicas de 25/11/2026) e o resultado é conferido contra um cálculo independente em Python sobre o JSON cru, mais três valores escritos à mão por SQL.
- CI: o `validate.yml` ganha o job `testes` com `postgres:16` e `QUANTILICA_TEST_DATABASE_URL`, que instala `quantilica-sql>=0.4.0` (a versão com o esquema dimensional do SIDRA) e roda os testes acima. No CI (`CI=true`), a falta do banco ou do pacote reprova em vez de pular.
- Testes: o caminho do `lake.py` de cada fonte deixa de ficar em `tests/lake_aliases.toml` e é derivado de `repo` e `module` do registro de fetchers (fixture offline em `tests/conftest.py`; `QUANTILICA_REGISTRO_PUBLICO=1` lê o registro público pelo cache do `quantilica-cli`).
- `docs/marts.md` e `docs/marts_contract.toml`: contrato de colunas e tipos das tabelas `marts.*`, com os marts ativos, os desativados (e o motivo) e o estado dos cinco marts do plano.
- `tests/test_marts_duckdb.py`: executa cada mart em DuckDB em memória com dados sintéticos e confere compilação, esquema de saída contra o contrato, chave única e resultado idêntico para qualquer ordem de entrada.
- Pipeline `tesouro_direto/marts` (`engine = "duckdb"`): agregados dos microdados do Tesouro Direto (investidores e operações) calculados sobre o lake de Parquet e materializados no PostgreSQL (`mv_investor_*`, `mv_investors_*`, `mv_operations_monthly`, `mv_dashboard_stats`), com os mesmos nomes e índices das materialized views que substituem.
- `manifest.toml` passa a listar todos os pipelines do catálogo (eram 11 de 30; entraram 19 de IBGE, macro e setorial) e declara o `engine` de cada um (`postgres` ou `duckdb`).
- Validação em CI (`quantilica-sql validate . --strict`): falha se um `transform.toml` ficar fora do manifest ou se o `engine` for inválido.

### Corrigido
- CI: o `validate.yml` instala `quantilica-sql` com `--find-links` da página do próprio pacote no índice Quantilica, em vez de `--index` + `--index-strategy unsafe-best-match`. Antes o uv consultava o índice (GitHub Pages) para cada dependência de terceiros, e o 503 intermitente que ele responde a pacote que não hospeda derrubava o job.
- Testes: a chave de `tests/lake_aliases.toml` é casada com o `lake_source_id` do registro de fetchers (o `id` quando ele falta), para um renome de fetcher não quebrar `test_every_alias_source_is_in_registry` com `QUANTILICA_REGISTRO_PUBLICO=1`.
- `tests/lake_aliases.toml`: `btc_posicoes_abertas` sai de `literal_aliases` da B3 (o `lake.py` não o escreve), o que fazia `test_literal_aliases_match_fetcher_lake_py` falhar dentro do workspace.
- `marts.trabalho_saldo` lia colunas inexistentes no lake (`uf`, `secao`, `tipomovimentacao`, `saldomovimentacao`, `salario`); passou a ler `id_uf`, `cnae_2_secao`, `tipo_movimentacao`, `saldo_movimento` e `salario_mensal`, e a competência converte `ano` e `mes` para inteiro.
- Ordenação de `marts.comex_fluxos` e `marts.trabalho_saldo` passou a incluir toda a chave, o que torna a saída determinística (antes, linhas empatadas saíam em ordem indefinida).
- Marts desativados do diretório `cross/`: o lado de comércio exterior lê `co_mes` (a coluna `mes` não existe em `comex.*`), as datas de B3 passam pela macro `b3_date`, e `marts.fato_short_interest_b3` e `marts.fato_balanca_logistica_portuaria` assumem os nomes de destino do plano.

## [1.0.0] - 2026-10-25

### Adicionado
- Catálogo declarativo unificado de pipelines ETL e modelos analíticos para o motor `quantilica-sql`, que substitui os catálogos `sidra-pipelines` e `bcb-sgs-pipelines`.
- Pipelines por domínio: `macro/` (juros, câmbio, atividade, crédito, preços e outros), `ibge/` (pesquisas estruturais e agregadas), `setorial/` e `cross/` (modelos que cruzam domínios, como macro e trabalho).
- `manifest.toml` com o índice de pipelines (tema, caminho e descrição).
