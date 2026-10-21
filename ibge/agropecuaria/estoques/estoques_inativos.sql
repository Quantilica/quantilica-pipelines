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
            D.TABELA_SIDRA_ID = '912'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    MAX(CASE WHEN VARIAVEL = 'Total de estabelecimentos inativos'                                         THEN VALOR   END) AS TOTAL_ESTABELECIMENTOS_INATIVOS,
    MAX(CASE WHEN VARIAVEL = 'Total de estabelecimentos inativos'                                         THEN UNIDADE END) AS UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Total de estabelecimentos inativos com%'                                 THEN VALOR   END) AS ESTABELECIMENTOS_INATIVOS_COM_CAPACIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Total de estabelecimentos inativos sem%'                                 THEN VALOR   END) AS ESTABELECIMENTOS_INATIVOS_SEM_CAPACIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE;
