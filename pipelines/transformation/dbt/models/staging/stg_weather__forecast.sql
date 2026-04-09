-- Cleans and enriches raw Open-Meteo hourly forecast records.
--
-- Transformations applied:
--   - Cast forecast_time string to timestamp
--   - Derive a human-readable weather_condition label from WMO weathercode
--   - Derive a boolean bad_weather flag for easy filtering in the mart layer

with source as (
    select * from {{ source('weather_raw', 'hourly_forecast') }}
),

cleaned as (
    select
        id,
        cast(forecast_time as timestamp)  as forecast_hour,
        latitude,
        longitude,
        temperature_2m,
        precipitation,
        rain,
        snowfall,
        windspeed_10m,
        weathercode,
        visibility,

        -- Map WMO weather codes to readable labels
        -- See: https://open-meteo.com/en/docs#weathervariables
        case
            when weathercode = 0                              then 'Clear'
            when weathercode in (1, 2, 3)                    then 'Cloudy'
            when weathercode in (45, 48)                     then 'Fog'
            when weathercode in (51, 53, 55, 61, 63, 65,
                                 80, 81, 82)                  then 'Rainy'
            when weathercode in (71, 73, 75, 77, 85, 86)    then 'Snowy'
            when weathercode in (95, 96, 99)                 then 'Thunderstorm'
            else 'Other'
        end as weather_condition,

        -- Flag hours where conditions may affect the commute
        precipitation > 2
            or snowfall > 0
            or weathercode in (45, 48, 71, 73, 75, 77,
                               85, 86, 95, 96, 99)            as bad_weather,

        cast(ingested_at as timestamp)  as ingested_at

    from source
)

select * from cleaned
