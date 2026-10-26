SELECT marital_status, td_age_range(age) AS age_range, count(investor_id) AS investor_count
FROM td_investor
WHERE marital_status IS NOT NULL AND age IS NOT NULL
GROUP BY marital_status, td_age_range(age)
