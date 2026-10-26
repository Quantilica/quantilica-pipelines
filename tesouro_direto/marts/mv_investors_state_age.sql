SELECT state, td_age_range(age) AS age_range, count(investor_id) AS investor_count
FROM td_investor
WHERE state IS NOT NULL AND age IS NOT NULL
GROUP BY state, td_age_range(age)
