-- Dialect: PostgreSQL

SELECT DISTINCT ON (event_id)
    event_id, user_id, app_id, event_name, event_time, 
    ingested_at, country, media_source, campaign, revenue_usd
FROM events_raw
WHERE is_test = FALSE
ORDER BY event_id, ingested_at DESC, event_time DESC;
