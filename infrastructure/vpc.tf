# Update S3 bucket policy to only allow VPC endpoint access
resource "aws_s3_bucket_policy" "iceberg_data_policy" {
  bucket = aws_s3_bucket.iceberg_data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEC2InstanceAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.instance_role.arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.iceberg_data.arn,
          "${aws_s3_bucket.iceberg_data.arn}/*"
        ]
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
      }
    ]
  })
}
