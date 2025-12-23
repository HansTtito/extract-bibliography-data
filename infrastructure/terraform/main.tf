# Configuración principal de Terraform para despliegue en AWS

terraform {
  required_version = ">= 1.0"
  
  # Opcional: Backend para estado remoto (S3)
  # backend "s3" {
  #   bucket = "bibliografia-terraform-state"
  #   key    = "terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "bibliografia-extractor"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Variables están definidas en variables.tf

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Outputs están definidos en outputs.tf

