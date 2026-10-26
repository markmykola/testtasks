-- Dialect: PostgreSQL
-- Check 1: No duplicate event_ids
SELECT event_id 
FROM clean_events 
GROUP BY event_id 
HAVING COUNT(*) > 1;

-- Check 2: No missing critical dimensions (app_id)
SELECT event_id 
FROM clean_events 
WHERE app_id IS NULL OR TRIM(app_id) = '';

-- Check 3: No illogical revenue values (e.g., negative revenue)
SELECT event_id 
FROM clean_events 
WHERE revenue_usd < 0;
