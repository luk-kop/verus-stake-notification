# Lambda config
resource "aws_lambda_function" "verus_lambda_get" {
  filename         = data.archive_file.lambda_get_zip.output_path
  function_name    = "verus-lambda-func-get-${random_id.name.hex}"
  description      = "Returns the number of stakes and their total value for the selected time period."
  role             = aws_iam_role.verus_iam_role_for_lambda_get.arn
  handler          = "lambda_function_get.lambda_handler_get"
  source_code_hash = filebase64sha256(data.archive_file.lambda_get_zip.output_path)
  runtime          = "python3.8"
  environment {
    variables = {
      DYNAMODB_VALUES_NAME = aws_dynamodb_table.verus_stakes_values_table.id
    }
  }
}

resource "aws_lambda_function" "verus_lambda_post" {
  filename         = data.archive_file.lambda_post_zip.output_path
  function_name    = "verus-lambda-func-post-${random_id.name.hex}"
  description      = "Put data to DynamDB and publish a msg to SNS topic when new stake appears in Verus wallet."
  role             = aws_iam_role.verus_iam_role_for_lambda_post.arn
  handler          = "lambda_function_post.lambda_handler_post"
  source_code_hash = filebase64sha256(data.archive_file.lambda_post_zip.output_path)
  runtime          = "python3.8"
  environment {
    variables = {
      TOPIC_ARN            = aws_sns_topic.verus_topic.arn
      DYNAMODB_TXIDS_NAME  = aws_dynamodb_table.verus_stakes_txids_table.id
      DYNAMODB_VALUES_NAME = aws_dynamodb_table.verus_stakes_values_table.id
    }
  }
}

resource "aws_lambda_permission" "verus_api_lambda_get" {
  statement_id  = "allow-execution-from-apigateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verus_lambda_get.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.verus_api.execution_arn}/*/*/*"
  //  source_arn    = "${aws_api_gateway_rest_api.verus_api.execution_arn}/*/${aws_api_gateway_method.verus_api_get.http_method}${aws_api_gateway_resource.verus_api.path}"
}

resource "aws_lambda_permission" "verus_api_lambda_post" {
  statement_id  = "allow-execution-from-apigateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verus_lambda_post.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.verus_api.execution_arn}/*/*/*"
  //  source_arn    = "${aws_api_gateway_rest_api.verus_api.execution_arn}/*/${aws_api_gateway_method.verus_api_post.http_method}${aws_api_gateway_resource.verus_api.path}"
}