output "instance_id" {
  description = "EC2 Instance ID"
  value       = local.instance_id
}

output "setup_script_path" {
  description = "Path to generated setup script"
  value       = local_file.setup_script.filename
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}
