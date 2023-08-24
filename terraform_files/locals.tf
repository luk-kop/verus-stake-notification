locals {
  project       = lookup(var.resource_tags, "Project", "vrsc-notification")
  environment   = lookup(var.resource_tags, "Environment", "dev")
  domain_prefix = "${var.cognito_pool_domain}-${random_string.name.id}"
  name_prefix   = "${local.project}-${local.environment}"
  api_stage     = "vrsc-${local.environment}"
}
