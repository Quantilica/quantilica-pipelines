WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS INSTRUMENTO_FINANCEIRO_ID,
            DIM.D4N                                                 AS INSTRUMENTO_FINANCEIRO,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '2205'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    INSTRUMENTO_FINANCEIRO_ID,
    INSTRUMENTO_FINANCEIRO,
    MAX(CASE WHEN VARIAVEL = 'Variações de ativos'                          THEN VALOR   END) AS VARIACOES_ATIVOS,
    MAX(CASE WHEN VARIAVEL = 'Variações de ativos'                          THEN UNIDADE END) AS VARIACOES_ATIVOS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variações de passivo%'                     THEN VALOR   END) AS VARIACOES_PASSIVO_PL,
    MAX(CASE WHEN VARIAVEL LIKE 'Variações de passivo%'                     THEN UNIDADE END) AS VARIACOES_PASSIVO_PL_UNIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    INSTRUMENTO_FINANCEIRO_ID,
    INSTRUMENTO_FINANCEIRO;
