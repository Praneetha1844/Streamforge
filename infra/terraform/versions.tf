terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state. Create the bucket first (versioning on, uniform access, no public access),
  # then uncomment and run `terraform init -migrate-state`. State contains the generated
  # database password, so restrict who can read the bucket.
  #
  # backend "gcs" {
  #   bucket = "<your-state-bucket>"
  #   prefix = "streamforge"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
