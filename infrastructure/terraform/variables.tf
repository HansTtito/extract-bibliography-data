# Variables compartidas (movidas desde main.tf para mejor organización)

variable "aws_region" {
  description = "Región de AWS"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Ambiente (sandbox, prod)"
  type        = string
  default     = "sandbox"
}

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "bibliografia"
}

variable "grobid_deployment" {
  description = "Tipo de despliegue de GROBID: ec2 o fargate"
  type        = string
  default     = "ec2"
  
  validation {
    condition     = contains(["ec2", "fargate"], var.grobid_deployment)
    error_message = "grobid_deployment debe ser 'ec2' o 'fargate'"
  }
}

variable "vpc_id" {
  description = "ID de VPC existente (opcional, se crea una nueva si no se especifica)"
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "CIDR block para VPC (si se crea nueva)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "Lista de subnets privadas (para ECS/RDS)"
  type        = list(string)
  default     = []
}

variable "public_subnets" {
  description = "Lista de subnets públicas (para ALB)"
  type        = list(string)
  default     = []
}

variable "crossref_email" {
  description = "Email para CrossRef API"
  type        = string
  default     = ""
}

variable "key_pair_name" {
  description = "Nombre del key pair para EC2 (opcional)"
  type        = string
  default     = ""
}

