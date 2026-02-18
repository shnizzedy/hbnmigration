# ============================================================================
# ICEBERG DATA BUCKET (for table data)
# ============================================================================

resource "aws_s3_bucket" "iceberg_data" {
  bucket = "${var.instance_name}-iceberg-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.instance_name}-iceberg"
    Environment = var.environment
    Purpose     = "Iceberg table storage"
  }
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "iceberg_data" {
  bucket = aws_s3_bucket.iceberg_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "iceberg_data" {
  bucket = aws_s3_bucket.iceberg_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "iceberg_data" {
  bucket = aws_s3_bucket.iceberg_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Enable access logging
resource "aws_s3_bucket_logging" "iceberg_data" {
  bucket = aws_s3_bucket.iceberg_data.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "iceberg-access-logs/"
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "iceberg_data" {
  bucket = aws_s3_bucket.iceberg_data.id

  rule {
    id     = "archive-old-data"
    status = "Enabled"

    filter { prefix = "" }

    # Move data older than 90 days to cheaper storage
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    # Move data older than 180 days to Glacier
    transition {
      days          = 180
      storage_class = "GLACIER_IR"
    }

    # Clean up old versions after 30 days
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "clean-incomplete-multipart-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Bucket policy - layered security
resource "aws_s3_bucket_policy" "iceberg_data" {
  bucket = aws_s3_bucket.iceberg_data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEC2InstanceRoleAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.instance_role.arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:ListBucketMultipartUploads",
          "s3:AbortMultipartUpload",
          "s3:ListMultipartUploadParts"
        ]
        Resource = [
          aws_s3_bucket.iceberg_data.arn,
          "${aws_s3_bucket.iceberg_data.arn}/*"
        ]
      },
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.iceberg_data.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      },
      {
        Sid       = "RequireEncryptedTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.iceberg_data.arn,
          "${aws_s3_bucket.iceberg_data.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid       = "DenyAccessFromOutsideVPC"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.iceberg_data.arn,
          "${aws_s3_bucket.iceberg_data.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "aws:SourceVpce" = aws_vpc_endpoint.s3.id
          }
        }
      }
    ]
  })

  depends_on = [
    aws_s3_bucket_public_access_block.iceberg_data,
    aws_vpc_endpoint.s3
  ]
}

# ============================================================================
# CONFIG BUCKET (for application configuration and service files)
# ============================================================================

resource "aws_s3_bucket" "config" {
  bucket = "${var.instance_name}-config-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.instance_name}-config"
    Environment = var.environment
    Purpose     = "Application configuration and systemd services"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "config" {
  bucket = aws_s3_bucket.config.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Enable access logging
resource "aws_s3_bucket_logging" "config" {
  bucket = aws_s3_bucket.config.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "config-access-logs/"
}

# Bucket policy for config bucket
resource "aws_s3_bucket_policy" "config" {
  bucket = aws_s3_bucket.config.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEC2InstanceRoleRead"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.instance_role.arn
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.config.arn,
          "${aws_s3_bucket.config.arn}/*"
        ]
      },
      {
        Sid       = "RequireEncryptedTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.config.arn,
          "${aws_s3_bucket.config.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid       = "DenyAccessFromOutsideVPC"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.config.arn,
          "${aws_s3_bucket.config.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "aws:SourceVpce" = aws_vpc_endpoint.s3.id
          }
        }
      }
    ]
  })

  depends_on = [
    aws_s3_bucket_public_access_block.config,
    aws_vpc_endpoint.s3
  ]
}

# ============================================================================
# LOGS BUCKET (for S3 access logs)
# ============================================================================

resource "aws_s3_bucket" "logs" {
  bucket = "${var.instance_name}-logs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.instance_name}-logs"
    Environment = var.environment
    Purpose     = "S3 access logs"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Lifecycle policy to expire old logs
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    filter { prefix = "" }
    expiration {
      days = 90 # Keep logs for 90 days
    }

    # Add this block to abort incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Bucket policy for logging bucket (allows S3 logging service)
resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ServerAccessLogsPolicy"
        Effect = "Allow"
        Principal = {
          Service = "logging.s3.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.logs.arn}/*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid       = "RequireEncryptedTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.logs.arn,
          "${aws_s3_bucket.logs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.logs]
}

# ============================================================================
# VPC ENDPOINT (keeps S3 traffic within AWS network)
# ============================================================================

# Get default VPC
data "aws_vpc" "default" {
  default = true
}

# Get default route table
data "aws_route_table" "default" {
  vpc_id = data.aws_vpc.default.id

  filter {
    name   = "association.main"
    values = ["true"]
  }
}

# VPC Endpoint for S3 (Gateway type - no additional cost!)
resource "aws_vpc_endpoint" "s3" {
  vpc_id          = data.aws_vpc.default.id
  service_name    = "com.amazonaws.${var.aws_region}.s3"
  route_table_ids = [data.aws_route_table.default.id]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:*"
        Resource  = "*"
      }
    ]
  })

  tags = {
    Name        = "${var.instance_name}-s3-endpoint"
    Environment = var.environment
  }
}

# ============================================================================
# UPLOAD SYSTEMD SERVICE FILES
# ============================================================================

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

  server_side_encryption = "AES256"

  tags = {
    Name = "websocket-monitor.service"
  }

  depends_on = [
    aws_s3_bucket_public_access_block.config,
    aws_s3_bucket_server_side_encryption_configuration.config
  ]
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

  server_side_encryption = "AES256"

  tags = {
    Name = "api-jobs.service"
  }

  depends_on = [
    aws_s3_bucket_public_access_block.config,
    aws_s3_bucket_server_side_encryption_configuration.config
  ]
}
