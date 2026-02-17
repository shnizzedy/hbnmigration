# HBN Migration VM

Infrastructure and code for Healthy Brain Network data migration.

## Prerequisites

### On EC2 Instance

The setup script installs all required tools:

- **Infrastructure:**
  - Terraform >= 1.7.0
  - AWS CLI v2

- **Linting:**
  - ShellCheck (bash linting)
  - ruff (Python linting)
  - mypy (Python type checking)
  - pre-commit (git hook framework)

## Quick Start

- SSH into your EC2 instance
- Clone or copy your project
- One-time setup: Install Terraform

   ```BASH
   ./setup_terraform.sh
   ```

- Configure

   ```BASH
   cp infrastructure/terraform.tfvars.example infrastructure/terraform.tfvars
   ```

- Lint

   ```BASH
   # Show help
   ./infrastructure/lint help

   # Lint Python templates
   ./infrastructure/lint lint-python

   # Lint Bash templates
   ./infrastructure/lint lint-bash

   # Clean up
   ./infrastructure/lint clean

   # Lint everything and clean up
   ./infrastructure/lint lint-all
   ```

- Deploy

   ```BASH
   terraform init
   terraform validate
   terraform plan
   terraform apply
   ```
