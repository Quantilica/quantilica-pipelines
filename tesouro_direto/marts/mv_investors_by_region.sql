SELECT td_region(state) AS region, count(DISTINCT investor_id) AS investor_count
FROM td_investor
WHERE state IS NOT NULL
GROUP BY td_region(state)
