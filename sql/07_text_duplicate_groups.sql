-- No text or IDs exported. Exact duplicate phrases are flagged, not deleted.
WITH groups AS (
 SELECT text_hash,count(*) AS n,count(DISTINCT listing_id) AS listing_n
 FROM analysis_reviews GROUP BY text_hash HAVING count(*)>1
)
SELECT count(*) AS duplicate_groups,coalesce(sum(n),0) AS involved_reviews,
       coalesce(sum(n-1),0) AS extra_reviews,
       coalesce(sum(CASE WHEN listing_n>1 THEN 1 ELSE 0 END),0) AS cross_listing_text_groups
FROM groups;
