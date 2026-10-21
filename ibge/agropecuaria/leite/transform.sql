WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS REFERENCIA_TEMPORAL_ID,
            DIM.D4N                                                 AS REFERENCIA_TEMPORAL,
            DIM.D5C                                                 AS TIPO_INSPECAO_ID,
            DIM.D5N                                                 AS TIPO_INSPECAO,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '1086'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    REFERENCIA_TEMPORAL_ID,
    REFERENCIA_TEMPORAL,
    TIPO_INSPECAO_ID,
    TIPO_INSPECAO,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                                                              THEN VALOR   END) AS NUMERO_INFORMANTES,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                                                              THEN UNIDADE END) AS NUMERO_INFORMANTES_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes - percentual do total geral'                                  THEN VALOR   END) AS NUMERO_INFORMANTES_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de leite cru%adquirido'                                               THEN VALOR   END) AS QTDE_LEITE_ADQUIRIDO,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de leite cru%adquirido'                                               THEN UNIDADE END) AS QTDE_LEITE_ADQUIRIDO_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de leite cru%adquirido - percentual%'                                 THEN VALOR   END) AS QTDE_LEITE_ADQUIRIDO_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de leite cru%industrializado'                                         THEN VALOR   END) AS QTDE_LEITE_INDUSTRIALIZADO,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de leite cru%industrializado'                                         THEN UNIDADE END) AS QTDE_LEITE_INDUSTRIALIZADO_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de leite cru%industrializado - percentual%'                           THEN VALOR   END) AS QTDE_LEITE_INDUSTRIALIZADO_PCT,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes do preço do leite'                                            THEN VALOR   END) AS NUMERO_INFORMANTES_PRECO,
    MAX(CASE WHEN VARIAVEL = 'Preço médio'                                                                        THEN VALOR   END) AS PRECO_MEDIO,
    MAX(CASE WHEN VARIAVEL = 'Preço médio'                                                                        THEN UNIDADE END) AS PRECO_MEDIO_UNIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    REFERENCIA_TEMPORAL_ID,
    REFERENCIA_TEMPORAL,
    TIPO_INSPECAO_ID,
    TIPO_INSPECAO;
