WITH top AS (
    SELECT profession
    FROM td_investor
    WHERE profession IS NOT NULL
    GROUP BY profession
    ORDER BY count(investor_id) DESC
    LIMIT 100
)
SELECT profession, gender, count(investor_id) AS investor_count
FROM td_investor
WHERE profession IN (SELECT profession FROM top) AND gender IS NOT NULL
GROUP BY profession, gender
