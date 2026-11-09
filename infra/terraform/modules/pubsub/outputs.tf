output "topic_name" {
  description = "Events topic name."
  value       = google_pubsub_topic.events.name
}

output "subscription_name" {
  description = "Events subscription name used by the worker."
  value       = google_pubsub_subscription.events.name
}

output "dead_letter_topic_name" {
  description = "Dead-letter topic name."
  value       = google_pubsub_topic.dead_letter.name
}
