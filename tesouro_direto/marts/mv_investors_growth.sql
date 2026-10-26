SELECT CAST(date_trunc('month', join_date) AS TIMESTAMPTZ) AS growth_month,
       count(DISTINCT investor_id) AS new_investors
FROM td_investidores
WHERE join_date IS NOT NULL
GROUP BY 1
