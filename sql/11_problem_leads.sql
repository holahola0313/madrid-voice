-- One method/version at a time; unique label key prevents join multiplication.
-- Counts use distinct IDs. A mention is not a complaint. Negative content includes mixed.
-- No rates here: selected-group rate thresholds remain in 10_dashboard_topics.sql.
WITH base AS (
  SELECT review_id, listing_id FROM analysis_reviews
  WHERE (:district IS NULL OR district=:district)
    AND (:room_type IS NULL OR room_type=:room_type)
    AND review_date BETWEEN :start_date AND :end_date
)
SELECT t.topic AS topic,
 COUNT(DISTINCT CASE WHEN l.mention_status='present' THEN b.review_id END) AS mention_reviews,
 COUNT(DISTINCT CASE WHEN l.mention_status='present' THEN b.listing_id END) AS mention_listings,
 COUNT(DISTINCT CASE WHEN l.mention_status='present' AND l.sentiment IN ('negative','mixed') THEN b.review_id END) AS lead_reviews,
 COUNT(DISTINCT CASE WHEN l.mention_status='present' AND l.sentiment IN ('negative','mixed') THEN b.listing_id END) AS lead_listings
FROM topics t CROSS JOIN base b
LEFT JOIN review_labels l ON l.review_id=b.review_id AND l.topic=t.topic
  AND l.method_id=:method_id AND l.version=:version
GROUP BY t.topic;
