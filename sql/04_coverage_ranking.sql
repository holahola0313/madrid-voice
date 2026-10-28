-- This is a SAMPLE COVERAGE ranking, not a satisfaction or problem ranking.
WITH counts AS (
 SELECT district,count(*) AS review_n,count(DISTINCT listing_id) AS listing_n
 FROM analysis_reviews GROUP BY district
), eligible AS (
 SELECT counts.* FROM counts CROSS JOIN settings s
 WHERE review_n>=s.min_reviews AND listing_n>=s.min_listings
)
SELECT dense_rank() OVER(ORDER BY review_n DESC) AS coverage_rank,
       district,review_n,listing_n,
       'sample_coverage_only_not_experience_quality' AS interpretation
FROM eligible ORDER BY coverage_rank,district;
