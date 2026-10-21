WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS TIPO_INDICE_ID,
            DIM.D4N                                                 AS TIPO_INDICE,
            DIM.D5C                                                 AS SEGMENTO_ID,
            DIM.D5N                                                 AS SEGMENTO,
            DIM.D2N                                                 AS VARIAVEL,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '8163'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TIPO_INDICE_ID,
    TIPO_INDICE,
    SEGMENTO_ID,
    SEGMENTO,
    MAX(CASE WHEN VARIAVEL LIKE 'PMS - Número-índice (2022=100)'
             AND VARIAVEL NOT LIKE '%ajuste%'                           THEN VALOR END) AS NUMERO_INDICE,
    MAX(CASE WHEN VARIAVEL LIKE 'PMS - Número-índice com ajuste sazonal%' THEN VALOR END) AS NUMERO_INDICE_SA,
    MAX(CASE WHEN VARIAVEL LIKE 'PMS - Variação mês/mês imediatamente anterior%' THEN VALOR END) AS VAR_MES_MES_ANTERIOR_SA,
    MAX(CASE WHEN VARIAVEL LIKE 'PMS - Variação mês/mesmo mês%'         THEN VALOR END) AS VAR_MES_ANO_ANTERIOR,
    MAX(CASE WHEN VARIAVEL LIKE 'PMS - Variação acumulada no ano%'      THEN VALOR END) AS VAR_ACUM_ANO,
    MAX(CASE WHEN VARIAVEL LIKE 'PMS - Variação acumulada em 12 meses%' THEN VALOR END) AS VAR_ACUM_12_MESES
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TIPO_INDICE_ID,
    TIPO_INDICE,
    SEGMENTO_ID,
    SEGMENTO;
