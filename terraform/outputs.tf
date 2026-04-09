output "data_lake_bucket" {
  description = "GCS data lake bucket name"
  value       = google_storage_bucket.data_lake.name
}

output "data_lake_url" {
  description = "GCS data lake bucket URL"
  value       = google_storage_bucket.data_lake.url
}

output "bigquery_dataset" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.rush.dataset_id
}

output "bigquery_transport_raw" {
  description = "BigQuery transport raw dataset ID"
  value       = google_bigquery_dataset.transport_raw.dataset_id
}

output "bigquery_weather_raw" {
  description = "BigQuery weather raw dataset ID"
  value       = google_bigquery_dataset.weather_raw.dataset_id
}
