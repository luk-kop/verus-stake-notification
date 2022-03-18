# SNS config
resource "aws_sns_topic" "verus_topic" {
  name = "${local.name_prefix}-topic-${random_id.name.hex}"
}

resource "aws_sns_topic_subscription" "verus_topic_subscription" {
  topic_arn = aws_sns_topic.verus_topic.arn
  protocol  = "email"
  endpoint  = var.sns_email
}