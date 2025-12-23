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

# Aurora Serverless v2 Cluster
resource "aws_rds_cluster" "main" {
  cluster_identifier      = "${var.project_name}-db-${var.environment}"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "15.8"  # Aurora PostgreSQL compatible
  database_name           = "bibliografia_db"
  master_username         = "bibliografia_user"
  master_password         = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  preferred_maintenance_window = "mon:04:00-mon:05:00"

  skip_final_snapshot       = var.environment == "sandbox"
  final_snapshot_identifier = var.environment == "prod" ? "${var.project_name}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  enabled_cloudwatch_logs_exports = ["postgresql"]
  storage_encrypted               = true

  # Serverless v2 scaling (se apaga cuando no se usa)
  serverlessv2_scaling_configuration {
    min_capacity = 0.5  # Mínimo: 0.5 ACU (~$0.06/hora)
    max_capacity = 1.0  # Máximo: 1 ACU para sandbox
  }

  tags = {
    Name = "${var.project_name}-db-${var.environment}"
  }
}

# Aurora Serverless v2 Instance (requiere al menos 1)
resource "aws_rds_cluster_instance" "main" {
  identifier         = "${var.project_name}-db-instance-${var.environment}"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  publicly_accessible = false

  tags = {
    Name = "${var.project_name}-db-instance-${var.environment}"
  }
}

# Random password para RDS
resource "random_password" "db_password" {
  length  = 16
  special = true
}

