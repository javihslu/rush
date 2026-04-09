variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for compute resources"
  type        = string
  default     = "europe-west6"
}

variable "location" {
  description = "GCP location for storage and BigQuery"
  type        = string
  default     = "europe-west6"
}

variable "bq_dataset_name" {
  description = "BigQuery dataset name"
  type        = string
  default     = "rush"
}
