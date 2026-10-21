WITH
    BASE AS (
        SELECT
            P.DATA_INICIO AS PERIODO,
            L.NC          AS NIVEL_TERRITORIAL_ID,
            L.NN          AS NIVEL_TERRITORIAL,
            L.D1C         AS LOCALIDADE_ID,
            L.D1N         AS LOCALIDADE,
            DIM.D2N       AS VARIAVEL,
            DIM.MN        AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END AS VALOR,
            D.V           AS VALOR_TEXTO
        FROM
            DADOS D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID = '6022'
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'    THEN VALOR       END) AS POPULACAO,
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'    THEN UNIDADE     END) AS POPULACAO_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'     THEN VALOR       END) AS CV,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'     THEN UNIDADE     END) AS CV_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'   THEN VALOR   END) AS VAR_3TM_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'   THEN UNIDADE END) AS VAR_3TM_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'     THEN VALOR   END) AS VAR_3TM_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'     THEN UNIDADE END) AS VAR_3TM_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação a três%'  THEN VALOR_TEXTO END) AS VAR_3TM_SIT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%' THEN VALOR   END) AS VAR_ANO_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%' THEN UNIDADE END) AS VAR_ANO_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'   THEN VALOR   END) AS VAR_ANO_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'   THEN UNIDADE END) AS VAR_ANO_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação ao mesmo%' THEN VALOR_TEXTO END) AS VAR_ANO_SIT
FROM BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE;
