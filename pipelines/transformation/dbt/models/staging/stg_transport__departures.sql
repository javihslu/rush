-- Cleans and types raw SBB departure records from the dlt ingestion layer.
--
-- Transformations applied:
--   - Cast ISO-8601 strings to typed timestamps
--   - Compute delay_minutes from scheduled vs actual departure
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
        cast(departure_scheduled as timestamp)  as departure_scheduled_at,
        cast(departure_actual as timestamp)      as departure_actual_at,

        -- Compute delay from raw timestamps (moved from ingestion layer)
        cast(coalesce(
            {{ delay_minutes(
                'cast(departure_actual as timestamp)',
                'cast(departure_scheduled as timestamp)'
            ) }},
            0
        ) as integer)                            as delay_minutes,

        -- Convenience flag for filtering/aggregation
        coalesce(
            {{ delay_minutes(
                'cast(departure_actual as timestamp)',
                'cast(departure_scheduled as timestamp)'
            ) }},
            0
        ) > 0                                    as is_delayed,

        cast(ingested_at as timestamp)           as ingested_at

    from source
    where departure_scheduled is not null
)

select * from cleaned
