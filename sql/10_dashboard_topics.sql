-- One selected method/version; labels have a unique four-column primary key.
WITH base AS (
 SELECT *, CASE :dimension WHEN 'district' THEN district WHEN 'room_type' THEN room_type
 WHEN 'month' THEN substr(review_date,1,7) ELSE '全部' END AS group_name
 FROM analysis_reviews WHERE (:district IS NULL OR district=:district)
 AND (:room_type IS NULL OR room_type=:room_type)
 AND review_date BETWEEN :start_date AND :end_date
), stats AS (
 SELECT b.group_name,t.topic,count(*) AS denominator_n,count(DISTINCT b.listing_id) AS listing_n,
 count(l.review_id) AS labelled_n,
 sum(CASE WHEN l.mention_status='present' THEN 1 ELSE 0 END) AS mention_n,
 sum(CASE WHEN l.mention_status='present' AND l.sentiment='negative' THEN 1 ELSE 0 END) AS negative_n,
 sum(CASE WHEN l.mention_status='present' AND l.sentiment='mixed' THEN 1 ELSE 0 END) AS mixed_n,
 sum(CASE WHEN l.mention_status='uncertain' OR l.sentiment='uncertain' THEN 1 ELSE 0 END) AS uncertain_n
 FROM base b CROSS JOIN topics t LEFT JOIN review_labels l
 ON l.review_id=b.review_id AND l.topic=t.topic AND l.method_id=:method_id AND l.version=:version
 GROUP BY b.group_name,t.topic
)
SELECT *, CASE WHEN labelled_n=denominator_n AND denominator_n>=100 AND listing_n>=20
 THEN 100.0*mention_n/denominator_n END AS mention_pct,
 CASE WHEN labelled_n=denominator_n AND denominator_n>=100 AND listing_n>=20
 THEN 100.0*negative_n/denominator_n END AS negative_pct,
 CASE WHEN labelled_n=denominator_n AND denominator_n>=100 AND listing_n>=20
 THEN 100.0*(negative_n+mixed_n)/denominator_n END AS negative_content_pct,
 CASE WHEN labelled_n=denominator_n AND denominator_n>=100 AND listing_n>=20 AND mention_n>=30
 THEN 100.0*negative_n/mention_n END AS negative_within_topic_pct
FROM stats ORDER BY group_name,topic;
