# DynamoDB config
resource "aws_dynamodb_table" "verus_stakes_txids_table" {
  name           = "${local.name_prefix}-stakes-txids-table-${random_id.name.hex}"
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
  name           = "${local.name_prefix}-stakes-values-table-${random_id.name.hex}"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "ts_id"
  attribute {
    name = "ts_id"
    type = "S"
  }
}