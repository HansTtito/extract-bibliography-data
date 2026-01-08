# Configuración de Lambda Function para FastAPI

# IAM Role para Lambda
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy para Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy-${var.environment}"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.pdfs.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "rds:DescribeDBInstances"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl"
        ]
        Resource = aws_sqs_queue.pdf_processing.arn
      }
    ]
  })
}

# Subir código de Lambda a S3
resource "aws_s3_object" "lambda_code" {
  bucket = aws_s3_bucket.lambda_code.id
  key    = "lambda_function.zip"
  source = "${path.module}/../../lambda_function.zip"
  etag   = filemd5("${path.module}/../../lambda_function.zip")
}

# Lambda Function
resource "aws_lambda_function" "main" {
  function_name    = "${var.project_name}-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "lambda_handler.handler"
  runtime         = "python3.11"
  timeout         = 900  # 15 minutos (máximo)
  memory_size     = 1024  # 1GB (suficiente para PDFs)

  s3_bucket = aws_s3_bucket.lambda_code.id
  s3_key    = aws_s3_object.lambda_code.key
  source_code_hash = base64sha256("${aws_s3_object.lambda_code.etag}-${aws_s3_object.lambda_code.version_id}")

  environment {
    variables = {
      DATABASE_URL      = "postgresql://${aws_rds_cluster.main.master_username}:${aws_rds_cluster.main.master_password}@${aws_rds_cluster.main.endpoint}/${aws_rds_cluster.main.database_name}"
      CROSSREF_EMAIL    = var.crossref_email
      USE_GROBID        = var.grobid_deployment == "ec2" ? "true" : "false"
      GROBID_URL        = var.grobid_deployment == "ec2" ? "http://${aws_instance.grobid[0].private_ip}:8070" : ""
      GROBID_TIMEOUT    = "120"
      MAX_PDF_SIZE_MB   = "10"
      MAX_BATCH_COUNT   = "10"
      MAX_BATCH_TOTAL_MB = "50"
      S3_BUCKET         = aws_s3_bucket.pdfs.bucket
      ALLOWED_ORIGINS   = "https://${aws_cloudfront_distribution.frontend.domain_name}"
      # Claude Configuration (AWS Bedrock)
      # Nota: AWS_REGION es automática en Lambda, no se puede establecer manualmente
      USE_CLAUDE        = "true"
      CLAUDE_MODEL      = "anthropic.claude-3-haiku-20240307-v1:0"
      CLAUDE_MAX_TOKENS = "2000"
      CLAUDE_FOR_REPORTS = "true"
      CLAUDE_FOR_THESIS = "true"
      CLAUDE_FOR_BOOKS  = "true"
      CLAUDE_AS_VALIDATOR = "false"
      PDF_PROCESSING_QUEUE_URL = aws_sqs_queue.pdf_processing.url
    }
  }

  vpc_config {
    subnet_ids         = local.private_subnets_final
    security_group_ids = [aws_security_group.lambda.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_cloudwatch_log_group.lambda,
    aws_s3_object.lambda_code,
    aws_sqs_queue.pdf_processing  # Asegurar que SQS existe antes de Lambda
  ]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}"
  retention_in_days = 7
}

# Security Group para Lambda (acceso a RDS y GROBID)
resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-lambda-sg-${var.environment}"
  description = "Security group para Lambda function"
  vpc_id      = local.vpc_id_final

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-lambda-sg-${var.environment}"
  }
}

# IAM Policy Attachment para VPC access
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Variable crossref_email está definida en variables.tf

# ===========================================
# LAMBDA DE EXPORTS (con pandas)
# ===========================================

# Subir código de Lambda de Exports a S3
resource "aws_s3_object" "lambda_export_code" {
  bucket = aws_s3_bucket.lambda_code.id
  key    = "lambda_function_export.zip"
  source = "${path.module}/../../lambda_function_export.zip"
  etag   = filemd5("${path.module}/../../lambda_function_export.zip")
}

# Lambda Function para Exports
resource "aws_lambda_function" "export" {
  function_name    = "${var.project_name}-export-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn  # Mismo role
  handler         = "lambda_handler_export.handler"
  runtime         = "python3.11"
  timeout         = 300  # 5 minutos (suficiente para exports)
  memory_size     = 512  # 512MB (menos que la principal)

  s3_bucket = aws_s3_bucket.lambda_code.id
  s3_key    = aws_s3_object.lambda_export_code.key
  source_code_hash = base64sha256("${aws_s3_object.lambda_export_code.etag}-${aws_s3_object.lambda_export_code.version_id}")

  environment {
    variables = {
      DATABASE_URL    = "postgresql://${aws_rds_cluster.main.master_username}:${aws_rds_cluster.main.master_password}@${aws_rds_cluster.main.endpoint}/${aws_rds_cluster.main.database_name}"
      ALLOWED_ORIGINS = "https://${aws_cloudfront_distribution.frontend.domain_name}"
    }
  }

  vpc_config {
    subnet_ids         = local.private_subnets_final
    security_group_ids = [aws_security_group.lambda.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_cloudwatch_log_group.lambda_export,
    aws_s3_object.lambda_export_code
  ]
}

# CloudWatch Log Group para Export Lambda
resource "aws_cloudwatch_log_group" "lambda_export" {
  name              = "/aws/lambda/${var.project_name}-export-${var.environment}"
  retention_in_days = 7
}

