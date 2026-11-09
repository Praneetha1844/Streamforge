resource "google_artifact_registry_repository" "this" {
  repository_id = var.repository_id
  location      = var.location
  format        = "DOCKER"
  description   = "Container images for Streamforge."
}
