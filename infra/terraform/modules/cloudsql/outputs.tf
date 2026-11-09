output "connection_name" {
  description = "Instance connection name."
  value       = google_sql_database_instance.this.connection_name
}

output "private_ip_address" {
  description = "Private IP address of the instance."
  value       = google_sql_database_instance.this.private_ip_address
}

output "database_url_secret_id" {
  description = "Secret Manager secret ID holding the connection URL."
  value       = google_secret_manager_secret.database_url.id
}
