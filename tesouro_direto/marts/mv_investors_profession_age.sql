WITH top AS (
    SELECT profession
    FROM td_investor
    WHERE profession IS NOT NULL
    GROUP BY profession
    ORDER BY count(investor_id) DESC
    LIMIT 100
)
SELECT profession, td_age_range(age) AS age_range, count(investor_id) AS investor_count
FROM td_investor
WHERE profession IN (SELECT profession FROM top) AND age IS NOT NULL
GROUP BY profession, td_age_range(age)
