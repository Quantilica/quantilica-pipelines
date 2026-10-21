-- analytics.cambio
WITH joined_tables AS (
    SELECT
        sd.date,
        sm.name_abbreviated,
        sm.unit,
        sd.value
    FROM
        series_data sd
        INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
    WHERE
        sd.series_id IN (
            1, 10813, 21619, 21620, 21621, 21622, 21623, 21624, 21625, 21626,
            21627, 21628, 21629, 21630, 21631, 21632, 21633, 21634, 21635, 21636
        )
        AND sd.ativo = TRUE
),
added_lado AS (
    SELECT
        date,
        REPLACE(REPLACE(name_abbreviated, ' (compra)', ''), ' (venda)', '') AS moeda,
        (
            CASE
                WHEN name_abbreviated ~ '.*\(compra\)$' THEN 'compra' ELSE 'venda'
            END
        ) AS lado,
        unit AS unidade,
        value AS valor
    FROM
        joined_tables
),
fin AS (
    SELECT
        date,
        moeda,
        unidade,
        SUM(
            CASE
                WHEN lado = 'compra' THEN valor ELSE NULL
            END
        ) AS taxa_compra,
        SUM(
            CASE
                WHEN lado = 'venda' THEN valor ELSE NULL
            END
        ) AS taxa_venda
    FROM
        added_lado
    GROUP BY
        date,
        moeda,
        unidade
)
SELECT
    date,
    moeda,
    unidade,
    taxa_compra,
    taxa_venda
FROM
    fin
ORDER BY
    date, moeda;
