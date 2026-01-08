# SQS Queue para procesamiento asíncrono de PDFs

# Dead Letter Queue (DLQ)
resource "aws_sqs_queue" "pdf_processing_dlq" {
  name                      = "${var.project_name}-pdf-processing-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 días
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Cola principal de procesamiento
resource "aws_sqs_queue" "pdf_processing" {
  name                      = "${var.project_name}-pdf-processing-${var.environment}"
  message_retention_seconds = 1209600  # 14 días
  visibility_timeout_seconds = 900      # 15 minutos (mismo que Lambda timeout)
  receive_wait_time_seconds  = 0       # Short polling (más rápido)
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.pdf_processing_dlq.arn
    maxReceiveCount     = 3
  })
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Outputs
output "pdf_processing_queue_url" {
  value       = aws_sqs_queue.pdf_processing.url
  description = "URL de la cola SQS para procesamiento de PDFs"
}

output "pdf_processing_queue_arn" {
  value       = aws_sqs_queue.pdf_processing.arn
  description = "ARN de la cola SQS para procesamiento de PDFs"
}
