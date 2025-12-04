output "api_url" {
  description = "Verus API URL"
  value       = "${aws_api_gateway_stage.verus_api.invoke_url}/${aws_api_gateway_resource.verus_api.path_part}"
}

output "cognito_client_id" {
  description = "Cognito client ID"
  sensitive   = true
  value       = aws_cognito_user_pool_client.this.id
}

output "cognito_client_secret" {
  description = "Cognito client ID"
  sensitive   = true
  value       = aws_cognito_user_pool_client.this.client_secret
}

output "cognito_token_url" {
  description = "Cognito token URL"
  value       = "https://${local.domain_prefix}.auth.${var.region}.amazoncognito.com/oauth2/token"
}

output "cognito_scopes" {
  description = "Cognito scope ids"
  value       = aws_cognito_resource_server.this.scope_identifiers
}
