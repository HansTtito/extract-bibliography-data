# RDS PostgreSQL Database

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-${var.environment}"
  subnet_ids = local.private_subnets_final

  tags = {
    Name = "${var.project_name}-db-subnet-${var.environment}"
  }
}

# Security Group para RDS
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg-${var.environment}"
  description = "Security group para RDS PostgreSQL"
  vpc_id      = local.vpc_id_final

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "PostgreSQL desde Lambda"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg-${var.environment}"
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier             = "${var.project_name}-db-${var.environment}"
  engine                 = "postgres"
  engine_version         = "15.10"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  max_allocated_storage  = 100
  storage_type           = "gp3"
  storage_encrypted      = true

  db_name  = "bibliografia_db"
  username = "bibliografia_user"
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  skip_final_snapshot       = var.environment == "sandbox"
  final_snapshot_identifier = var.environment == "prod" ? "${var.project_name}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Name = "${var.project_name}-db-${var.environment}"
  }
}

# Random password para RDS
resource "random_password" "db_password" {
  length  = 16
  special = true
}

