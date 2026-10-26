-- Dialect: PostgreSQL

WITH daily_app_revenue AS (
    SELECT 
        app_id,
        DATE(event_time) AS event_date,
        SUM(revenue_usd) AS daily_revenue
    FROM clean_events
    GROUP BY app_id, DATE(event_time)
)
SELECT 
    app_id,
    event_date,
    daily_revenue,
    SUM(daily_revenue) OVER (
        PARTITION BY app_id 
        ORDER BY event_date
    ) AS running_total_revenue,
    AVG(daily_revenue) OVER (
        PARTITION BY app_id 
        ORDER BY event_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7d,
    (daily_revenue - LAG(daily_revenue) OVER (PARTITION BY app_id ORDER BY event_date)) 
    / NULLIF(LAG(daily_revenue) OVER (PARTITION BY app_id ORDER BY event_date), 0) * 100 AS dod_change_percent
FROM daily_app_revenue;