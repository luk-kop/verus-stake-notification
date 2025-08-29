resource "aws_iam_role" "verus_iam_role_for_lambda_post" {
  name               = "${local.name_prefix}-lambda-post-${random_id.name.hex}"
  assume_role_policy = data.aws_iam_policy_document.verus_assume_role_policy.json
}

resource "aws_iam_role_policy_attachment" "verus_iam_role_for_lambda_post_attach" {
  role       = aws_iam_role.verus_iam_role_for_lambda_post.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "verus_role_inline_policy_sns" {
  name = "verus-lambda-sns-publish-inline"
  role = aws_iam_role.verus_iam_role_for_lambda_post.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sns:Publish",
        ]
        Effect   = "Allow"
        Resource = aws_sns_topic.verus_topic.arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "verus_role_inline_policy_dynamodb_post" {
  name = "verus-lambda-dynamodb-post-inline"
  role = aws_iam_role.verus_iam_role_for_lambda_post.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "PutItemToVerusStakesTxidsTable"
        Action = [
          "dynamodb:PutItem",
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.verus_stakes_txids_table.arn
      },
      {
        Sid = "PutGetUpdateItemToVerusStakesValuesTable"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.verus_stakes_values_table.arn
      }
    ]
  })
}

resource "aws_iam_role" "verus_iam_role_for_lambda_get" {
  name               = "${local.name_prefix}-lambda-get-${random_id.name.hex}"
  assume_role_policy = data.aws_iam_policy_document.verus_assume_role_policy.json
}

resource "aws_iam_role_policy_attachment" "verus_iam_role_for_lambda_get_attach" {
  role       = aws_iam_role.verus_iam_role_for_lambda_get.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "verus_role_inline_policy_dynamodb_get" {
  name = "verus-lambda-dynamodb-get-inline"
  role = aws_iam_role.verus_iam_role_for_lambda_get.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "GetItemFromVerusStakesValuesTable"
        Action = [
          "dynamodb:GetItem",
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.verus_stakes_values_table.arn
      },
    ]
  })
}
