# IAM role config
resource "aws_iam_role" "verus_iam_role_for_lambda_post" {
  name                = "${local.name_prefix}-lambda-post-${random_id.name.hex}"
  assume_role_policy  = data.aws_iam_policy_document.verus_assume_role_policy.json
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  inline_policy {
    name   = "verus-lambda-sns-publish-inline"
    policy = data.aws_iam_policy_document.verus_role_inline_policy_sns.json
  }
  inline_policy {
    name   = "verus-lambda-dynamodb-post-inline"
    policy = data.aws_iam_policy_document.verus_role_inline_policy_dynamodb_post.json
  }
}

resource "aws_iam_role" "verus_iam_role_for_lambda_get" {
  name                = "${local.name_prefix}-lambda-get-${random_id.name.hex}"
  assume_role_policy  = data.aws_iam_policy_document.verus_assume_role_policy.json
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  inline_policy {
    name   = "verus-lambda-dynamodb-get-inline"
    policy = data.aws_iam_policy_document.verus_role_inline_policy_dynamodb_get.json
  }
}