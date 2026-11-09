variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for topic and subscription names."
  type        = string
}

variable "max_delivery_attempts" {
  description = "Delivery attempts before Pub/Sub forwards a message to the dead-letter topic."
  type        = number
  default     = 10

  validation {
    condition     = var.max_delivery_attempts >= 5 && var.max_delivery_attempts <= 100
    error_message = "max_delivery_attempts must be between 5 and 100, which are Pub/Sub's limits."
  }
}
