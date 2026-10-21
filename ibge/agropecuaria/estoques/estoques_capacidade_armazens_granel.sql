WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS TIPO_ARMAZEM_ID,
            DIM.D4N                                                 AS TIPO_ARMAZEM,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '259'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TIPO_ARMAZEM_ID,
    TIPO_ARMAZEM,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                        THEN VALOR   END) AS NUMERO_INFORMANTES,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                        THEN UNIDADE END) AS NUMERO_INFORMANTES_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes - percentual do total geral' THEN VALOR END) AS NUMERO_INFORMANTES_PCT,
    MAX(CASE WHEN VARIAVEL = 'Capacidade útil'                              THEN VALOR   END) AS CAPACIDADE_UTIL,
    MAX(CASE WHEN VARIAVEL = 'Capacidade útil'                              THEN UNIDADE END) AS CAPACIDADE_UTIL_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Capacidade útil - percentual do total geral'  THEN VALOR   END) AS CAPACIDADE_UTIL_PCT
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TIPO_ARMAZEM_ID,
    TIPO_ARMAZEM;
