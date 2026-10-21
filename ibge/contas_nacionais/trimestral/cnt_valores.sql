WITH
    BASE AS (
        SELECT
            P.DATA_INICIO                                           AS PERIODO,
            L.NC                                                    AS NIVEL_TERRITORIAL_ID,
            L.NN                                                    AS NIVEL_TERRITORIAL,
            L.D1C                                                   AS LOCALIDADE_ID,
            L.D1N                                                   AS LOCALIDADE,
            DIM.D4C                                                 AS SETOR_SUBSETOR_ID,
            DIM.D4N                                                 AS SETOR_SUBSETOR,
            DIM.D2N                                                 AS VARIAVEL,
            DIM.MN                                                  AS UNIDADE,
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID IN ('1846', '6612', '6613')
            AND D.ATIVO = TRUE
    )
SELECT
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    SETOR_SUBSETOR_ID,
    SETOR_SUBSETOR,
    MAX(CASE WHEN VARIAVEL LIKE 'Valores a preços correntes%'                                   THEN VALOR   END) AS VALORES_CORRENTES,
    MAX(CASE WHEN VARIAVEL LIKE 'Valores a preços correntes%'                                   THEN UNIDADE END) AS VALORES_CORRENTES_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Valores encadeados%' AND VARIAVEL NOT LIKE '%ajuste%'          THEN VALOR   END) AS VALORES_ENCADEADOS_1995,
    MAX(CASE WHEN VARIAVEL LIKE 'Valores encadeados%' AND VARIAVEL NOT LIKE '%ajuste%'          THEN UNIDADE END) AS VALORES_ENCADEADOS_1995_UNIDADE,
    MAX(CASE WHEN VARIAVEL LIKE 'Valores encadeados%' AND VARIAVEL LIKE '%ajuste%'              THEN VALOR   END) AS VALORES_ENCADEADOS_1995_SA,
    MAX(CASE WHEN VARIAVEL LIKE 'Valores encadeados%' AND VARIAVEL LIKE '%ajuste%'              THEN UNIDADE END) AS VALORES_ENCADEADOS_1995_SA_UNIDADE
FROM
    BASE
GROUP BY
    PERIODO,
    NIVEL_TERRITORIAL_ID,
    NIVEL_TERRITORIAL,
    LOCALIDADE_ID,
    LOCALIDADE,
    SETOR_SUBSETOR_ID,
    SETOR_SUBSETOR;
