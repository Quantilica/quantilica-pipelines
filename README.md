# quantilica-pipelines

Catálogo unificado de pipelines ETL e transformações analíticas em SQL para o motor `quantilica-sql`.

## Estrutura

- `macro/`: Indicadores macroeconômicos (juros, inflação, câmbio, atividade econômica).
- `setorial/`: Dados setoriais de infraestrutura, energia e commodities.
- `ibge/`: Pesquisas estruturais e agregadas do IBGE (contas nacionais, agropecuária, indústria, preços).
- `cross/`: Modelos multidimensionais cruzando indicadores de múltiplos domínios e schemas.

## Instalação e Execução

Instale como plugin no `quantilica-sql`:
```bash
quantilica sql plugin install https://github.com/Quantilica/quantilica-pipelines.git --alias std
```

Execute um modelo analítico:
```bash
quantilica sql run macro/juros
quantilica sql run cross/macro_trabalho
```
