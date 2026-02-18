variable "instance_name" {
  description = "Name for this instance"
  type        = string
}

variable "instance_id" {
  description = "EC2 instance ID"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "websocket_url" {
  description = "WebSocket URL for the application"
  type        = string
}
