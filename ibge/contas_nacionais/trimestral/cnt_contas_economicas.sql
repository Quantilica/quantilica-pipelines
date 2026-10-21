WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '2072'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    MAX(CASE WHEN VARIAVEL = 'Produto Interno Bruto'                                                          THEN VALOR   END) AS PIB,
    MAX(CASE WHEN VARIAVEL = 'Produto Interno Bruto'                                                          THEN UNIDADE END) AS PIB_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE '(+) Salários%'                                                               THEN VALOR   END) AS SALARIOS_LIQUIDOS,
    MAX(CASE WHEN VARIAVEL LIKE '(+) Rendas de propriedade%'                                                  THEN VALOR   END) AS RENDAS_PROPRIEDADE,
    MAX(CASE WHEN VARIAVEL LIKE '(=) Renda nacional bruta%'                                                   THEN VALOR   END) AS RENDA_NACIONAL_BRUTA,
    MAX(CASE WHEN VARIAVEL LIKE '(+) Outras transferências%'                                                  THEN VALOR   END) AS OUTRAS_TRANSFERENCIAS_CORRENTES,
    MAX(CASE WHEN VARIAVEL LIKE '(=) Renda nacional disponível%'                                              THEN VALOR   END) AS RENDA_NACIONAL_DISPONIVEL,
    MAX(CASE WHEN VARIAVEL LIKE '(-) Despesa de consumo%'                                                     THEN VALOR   END) AS DESPESA_CONSUMO_FINAL,
    MAX(CASE WHEN VARIAVEL LIKE '(=) Poupança%'                                                               THEN VALOR   END) AS POUPANCA_BRUTA,
    MAX(CASE WHEN VARIAVEL LIKE '(-) Formação bruta de capital%'                                              THEN VALOR   END) AS FORMACAO_BRUTA_CAPITAL,
    MAX(CASE WHEN VARIAVEL LIKE '(+) Cessão de ativos%'                                                       THEN VALOR   END) AS CESSAO_ATIVOS_NAO_FINANCEIROS,
    MAX(CASE WHEN VARIAVEL LIKE '(+) Transferências de capital%'                                              THEN VALOR   END) AS TRANSFERENCIAS_CAPITAL,
    MAX(CASE WHEN VARIAVEL LIKE '(=) Capacidade%'                                                             THEN VALOR   END) AS CAPACIDADE_NECESSIDADE_FINANCIAMENTO,
    MAX(CASE WHEN VARIAVEL LIKE '(=) Renda nacional bruta%'                                                   THEN UNIDADE END) AS UNIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE;
