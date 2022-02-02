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
  name_suffix = "${var.resource_tags["project"]}-${var.resource_tags["environment"]}"
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

# Data config
data "archive_file" "lambda_get_zip" {
  type             = "zip"
  source_file      = "${path.module}/../lambda_function_get.py"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_function_get_payload.zip"
}

data "archive_file" "lambda_post_zip" {
  type             = "zip"
  source_file      = "${path.module}/../lambda_function_post.py"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_function_post_payload.zip"
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

data "aws_iam_policy_document" "verus_role_inline_policy_dynamodb_post" {
  statement {
    sid       = "PutItemToVerusStakesTxidsTable"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.verus_stakes_txids_table.arn]
  }
  statement {
    sid       = "PutGetUpdateItemToVerusStakesValuesTable"
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.verus_stakes_values_table.arn]
  }
}

data "aws_iam_policy_document" "verus_role_inline_policy_dynamodb_get" {
  statement {
    sid       = "GetItemFromVerusStakesValuesTable"
    actions   = ["dynamodb:GetItem"]
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
