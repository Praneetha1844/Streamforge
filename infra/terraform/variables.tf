variable "project_id" {
  description = "GCP project ID to deploy into."
  type        = string
}

variable "region" {
  description = "Region for all regional resources."
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "Environment name, used in resource names."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,14}$", var.environment))
    error_message = "environment must be 2-15 characters: lower-case letters, digits and hyphens."
  }
}

variable "api_image" {
  description = "Full image reference for the API service, for example <region>-docker.pkg.dev/<project>/<repo>/streamforge:<tag>. Push it before applying."
  type        = string
}

variable "worker_image" {
  description = "Full image reference for the worker service. Usually the same image as the API."
  type        = string
}

variable "vpc_network_id" {
  description = "ID of an existing VPC with private services access configured, in the form projects/<project>/global/networks/<name>."
  type        = string
}

variable "vpc_subnetwork_id" {
  description = "ID of an existing subnetwork in the same region, used for Cloud Run direct VPC egress."
  type        = string
}

variable "db_tier" {
  description = "Cloud SQL machine tier."
  type        = string
  default     = "db-custom-1-3840"
}

variable "deletion_protection" {
  description = "Protect the database and services from accidental deletion."
  type        = bool
  default     = true
}
