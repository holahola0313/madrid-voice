-- Explicit month calendar keeps zero-review months. LAG compares sample counts.
WITH RECURSIVE months(month) AS (
 SELECT substr(start_date,1,7)||'-01' FROM settings
 UNION ALL SELECT date(month,'+1 month') FROM months
 WHERE date(month,'+1 month') <= (SELECT end_date FROM settings)
), grouped AS (
 SELECT substr(review_date,1,7) AS month,count(*) AS review_n,
        count(DISTINCT listing_id) AS listing_n
 FROM analysis_reviews GROUP BY substr(review_date,1,7)
), series AS (
 SELECT substr(m.month,1,7) AS month,coalesce(g.review_n,0) AS review_n,
        coalesce(g.listing_n,0) AS listing_n
 FROM months m LEFT JOIN grouped g ON substr(m.month,1,7)=g.month
), changes AS (
 SELECT *,lag(review_n) OVER(ORDER BY month) AS prior_review_n FROM series
)
SELECT month,review_n,listing_n,prior_review_n,review_n-prior_review_n AS sample_count_change,
 round(100.0*(review_n-prior_review_n)/NULLIF(prior_review_n,0),4) AS sample_count_change_pct,
 CASE WHEN review_n>=s.min_reviews AND listing_n>=s.min_listings THEN 1 ELSE 0 END AS meets_minimum
FROM changes CROSS JOIN settings s
ORDER BY month;
