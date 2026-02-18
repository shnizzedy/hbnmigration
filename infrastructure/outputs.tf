output "instance_id" {
  description = "Current EC2 instance ID"
  value       = local.instance_id
}

output "s3_bucket_iceberg" {
  description = "S3 bucket for Iceberg data"
  value       = aws_s3_bucket.iceberg_data.id
}

output "s3_bucket_config" {
  description = "S3 bucket for configuration files"
  value       = aws_s3_bucket.config.id
}

output "iceberg_warehouse" {
  description = "Iceberg warehouse location"
  value       = "s3://${aws_s3_bucket.iceberg_data.id}/warehouse"
}

output "service_status_commands" {
  description = "Commands to check service status"
  value       = <<-EOT
    # Check service status:
    sudo systemctl status websocket-monitor.service
    sudo systemctl status api-jobs.service

    # View logs:
    sudo journalctl -u websocket-monitor.service -f
    sudo journalctl -u api-jobs.service -f

    # Or check log files:
    tail -f /var/log/app/websocket-monitor.log
    tail -f /var/log/app/api-jobs.log
  EOT
}

output "update_services_command" {
  description = "Command to update services after code changes"
  value       = <<-EOT
    # After editing templates/ and running 'terraform apply':

    # Restart services:
    sudo systemctl restart websocket-monitor.service
    sudo systemctl restart api-jobs.service

    # Check status:
    sudo systemctl status websocket-monitor.service
    sudo systemctl status api-jobs.service
  EOT
}
