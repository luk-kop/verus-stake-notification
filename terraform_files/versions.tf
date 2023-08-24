terraform {
  //  required_version = "~> 1.0.0"
  required_version = ">= 1.0.0"

  backend "s3" {
    key = "verus-notification/terraform.tfstate"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4.0"
    }
  }
}
