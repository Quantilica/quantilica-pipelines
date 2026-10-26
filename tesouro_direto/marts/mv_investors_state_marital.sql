SELECT state, marital_status, count(investor_id) AS investor_count
FROM td_investor
WHERE state IS NOT NULL AND marital_status IS NOT NULL
GROUP BY state, marital_status
