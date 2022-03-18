# Cognito config
resource "aws_cognito_user_pool" "verus_cognito_pool" {
  name = "${local.name_prefix}-notification-pool-${random_pet.name.id}"
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
}

resource "aws_cognito_resource_server" "verus_cognito_resource_server" {
  identifier = "verus-api"
  name       = "${local.name_prefix}-api-resource-server"
  scope {
    scope_name        = "access"
    scope_description = "Retrieve or update VRSC stakes data"
  }
  user_pool_id = aws_cognito_user_pool.verus_cognito_pool.id
}

resource "aws_cognito_user_pool_domain" "verus_cognito_domain" {
  domain       = local.domain_prefix
  user_pool_id = aws_cognito_user_pool.verus_cognito_pool.id
}

resource "aws_cognito_user_pool_client" "verus_cognito_client" {
  name                                 = "${local.name_prefix}-cli-wallet"
  user_pool_id                         = aws_cognito_user_pool.verus_cognito_pool.id
  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_scopes                 = aws_cognito_resource_server.verus_cognito_resource_server.scope_identifiers
}