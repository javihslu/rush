-- Joins cleaned departures with weather forecasts to produce actionable
-- departure recommendations for the end user (commuter leaving the office).
--
-- Logic:
--   - Each departure is matched to its forecast hour via date_trunc
--   - A rush_score is computed (lower = better):
--       delay_minutes + precipitation * 2 + snowfall * 5
--   - A recommendation label is derived from the score thresholds

{{ config(
    materialized='table',
    partition_by={'field': 'departure_scheduled_at', 'data_type': 'timestamp', 'granularity': 'day'} if target.type == 'bigquery' else none,
    cluster_by=['station', 'category'] if target.type == 'bigquery' else none
) }}

with departures as (
    select * from {{ ref('stg_transport__departures') }}
),

weather as (
    select * from {{ ref('stg_weather__forecast') }}
),

joined as (
    select
        -- Departure identity
        d.id                                              as departure_id,
        d.station,
        d.line_name,
        d.category,
        d.destination,
        -- Timing
        d.departure_scheduled_at,
        d.departure_actual_at,
        d.delay_minutes,
        d.is_delayed,

        -- Weather at departure hour
        w.forecast_hour,
        w.temperature_2m,
        w.precipitation,
        w.snowfall,
        w.windspeed_10m,
        w.weather_condition,
        w.bad_weather,

        -- Composite score: lower is better
        -- Delay hurts, rain and snow hurt more (they compound travel disruption)
        d.delay_minutes
            + (coalesce(w.precipitation, 0) * 2)
            + (coalesce(w.snowfall, 0) * 5)               as rush_score,

        -- Human-readable recommendation for the UI / analyst
        case
            when d.delay_minutes = 0
                 and coalesce(w.precipitation, 0) = 0     then 'Ideal'
            when d.delay_minutes <= 5
                 and coalesce(w.precipitation, 0) < 1     then 'Good'
            when d.delay_minutes <= 10
                 or coalesce(w.precipitation, 0) < 3      then 'Acceptable'
            else                                               'Avoid'
        end                                               as recommendation

    from departures d
    left join weather w
        on {{ dbt.date_trunc("hour", "d.departure_scheduled_at") }} = w.forecast_hour
)

select * from joined
order by departure_scheduled_at
