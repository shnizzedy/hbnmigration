# IAM Role for this EC2 Instance
resource "aws_iam_role" "instance_role" {
  name = "${var.instance_name}-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.instance_name}-role"
    Environment = var.environment
  }
}

# IAM Policy for S3 and Glue (for Iceberg)
resource "aws_iam_role_policy" "iceberg_policy" {
  name = "${var.instance_name}-iceberg-policy"
  role = aws_iam_role.instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
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
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:CreateDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:DeleteTable",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:CreatePartition",
          "glue:UpdatePartition",
          "glue:DeletePartition",
          "glue:BatchCreatePartition",
          "glue:BatchDeletePartition"
        ]
        Resource = [
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/hbnmigration",
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/hbnmigration/*"
        ]
      }
    ]
  })
}

# IAM Policy for reading config bucket
resource "aws_iam_role_policy" "config_policy" {
  name = "${var.instance_name}-config-policy"
  role = aws_iam_role.instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.config.arn,
          "${aws_s3_bucket.config.arn}/*"
        ]
      }
    ]
  })
}

# Instance Profile
resource "aws_iam_instance_profile" "instance_profile" {
  name = "${var.instance_name}-profile-${var.environment}"
  role = aws_iam_role.instance_role.name
}

# Output the IAM instance profile ARN for manual attachment
output "instance_profile_arn" {
  description = "IAM instance profile ARN"
  value       = aws_iam_instance_profile.instance_profile.arn
}

output "attach_iam_command" {
  description = "Command to attach IAM role to this instance"
  value       = "aws ec2 associate-iam-instance-profile --instance-id ${local.instance_id} --iam-instance-profile Name=${aws_iam_instance_profile.instance_profile.name}"
}

# Policy for Systems Manager
resource "aws_iam_role_policy" "ssm_policy" {
  count = var.enable_session_manager ? 1 : 0

  name = "${var.instance_name}-ssm-policy"
  role = aws_iam_role.instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2messages:GetMessages"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "terraform_ec2_permissions" {
  name = "terraform-ec2-permissions"
  role = "AmazonSSMRoleForInstancesQuickSetup"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# Add this data source if it doesn't exist
data "aws_caller_identity" "current" {}
