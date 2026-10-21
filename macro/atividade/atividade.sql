-- analytics.atividade
WITH joined_tables AS (
    SELECT
        sd.date,
        sd.series_id,
        sd.value,
        sm.name
    FROM
        series_data sd
        INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
    WHERE
        sd.series_id IN (
            24363, 24364, 25398, 25379, 25380, 25381, 25382, 25383, 25384, 25388,
            25389, 25390, 25391, 25392, 25393, 25394, 25395, 25396, 25397, 25399,
            25400, 25401, 25402, 25403, 25404, 25405, 25406, 25407, 25408, 25409,
            25410, 25411, 25412, 25413, 25415, 25416, 25417, 25418
        )
        AND sd.ativo = TRUE
),
ibcbr_metadata_processed AS (
    SELECT
        series_id,
        (
            CASE
                WHEN name LIKE '%Espírito Santo%' THEN 30000032
                WHEN name LIKE '%Minas Gerais%' THEN 30000031
                WHEN name LIKE '%Região Centro-Oeste%' THEN 20000005
                WHEN name LIKE '%Goiás%' THEN 30000052
                WHEN name LIKE '%Nordeste%' THEN 20000002
                WHEN name LIKE '%Ceará%' THEN 30000023
                WHEN name LIKE '%São Paulo%' THEN 30000035
                WHEN name LIKE '%Região Sudeste%' THEN 20000003
                WHEN name LIKE '%Rio de Janeiro%' THEN 30000033
                WHEN name LIKE '%Região Sul%' THEN 20000004
                WHEN name LIKE '%Rio Grande do Sul%' THEN 30000043
                WHEN name LIKE '%Santa Catarina%' THEN 30000042
                WHEN name LIKE '%Região Norte%' THEN 20000001
                WHEN name LIKE '%Paraná%' THEN 30000041
                WHEN name LIKE '%Pará%' THEN 30000015
                WHEN name LIKE '%Amazonas%' THEN 30000013
                WHEN name LIKE '%Bahia%' THEN 30000029
                WHEN name LIKE '%Pernambuco%' THEN 30000026
                ELSE 10000001  -- Brasil
            END
        ) AS localidade_id,
        (
            CASE
                WHEN name LIKE '%com ajuste sazonal%' THEN 'Índice Ajustado' ELSE 'Índice'
            END
        ) AS tipo_indice
    FROM
        joined_tables
    GROUP BY
        series_id, name
),
localidades AS (
    SELECT 10000001 AS id, 'País' AS nivel_territorial, 'Brasil' AS unidade_territorial
    UNION ALL SELECT 20000001, 'Região Grande', 'Região Norte'
    UNION ALL SELECT 20000002, 'Região Grande', 'Região Nordeste'
    UNION ALL SELECT 20000003, 'Região Grande', 'Região Sudeste'
    UNION ALL SELECT 20000004, 'Região Grande', 'Região Sul'
    UNION ALL SELECT 20000005, 'Região Grande', 'Região Centro-Oeste'
    UNION ALL SELECT 30000013, 'Estado', 'Amazonas'
    UNION ALL SELECT 30000015, 'Estado', 'Pará'
    UNION ALL SELECT 30000023, 'Estado', 'Ceará'
    UNION ALL SELECT 30000026, 'Estado', 'Pernambuco'
    UNION ALL SELECT 30000029, 'Estado', 'Bahia'
    UNION ALL SELECT 30000031, 'Estado', 'Minas Gerais'
    UNION ALL SELECT 30000032, 'Estado', 'Espírito Santo'
    UNION ALL SELECT 30000033, 'Estado', 'Rio de Janeiro'
    UNION ALL SELECT 30000035, 'Estado', 'São Paulo'
    UNION ALL SELECT 30000041, 'Estado', 'Paraná'
    UNION ALL SELECT 30000042, 'Estado', 'Santa Catarina'
    UNION ALL SELECT 30000043, 'Estado', 'Rio Grande do Sul'
    UNION ALL SELECT 30000052, 'Estado', 'Goiás'
)
SELECT
    t0.date,
    t2.unidade_territorial AS localidade,
    t2.nivel_territorial,
    t1.tipo_indice,
    t0.value AS valor
FROM
    joined_tables AS t0
    LEFT JOIN ibcbr_metadata_processed AS t1
        ON t0.series_id = t1.series_id
    LEFT JOIN localidades AS t2
        ON t1.localidade_id = t2.id
ORDER BY
    t0.date, t2.nivel_territorial, t2.unidade_territorial, t1.tipo_indice;
