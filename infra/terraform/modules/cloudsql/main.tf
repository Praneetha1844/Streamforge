resource "random_password" "database" {
  length  = 32
  special = false # keeps the password safe to embed in a connection URL
}

resource "google_sql_database_instance" "this" {
  name                = var.instance_name
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = var.deletion_protection

  settings {
    tier              = var.tier
    availability_type = var.availability_type
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }

    # Private IP only: the instance has no public address.
    # Requires private services access on the VPC (see the README).
    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_id
    }
  }
}

resource "google_sql_database" "this" {
  name     = var.database_name
  instance = google_sql_database_instance.this.name
}

resource "google_sql_user" "this" {
  name     = var.database_user
  instance = google_sql_database_instance.this.name
  password = random_password.database.result
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "${var.instance_name}-database-url"

  replication {
    auto {}
  }
}

# The password is stored in Terraform state as well as in Secret Manager.
resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql://${var.database_user}:${random_password.database.result}@${google_sql_database_instance.this.private_ip_address}:5432/${var.database_name}"
}
