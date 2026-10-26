SELECT profession, count(investor_id) AS investor_count
FROM td_investor
WHERE profession IS NOT NULL
GROUP BY profession
