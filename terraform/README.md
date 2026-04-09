# Terraform -- GCP Infrastructure

Provisions the cloud resources for the Rush project on Google Cloud Platform.

## Resources

| Resource | Type | Description |
|----------|------|-------------|
| `data_lake` | GCS bucket | Raw data storage (`{project_id}-data-lake`) |
| `rush` | BigQuery dataset | Transformed data for analytics |

## Prerequisites

1. [Terraform](https://developer.hashicorp.com/terraform/install) installed
2. GCP project created and billing linked
3. Application Default Credentials configured

All three are handled by `setup.sh` if you run it first.

## Usage

If you already ran `setup.sh`, Terraform is ready to go:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Manual setup (without setup.sh)

```bash
# authenticate
gcloud auth login
gcloud auth application-default login

# create terraform.tfvars
cat > terraform.tfvars <<EOF
project_id = "your-gcp-project-id"
region     = "europe-west6"
EOF

# provision
terraform init
terraform apply
```

### Destroy

```bash
cd terraform
terraform destroy
```

## Files

| File | Purpose |
|------|---------|
| `main.tf` | Provider config, GCS bucket, BigQuery dataset |
| `variables.tf` | Input variables with defaults |
| `outputs.tf` | Bucket name/URL, dataset ID |
| `terraform.tfvars` | Your project-specific values (gitignored) |
