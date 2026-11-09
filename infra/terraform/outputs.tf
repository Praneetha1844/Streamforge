output "events_topic" {
  description = "Topic producers publish events to."
  value       = module.pubsub.topic_name
}

output "events_subscription" {
  description = "Subscription the worker pulls from."
  value       = module.pubsub.subscription_name
}

output "dead_letter_topic" {
  description = "Topic that receives messages Pub/Sub gave up redelivering."
  value       = module.pubsub.dead_letter_topic_name
}

output "registry_url" {
  description = "Artifact Registry path to push container images to."
  value       = module.registry.repository_url
}

output "api_url" {
  description = "Cloud Run URL of the read API (internal ingress only)."
  value       = module.api.url
}

output "database_url_secret_id" {
  description = "Secret Manager secret holding the database connection URL."
  value       = module.cloudsql.database_url_secret_id
}
