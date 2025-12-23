# VPC y Networking (si no se proporciona VPC existente)

resource "aws_vpc" "main" {
  count = var.vpc_id == "" ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc-${var.environment}"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  count = var.vpc_id == "" ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  tags = {
    Name = "${var.project_name}-igw-${var.environment}"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count = var.vpc_id == "" && length(var.public_subnets) == 0 ? 2 : 0

  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}-${var.environment}"
    Type = "public"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count = var.vpc_id == "" && length(var.private_subnets) == 0 ? 2 : 0

  vpc_id            = aws_vpc.main[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 2)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}-${var.environment}"
    Type = "private"
  }
}

# NAT Gateway (para que recursos privados puedan acceder a internet)
resource "aws_eip" "nat" {
  count = var.vpc_id == "" && length(var.private_subnets) == 0 ? 1 : 0

  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip-${var.environment}"
  }
}

resource "aws_nat_gateway" "main" {
  count = var.vpc_id == "" && length(var.private_subnets) == 0 ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "${var.project_name}-nat-${var.environment}"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  count = var.vpc_id == "" && length(var.public_subnets) == 0 ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  tags = {
    Name = "${var.project_name}-public-rt-${var.environment}"
  }
}

resource "aws_route_table" "private" {
  count = var.vpc_id == "" && length(var.private_subnets) == 0 ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[0].id
  }

  tags = {
    Name = "${var.project_name}-private-rt-${var.environment}"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count = var.vpc_id == "" && length(var.public_subnets) == 0 ? 2 : 0

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table_association" "private" {
  count = var.vpc_id == "" && length(var.private_subnets) == 0 ? 2 : 0

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id
}

# Locals para usar VPC/subnets existentes o creadas
locals {
  vpc_id_final         = var.vpc_id != "" ? var.vpc_id : (length(aws_vpc.main) > 0 ? aws_vpc.main[0].id : "")
  private_subnets_final = length(var.private_subnets) > 0 ? var.private_subnets : (length(aws_subnet.private) > 0 ? aws_subnet.private[*].id : [])
  public_subnets_final  = length(var.public_subnets) > 0 ? var.public_subnets : (length(aws_subnet.public) > 0 ? aws_subnet.public[*].id : [])
}

