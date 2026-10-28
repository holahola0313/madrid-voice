-- All proportions use selected ES candidates, NOT all guests or raw source rows.
WITH grouped AS (
 SELECT 'district' AS dimension,district AS group_name,count(*) AS review_n,
        count(DISTINCT listing_id) AS listing_n FROM analysis_reviews GROUP BY district
 UNION ALL
 SELECT 'room_type',room_type,count(*),count(DISTINCT listing_id)
 FROM analysis_reviews GROUP BY room_type
), totals AS (SELECT count(*) AS n FROM analysis_reviews)
SELECT dimension,group_name,review_n,listing_n,totals.n AS denominator_n,
 round(100.0*review_n/NULLIF(totals.n,0),4) AS sample_share_pct,
 CASE WHEN review_n>=s.min_reviews AND listing_n>=s.min_listings THEN 1 ELSE 0 END AS meets_minimum
FROM grouped CROSS JOIN totals CROSS JOIN settings s
ORDER BY dimension,review_n DESC,group_name;
