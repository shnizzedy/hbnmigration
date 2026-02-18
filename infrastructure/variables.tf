variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_id" {
  description = "EC2 instance ID for self-reference"
  type        = string
}

variable "instance_name" {
  description = "Name of the EC2 instance/project"
  type        = string
  default     = "hbnmigration-vm"
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


variable "enable_session_manager" {
  description = "Enable AWS Systems Manager Session Manager"
  type        = bool
  default     = true
}
