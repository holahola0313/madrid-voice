-- LEFT JOIN proves both row preservation and absence of orphan reviews.
SELECT
 (SELECT count(*) FROM listings) AS listing_rows,
 (SELECT count(*) FROM reviews) AS sample_rows,
 (SELECT count(DISTINCT review_id) FROM reviews) AS distinct_sample_ids,
 count(*) AS joined_rows,
 count(DISTINCT r.review_id) AS joined_distinct_ids,
 sum(CASE WHEN l.listing_id IS NULL THEN 1 ELSE 0 END) AS orphan_rows,
 (SELECT count(*) FROM analysis_reviews) AS eligible_rows,
 (SELECT count(DISTINCT review_id) FROM analysis_reviews) AS eligible_distinct_ids,
 (SELECT count(*) FROM review_labels) AS label_rows,
 (SELECT count(*) FROM language_human_checks) AS human_language_rows
FROM reviews r LEFT JOIN listings l ON r.listing_id=l.listing_id;
