resource "random_id" "name" {
  byte_length = 8
}

resource "random_string" "name" {
  length  = 8
  lower   = true
  special = false
  numeric = true
  upper   = false
}

resource "random_pet" "name" {
  length = 1
}
