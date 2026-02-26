# main.tf
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
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3"
    }
  }
}

data "external" "current_user" {
  program = ["bash", "-c", <<-EOF
    echo '{"user":"'$${SUDO_USER:-$(whoami)}'"}'
  EOF
  ]
}

locals {
  current_user = data.external.current_user.result.user
  instance_id  = var.instance_id
}

# Generate setup script from template
locals {
  setup_script_content = templatefile("${path.module}/templates/setup_services.sh.tpl", {
    AWS_REGION    = var.aws_region
    ENVIRONMENT   = var.environment
    WEBSOCKET_URL = var.websocket_url
    VENV_PATH     = var.venv_path
    INSTANCE_NAME = var.instance_name
    USER          = local.current_user
    USER_GROUP    = var.user_group
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

# ============================================================================
# Ripple to REDCap Sync Timer
# ============================================================================

# Generate systemd service file
resource "local_file" "ripple_sync_service" {
  content = templatefile("${path.module}/templates/ripple-sync.service.tpl", {
    USER        = local.current_user
    USER_GROUP  = var.user_group
    VENV_PATH   = var.venv_path
    ENVIRONMENT = var.environment
  })
  filename        = "${path.module}/generated_ripple-sync.service"
  file_permission = "0644"
}

# Generate systemd timer file
resource "local_file" "ripple_sync_timer" {
  content = templatefile("${path.module}/templates/ripple-sync.timer.tpl", {
    INTERVAL_MINUTES = var.ripple_sync_interval_minutes
  })
  filename        = "${path.module}/generated_ripple-sync.timer"
  file_permission = "0644"
}

# Install and enable systemd service and timer
resource "null_resource" "install_ripple_sync" {
  triggers = {
    service_hash = sha256(local_file.ripple_sync_service.content)
    timer_hash   = sha256(local_file.ripple_sync_timer.content)
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e

      # Copy service and timer files
      sudo cp ${local_file.ripple_sync_service.filename} /etc/systemd/system/ripple-sync.service
      sudo cp ${local_file.ripple_sync_timer.filename} /etc/systemd/system/ripple-sync.timer

      # Create log directory
      sudo mkdir -p /var/log/ripple-sync
      sudo chown ${local.current_user}:${var.user_group} /var/log/ripple-sync

      # Reload systemd
      sudo systemctl daemon-reload

      # Enable and start timer
      sudo systemctl enable ripple-sync.timer
      sudo systemctl restart ripple-sync.timer

      # Show status
      echo "Timer status:"
      sudo systemctl status ripple-sync.timer --no-pager || true
      echo ""
      echo "Next run times:"
      sudo systemctl list-timers ripple-sync.timer --no-pager || true
    EOT
  }

  depends_on = [
    local_file.ripple_sync_service,
    local_file.ripple_sync_timer,
    null_resource.setup_services
  ]
}

# Output timer status
output "ripple_sync_status" {
  value = "Run 'systemctl status ripple-sync.timer' to check status"
}
