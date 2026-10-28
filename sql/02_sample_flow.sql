-- Mutually exclusive reasons: priority is mapping conflict, date, text, language.
SELECT analysis_status, exclusion_reason, count(*) AS review_n
FROM reviews
GROUP BY analysis_status,exclusion_reason
ORDER BY analysis_status,exclusion_reason;
