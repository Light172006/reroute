# Reroute Backend Deployment Guide

This document outlines the DevOps setup, CI/CD pipeline, containerization, and AWS ECS/Fargate deployment steps for the Reroute backend service.

---

## Architecture Overview

- **Containerization**: Docker multi-stage / slim Python 3.11 environment with automated Alembic migration execution on startup.
- **CI/CD Platform**: GitHub Actions (`.github/workflows/ci-cd.yml`) executing tests against PostgreSQL and pushing images to Amazon ECR.
- **Compute**: AWS ECS with AWS Fargate (serverless container compute).
- **Secrets & Configuration**: AWS Secrets Manager and Parameter Store.

---

## 1. Docker Setup

The `Dockerfile` installs system and Python dependencies, sets up the FastAPI application, and runs database migrations before starting Uvicorn.

### Local Build & Run Commands

```bash
# Build the Docker image
docker build -t reroute-backend:latest .

# Run locally with environment variables
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/reroute" \
  -e SECRET_KEY="your-local-secret-key" \
  reroute-backend:latest
```

---

## 2. GitHub Actions CI/CD Pipeline

Located at `.github/workflows/ci-cd.yml`.

### Pipeline Stages:
1. **Test**: Spawns a PostgreSQL 15 service container, installs project requirements, and executes `pytest`.
2. **Build & Push**: Authenticates with AWS ECR, builds the Docker image tagged with the Git SHA and `latest`, and pushes to Amazon ECR.
3. **Deploy**: Automatically updates the AWS ECS Fargate task definition with the new image and triggers a rolling deployment.

### Required GitHub Secrets:
Configure the following secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):
- `AWS_ACCESS_KEY_ID`: AWS IAM access key with permissions for ECR and ECS.
- `AWS_SECRET_ACCESS_KEY`: AWS IAM secret key.

---

## 3. AWS ECS/Fargate Deployment Commands

### Initial AWS Infrastructure Provisioning (AWS CLI)

```bash
# 1. Create ECR Repository
aws ecr create-repository --repository-name reroute-backend --region us-east-1

# 2. Create ECS Cluster
aws ecs create-cluster --cluster-name reroute-cluster --region us-east-1

# 3. Create CloudWatch Log Group
aws logs create-log-group --log-group-name /ecs/reroute-backend
```

### Manual Build, Tag, and Push to ECR

If you need to push manually from your local terminal:

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag reroute-backend:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/reroute-backend:latest

# Push image
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/reroute-backend:latest
```

---

## 4. Secrets Management

Production secrets (Database URLs, JWT secret keys, API keys) are stored in **AWS Secrets Manager** under the secret path `reroute/prod/`:
- `reroute/prod/db_url`
- `reroute/prod/secret_key`
- `reroute/prod/openai_api_key`

The ECS task definition (`.aws/task-definition.json`) securely resolves these values at runtime via IAM execution roles without exposing plaintext secrets in environment variables.
