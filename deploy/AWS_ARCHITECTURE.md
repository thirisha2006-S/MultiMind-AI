# MultiMind AI - AWS Production Architecture

## Overview

Production deployment on AWS using managed services for scalability, security, and observability.

## Architecture Diagram

```
Users (Browser / Mobile)
   │
   ▼
Amazon CloudFront (CDN + WAF)
   │
   ▼
API Gateway (REST/WebSocket)
   │
   ▼
AWS Cognito (Authentication + User Management)
   │
   ▼
Application Load Balancer
   │
   ▼
ECS Fargate (Docker Containers)
   ├── Streamlit Dashboard
   └── LangGraph Workers
   │
   ▼
Data Layer
   ├── Amazon RDS PostgreSQL (conversations, audit logs)
   ├── Amazon ElastiCache Redis (sessions, caching)
   ├── Amazon S3 (document storage)
   └── OpenSearch Service (vector search for RAG)
   │
   ▼
LLM Layer
   ├── Amazon Bedrock (Claude, Titan)
   ├── OpenAI API (via VPC Endpoint)
   └── Cohere API (via VPC Endpoint)
   │
   ▼
Observability
   ├── Amazon CloudWatch (metrics, logs, alarms)
   ├── AWS X-Ray (distributed tracing)
   └── AWS Security Hub (security findings)
```

## Service Catalog

| Component | AWS Service | Purpose |
|-----------|-------------|---------|
| Frontend | CloudFront + S3 | Static hosting + CDN |
| API Gateway | API Gateway | REST/WebSocket endpoint |
| Auth | Cognito | User pools, identity provider |
| Compute | ECS Fargate | Container orchestration |
| Database | RDS PostgreSQL | Structured data |
| Cache | ElastiCache Redis | Session store, rate limiting |
| Object Storage | S3 | Document uploads |
| Vector DB | OpenSearch | RAG vector search |
| LLM | Bedrock / API | Language model inference |
| Monitoring | CloudWatch + X-Ray | Metrics, logs, traces |
| Security | Security Hub + WAF | Threat detection |

## Terraform / Bicep Example (Conceptual)

```hcl
# S3 bucket for documents
resource "aws_s3_bucket" "multimind_documents" {
  bucket = "multimind-${var.environment}-documents"
}

# RDS PostgreSQL
resource "aws_db_instance" "multimind" {
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  allocated_storage = 20
}

# ECS Fargate service
resource "aws_ecs_service" "multimind" {
  name            = "multimind-ai"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.multimind.arn
  desired_count   = 2
}

# OpenSearch domain for RAG
resource "aws_opensearch_domain" "multimind_vectors" {
  domain_name    = "multimind-vectors"
  cluster_config {
    instance_type = "t3.small.search"
  }
}
```

## Security Considerations

- **VPC**: All services in private subnets
- **WAF**: SQL injection, XSS, IP blocklists
- **KMS**: Encryption at rest for all data stores
- **IAM**: Least-privilege roles per service
- **Secrets Manager**: API keys, database credentials
- **GuardDuty**: Threat detection

## Cost Estimate

| Service | Monthly Cost (est.) |
|---------|---------------------|
| ECS Fargate (2 tasks, 1GB) | ~$30 |
| RDS t3.micro | ~$15 |
| OpenSearch t3.small | ~$40 |
| S3 + CloudFront | ~$5 |
| Bedrock / LLM API | ~$20-50 |
| **Total** | **~$110-140/month** |

## Deployment Steps

1. Provision infrastructure (Terraform/Bicep)
2. Build Docker image → ECR
3. Deploy ECS service with ALB
4. Configure Cognito user pool
5. Set up CloudWatch alarms
6. Run database migrations
7. Smoke test endpoints
