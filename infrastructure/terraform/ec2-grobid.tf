# EC2 Instance para GROBID (alternativa a ECS Fargate)

resource "aws_instance" "grobid" {
  count = var.grobid_deployment == "ec2" ? 1 : 0

  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.small"
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.grobid_ec2[0].id]
  subnet_id              = length(local.public_subnets_final) > 0 ? local.public_subnets_final[0] : null

  user_data = file("${path.module}/../grobid/ec2-setup.sh")

  tags = {
    Name = "${var.project_name}-grobid-${var.environment}"
  }
}

# Security Group para GROBID EC2
resource "aws_security_group" "grobid_ec2" {
  count = var.grobid_deployment == "ec2" ? 1 : 0

  name        = "${var.project_name}-grobid-ec2-sg-${var.environment}"
  description = "Security group para GROBID en EC2"
  vpc_id      = local.vpc_id_final != "" ? local.vpc_id_final : null

  ingress {
    from_port   = 8070
    to_port     = 8070
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "GROBID API desde VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-grobid-ec2-sg-${var.environment}"
  }
}

# AMI para Amazon Linux
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# Variable key_pair_name está definida en variables.tf

