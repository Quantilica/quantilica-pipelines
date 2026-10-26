SELECT state, gender, count(investor_id) AS investor_count
FROM td_investor
WHERE state IS NOT NULL AND gender IS NOT NULL
GROUP BY state, gender
