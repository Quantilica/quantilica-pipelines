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
            DIM.D5C                                                 AS PROCEDENCIA_ID,
            DIM.D5N                                                 AS PROCEDENCIA,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '1088'
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
    PROCEDENCIA_ID,
    PROCEDENCIA,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                                                                          THEN VALOR   END) AS NUMERO_INFORMANTES,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes'                                                                          THEN UNIDADE END) AS NUMERO_INFORMANTES_UNIDADE,
    MAX(CASE WHEN VARIAVEL = 'Número de informantes - percentual do total geral'                                              THEN VALOR   END) AS NUMERO_INFORMANTES_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de couro cru inteiro de bovino adquirido para curtimento'                         THEN VALOR   END) AS QTDE_ADQUIRIDA,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de couro cru inteiro de bovino adquirido para curtimento'                         THEN UNIDADE END) AS QTDE_ADQUIRIDA_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Quantidade de couro cru inteiro de bovino adquirido para curtimento - percentual%'           THEN VALOR   END) AS QTDE_ADQUIRIDA_PCT
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
    PROCEDENCIA_ID,
    PROCEDENCIA;
