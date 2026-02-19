terraform {
  required_version = ">= 1.0"
  required_providers {
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

locals {
  instance_id = var.instance_id
}

# Generate setup script from template
locals {
  setup_script_content = templatefile("${path.module}/templates/setup_services.sh.tpl", {
    AWS_REGION    = var.aws_region
    ENVIRONMENT   = var.environment
    WEBSOCKET_URL = var.websocket_url
    VENV_PATH     = var.venv_path
    INSTANCE_NAME = var.instance_name
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
    command = "sudo -E bash ${local_file.setup_script.filename}"
  }

  depends_on = [
    local_file.setup_script
  ]
}
