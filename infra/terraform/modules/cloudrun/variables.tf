variable "name" {
  description = "Cloud Run service name."
  type        = string
}

variable "location" {
  description = "Region of the service."
  type        = string
}

variable "image" {
  description = "Container image reference."
  type        = string
}

variable "service_account_email" {
  description = "Service account the service runs as."
  type        = string
}

variable "network" {
  description = "VPC network for direct egress."
  type        = string
}

variable "subnetwork" {
  description = "Subnetwork for direct egress."
  type        = string
}

variable "args" {
  description = "Arguments passed to the image entrypoint."
  type        = list(string)
  default     = []
}

variable "env" {
  description = "Plain environment variables."
  type        = map(string)
  default     = {}
}

variable "secret_env" {
  description = "Environment variables sourced from Secret Manager, as name to secret ID."
  type        = map(string)
  default     = {}
}

variable "container_port" {
  description = "Port the container listens on."
  type        = number
}

variable "min_instances" {
  description = "Minimum instance count. 0 allows scale to zero."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum instance count."
  type        = number
  default     = 3
}

variable "cpu_always_allocated" {
  description = "Keep CPU allocated outside requests. Needed for background pulling workers."
  type        = bool
  default     = false
}

variable "ingress" {
  description = "Ingress setting. Internal only by default; no public invoker is granted."
  type        = string
  default     = "INGRESS_TRAFFIC_INTERNAL_ONLY"
}

variable "deletion_protection" {
  description = "Protect the service from accidental deletion."
  type        = bool
  default     = true
}
