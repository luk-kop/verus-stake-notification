variable "sns_email" {
  description = "SNS Topic subscription"
  type        = string
  default     = "test-user@example.com"
  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9_\\.-]){3,30}@([a-z0-9_\\.-]){1,30}\\.([a-z\\.]{2,8})$", var.sns_email))
    error_message = "The sns_email must be a valid email address."
  }

}

variable "resource_tags" {
  description = "Tags to set for all resources"
  type        = map(string)
  default = {
    project     = "verus-notification",
    environment = "dev"
  }
}

variable "profile" {
  description = "AWS profile used to deploy resources"
  type        = string
  default     = "default"
}

variable "region" {
  description = "AWS region in which resources will be deployed"
  type        = string
  default     = "eu-west-1"
}

variable "wallet_ip" {
  description = "Public ip address of working Verus wallet"
  type        = string
  default     = "0.0.0.0/0"
}

variable "cognito_pool_domain" {
  description = "Domain prefix for Cognito sign-in endpoint"
  type        = string
  default     = "verus-creds"
}