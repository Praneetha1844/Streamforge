variable "instance_name" {
  description = "Cloud SQL instance name."
  type        = string
}

variable "region" {
  description = "Region of the instance."
  type        = string
}

variable "network_id" {
  description = "VPC network ID with private services access, projects/<project>/global/networks/<name>."
  type        = string
}

variable "tier" {
  description = "Machine tier."
  type        = string
  default     = "db-custom-1-3840"
}

variable "availability_type" {
  description = "ZONAL for a single zone, REGIONAL for high availability."
  type        = string
  default     = "ZONAL"

  validation {
    condition     = contains(["ZONAL", "REGIONAL"], var.availability_type)
    error_message = "availability_type must be ZONAL or REGIONAL."
  }
}

variable "deletion_protection" {
  description = "Protect the instance from accidental deletion."
  type        = bool
  default     = true
}

variable "database_name" {
  description = "Name of the application database."
  type        = string
  default     = "streamforge"
}

variable "database_user" {
  description = "Name of the application database user."
  type        = string
  default     = "streamforge"
}
