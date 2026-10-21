-- analytics.derivados_petroleo
WITH joined_tables AS (
    SELECT
        sd.date,
        sm.name,
        sm.unit,
        sd.value
    FROM
        series_data sd
        INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
    WHERE
        sd.series_id IN (1389, 1390, 1391, 1392, 1393, 1394, 1395, 1396, 1397, 1398)
        AND sd.ativo = TRUE
),
corrected_unit AS (
    SELECT
        date,
        name,
        'Barris/dia' AS unidade,
        (
            CASE unit
                WHEN 'Barris/dia (mil)' THEN value * 1000
                WHEN 'Barris/dia (milhões)' THEN value * 1000000
                ELSE value
            END
        ) AS valor
    FROM
        joined_tables
),
normalized_product_and_variable AS (
    SELECT
        date,
        REGEXP_REPLACE(name, '^(Consumo|Produção) de derivados de petróleo - ', '') AS produto,
        (
            CASE
                WHEN name LIKE 'Consumo de derivados de petróleo%' THEN 'Consumo'
                WHEN name LIKE 'Produção de derivados de petróleo%' THEN 'Produção'
            END
        ) AS variavel,
        unidade,
        valor
    FROM
        corrected_unit
),
filtered_zeros AS (
    SELECT
        *
    FROM
        normalized_product_and_variable
    WHERE
        valor > 0
)
SELECT
    date,
    produto,
    variavel,
    unidade,
    valor
FROM
    filtered_zeros
ORDER BY
    date, variavel, produto;
