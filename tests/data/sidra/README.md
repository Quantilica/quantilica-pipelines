# Fixtures do SIDRA (cortes de respostas reais)

Cortes de respostas públicas do IBGE (SIDRA, `https://apisidra.ibge.gov.br/values/...`,
e metadados de agregados em `https://servicodados.ibge.gov.br/api/v3/agregados/<id>`),
baixadas em **25/11/2026**. O teste não chama a rede. Dados do IBGE.

Usadas por `tests/test_ibge_resultado.py`, que as carrega no esquema do SIDRA do
`quantilica-sql` e roda cinco SQL do catálogo sobre elas. As tabelas 1086, 1612, 6579
e 7060 são cópias byte a byte das fixtures de `quantilica-sql/tests/data/sidra`; a
5938 foi cortada aqui da mesma forma.

| Pasta | Tabela | Consulta | SQL que roda sobre ela |
|---|---|---|---|
| `t-7060/` | 7060, IPCA por grupos e itens | `n1, v, p, c315` | `ibge/precos/snipc/ipca.sql` |
| `t-1086/` | 1086, leite (trimestral) | `n1, v, p, c12716, c12529` | `ibge/agropecuaria/leite/transform.sql` |
| `t-6579/` | 6579, população estimada | `n6 (município), v, p` | `ibge/populacao/estimativa_populacao.sql` |
| `t-5938/` | 5938, PIB dos municípios | `n6 (município), v (7), p 2021` | `ibge/contas_nacionais/pib_municipal/transform.sql` |
| `t-1612/` | 1612, lavouras temporárias | `n3 (UF), v, p, c81` | `ibge/agropecuaria/pam/lavouras_temporarias.sql` (símbolos `-`, `..`, `...`) |

## O corte

- **Dados:** cabeçalho íntegro (primeira linha) e algumas dezenas de linhas, na ordem do
  arquivo original, **sem editar nenhum valor**. Na 5938: 5 municípios (3550308,
  3304557, 5300108, 2927408 e 1100015) com as 7 variáveis da coleta, do ano 2021. O
  `sha256` e o `size_bytes` do sidecar `.manifest.json` são os do arquivo cortado; a
  `url` é a da consulta inteira.
- **Metadados:** estrutura e chaves iguais às do original; na 5938, as localidades
  ficam só nos 5 municípios e os períodos nos anos 2019 a 2021. As variáveis e as
  classificações ficam inteiras.
