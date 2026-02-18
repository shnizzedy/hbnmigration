# IAM policy for users to connect via Session Manager
data "aws_iam_policy_document" "ssm_user_access" {
  statement {
    effect = "Allow"
    actions = [
      "ssm:StartSession",
      "ssm:TerminateSession",
      "ssm:ResumeSession",
      "ssm:DescribeSessions",
      "ssm:GetConnectionStatus"
    ]
    resources = [
      "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:instance/${local.instance_id}",
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:session/$${aws:username}-*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances"
    ]
    resources = ["*"]
  }
}

# Output the policy for manual attachment to IAM users
output "ssm_user_policy" {
  description = "IAM policy for users to connect via Session Manager"
  value       = data.aws_iam_policy_document.ssm_user_access.json
}
