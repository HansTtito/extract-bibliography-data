# Outputs de Terraform

output "api_gateway_url" {
  description = "URL del API Gateway"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
}

output "frontend_url" {
  description = "URL del frontend (CloudFront)"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "frontend_bucket" {
  description = "Nombre del bucket S3 para frontend"
  value       = aws_s3_bucket.frontend.bucket
}

output "pdfs_bucket" {
  description = "Nombre del bucket S3 para PDFs"
  value       = aws_s3_bucket.pdfs.bucket
}

output "rds_endpoint" {
  description = "Endpoint de Aurora PostgreSQL"
  value       = aws_rds_cluster.main.endpoint
  sensitive   = true
}

output "rds_password" {
  description = "Password de RDS (guardar de forma segura)"
  value       = random_password.db_password.result
  sensitive   = true
}

output "grobid_url" {
  description = "URL de GROBID"
  value       = var.grobid_deployment == "fargate" ? "http://${aws_lb.grobid[0].dns_name}:8070" : "http://${aws_instance.grobid[0].public_ip}:8070"
}

output "grobid_alb_dns" {
  description = "DNS del ALB de GROBID (solo Fargate)"
  value       = var.grobid_deployment == "fargate" ? aws_lb.grobid[0].dns_name : null
}

output "grobid_ec2_ip" {
  description = "IP pública de GROBID EC2 (solo EC2)"
  value       = var.grobid_deployment == "ec2" ? aws_instance.grobid[0].public_ip : null
}

