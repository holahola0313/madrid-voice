-- Bound parameters; dimension is selected from fixed CASE expressions.
WITH base AS (
 SELECT * FROM analysis_reviews
 WHERE (:district IS NULL OR district=:district)
 AND (:room_type IS NULL OR room_type=:room_type)
 AND review_date BETWEEN :start_date AND :end_date
), grouped AS (
 SELECT CASE :dimension WHEN 'district' THEN district WHEN 'room_type' THEN room_type
 WHEN 'month' THEN substr(review_date,1,7) ELSE '全部' END AS group_name,
 count(*) AS reviews, count(DISTINCT listing_id) AS listings
 FROM base GROUP BY group_name
)
SELECT *, CASE WHEN reviews>=100 AND listings>=20 THEN '达到展示门槛' ELSE '样本不足，仅展示数量' END AS sample_status,
CASE WHEN reviews>=100 AND listings>=20 THEN DENSE_RANK() OVER (ORDER BY reviews DESC) END AS coverage_rank
FROM grouped ORDER BY reviews DESC,group_name;
