-- Future template, executed with empty label tables in stage 2 -> zero rows.
-- A method/version and topic are separate groups. Never pool rules/AI/human.
-- Explicit absent labels are required; partial labelling yields NULL rates.
WITH base AS (
 SELECT * FROM analysis_reviews
 WHERE (:district IS NULL OR district=:district)
   AND (:room_type IS NULL OR room_type=:room_type)
   AND review_date BETWEEN :start_date AND :end_date
), stats AS (
 SELECT m.method_id,m.version,m.origin,m.validation_status,t.topic,
 count(b.review_id) AS denominator_n,count(DISTINCT b.listing_id) AS listing_n,
 count(l.review_id) AS labelled_n,
 sum(CASE WHEN l.mention_status='present' THEN 1 ELSE 0 END) AS mention_n,
 sum(CASE WHEN l.mention_status='present' AND l.sentiment='negative' THEN 1 ELSE 0 END) AS negative_n,
 sum(CASE WHEN l.mention_status='present' AND l.sentiment='mixed' THEN 1 ELSE 0 END) AS mixed_n,
 sum(CASE WHEN l.mention_status='uncertain' OR l.sentiment='uncertain' THEN 1 ELSE 0 END) AS uncertain_n
 FROM methods m CROSS JOIN topics t CROSS JOIN base b
 LEFT JOIN review_labels l ON l.review_id=b.review_id AND l.topic=t.topic
      AND l.method_id=m.method_id AND l.version=m.version
 GROUP BY m.method_id,m.version,m.origin,m.validation_status,t.topic
)
SELECT stats.*,
 CASE WHEN labelled_n=denominator_n AND denominator_n>=s.min_reviews AND listing_n>=s.min_listings
      THEN 100.0*mention_n/NULLIF(denominator_n,0) END AS mention_pct,
 CASE WHEN labelled_n=denominator_n AND denominator_n>=s.min_reviews AND listing_n>=s.min_listings
      THEN 100.0*negative_n/NULLIF(denominator_n,0) END AS negative_feedback_pct,
 CASE WHEN labelled_n=denominator_n AND denominator_n>=s.min_reviews AND listing_n>=s.min_listings
           AND mention_n>=s.min_topic_mentions
      THEN 100.0*negative_n/NULLIF(mention_n,0) END AS negative_within_topic_pct
FROM stats CROSS JOIN settings s ORDER BY method_id,version,topic;
