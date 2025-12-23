# S3 Buckets para PDFs, Frontend y Lambda Code

# Bucket para código de Lambda
resource "aws_s3_bucket" "lambda_code" {
  bucket = "${var.project_name}-lambda-code-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-lambda-code-${var.environment}"
  }
}

resource "aws_s3_bucket_versioning" "lambda_code" {
  bucket = aws_s3_bucket.lambda_code.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Bucket para PDFs
resource "aws_s3_bucket" "pdfs" {
  bucket = "${var.project_name}-pdfs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-pdfs-${var.environment}"
  }
}

resource "aws_s3_bucket_versioning" "pdfs" {
  bucket = aws_s3_bucket.pdfs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "pdfs" {
  bucket = aws_s3_bucket.pdfs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "pdfs" {
  bucket = aws_s3_bucket.pdfs.id

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# CORS configuration para permitir uploads directos desde el navegador
resource "aws_s3_bucket_cors_configuration" "pdfs" {
  bucket = aws_s3_bucket.pdfs.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET", "HEAD"]
    allowed_origins = [
      "https://${aws_cloudfront_distribution.frontend.domain_name}",
      "http://localhost:8000",
      "http://127.0.0.1:8000"
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# Bucket para Frontend
resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project_name}-frontend-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-frontend-${var.environment}"
  }
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# CloudFront Origin Access Identity (OAI) - No requiere política pública
resource "aws_cloudfront_origin_access_identity" "frontend" {
  comment = "OAI para ${var.project_name}-frontend-${var.environment}"
}

# Política de bucket para CloudFront OAI (no requiere desbloquear acceso público)
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  depends_on = [aws_cloudfront_origin_access_identity.frontend]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.frontend.iam_arn
        }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}

# CloudFront Distribution para Frontend
resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.frontend.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.frontend.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "${var.project_name}-frontend-${var.environment}"
  }
}

