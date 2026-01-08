# Lambda Worker para procesar PDFs desde SQS

# IAM Role para Worker Lambda
resource "aws_iam_role" "lambda_worker" {
  name = "${var.project_name}-lambda-worker-${var.environment}"

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

# IAM Policy para Worker Lambda
resource "aws_iam_role_policy" "lambda_worker_policy" {
  name = "${var.project_name}-lambda-worker-policy-${var.environment}"
  role = aws_iam_role.lambda_worker.id

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
          "s3:GetObject"
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
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = aws_sqs_queue.pdf_processing.arn
      }
    ]
  })
}

# IAM Policy Attachment para VPC access
resource "aws_iam_role_policy_attachment" "lambda_worker_vpc" {
  role       = aws_iam_role.lambda_worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Subir código de Worker Lambda a S3
resource "aws_s3_object" "lambda_worker_code" {
  bucket = aws_s3_bucket.lambda_code.id
  key    = "lambda_worker.zip"
  source = "${path.module}/../../lambda_worker.zip"
  etag   = filemd5("${path.module}/../../lambda_worker.zip")
  
  # Forzar actualización cuando cambie el código
  lifecycle {
    create_before_destroy = true
  }
}

# Lambda Worker Function
resource "aws_lambda_function" "pdf_worker" {
  function_name    = "${var.project_name}-worker-${var.environment}"
  role            = aws_iam_role.lambda_worker.arn
  handler         = "lambda_worker.handler"
  runtime         = "python3.11"
  timeout         = 900  # 15 minutos (máximo)
  memory_size     = 1024  # 1GB (suficiente para PDFs)

  s3_bucket = aws_s3_bucket.lambda_code.id
  s3_key    = aws_s3_object.lambda_worker_code.key
  source_code_hash = base64sha256("${aws_s3_object.lambda_worker_code.etag}-${aws_s3_object.lambda_worker_code.version_id}")

  environment {
    variables = {
      DATABASE_URL      = "postgresql://${aws_rds_cluster.main.master_username}:${aws_rds_cluster.main.master_password}@${aws_rds_cluster.main.endpoint}/${aws_rds_cluster.main.database_name}"
      CROSSREF_EMAIL    = var.crossref_email
      USE_GROBID        = var.grobid_deployment == "ec2" ? "true" : "false"
      GROBID_URL        = var.grobid_deployment == "ec2" ? "http://${aws_instance.grobid[0].private_ip}:8070" : ""
      GROBID_TIMEOUT    = "120"
      S3_BUCKET         = aws_s3_bucket.pdfs.bucket
      USE_CLAUDE        = "true"
      CLAUDE_MODEL      = "anthropic.claude-3-haiku-20240307-v1:0"
      CLAUDE_MAX_TOKENS = "2000"
      CLAUDE_FOR_REPORTS = "true"
      CLAUDE_FOR_THESIS = "true"
      CLAUDE_FOR_BOOKS  = "true"
      CLAUDE_AS_VALIDATOR = "false"
    }
  }

  vpc_config {
    subnet_ids         = local.private_subnets_final
    security_group_ids = [aws_security_group.lambda.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_worker_vpc,
    aws_cloudwatch_log_group.lambda_worker,
    aws_s3_object.lambda_worker_code,
    aws_sqs_queue.pdf_processing  # Asegurar que SQS existe antes de Lambda
  ]
}

# CloudWatch Log Group para Worker
resource "aws_cloudwatch_log_group" "lambda_worker" {
  name              = "/aws/lambda/${var.project_name}-worker-${var.environment}"
  retention_in_days  = 7
}

# Event Source Mapping: SQS → Lambda Worker
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.pdf_processing.arn
  function_name    = aws_lambda_function.pdf_worker.arn
  batch_size       = 1  # Procesar un mensaje a la vez
  maximum_batching_window_in_seconds = 0  # Procesar inmediatamente
}

# Permiso para que SQS invoque Lambda Worker
resource "aws_lambda_permission" "allow_sqs" {
  statement_id  = "AllowExecutionFromSQS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pdf_worker.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.pdf_processing.arn
}
