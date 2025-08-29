resource "aws_cognito_user_pool" "this" {
  name = "${local.name_prefix}-notification-pool-${random_pet.name.id}"

  admin_create_user_config {
    allow_admin_create_user_only = true
  }
}

resource "aws_cognito_resource_server" "this" {
  identifier   = "verus-api"
  name         = "${local.name_prefix}-api-resource-server"
  user_pool_id = aws_cognito_user_pool.this.id

  scope {
    scope_name        = "access"
    scope_description = "Retrieve or update VRSC stakes data"
  }
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = local.domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}

resource "aws_cognito_user_pool_client" "this" {
  name                                 = "${local.name_prefix}-cli-wallet"
  user_pool_id                         = aws_cognito_user_pool.this.id
  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_scopes                 = aws_cognito_resource_server.this.scope_identifiers
}
