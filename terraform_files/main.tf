terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.50"
    }
  }

  required_version = ">= 0.14.9"
}

provider "aws" {
  profile = var.profile
  region  = var.region
  default_tags {
    tags = var.resource_tags
  }
}

locals {
  domain_prefix = "${var.cognito_pool_domain}-${random_string.name.id}"
}

# Random resources
resource "random_id" "name" {
  byte_length = 8
}

resource "random_string" "name" {
  length  = 8
  lower   = true
  special = false
  number  = true
  upper   = false
}

resource "random_pet" "name" {
  length = 1
}

# SNS config
resource "aws_sns_topic" "verus_topic" {
  name = "verus-topic-${random_id.name.hex}"
}

resource "aws_sns_topic_subscription" "verus_topic_subscription" {
  topic_arn = aws_sns_topic.verus_topic.arn
  protocol  = "email"
  endpoint  = var.sns_email
}

# IAM role config
resource "aws_iam_role" "verus_iam_role_for_lambda" {
  name                = "verus-lambda-to-sns-${random_id.name.hex}"
  assume_role_policy  = data.aws_iam_policy_document.verus_assume_role_policy.json
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  inline_policy {
    name   = "verus-lambda-sns-publish-inline"
    policy = data.aws_iam_policy_document.verus_role_inline_policy_sns.json
  }
  inline_policy {
    name   = "verus-lambda-dynamodb-inline"
    policy = data.aws_iam_policy_document.verus_role_inline_policy_dynamodb.json
  }
}

# Lambda config
resource "aws_lambda_function" "verus_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "verus-lambda-func-${random_id.name.hex}"
  description      = "Publish a msg to SNS topic when new stake appears in Verus wallet."
  role             = aws_iam_role.verus_iam_role_for_lambda.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256(data.archive_file.lambda_zip.output_path)
  runtime          = "python3.8"
  environment {
    variables = {
      TOPIC_ARN            = aws_sns_topic.verus_topic.arn
      DYNAMODB_TXIDS_NAME  = aws_dynamodb_table.verus_stakes_txids_table.id
      DYNAMODB_VALUES_NAME = aws_dynamodb_table.verus_stakes_values_table.id
    }
  }
}

resource "aws_lambda_permission" "verus_api_lambda" {
  statement_id  = "allow-execution-from-apigateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verus_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.verus_api.execution_arn}/*/*/*"
  //  source_arn    = "${aws_api_gateway_rest_api.verus_api.execution_arn}/*/${aws_api_gateway_method.verus_api_get.http_method}${aws_api_gateway_resource.verus_api.path}"
}

# Cognito config
resource "aws_cognito_user_pool" "verus_cognito_pool" {
  name = "vrsc-notification-pool-${random_pet.name.id}"
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
}

resource "aws_cognito_resource_server" "verus_cognito_resource_server" {
  identifier = "verus-api"
  name       = "verus-api-resource-server"
  scope {
    scope_name        = "api-read"
    scope_description = "Read access to the API"
  }
  user_pool_id = aws_cognito_user_pool.verus_cognito_pool.id
}

resource "aws_cognito_user_pool_domain" "verus_cognito_domain" {
  domain       = local.domain_prefix
  user_pool_id = aws_cognito_user_pool.verus_cognito_pool.id
}

resource "aws_cognito_user_pool_client" "verus_cognito_client" {
  name                                 = "verus-cli-wallet"
  user_pool_id                         = aws_cognito_user_pool.verus_cognito_pool.id
  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_scopes                 = aws_cognito_resource_server.verus_cognito_resource_server.scope_identifiers
}

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
  authorization        = "COGNITO_USER_POOLS"
//  authorization = "NONE"
  authorizer_id        = aws_api_gateway_authorizer.verus_auth.id
  http_method = "GET"
  resource_id = aws_api_gateway_resource.verus_api.id
  rest_api_id = aws_api_gateway_rest_api.verus_api.id
  authorization_scopes = aws_cognito_resource_server.verus_cognito_resource_server.scope_identifiers
}

resource "aws_api_gateway_integration" "verus_api_get" {
  http_method             = aws_api_gateway_method.verus_api_get.http_method
  resource_id             = aws_api_gateway_resource.verus_api.id
  rest_api_id             = aws_api_gateway_rest_api.verus_api.id
  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = aws_lambda_function.verus_lambda.invoke_arn
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

resource "aws_api_gateway_method" "verus_api_post" {
//  authorization = "NONE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id        = aws_api_gateway_authorizer.verus_auth.id
  http_method = "POST"
  resource_id = aws_api_gateway_resource.verus_api.id
  rest_api_id = aws_api_gateway_rest_api.verus_api.id
  request_models = {
    "application/json" = aws_api_gateway_model.verus_api_post_model.name
  }
  request_validator_id = aws_api_gateway_request_validator.verus_api_post_validate_body.id
  authorization_scopes = aws_cognito_resource_server.verus_cognito_resource_server.scope_identifiers
}

resource "aws_api_gateway_integration" "verus_api_post" {
  http_method             = aws_api_gateway_method.verus_api_post.http_method
  resource_id             = aws_api_gateway_resource.verus_api.id
  rest_api_id             = aws_api_gateway_rest_api.verus_api.id
  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = aws_lambda_function.verus_lambda.invoke_arn
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

# DynamoDB config
resource "aws_dynamodb_table" "verus_stakes_txids_table" {
  name           = "verus_stakes_txids_table-${random_id.name.hex}"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "tx_id"
  attribute {
    name = "tx_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "verus_stakes_values_table" {
  name           = "verus_stakes_values_table-${random_id.name.hex}"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "ts_id"
  attribute {
    name = "ts_id"
    type = "S"
  }
}

# Data config
data "archive_file" "lambda_zip" {
  type             = "zip"
  source_file      = "${path.module}/../lambda_function.py"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_function_payload.zip"
}

data "aws_iam_policy_document" "verus_role_inline_policy_sns" {
  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.verus_topic.arn]
  }
}

data "aws_iam_policy_document" "verus_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "verus_role_inline_policy_dynamodb" {
  statement {
    sid       = "PutItemToVerusStakesTxidsTable"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.verus_stakes_txids_table.arn]
  }
  statement {
    sid       = "PutGetUpdateItemIoVerusStakesValuesTable"
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.verus_stakes_values_table.arn]
  }
}

data "aws_iam_policy_document" "verus_api_resource_ip_limit_policy" {
  statement {
    actions   = ["execute-api:Invoke"]
    resources = ["execute-api:/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "IpAddress"
      variable = "aws:SourceIp"

      values = [
        var.wallet_ip
      ]
    }
  }
}

data "aws_caller_identity" "current_aws_account" {}
