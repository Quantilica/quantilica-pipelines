-- Tabela 278: estabelecimentos e capacidade útil por tipo de unidade, propriedade e atividade
-- Tabela 911: capacidade útil por tipo de unidade (sem desagregação por propriedade/atividade)
WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            D.TABELA_SIDRA_ID                                       AS TABELA_SIDRA_ID,
            DIM.D4C                                                 AS TIPO_UNIDADE_ID,
            DIM.D4N                                                 AS TIPO_UNIDADE,
            CASE WHEN D.TABELA_SIDRA_ID = '278' THEN DIM.D5C END   AS TIPO_PROPRIEDADE_ID,
            CASE WHEN D.TABELA_SIDRA_ID = '278' THEN DIM.D5N END   AS TIPO_PROPRIEDADE,
            CASE WHEN D.TABELA_SIDRA_ID = '278' THEN DIM.D6C END   AS TIPO_ATIVIDADE_ID,
            CASE WHEN D.TABELA_SIDRA_ID = '278' THEN DIM.D6N END   AS TIPO_ATIVIDADE,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID IN ('278', '911')
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TABELA_SIDRA_ID,
    TIPO_UNIDADE_ID,
    TIPO_UNIDADE,
    TIPO_PROPRIEDADE_ID,
    TIPO_PROPRIEDADE,
    TIPO_ATIVIDADE_ID,
    TIPO_ATIVIDADE,
    MAX(CASE WHEN VARIAVEL = 'Número de estabelecimentos'   THEN VALOR   END) AS NUMERO_ESTABELECIMENTOS,
    MAX(CASE WHEN VARIAVEL = 'Número de estabelecimentos'   THEN UNIDADE END) AS NUMERO_ESTABELECIMENTOS_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Capacidade útil'              THEN VALOR   END) AS CAPACIDADE_UTIL,
    MAX(CASE WHEN VARIAVEL = 'Capacidade útil'              THEN UNIDADE END) AS CAPACIDADE_UTIL_UNIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TABELA_SIDRA_ID,
    TIPO_UNIDADE_ID,
    TIPO_UNIDADE,
    TIPO_PROPRIEDADE_ID,
    TIPO_PROPRIEDADE,
    TIPO_ATIVIDADE_ID,
    TIPO_ATIVIDADE;
