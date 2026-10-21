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
            CASE WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC END       AS VALOR
        FROM
            DADOS       D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID IN ('1620', '1621')
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
    MAX(CASE WHEN VARIAVEL LIKE 'Série encadeada%' AND VARIAVEL NOT LIKE '%ajuste%' THEN VALOR END) AS SERIE_ENCADEADA_VOLUME,
    MAX(CASE WHEN VARIAVEL LIKE 'Série encadeada%' AND VARIAVEL LIKE '%ajuste%'     THEN VALOR END) AS SERIE_ENCADEADA_VOLUME_SA
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
