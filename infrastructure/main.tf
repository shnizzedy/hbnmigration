terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
locals {
  instance_id = var.instance_id
}

# Get information about current instance
data "aws_instance" "self" {
  instance_id = var.instance_id
}

# Generate setup script from template
locals {
  setup_script_content = templatefile("${path.module}/templates/setup_services.sh.tpl", {
    S3_BUCKET     = aws_s3_bucket.iceberg_data.id
    CONFIG_BUCKET = aws_s3_bucket.config.id
    AWS_REGION    = var.aws_region
    ENVIRONMENT   = var.environment
    WEBSOCKET_URL = var.websocket_url
  })
}

# Write generated script to disk
resource "local_file" "setup_script" {
  content         = local.setup_script_content
  filename        = "${path.module}/generated_setup.sh"
  file_permission = "0755"
}

# Execute the generated script
resource "null_resource" "setup_services" {
  triggers = {
    # Re-run when script content changes
    script_hash = sha256(local.setup_script_content)
  }

  provisioner "local-exec" {
    command = "sudo ${local_file.setup_script.filename}"
  }

  depends_on = [
    local_file.setup_script,
    aws_s3_object.websocket_service,
    aws_s3_object.api_jobs_service
  ]
}
