output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "eks_cluster_name" {
  description = "EKS Cluster Name"
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "RDS Endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "ecr_repository_url" {
  description = "ECR Repository URL"
  value       = aws_ecr_repository.webapp_repo.repository_url
}
