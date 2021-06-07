output "api_url" {
  description = "Verus API URL"
  value       = "${aws_api_gateway_stage.verus_api.invoke_url}/${aws_api_gateway_resource.verus_api.path_part}"
}