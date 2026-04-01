# Deployment Guide

## Prerequisites

- Azure Subscription with appropriate permissions
- Azure CLI (`az`) installed and authenticated
- Terraform 1.0+ installed
- kubectl 1.24+ installed
- Helm 3.0+ installed
- Docker Desktop (for local development)
- Python 3.11+, Node.js 18+

## Quick Start

### 1. Local Development Setup

```bash
# Clone repository
git clone <repo-url>
cd bill-processing-system

# Start local development environment
docker-compose up -d

# This starts:
# - Azure Storage Emulator (Azurite)
# - PostgreSQL database
# - RabbitMQ message broker
# - Backend API
# - Frontend (optional)

# Access the API at http://localhost:8000
# View health: http://localhost:8000/health
```

### 2. Infrastructure Deployment

```bash
# Configure Terraform variables
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Azure details

# Initialize and deploy
terraform init
terraform plan
terraform apply

# Retrieve outputs
terraform output
```

### 3. Container Build & Registry

```bash
# Build Docker image
docker build -t bill-processing:latest .

# Push to Azure Container Registry
az acr login --name <your-acr-name>
docker tag bill-processing:latest <your-acr-name>.azurecr.io/bill-processing:latest
docker push <your-acr-name>.azurecr.io/bill-processing:latest
```

### 4. AKS Deployment

```bash
# Get AKS credentials
az aks get-credentials -g <resource-group> -n <aks-cluster-name>

# Create namespace
kubectl create namespace bill-processing

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Check deployment status
kubectl get deployments -n bill-processing
kubectl get pods -n bill-processing
kubectl logs -n bill-processing -l app=bill-processing
```

### 5. CI/CD Pipeline Setup

```bash
# Create Azure DevOps project
az devops project create --name "bill-processing"

# Create pipeline from YAML
az pipelines create --name "bill-processing-pipeline" \
  --repository <repo-url> \
  --branch main \
  --yaml-path pipelines/azure-pipelines.yml

# Configure service connections in Azure DevOps:
# - Azure Resource Manager
# - Container Registry
# - Kubernetes
```

## Architecture Components

### Ingestion Service (Azure Functions)
- HTTP endpoint: POST `/documents`
- Batch endpoint: Service Bus trigger
- Validates, enriches, and queues documents

### Document Processing (Databricks)
- OCR extraction via Document Intelligence
- Text preprocessing and entity extraction
- Runs on Databricks clusters

### AI Agent Framework
- Extractor Agent: Structured data extraction
- Validator Agent: Business rule validation
- Predictor Agent: Rule generation

### Business Rule Engine
- Deterministic, probabilistic, and AI-inferred rules
- Document and line-item validation
- Conflict resolution

### Backend API (FastAPI)
- Endpoints for document management
- Rule CRUD operations
- Analytics and reporting

### Frontend (React)
- Document upload and tracking
- Rule management UI
- Dashboard and analytics
- Manual review queue

## Deployment Stages

### Stage 1: Development (Dev)
- Local development environment
- Docker Compose setup
- Database: Postgres
- Message Broker: RabbitMQ

### Stage 2: Staging
- Kubernetes (AKS)
- Azure services: Storage, Service Bus, SQL, Cosmos DB
- CI/CD: Automated deployments
- Monitoring: App Insights, Log Analytics

### Stage 3: Production
- Multi-region AKS clusters
- Azure Traffic Manager for load balancing
- Backup and disaster recovery
- Enhanced monitoring and alerts

## Monitoring & Observability

### Application Insights
- Track request latency, errors, dependencies
- Custom metrics for business KPIs
- Availability tests

### Log Analytics
- Centralized logging from all services
- Kusto Query Language (KQL) for analysis
- Custom workbooks and dashboards

### Alerts
- High latency (P95 > 2s)
- Error rate > 5%
- Service Bus queue depth > 1000 messages
- Document processing failures > 10%
- Rule validation accuracy < 85%

## Scaling Considerations

### Horizontal Scaling
- Azure Functions: Auto-scale based on queue depth
- AKS: Pod autoscaling based on CPU/memory
- Service Bus: Partitioned topics for throughput
- Database: Read replicas for reporting

### Performance Optimization
- Azure Cache for Redis for frequent queries
- Azure CDN for static assets
- Database query optimization
- Asynchronous processing for non-critical operations

## Security Configuration

### Authentication
- OAuth 2.0 / OpenID Connect via Azure Entra ID
- Service-to-service: Managed Identities
- API keys for external integrations (deprecated in favor of OAuth)

### Authorization
- Role-based access control (RBAC)
- Resource-level permissions
- Scope-based API access

### Data Protection
- Encryption in transit (TLS 1.2+)
- Encryption at rest (Azure Storage encryption)
- PII data masking
- Audit logging for compliance

### Secrets Management
- Azure Key Vault for credential storage
- Automatic secret rotation
- No secrets in code or configuration files

## Troubleshooting

### Common Issues

**Issue: Pods not starting**
```bash
kubectl describe pod <pod-name> -n bill-processing
kubectl logs <pod-name> -n bill-processing
```

**Issue: High memory usage**
```bash
kubectl top nodes
kubectl top pods -n bill-processing
# Adjust resource limits in deployment.yaml
```

**Issue: Service Bus connection errors**
```bash
# Check Service Bus connection string in Key Vault
az keyvault secret show --vault-name <kv-name> \
  --name servicebus-connection
```

**Issue: Database connectivity**
```bash
# Check SQL Server firewall rules
az sql server firewall-rule list -g <rg> -s <sql-server>

# Add your IP
az sql server firewall-rule create -g <rg> -s <sql-server> \
  -n "AllowMyIP" --start-ip-address <your-ip> --end-ip-address <your-ip>
```

## Disaster Recovery

### Backup Strategy
- Daily automated backups to geo-redundant storage
- Database backups with point-in-time restore
- Document archives in cold storage

### Recovery Procedures
- **RTO**: 4 hours
- **RPO**: 1 hour
- Test failover monthly
- Maintain runbooks for common scenarios

## Cost Optimization

### Reserved Instances
- Reserve compute capacity for predictable workloads
- App Service Plans: Reserve for 1-3 years
- SQL Database: Reserve for 1-3 years

### Spot Instances
- Use for non-critical batch jobs
- Document processing can be delayed
- Cost savings: 70-90%

### Autoscaling Policies
- Scale down during off-peak hours (nights, weekends)
- Archive old documents to cold storage
- Monitor and optimize database indexes

## Updating & Maintenance

### Rolling Updates
```bash
# Update container image
kubectl set image deployment/bill-processing \
  bill-processing=<new-image> \
  --record -n bill-processing

# Check rollout status
kubectl rollout status deployment/bill-processing \
  -n bill-processing
```

### Blue-Green Deployment
```bash
# Scale up green (new version)
kubectl scale deployment/bill-processing-green --replicas=3

# Wait for health checks
kubectl wait --for=condition=available \
  deployment/bill-processing-green

# Switch traffic
kubectl delete service bill-processing
kubectl rename service bill-processing-green bill-processing
```

## Further Reading

- [Azure Enterprise Scale Architecture](https://docs.microsoft.com/en-us/azure/cloud-adoption-framework/ready/enterprise-scale/)
- [AKS Best Practices](https://docs.microsoft.com/en-us/azure/aks/best-practices)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
