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
  region  = "eu-west-1"
}

# SNS config
resource "aws_sns_topic" "verus_topic" {
  name = "verus-topic-2"
  tags = var.resource_tags
}

resource "aws_sns_topic_subscription" "verus_topic_subscription" {
  topic_arn = aws_sns_topic.verus_topic.arn
  protocol  = "email"
  endpoint  = var.sns_email
}

# IAM role config
resource "aws_iam_role" "verus_iam_role_for_lambda" {
  name                = "verus-lambda-to-sns-2"
  tags                = var.resource_tags
  assume_role_policy  = data.aws_iam_policy_document.verus_assume_role_policy.json
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  inline_policy {
    name   = "verus-lambda-sns-publish-inline-2"
    policy = data.aws_iam_policy_document.verus_role_inline_policy.json
  }
}

# Lambda config
resource "aws_lambda_function" "verus_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "verus-lambda-func-2"
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