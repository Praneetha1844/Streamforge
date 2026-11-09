data "google_project" "this" {
  project_id = var.project_id
}

locals {
  # Pub/Sub's own service agent forwards dead-lettered messages, so it needs these roles.
  pubsub_service_agent = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_topic" "events" {
  name = "${var.name_prefix}-events"
}

resource "google_pubsub_topic" "dead_letter" {
  name = "${var.name_prefix}-events-dlq"
}

resource "google_pubsub_subscription" "events" {
  name                       = "${var.name_prefix}-events-worker"
  topic                      = google_pubsub_topic.events.id
  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  # Safety net. The application dead-letters earlier with a reason code
  # (SF_MAX_DELIVERY_ATTEMPTS=5), so this limit must stay higher than that.
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = var.max_delivery_attempts
  }

  expiration_policy {
    ttl = ""
  }
}

# Without a subscription, messages forwarded to the dead-letter topic are dropped.
resource "google_pubsub_subscription" "dead_letter" {
  name                       = "${var.name_prefix}-events-dlq-inspect"
  topic                      = google_pubsub_topic.dead_letter.id
  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  expiration_policy {
    ttl = ""
  }
}

resource "google_pubsub_topic_iam_member" "dead_letter_publisher" {
  topic  = google_pubsub_topic.dead_letter.name
  role   = "roles/pubsub.publisher"
  member = local.pubsub_service_agent
}

resource "google_pubsub_subscription_iam_member" "dead_letter_forwarder" {
  subscription = google_pubsub_subscription.events.name
  role         = "roles/pubsub.subscriber"
  member       = local.pubsub_service_agent
}
