# Terraform configuration para GROBID en ECS Fargate
# Nota: Las variables están definidas en variables.tf

# ECS Cluster (solo para Fargate)
resource "aws_ecs_cluster" "grobid" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  name = "grobid-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Environment = var.environment
    Service     = "grobid"
  }
}

# Task Definition para GROBID (solo para Fargate)
resource "aws_ecs_task_definition" "grobid" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  family                   = "grobid-service-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities  = ["FARGATE"]
  cpu                      = "512"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution_role[0].arn
  task_role_arn            = aws_iam_role.ecs_task_role[0].arn

  container_definitions = jsonencode([
    {
      name      = "grobid"
      image     = "lfoppiano/grobid:0.7.3"
      memory    = 2048
      cpu       = 512
      essential = true

      portMappings = [
        {
          containerPort = 8070
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "JAVA_OPTS"
          value = "-Xmx2g"
        }
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8070/api/isalive || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/grobid-service-${var.environment}"
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "grobid"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "grobid"
  }
}

# ECS Service (solo para Fargate)
resource "aws_ecs_service" "grobid" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  name            = "grobid-service-${var.environment}"
  cluster         = aws_ecs_cluster.grobid[0].id
  task_definition = aws_ecs_task_definition.grobid[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.private_subnets_final
    security_groups  = [aws_security_group.grobid[0].id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.grobid[0].arn
    container_name   = "grobid"
    container_port   = 8070
  }

  depends_on = [
    aws_lb_listener.grobid[0],
    aws_iam_role_policy_attachment.ecs_task_execution_role[0]
  ]

  tags = {
    Environment = var.environment
    Service     = "grobid"
  }
}

# Security Group para GROBID (solo para Fargate)
resource "aws_security_group" "grobid" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  name        = "grobid-sg-${var.environment}"
  description = "Security group para GROBID service"
  vpc_id      = local.vpc_id_final

  ingress {
    from_port       = 8070
    to_port         = 8070
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "GROBID API desde Lambda"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Environment = var.environment
    Service     = "grobid"
  }
}

# Application Load Balancer (interno, solo para Fargate)
resource "aws_lb" "grobid" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  name               = "grobid-alb-${var.environment}"
  internal           = true
  load_balancer_type = "application"
  subnets            = local.private_subnets_final
  security_groups     = [aws_security_group.grobid_alb[0].id]

  enable_deletion_protection = false

  tags = {
    Environment = var.environment
    Service     = "grobid"
  }
}

# Security Group para ALB (solo para Fargate)
resource "aws_security_group" "grobid_alb" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  name        = "grobid-alb-sg-${var.environment}"
  description = "Security group para GROBID ALB"
  vpc_id      = local.vpc_id_final

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "HTTP desde Lambda"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Service     = "grobid"
  }
}

# Target Group (solo para Fargate)
resource "aws_lb_target_group" "grobid" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  name        = "grobid-tg-${var.environment}"
  port        = 8070
  protocol    = "HTTP"
  vpc_id      = local.vpc_id_final
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/api/isalive"
    matcher             = "200"
  }

  tags = {
    Environment = var.environment
    Service     = "grobid"
  }
}

# Listener (solo para Fargate)
resource "aws_lb_listener" "grobid" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  load_balancer_arn = aws_lb.grobid[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grobid[0].arn
  }
}

# IAM Roles (solo para Fargate)
resource "aws_iam_role" "ecs_execution_role" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  name = "grobid-ecs-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task_role" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  name = "grobid-ecs-task-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  role       = aws_iam_role.ecs_execution_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# CloudWatch Log Group (solo para Fargate)
resource "aws_cloudwatch_log_group" "grobid" {
  count = var.grobid_deployment == "fargate" ? 1 : 0
  
  name              = "/ecs/grobid-service-${var.environment}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Service     = "grobid"
  }
}

