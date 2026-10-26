SELECT CAST(date_trunc('month', operation_date) AS TIMESTAMPTZ) AS operation_month,
       operation_type,
       bond_type,
       count(*) AS operation_count,
       sum(operation_value) AS total_operation_value
FROM td_operacoes
GROUP BY 1, operation_type, bond_type
