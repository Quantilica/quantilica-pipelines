WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS PRODUTO_ID,
            DIM.D4N                                                 AS PRODUTO,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '6588'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    PRODUTO_ID,
    PRODUTO,
    MAX(CASE WHEN VARIAVEL = 'Área plantada'     THEN VALOR   END) AS AREA_PLANTADA,
    MAX(CASE WHEN VARIAVEL = 'Área plantada'     THEN UNIDADE END) AS AREA_PLANTADA_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Área colhida'      THEN VALOR   END) AS AREA_COLHIDA,
    MAX(CASE WHEN VARIAVEL = 'Área colhida'      THEN UNIDADE END) AS AREA_COLHIDA_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Produção'          THEN VALOR   END) AS PRODUCAO,
    MAX(CASE WHEN VARIAVEL = 'Produção'          THEN UNIDADE END) AS PRODUCAO_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Rendimento médio'  THEN VALOR   END) AS RENDIMENTO_MEDIO,
    MAX(CASE WHEN VARIAVEL = 'Rendimento médio'  THEN UNIDADE END) AS RENDIMENTO_MEDIO_UNIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    PRODUTO_ID,
    PRODUTO;
