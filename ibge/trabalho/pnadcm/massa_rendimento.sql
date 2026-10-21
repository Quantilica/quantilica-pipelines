-- 6392 → massa de rendimento mensal habitual, todos os trabalhos  (real + nominal, 16 variáveis)
-- 6393 → massa de rendimento mensal efetivo, todos os trabalhos   (real + nominal, 16 variáveis)
-- Sem classificações em nenhuma das tabelas
WITH
    BASE AS (
        SELECT
            P.DATA_INICIO AS PERIODO,
            L.NC          AS NIVEL_TERRITORIAL_ID,
            L.NN          AS NIVEL_TERRITORIAL,
            L.D1C         AS LOCALIDADE_ID,
            L.D1N         AS LOCALIDADE,
            D.TABELA_SIDRA_ID,
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
            D.TABELA_SIDRA_ID IN ('6392', '6393')
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TABELA_SIDRA_ID,
    -- Massa real
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS MASSA_REAL,
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS MASSA_REAL_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS MASSA_REAL_CV,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS MASSA_REAL_CV_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS MASSA_REAL_VAR_3TM_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS MASSA_REAL_VAR_3TM_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS MASSA_REAL_VAR_3TM_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS MASSA_REAL_VAR_3TM_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação a três%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR_TEXTO END) AS MASSA_REAL_VAR_3TM_SIT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS MASSA_REAL_VAR_ANO_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS MASSA_REAL_VAR_ANO_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR       END) AS MASSA_REAL_VAR_ANO_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN UNIDADE     END) AS MASSA_REAL_VAR_ANO_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação ao mesmo%'
              AND VARIAVEL LIKE '%real%'                                   THEN VALOR_TEXTO END) AS MASSA_REAL_VAR_ANO_SIT,
    -- Massa nominal
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS MASSA_NOMINAL,
    MAX(CASE WHEN VARIAVEL NOT LIKE 'Coeficiente%'
              AND VARIAVEL NOT LIKE 'Variação%'
              AND VARIAVEL NOT LIKE 'Situação%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS MASSA_NOMINAL_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS MASSA_NOMINAL_CV,
    MAX(CASE WHEN VARIAVEL LIKE 'Coeficiente%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS MASSA_NOMINAL_CV_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS MASSA_NOMINAL_VAR_3TM_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS MASSA_NOMINAL_VAR_3TM_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS MASSA_NOMINAL_VAR_3TM_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS MASSA_NOMINAL_VAR_3TM_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação a três%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR_TEXTO END) AS MASSA_NOMINAL_VAR_3TM_SIT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS MASSA_NOMINAL_VAR_ANO_PCT,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação percentual em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS MASSA_NOMINAL_VAR_ANO_PCT_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR       END) AS MASSA_NOMINAL_VAR_ANO_ABS,
    MAX(CASE WHEN VARIAVEL LIKE 'Variação absoluta em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN UNIDADE     END) AS MASSA_NOMINAL_VAR_ANO_ABS_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Situação da Variação em relação ao mesmo%'
              AND VARIAVEL LIKE '%nominal%'                                THEN VALOR_TEXTO END) AS MASSA_NOMINAL_VAR_ANO_SIT
FROM BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    TABELA_SIDRA_ID;
