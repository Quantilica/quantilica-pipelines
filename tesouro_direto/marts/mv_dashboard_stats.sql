-- Totais dos microdados (mart_microdata_totais, via DuckDB) + o que continua no PostgreSQL.
-- mart_microdata_totais não é qualificada: resolve pelo search_path (--raw-schema).
SELECT
    1::integer AS pkey,
    t.total_investors,
    t.active_investors,
    t.total_operations,
    COALESCE((SELECT sum(value) FROM tesouro_direto.sale), 0)::numeric(18, 2) AS total_sales_value,
    (SELECT count(*) FROM tesouro_direto.bond) AS total_bonds,
    (SELECT max(reference_date) FROM tesouro_direto.bond_price) AS latest_data_date
FROM mart_microdata_totais t
