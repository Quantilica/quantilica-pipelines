WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS GRUPO_CAPACIDADE_ID,
            DIM.D4N                                                 AS GRUPO_CAPACIDADE,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '5470'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    GRUPO_CAPACIDADE_ID,
    GRUPO_CAPACIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Número de estabelecimentos com armazéns%'
             AND VARIAVEL NOT LIKE '% - percentual%'                    THEN VALOR   END) AS NUMERO_ESTABELECIMENTOS,
    MAX(CASE WHEN VARIAVEL LIKE 'Número de estabelecimentos com armazéns%'
             AND VARIAVEL NOT LIKE '% - percentual%'                    THEN UNIDADE END) AS NUMERO_ESTABELECIMENTOS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Capacidade útil dos armazéns%'
             AND VARIAVEL NOT LIKE '% - percentual%'                    THEN VALOR   END) AS CAPACIDADE_UTIL,
    MAX(CASE WHEN VARIAVEL LIKE 'Capacidade útil dos armazéns%'
             AND VARIAVEL NOT LIKE '% - percentual%'                    THEN UNIDADE END) AS CAPACIDADE_UTIL_UNIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    GRUPO_CAPACIDADE_ID,
    GRUPO_CAPACIDADE;
