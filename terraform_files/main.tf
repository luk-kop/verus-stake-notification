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
  profile = "default"
  region  = "eu-west-1"
}

resource "aws_sns_topic" "verus_topic" {
  name = "verus-topic-2"
  tags = {
    Project = "verus-notification"
  }
}

resource "aws_sns_topic_subscription" "verus_topic_subscription" {
  topic_arn = aws_sns_topic.verus_topic.arn
  protocol  = "email"
  endpoint  = var.sns_topic_subscription_email
}