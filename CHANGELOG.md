# Changelog

Todas as alterações notáveis deste catálogo serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Adicionado
- `manifest.toml` passa a listar todos os pipelines do catálogo (eram 11 de 30; entraram 19 de IBGE, macro e setorial) e declara o `engine` de cada um (`postgres` ou `duckdb`).
- Validação em CI (`quantilica-sql validate . --strict`): falha se um `transform.toml` ficar fora do manifest ou se o `engine` for inválido.

## [1.0.0] - 2026-10-25

### Adicionado
- Catálogo declarativo unificado de pipelines ETL e modelos analíticos para o motor `quantilica-sql`, que substitui os catálogos `sidra-pipelines` e `bcb-sgs-pipelines`.
- Pipelines por domínio: `macro/` (juros, câmbio, atividade, crédito, preços e outros), `ibge/` (pesquisas estruturais e agregadas), `setorial/` e `cross/` (modelos que cruzam domínios, como macro e trabalho).
- `manifest.toml` com o índice de pipelines (tema, caminho e descrição).
