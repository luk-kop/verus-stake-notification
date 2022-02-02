# API Gateway config
resource "aws_api_gateway_rest_api" "verus_api" {
  name        = "verus-api-gateway-${random_id.name.hex}"
  description = "Invoke Lambda function when a new stake appears in your Verus (VRSC) wallet."
}

resource "aws_api_gateway_resource" "verus_api" {
  parent_id   = aws_api_gateway_rest_api.verus_api.root_resource_id
  path_part   = "stake"
  rest_api_id = aws_api_gateway_rest_api.verus_api.id
}

resource "aws_api_gateway_authorizer" "verus_auth" {
  name          = "Verus-API-Authorizer"
  type          = "COGNITO_USER_POOLS"
  rest_api_id   = aws_api_gateway_rest_api.verus_api.id
  provider_arns = [aws_cognito_user_pool.verus_cognito_pool.arn]
}

# API Gateway - GET
resource "aws_api_gateway_method" "verus_api_get" {
  authorization = "COGNITO_USER_POOLS"
  //  authorization = "NONE"
  authorizer_id        = aws_api_gateway_authorizer.verus_auth.id
  http_method          = "GET"
  resource_id          = aws_api_gateway_resource.verus_api.id
  rest_api_id          = aws_api_gateway_rest_api.verus_api.id
  authorization_scopes = aws_cognito_resource_server.verus_cognito_resource_server.scope_identifiers
}

resource "aws_api_gateway_integration" "verus_api_get" {
  http_method             = aws_api_gateway_method.verus_api_get.http_method
  resource_id             = aws_api_gateway_resource.verus_api.id
  rest_api_id             = aws_api_gateway_rest_api.verus_api.id
  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = aws_lambda_function.verus_lambda_get.invoke_arn
  connection_type         = "INTERNET"
  passthrough_behavior    = "WHEN_NO_TEMPLATES"
  request_templates = {
    "application/json" = <<EOF
{
    "year": "$input.params('year')",
    "month": "$input.params('month')",
    "http_method": "$context.httpMethod"
}
EOF
  }
}

resource "aws_api_gateway_method_response" "verus_api_method_response_get_200" {
  http_method = aws_api_gateway_method.verus_api_get.http_method
  resource_id = aws_api_gateway_resource.verus_api.id
  rest_api_id = aws_api_gateway_rest_api.verus_api.id
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "verus_api_integration_response_get_200" {
  http_method       = aws_api_gateway_method.verus_api_get.http_method
  resource_id       = aws_api_gateway_resource.verus_api.id
  rest_api_id       = aws_api_gateway_rest_api.verus_api.id
  status_code       = aws_api_gateway_method_response.verus_api_method_response_get_200.status_code
  selection_pattern = ""
  content_handling  = "CONVERT_TO_TEXT"
  depends_on        = [aws_api_gateway_integration.verus_api_get]
}

# API Gateway - POST
resource "aws_api_gateway_method" "verus_api_post" {
  //  authorization = "NONE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.verus_auth.id
  http_method   = "POST"
  resource_id   = aws_api_gateway_resource.verus_api.id
  rest_api_id   = aws_api_gateway_rest_api.verus_api.id
  request_models = {
    "application/json" = aws_api_gateway_model.verus_api_post_model.name
  }
  request_validator_id = aws_api_gateway_request_validator.verus_api_post_validate_body.id
  authorization_scopes = aws_cognito_resource_server.verus_cognito_resource_server.scope_identifiers
}

resource "aws_api_gateway_model" "verus_api_post_model" {
  rest_api_id  = aws_api_gateway_rest_api.verus_api.id
  name         = "StakePOST"
  description  = "JSON schema for stake POST method"
  content_type = "application/json"
  schema       = <<EOF
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "title" : "New Stake",
  "type" : "object",
  "properties": {
      "txid": {
          "description": "Stake transaction (tx) id",
          "type": "string"
      },
      "time": {
          "description": "Time of stake tx",
          "type": "integer"
      },
      "amount": {
          "description": "Stake amount",
          "type": "number",
          "minimum": 0
      }
  },
  "required": ["txid", "time", "amount"]
}
EOF
}

resource "aws_api_gateway_request_validator" "verus_api_post_validate_body" {
  name                  = "POST-body-validator"
  rest_api_id           = aws_api_gateway_rest_api.verus_api.id
  validate_request_body = true
}

resource "aws_api_gateway_integration" "verus_api_post" {
  http_method             = aws_api_gateway_method.verus_api_post.http_method
  resource_id             = aws_api_gateway_resource.verus_api.id
  rest_api_id             = aws_api_gateway_rest_api.verus_api.id
  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = aws_lambda_function.verus_lambda_post.invoke_arn
  connection_type         = "INTERNET"
  passthrough_behavior    = "NEVER"
  request_templates = {
    "application/json" = <<EOF
{
    "body": $input.json('$'),
    "http_method": "$context.httpMethod"
}
EOF
  }
}

resource "aws_api_gateway_method_response" "verus_api_method_response_post_200" {
  http_method = aws_api_gateway_method.verus_api_post.http_method
  resource_id = aws_api_gateway_resource.verus_api.id
  rest_api_id = aws_api_gateway_rest_api.verus_api.id
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "verus_api_integration_response_post_200" {
  http_method       = aws_api_gateway_method.verus_api_post.http_method
  resource_id       = aws_api_gateway_resource.verus_api.id
  rest_api_id       = aws_api_gateway_rest_api.verus_api.id
  status_code       = aws_api_gateway_method_response.verus_api_method_response_post_200.status_code
  selection_pattern = ""
  content_handling  = "CONVERT_TO_TEXT"
  depends_on        = [aws_api_gateway_integration.verus_api_post]
}

resource "aws_api_gateway_deployment" "verus_api" {
  rest_api_id = aws_api_gateway_rest_api.verus_api.id
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.verus_api.id,
      aws_api_gateway_method.verus_api_get.id,
      aws_api_gateway_integration.verus_api_get.id,
      aws_api_gateway_method.verus_api_post.id,
      aws_api_gateway_integration.verus_api_post.id
    ]))
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "verus_api" {
  deployment_id = aws_api_gateway_deployment.verus_api.id
  rest_api_id   = aws_api_gateway_rest_api.verus_api.id
  stage_name    = "vrsc"
}

resource "aws_api_gateway_rest_api_policy" "verus_api" {
  rest_api_id = aws_api_gateway_rest_api.verus_api.id
  policy      = data.aws_iam_policy_document.verus_api_resource_ip_limit_policy.json
}