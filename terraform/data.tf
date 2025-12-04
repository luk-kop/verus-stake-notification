data "archive_file" "lambda_get_zip" {
  type             = "zip"
  source_file      = "${path.module}/../lambda_functions/lambda_function_get.py"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_function_get_payload.zip"
}

data "archive_file" "lambda_post_zip" {
  type             = "zip"
  source_file      = "${path.module}/../lambda_functions/lambda_function_post.py"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_function_post_payload.zip"
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
