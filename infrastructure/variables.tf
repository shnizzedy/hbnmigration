variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1e"
}

variable "instance_name" {
  description = "Name of the EC2 instance/project"
  type        = string
  default     = "monitoring-curious-vm"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "websocket_url" {
  description = "WebSocket URL to monitor"
  type        = string
  default     = "wss://api-v2.gettingcurious.com/alerts"
}
