-- Cleans and types raw SBB departure records from the dlt ingestion layer.
--
-- Transformations applied:
--   - Cast ISO-8601 strings to typed timestamps
--   - Default null delay to 0 (on-time) and derive is_delayed flag
--   - Filter rows missing a scheduled departure (incomplete API records)

with source as (
    select * from {{ source('transport_raw', 'departures') }}
),

cleaned as (
    select
        id,
        station,
        line_name,
        category,
        line_number,
        operator,
        destination,
        platform_scheduled,

        -- Cast string timestamps to proper types
        departure_scheduled::timestamptz  as departure_scheduled_at,
        departure_actual::timestamptz     as departure_actual_at,

        -- Treat null delay as on-time (0 minutes)
        coalesce(delay_minutes, 0)        as delay_minutes,

        -- Convenience flag for filtering/aggregation
        coalesce(delay_minutes, 0) > 0    as is_delayed,

        ingested_at::timestamptz          as ingested_at

    from source
    where departure_scheduled is not null
)

select * from cleaned
