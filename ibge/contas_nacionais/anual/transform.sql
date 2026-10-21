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
            D.TABELA_SIDRA_ID = '6784'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB - valores correntes%'              THEN VALOR   END) AS PIB_VALORES_CORRENTES,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB - valores correntes%'              THEN UNIDADE END) AS PIB_VALORES_CORRENTES_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB - preços do ano anterior%'         THEN VALOR   END) AS PIB_PRECOS_ANO_ANTERIOR,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB - preços do ano anterior%'         THEN UNIDADE END) AS PIB_PRECOS_ANO_ANTERIOR_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB - variação em volume%'             THEN VALOR   END) AS PIB_VARIACAO_VOLUME,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB - deflator%'                       THEN VALOR   END) AS PIB_DEFLATOR,
    MAX(CASE WHEN VARIAVEL LIKE 'População residente%'                  THEN VALOR   END) AS POPULACAO_RESIDENTE,
    MAX(CASE WHEN VARIAVEL LIKE 'População residente%'                  THEN UNIDADE END) AS POPULACAO_RESIDENTE_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB per capita - valores correntes%'   THEN VALOR   END) AS PIB_PERCAPITA_VALORES_CORRENTES,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB per capita - valores correntes%'   THEN UNIDADE END) AS PIB_PERCAPITA_VALORES_CORRENTES_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB per capita - preços do ano anterior%' THEN VALOR END) AS PIB_PERCAPITA_PRECOS_ANO_ANTERIOR,
    MAX(CASE WHEN VARIAVEL LIKE 'PIB per capita - variação em volume%'  THEN VALOR   END) AS PIB_PERCAPITA_VARIACAO_VOLUME
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE;
