# Answers and Explanations

## Section 2: SQL

**Task 2.1 (Explain):**
If two deliveries share the exact same `ingested_at`, I added `event_time DESC` to the `ORDER BY` clause to act as a secondary tie-breaker. If even `event_time` is identical, PostgreSQL will pick one arbitrarily.

**Task 2.2 (Explain):**
Yes, missing days completely break the "7-day moving average" logic in standard window functions. `ROWS BETWEEN 6 PRECEDING` will simply take the last 6 *available* data points, which might span across 3 weeks if the app is inactive. 
**Fix:** I can generate a calendar "date spine", `CROSS JOIN` it with all unique `app_id`s, and `LEFT JOIN` the daily revenue table to this spine. I would `COALESCE` null revenues to 0, ensuring every calendar day exists before applying the window function.

**Task 2.3 (Explain):**
I used a `FULL OUTER JOIN`. 
- **Cost but no revenue:** Means marketing spent money on clicks/impressions, but users haven't triggered revenue events yet (low conversion or attribution delay).
- **Revenue but no cost:** Means organic traffic, late conversions from old campaigns, or broken attribution tracking.
- **Division by zero:** I wrapped the denominator in `NULLIF(c.total_cost, 0)`. If cost is 0, the ROAS becomes `NULL` instead of throwing a math exception.

**Task 2.4 (Explain):**
I filter on `ingested_at`. If I filter on `event_time`, I will miss late-arriving events (e.g., a phone was offline for 3 days and sent Monday's event on Thursday) unless I constantly overwrite the entire history. 
The smallest window I can reload is `ingested_at > last_pipeline_run_timestamp`. The cost of this choice is that I am completely dependent on the vendor's `ingested_at` being monotonic and trustworthy. If the vendor updates an old record but fails to update `ingested_at`, I will never pick up that correction.

**Task 2.5 (Explain):**
1. **Uniqueness check (`event_id` duplicates):** 
   - **Action:** **Fail the pipeline.** 
   - **Why:** The clean table must have strictly one row per event. If this query returns rows, our deduplication logic or incremental UPSERT is fundamentally broken. Downstream aggregations (revenue, ROAS) will be inflated, which is unacceptable for financial metrics.

2. **Completeness check (Missing `app_id`):** 
   - **Action:** **Fail the pipeline.** 
   - **Why:** `app_id` is the primary dimension for all grouping in downstream window functions and cost joins. An event without an app association is orphaned data that breaks analytical models. It should be blocked and quarantined.

3. **Anomaly check (Negative `revenue_usd`):** 
   - **Action:** **Warn.** 
   - **Why:** While negative revenue is generally unexpected, it might represent a valid refund process silently introduced by the vendor. Failing the pipeline would stop all other valid reporting. We should trigger a Slack/email alert to the data team to investigate with the business stakeholders before making a strict drop rule.
---

## Section 3: Python

**Task 3.2 (Explain):**
If the script dies halfway through, it leaves partially written Parquet files in the `event_date=...` folders. Because it's not atomic, a subsequent run or a reporting query might read duplicate or corrupted data. 
**Fix:** I would implement atomic writes. The script should write the output to a temporary staging directory (e.g., `out_temp/`). Only if the entire execution succeeds, it atomically renames/moves the temporary directory to the final `out/` directory.

**Task 3.3 (Code Review & Problems):**
1. **Performance (Critical):** `iterrows()` is extremely slow for Pandas. Pandas is meant to be vectorized; iterating row-by-row defeats its purpose.
2. **Robustness (Critical):** `astype(float)` will crash immediately if `revenue_usd` contains empty strings `""` or commas `","`.
3. **Correctness (High):** `str.startswith(day)` is dangerous. If timestamps have different formats or unexpected spaces, it fails silently or incorrectly. Proper datetime parsing is required.
4. **Robustness (Medium):** String concatenation `row["app_id"] + "-"` will throw a TypeError if `app_id` is parsed as a numeric type or is NaN.

---

## Section 4: Modelling and design

**4.1 Star schema**
- **Fact table:** `fact_events`
- **Grain:** One row per single, valid, deduplicated event triggered by a user.
- **Measures:** `revenue_usd`.
- **Dimensions:** `dim_user`, `dim_app`, `dim_campaign` (media_source, campaign), `dim_date`.

**4.2 A dimension that changes**
I would implement Slowly Changing Dimensions (SCD) Type 2 on the campaign dimension. I would add `valid_from` and `valid_to` timestamp columns to the dimension table. Yesterday's fact rows will join to the old dimension record (where `event_time` falls between `valid_from` and `valid_to`), preserving historical names. The cost is query complexity: standard joins now require `BETWEEN` date conditions, which are slower and harder to write.

**4.3 Idempotency**
Idempotency means that doing a task once has the exact same effect as doing it ten times. If you press the "up" button on an elevator that is already going up, nothing changes — that's idempotent. 
To an engineer: `INSERT ... SELECT` is not idempotent because running it twice inserts the data twice, creating duplicates. The usual fixes are using `UPSERT` / `MERGE` statements, or using the "Delete-Write" pattern (deleting the target partition completely before inserting the new data).

**4.4 Late data**
The pipeline reads the late Thursday batch using `ingested_at`. The logic processes the event, determines its `event_date` is Monday, and updates/overwrites Monday's partition. I tell the client: "Our data model is designed to be eventually consistent to accommodate late mobile network deliveries. Monday's initial numbers were preliminary; the final accurate numbers are now updated in the dashboard."

**4.5 Partitioning**
I would partition the fact table on `event_date` (derived from `event_time`). We partition by this because 99% of business queries filter by when the event actually happened ("How much revenue did we make last month?"), enabling partition pruning. One query pattern this makes slower is auditing data ingestion ("How many rows did the vendor send us today?"), which filters by `ingested_at` and requires scanning multiple partitions.

---

## Section 5: Debugging scenario

1. **Check BI Tool / Cache:** Has the dashboard refreshed properly, or is it showing cached data? 
   *(Yes: dashboard issue. No: data is actually missing in the database).*
2. **Check the Fact Table:** Run `SELECT SUM(revenue) FROM fact WHERE date='Sunday' AND app='X'`. 
   *(Yes (returns > 0): dashboard/semantic layer issue. No (returns 0): issue is in the pipeline).*
3. **Check the Staging/Raw layer:** Did the vendor deliver raw events for this app on Sunday? 
   *(Yes: our ETL logic filtered them out. No: the vendor or the app tracking SDK is broken).*
4. **Check Data Quality / Quarantine logs:** Were this app's events dropped because `is_test` was incorrectly flagged as true, or revenue came as a completely unparseable string? 
   *(Yes: DQ bug or vendor schema change. No: move to step 5).*
5. **Check Dimension Joins:** Run a `LEFT JOIN` instead of an `INNER JOIN` with `dim_app`. Is the `app_id` missing from the dimension table, causing the inner join to silently drop all Sunday events? 
   *(Yes: we need to add the new app metadata. No: investigate deeper edge cases in incremental load).*
