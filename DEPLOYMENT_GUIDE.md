# Deployment Guide - EDGP AI Data Quality Engine

## Environment Configuration

The project supports multiple deployment environments, each with its own configuration:

### 🛠️ Available Environments

1. **`.env.development`** - Local development environment
2. **`.env.sit`** - System Integration Testing environment  
3. **`.env.production`** - Production environment
4. **`.env.template`** - Template for creating new environment files

### 🔧 Environment-Specific Settings

#### Development Environment
- **Purpose**: Local development and debugging
- **Log Level**: DEBUG (verbose logging)
- **Thresholds**: More lenient (80% similarity, 70% GPT confidence)
- **Features**: Detailed logging, performance metrics, GPT response caching
- **Batch Size**: 5 messages per batch
- **Timeout**: 30 seconds

#### SIT Environment  
- **Purpose**: System integration testing and validation
- **Log Level**: INFO (balanced logging)
- **Thresholds**: Production-like (85% similarity, 75% GPT confidence)
- **Features**: Integration tests, load testing, data profiling
- **Batch Size**: 10 messages per batch
- **Timeout**: 60 seconds

#### Production Environment
- **Purpose**: Live production deployment
- **Log Level**: WARNING (minimal logging)
- **Thresholds**: Strict (85% similarity, 75% GPT confidence)
- **Features**: Auto-scaling, monitoring, security, circuit breaker
- **Batch Size**: 20 messages per batch
- **Timeout**: 120 seconds

## 🚀 Deployment Instructions

### 1. Environment Setup

#### Option A: Using Environment Loader Script
```bash
# Load development environment
python load_env.py development

# Load SIT environment  
python load_env.py sit

# Load production environment
python load_env.py production
```

#### Option B: Manual Environment Variable
```bash
# Set environment name
export ENV_NAME=development  # or sit, production

# Run application
python src/main.py
```

#### Option C: Direct Environment File
```bash
# Copy specific environment file
cp .env.development .env

# Run application (will load .env by default)
python src/main.py
```

### 2. AWS Resource Setup

#### Development Environment
```bash
# Create development queues
aws sqs create-queue --queue-name customer-input-queue-dev --region us-east-1
aws sqs create-queue --queue-name customer-output-queue-dev --region us-east-1

# Create development DynamoDB table
aws dynamodb create-table \
    --table-name customer_records_dev \
    --attribute-definitions \
        AttributeName=full_hash,AttributeType=S \
        AttributeName=block_key,AttributeType=S \
    --key-schema \
        AttributeName=full_hash,KeyType=HASH \
    --global-secondary-indexes \
        'IndexName=block-key-index,KeySchema=[{AttributeName=block_key,KeyType=HASH}],Projection={ProjectionType=ALL}' \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

#### SIT Environment
```bash
# Create SIT queues
aws sqs create-queue --queue-name customer-input-queue-sit --region us-east-1
aws sqs create-queue --queue-name customer-output-queue-sit --region us-east-1

# Create SIT DynamoDB table with higher capacity
aws dynamodb create-table \
    --table-name customer_records_sit \
    --attribute-definitions \
        AttributeName=full_hash,AttributeType=S \
        AttributeName=block_key,AttributeType=S \
    --key-schema \
        AttributeName=full_hash,KeyType=HASH \
    --global-secondary-indexes \
        'IndexName=block-key-index,KeySchema=[{AttributeName=block_key,KeyType=HASH}],Projection={ProjectionType=ALL}' \
    --provisioned-throughput ReadCapacityUnits=50,WriteCapacityUnits=50 \
    --global-secondary-indexes \
        ProvisionedThroughput='{ReadCapacityUnits=50,WriteCapacityUnits=50}' \
    --region us-east-1
```

#### Production Environment
```bash
# Create production queues with DLQ
aws sqs create-queue --queue-name customer-dlq-prod --region us-east-1
aws sqs create-queue --queue-name customer-input-queue-prod --region us-east-1
aws sqs create-queue --queue-name customer-output-queue-prod --region us-east-1

# Create production DynamoDB table with auto-scaling
aws dynamodb create-table \
    --table-name customer_records_prod \
    --attribute-definitions \
        AttributeName=full_hash,AttributeType=S \
        AttributeName=block_key,AttributeType=S \
    --key-schema \
        AttributeName=full_hash,KeyType=HASH \
    --global-secondary-indexes \
        'IndexName=block-key-index,KeySchema=[{AttributeName=block_key,KeyType=HASH}],Projection={ProjectionType=ALL}' \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### 3. Docker Deployment

#### Build Multi-Environment Image
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY load_env.py .

# Environment files (secrets should be mounted)
COPY .env.* ./

# Default to development
ENV ENV_NAME=development

# Run application
CMD ["python", "src/main.py"]
```

#### Build and Run
```bash
# Build image
docker build -t edgp-ai-data-quality:latest .

# Run development
docker run -e ENV_NAME=development edgp-ai-data-quality:latest

# Run SIT
docker run -e ENV_NAME=sit edgp-ai-data-quality:latest

# Run production (with secrets)
docker run \
  -e ENV_NAME=production \
  -e AWS_ACCESS_KEY_ID=$PROD_AWS_KEY \
  -e AWS_SECRET_ACCESS_KEY=$PROD_AWS_SECRET \
  -e OPENAI_API_KEY=$PROD_OPENAI_KEY \
  edgp-ai-data-quality:latest
```

### 4. Kubernetes Deployment

#### ConfigMaps and Secrets
```yaml
# development-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: edgp-dev-config
data:
  ENV_NAME: "development"
  LOG_LEVEL: "DEBUG"
  SIMILARITY_THRESHOLD: "0.80"
---
apiVersion: v1
kind: Secret
metadata:
  name: edgp-dev-secrets
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "your-dev-key"
  AWS_SECRET_ACCESS_KEY: "your-dev-secret"
  OPENAI_API_KEY: "your-dev-openai-key"
```

#### Deployment
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edgp-ai-data-quality
spec:
  replicas: 3
  selector:
    matchLabels:
      app: edgp-ai-data-quality
  template:
    metadata:
      labels:
        app: edgp-ai-data-quality
    spec:
      containers:
      - name: edgp-ai-data-quality
        image: edgp-ai-data-quality:latest
        envFrom:
        - configMapRef:
            name: edgp-dev-config
        - secretRef:
            name: edgp-dev-secrets
```

## 🔍 Environment Validation

### Test Environment Configuration
```bash
# Test development environment
python load_env.py development
python -c "import src.config; src.config.validate_config()"

# Test SIT environment
python load_env.py sit
python -c "import src.config; src.config.validate_config()"

# Test production environment
python load_env.py production
python -c "import src.config; src.config.validate_config()"
```

### Run Environment-Specific Tests
```bash
# Development tests (with mocking)
ENV_NAME=development pytest tests/ -v

# SIT tests (integration tests)
ENV_NAME=sit pytest tests/test_integration.py -v

# Production tests (smoke tests only)
ENV_NAME=production pytest tests/test_models.py -v
```

## 📊 Monitoring by Environment

### Development
- Local logging to console
- Performance metrics collection
- Debug information enabled

### SIT
- Structured logging to files
- Load testing metrics
- Integration test results

### Production
- CloudWatch logs and metrics
- Error alerting via email/Slack
- Health check endpoints
- Auto-scaling metrics

## 🔒 Security Considerations

### Development
- Use development AWS account
- Dummy/test data only
- Local environment variables

### SIT
- Separate AWS account from production
- Anonymized production-like data
- Network isolation

### Production
- Production AWS account
- Encrypted secrets management
- VPC and security groups
- IAM least privilege access
- Audit logging enabled

## 📈 Scaling Configuration

### Development
- Single instance
- Minimal resource allocation

### SIT  
- 2-5 instances for load testing
- Medium resource allocation

### Production
- Auto-scaling 2-20 instances
- High resource allocation
- Circuit breaker patterns
- Rate limiting enabled
