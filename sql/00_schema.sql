PRAGMA foreign_keys = ON;

CREATE TABLE settings (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    snapshot TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
    min_reviews INTEGER NOT NULL, min_listings INTEGER NOT NULL,
    min_topic_mentions INTEGER NOT NULL, pipeline_version TEXT NOT NULL
);

-- IDs remain TEXT: long Airbnb identifiers must never pass through floating point.
CREATE TABLE listings (
    listing_id TEXT PRIMARY KEY NOT NULL,
    public_listing_id TEXT UNIQUE NOT NULL,
    scrape_id TEXT NOT NULL,
    last_scraped TEXT NOT NULL,
    district TEXT NOT NULL,
    neighbourhood TEXT NOT NULL,
    room_type TEXT NOT NULL CHECK(room_type IN ('Entire home/apt','Private room','Shared room','Hotel room')),
    number_of_reviews_source INTEGER NOT NULL CHECK(number_of_reviews_source>=0)
);

-- This is the fixed SAMPLE, not the full review corpus.
-- Ambiguous records retain a provenance pointer; the view below never analyses it.
CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY NOT NULL,
    public_review_id TEXT UNIQUE NOT NULL,
    listing_id TEXT NOT NULL REFERENCES listings(listing_id),
    review_date TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    clean_text TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    language_top TEXT NOT NULL,
    language_score REAL NOT NULL CHECK(language_score BETWEEN 0 AND 1),
    language_status TEXT NOT NULL CHECK(language_status IN ('es_candidate','needs_review','other_language')),
    language_method TEXT NOT NULL,
    join_status TEXT NOT NULL CHECK(join_status IN ('unambiguous','quarantine_cross_listing_id')),
    analysis_status TEXT NOT NULL CHECK(analysis_status IN ('included','excluded')),
    exclusion_reason TEXT NOT NULL,
    text_cleaning_version TEXT NOT NULL,
    source_sample_row INTEGER UNIQUE NOT NULL,
    CHECK ((analysis_status='included' AND exclusion_reason='') OR
           (analysis_status='excluded' AND exclusion_reason<>''))
);
CREATE INDEX reviews_listing ON reviews(listing_id);
CREATE INDEX reviews_date ON reviews(review_date);
CREATE INDEX reviews_hash ON reviews(text_hash);

CREATE TABLE methods (
    method_id TEXT NOT NULL, version TEXT NOT NULL,
    origin TEXT NOT NULL CHECK(origin IN ('human','rule','ai')),
    validation_status TEXT NOT NULL CHECK(validation_status IN ('unvalidated','evaluated')),
    description TEXT NOT NULL,
    PRIMARY KEY(method_id,version)
);
CREATE TABLE topics (
    topic TEXT PRIMARY KEY NOT NULL, label_zh TEXT NOT NULL
);
INSERT INTO topics VALUES ('cleanliness','清洁'),('noise','噪音'),('checkin','入住流程'),
                          ('facilities','设施'),('communication','沟通'),('location','位置');

-- Empty in stage 2. Missing rows mean unlabelled, never 'not mentioned'.
CREATE TABLE review_labels (
    review_id TEXT NOT NULL REFERENCES reviews(review_id),
    topic TEXT NOT NULL REFERENCES topics(topic),
    method_id TEXT NOT NULL, version TEXT NOT NULL,
    mention_status TEXT NOT NULL CHECK(mention_status IN ('present','absent','uncertain')),
    sentiment TEXT NOT NULL CHECK(sentiment IN ('positive','negative','neutral','mixed','uncertain','not_applicable')),
    evidence_text TEXT NOT NULL,
    labelled_at TEXT NOT NULL,
    PRIMARY KEY(review_id,topic,method_id,version),
    FOREIGN KEY(method_id,version) REFERENCES methods(method_id,version),
    CHECK((mention_status='absent' AND sentiment='not_applicable') OR
          (mention_status='present' AND sentiment<>'not_applicable' AND length(trim(evidence_text))>0) OR
          (mention_status='uncertain' AND sentiment='uncertain' AND length(trim(evidence_text))>0))
);

CREATE TABLE language_human_checks (
    review_id TEXT PRIMARY KEY NOT NULL REFERENCES reviews(review_id),
    user_language_label TEXT NOT NULL CHECK(user_language_label IN ('es','other','mixed','uncertain','no_text')),
    user_notes TEXT NOT NULL
);
CREATE TABLE build_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE VIEW analysis_reviews AS
SELECT r.*, l.public_listing_id, l.district, l.neighbourhood, l.room_type
FROM reviews r JOIN listings l ON l.listing_id=r.listing_id
CROSS JOIN settings s
WHERE r.analysis_status='included'
  AND r.join_status='unambiguous' AND r.language_status='es_candidate'
  AND r.review_date BETWEEN s.start_date AND s.end_date;

-- Safe projection: aggregate queries should read this or analysis_reviews.
-- This view deliberately exposes no source ID, name, URL, coordinates or text.
CREATE VIEW public_sample_metadata AS
SELECT public_review_id, public_listing_id, substr(review_date,1,7) AS month,
       district,room_type, 'unvalidated_language_prediction' AS language_validation
FROM analysis_reviews;
