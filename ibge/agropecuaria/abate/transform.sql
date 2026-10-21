WITH
    BASE AS (
        SELECT
            P.ANO                   AS ANO,
            P.TRIMESTRE             AS TRIMESTRE,
            P.MES                   AS MES,
            P.FREQUENCIA            AS FREQUENCIA,
            L.D1C                   AS ID_UF,
            L.D1N                   AS NOME_UF,
            CASE D.TABELA_SIDRA_ID
                WHEN '1092' THEN 'Bovinos'
                WHEN '1093' THEN 'Suínos'
                WHEN '1094' THEN 'Frangos'
            END                     AS ANIMAL,
            -- Tabela 1092: D4 = tipo de rebanho, D5 = tipo de inspeção
            -- Tabelas 1093/1094: D4 = tipo de inspeção, D5 = NULL
            CASE D.TABELA_SIDRA_ID
                WHEN '1092' THEN DIM.D4N
                ELSE NULL
            END                     AS TIPO_REBANHO,
            CASE D.TABELA_SIDRA_ID
                WHEN '1092' THEN DIM.D5N
                ELSE DIM.D4N
            END                     AS TIPO_INSPECAO,
            DIM.D2N                 AS VARIAVEL,
            DIM.MN                  AS UNIDADE,
            CASE
                WHEN D.V ~ '^-?[0-9]' THEN D.V::NUMERIC
            END                     AS VALOR
        FROM
            DADOS D
            JOIN PERIODO    P   ON D.PERIODO_ID    = P.ID
            JOIN DIMENSAO   DIM ON D.DIMENSAO_ID   = DIM.ID
            JOIN LOCALIDADE L   ON D.LOCALIDADE_ID = L.ID
        WHERE
            D.TABELA_SIDRA_ID IN ('1092', '1093', '1094')
            AND D.ATIVO = TRUE
    )
SELECT
    ANO,
    TRIMESTRE,
    MES,
    FREQUENCIA,
    ID_UF,
    NOME_UF,
    ANIMAL,
    TIPO_REBANHO,
    TIPO_INSPECAO,
    SUM(
        CASE
            WHEN VARIAVEL = 'Número de informantes' THEN VALOR
            ELSE NULL
        END
    )                               AS NUMERO_INFORMANTES,
    MAX(
        CASE
            WHEN VARIAVEL = 'Número de informantes' THEN UNIDADE
        END
    )                               AS NUMERO_INFORMANTES_UNIDADE,
    SUM(
        CASE
            WHEN VARIAVEL = 'Quantidade' THEN VALOR
            ELSE NULL
        END
    )                               AS QUANTIDADE,
    MAX(
        CASE
            WHEN VARIAVEL = 'Quantidade' THEN UNIDADE
        END
    )                               AS QUANTIDADE_UNIDADE,
    SUM(
        CASE
            WHEN VARIAVEL = 'Peso total das carcaças' THEN VALOR
            ELSE NULL
        END
    )                               AS PESO_CARCACAS,
    MAX(
        CASE
            WHEN VARIAVEL = 'Peso total das carcaças' THEN UNIDADE
        END
    )                               AS PESO_CARCACAS_UNIDADE
FROM
    BASE
GROUP BY
    ANO,
    TRIMESTRE,
    MES,
    FREQUENCIA,
    ID_UF,
    NOME_UF,
    ANIMAL,
    TIPO_REBANHO,
    TIPO_INSPECAO;
