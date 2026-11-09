locals {
  name_prefix = "streamforge-${var.environment}"

  apis = toset([
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
  ])
}

resource "google_project_service" "enabled" {
  for_each = local.apis

  service            = each.value
  disable_on_destroy = false
}

# One service account per workload, each with only the roles it needs.
resource "google_service_account" "worker" {
  account_id   = "${local.name_prefix}-worker"
  display_name = "Streamforge worker (${var.environment})"
}

resource "google_service_account" "api" {
  account_id   = "${local.name_prefix}-api"
  display_name = "Streamforge API (${var.environment})"
}

module "registry" {
  source        = "./modules/registry"
  repository_id = local.name_prefix
  location      = var.region

  depends_on = [google_project_service.enabled]
}

module "pubsub" {
  source      = "./modules/pubsub"
  project_id  = var.project_id
  name_prefix = local.name_prefix

  depends_on = [google_project_service.enabled]
}

module "cloudsql" {
  source              = "./modules/cloudsql"
  instance_name       = "${local.name_prefix}-db"
  region              = var.region
  network_id          = var.vpc_network_id
  tier                = var.db_tier
  deletion_protection = var.deletion_protection

  depends_on = [google_project_service.enabled]
}

# The worker may pull from the events subscription and nothing else on Pub/Sub.
resource "google_pubsub_subscription_iam_member" "worker_subscriber" {
  subscription = module.pubsub.subscription_name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.worker.email}"
}

# Both services read the database URL from Secret Manager at start-up.
resource "google_secret_manager_secret_iam_member" "database_url" {
  for_each = {
    worker = google_service_account.worker.email
    api    = google_service_account.api.email
  }

  secret_id = module.cloudsql.database_url_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}

module "worker" {
  source                = "./modules/cloudrun"
  name                  = "${local.name_prefix}-worker"
  location              = var.region
  image                 = var.worker_image
  service_account_email = google_service_account.worker.email
  network               = var.vpc_network_id
  subnetwork            = var.vpc_subnetwork_id
  container_port        = 9100
  min_instances         = 1
  max_instances         = 3
  cpu_always_allocated  = true
  deletion_protection   = var.deletion_protection

  args = ["run", "--follow"]

  env = {
    SF_STORE_BACKEND         = "postgres"
    SF_QUEUE_BACKEND         = "pubsub"
    SF_PUBSUB_PROJECT        = var.project_id
    SF_PUBSUB_TOPIC          = module.pubsub.topic_name
    SF_PUBSUB_SUBSCRIPTION   = module.pubsub.subscription_name
    SF_MAX_DELIVERY_ATTEMPTS = "5"
  }

  secret_env = {
    SF_DATABASE_URL = module.cloudsql.database_url_secret_id
  }

  depends_on = [google_secret_manager_secret_iam_member.database_url]
}

module "api" {
  source                = "./modules/cloudrun"
  name                  = "${local.name_prefix}-api"
  location              = var.region
  image                 = var.api_image
  service_account_email = google_service_account.api.email
  network               = var.vpc_network_id
  subnetwork            = var.vpc_subnetwork_id
  container_port        = 8000
  min_instances         = 0
  max_instances         = 3
  cpu_always_allocated  = false
  deletion_protection   = var.deletion_protection

  args = ["serve"]

  env = {
    SF_STORE_BACKEND = "postgres"
    SF_API_HOST      = "0.0.0.0"
  }

  secret_env = {
    SF_DATABASE_URL = module.cloudsql.database_url_secret_id
  }

  depends_on = [google_secret_manager_secret_iam_member.database_url]
}
