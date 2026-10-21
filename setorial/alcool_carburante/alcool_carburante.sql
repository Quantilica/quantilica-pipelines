-- analytics.alcool_carburante
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
        sd.series_id IN (1399, 1400, 1401)
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
        REPLACE(name, 'Consumo de álcool carburante - ', '') AS produto,
        (
            CASE
                WHEN name LIKE 'Consumo de álcool carburante%' THEN 'Consumo'
            END
        ) AS variavel,
        unidade,
        valor
    FROM
        corrected_unit
)
SELECT
    date,
    produto,
    variavel,
    unidade,
    valor
FROM
    normalized_product_and_variable
ORDER BY
    date, produto;
