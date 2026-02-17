# Get current AWS account ID
data "aws_caller_identity" "current" {}

# S3 Bucket for Iceberg data
resource "aws_s3_bucket" "iceberg_data" {
  bucket = "${var.instance_name}-iceberg-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.instance_name}-iceberg"
    Environment = var.environment
    Purpose     = "Iceberg table storage"
  }
}

resource "aws_s3_bucket_versioning" "iceberg_data" {
  bucket = aws_s3_bucket.iceberg_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "iceberg_data" {
  bucket = aws_s3_bucket.iceberg_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket for configuration files
resource "aws_s3_bucket" "config" {
  bucket = "${var.instance_name}-config-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.instance_name}-config"
    Environment = var.environment
    Purpose     = "Application configuration and systemd services"
  }
}

resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket = aws_s3_bucket.config.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload systemd service files (rendered from templates)
resource "aws_s3_object" "websocket_service" {
  bucket = aws_s3_bucket.config.id
  key    = "websocket-monitor.service"
  content = templatefile("${path.module}/templates/websocket-monitor.service.tpl", {
    S3_BUCKET     = aws_s3_bucket.iceberg_data.id
    AWS_REGION    = var.aws_region
    WEBSOCKET_URL = var.websocket_url
  })
  etag = md5(templatefile("${path.module}/templates/websocket-monitor.service.tpl", {
    S3_BUCKET     = aws_s3_bucket.iceberg_data.id
    AWS_REGION    = var.aws_region
    WEBSOCKET_URL = var.websocket_url
  }))

  tags = {
    Name = "websocket-monitor.service"
  }
}

resource "aws_s3_object" "api_jobs_service" {
  bucket = aws_s3_bucket.config.id
  key    = "api-jobs.service"
  content = templatefile("${path.module}/templates/api-jobs.service.tpl", {
    S3_BUCKET  = aws_s3_bucket.iceberg_data.id
    AWS_REGION = var.aws_region
  })
  etag = md5(templatefile("${path.module}/templates/api-jobs.service.tpl", {
    S3_BUCKET  = aws_s3_bucket.iceberg_data.id
    AWS_REGION = var.aws_region
  }))

  tags = {
    Name = "api-jobs.service"
  }
}
