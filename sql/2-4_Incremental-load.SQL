-- Dialect: PostgreSQL

INSERT INTO clean_events (
    event_id, user_id, app_id, event_name, event_time, 
    ingested_at, country, media_source, campaign, revenue_usd
)
SELECT 
    event_id, user_id, app_id, event_name, event_time, 
    ingested_at, country, media_source, campaign, revenue_usd
FROM staging_events_deduplicated
ON CONFLICT (event_id) 
DO UPDATE SET 
    ingested_at = EXCLUDED.ingested_at,
    revenue_usd = EXCLUDED.revenue_usd,
    event_time = EXCLUDED.event_time,
    country = EXCLUDED.country,
    media_source = EXCLUDED.media_source,
    campaign = EXCLUDED.campaign
WHERE clean_events.ingested_at < EXCLUDED.ingested_at;