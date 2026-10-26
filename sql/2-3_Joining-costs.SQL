-- Dialect: PostgreSQL

WITH daily_revenue AS (
    SELECT 
        DATE(event_time) AS event_date,
        app_id,
        media_source,
        campaign,
        SUM(revenue_usd) AS total_revenue
    FROM clean_events
    GROUP BY 1, 2, 3, 4
),
daily_costs AS (
    SELECT 
        date AS event_date,
        app_id,
        media_source,
        campaign,
        SUM(cost_usd) AS total_cost
    FROM campaign_costs
    GROUP BY 1, 2, 3, 4
)
SELECT 
    COALESCE(r.event_date, c.event_date) AS event_date,
    COALESCE(r.app_id, c.app_id) AS app_id,
    COALESCE(r.media_source, c.media_source) AS media_source,
    COALESCE(r.campaign, c.campaign) AS campaign,
    COALESCE(r.total_revenue, 0) AS revenue,
    COALESCE(c.total_cost, 0) AS cost,
    COALESCE(r.total_revenue, 0) / NULLIF(c.total_cost, 0) AS roas
FROM daily_revenue r
FULL OUTER JOIN daily_costs c
    ON r.event_date = c.event_date
    AND r.app_id = c.app_id
    AND r.media_source = c.media_source
    AND r.campaign = c.campaign;