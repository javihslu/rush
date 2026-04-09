-- Compute the delay in minutes between two timestamps.
-- Uses the correct function for each database adapter.

{% macro delay_minutes(actual, scheduled) %}
    {% if target.type == 'bigquery' %}
        timestamp_diff({{ actual }}, {{ scheduled }}, MINUTE)
    {% else %}
        extract(epoch from {{ actual }} - {{ scheduled }}) / 60
    {% endif %}
{% endmacro %}
