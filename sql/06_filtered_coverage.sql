-- Bind all values with SQLite parameters; never concatenate user filter values.
-- NULL district/room_type means all. Thresholds apply AFTER filtering.
SELECT count(*) AS review_n,count(DISTINCT listing_id) AS listing_n,
 CASE WHEN count(*)>=s.min_reviews AND count(DISTINCT listing_id)>=s.min_listings
      THEN 1 ELSE 0 END AS meets_minimum
FROM analysis_reviews CROSS JOIN settings s
WHERE (:district IS NULL OR district=:district)
  AND (:room_type IS NULL OR room_type=:room_type)
  AND review_date BETWEEN :start_date AND :end_date;
