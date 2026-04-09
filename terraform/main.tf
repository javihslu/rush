terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.6"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "data_lake" {
  name          = "${var.project_id}-data-lake"
  location      = var.location
  force_destroy = true

  uniform_bucket_level_access = true
  storage_class = "STANDARD"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
}

resource "google_bigquery_dataset" "rush" {
  dataset_id = var.bq_dataset_name
  location   = var.location

  delete_contents_on_destroy = true
}

resource "google_bigquery_dataset" "transport_raw" {
  dataset_id = "transport_raw"
  location   = var.location

  delete_contents_on_destroy = true
}

resource "google_bigquery_dataset" "weather_raw" {
  dataset_id = "weather_raw"
  location   = var.location

  delete_contents_on_destroy = true
}
