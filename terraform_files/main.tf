terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
}

provider "aws" {
  profile = var.profile
  region  = var.region
}

# SNS config
resource "aws_sns_topic" "verus_topic" {
  name = "verus-topic"
  tags = var.resource_tags
}

resource "aws_sns_topic_subscription" "verus_topic_subscription" {
  topic_arn = aws_sns_topic.verus_topic.arn
  protocol  = "email"
  endpoint  = var.sns_email
}

# IAM role config
resource "aws_iam_role" "verus_iam_role_for_lambda" {
  name                = "verus-lambda-to-sns"
  tags                = var.resource_tags
  assume_role_policy  = data.aws_iam_policy_document.verus_assume_role_policy.json
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  inline_policy {
    name   = "verus-lambda-sns-publish-inline"
    policy = data.aws_iam_policy_document.verus_role_inline_policy.json
  }
}

# Lambda config
resource "aws_lambda_function" "verus_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "verus-lambda-func"
  description      = "Publish a msg to SNS topic when new stake appears in Verus wallet."
  role             = aws_iam_role.verus_iam_role_for_lambda.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256(data.archive_file.lambda_zip.output_path)
  runtime          = "python3.8"
  environment {
    variables = {
      TOPIC_ARN = aws_sns_topic.verus_topic.arn
    }
  }
  tags = var.resource_tags
}

resource "aws_lambda_permission" "verus_api_lambda" {
  statement_id  = "allow-execution-from-apigateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verus_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current_aws_account.account_id}:${aws_api_gateway_rest_api.verus_api.id}/*/${aws_api_gateway_method.verus_api.http_method}${aws_api_gateway_resource.verus_api.path}"
}

# API Gateway config
resource "aws_api_gateway_rest_api" "verus_api" {
  name        = "verus-api-gateway"
  description = "Invoke Lambda function to publish a msg to SNS topic when new stake appears in Verus wallet."
  tags        = var.resource_tags
}

resource "aws_api_gateway_resource" "verus_api" {
  parent_id   = aws_api_gateway_rest_api.verus_api.root_resource_id
  path_part   = "stake"
  rest_api_id = aws_api_gateway_rest_api.verus_api.id

}

resource "aws_api_gateway_method" "verus_api" {
  authorization = "NONE"
  http_method   = "GET"
  resource_id   = aws_api_gateway_resource.verus_api.id
  rest_api_id   = aws_api_gateway_rest_api.verus_api.id
}

resource "aws_api_gateway_integration" "verus_api" {
  http_method             = aws_api_gateway_method.verus_api.http_method
  resource_id             = aws_api_gateway_resource.verus_api.id
  rest_api_id             = aws_api_gateway_rest_api.verus_api.id
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.verus_lambda.invoke_arn
}

resource "aws_api_gateway_deployment" "verus_api" {
  rest_api_id = aws_api_gateway_rest_api.verus_api.id
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.verus_api.id,
      aws_api_gateway_method.verus_api.id,
      aws_api_gateway_integration.verus_api.id,
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

# DynamoDB
resource "aws_dynamodb_table" "verus_stakes_table" {
  name           = "VerusStakes"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "stake_id"

  attribute {
    name = "stake_id"
    type = "S"
  }

  tags        = var.resource_tags
}


# Data config
data "archive_file" "lambda_zip" {
  type             = "zip"
  source_file      = "${path.module}/../lambda_function.py"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_function_payload.zip"
}

data "aws_iam_policy_document" "verus_role_inline_policy" {
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
