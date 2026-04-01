#!/bin/bash
# Deployment script for Bill Processing System

set -e

PROJECT_NAME="bill-processing"
ENVIRONMENT="${1:-dev}"
LOCATION="${2:-eastus}"

echo "======================================================================"
echo "Bill Processing System - Deployment Script"
echo "======================================================================"
echo "Environment: $ENVIRONMENT"
echo "Location: $LOCATION"
echo "Project: $PROJECT_NAME"
echo "======================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"
    
    commands=("az" "terraform" "kubectl" "helm" "docker")
    
    for cmd in "${commands[@]}"; do
        if command -v $cmd &> /dev/null; then
            print_status "$cmd is installed"
        else
            print_error "$cmd is not installed"
            exit 1
        fi
    done
}

# Setup Azure authentication
setup_azure_auth() {
    echo -e "\n${YELLOW}Setting up Azure authentication...${NC}"
    
    az login
    
    # Set subscription
    read -p "Enter your Azure Subscription ID: " subscription_id
    az account set --subscription "$subscription_id"
    
    print_status "Azure authentication configured"
}

# Deploy infrastructure
deploy_infrastructure() {
    echo -e "\n${YELLOW}Deploying infrastructure with Terraform...${NC}"
    
    cd infrastructure
    
    # Copy example tfvars
    cp terraform.tfvars.example terraform.tfvars
    
    echo "Please edit terraform.tfvars with your values"
    read -p "Press Enter when ready..."
    
    # Initialize Terraform
    terraform init
    
    # Plan
    terraform plan -out=tfplan
    
    # Apply
    read -p "Apply Terraform changes? (yes/no): " response
    if [ "$response" == "yes" ]; then
        terraform apply tfplan
        print_status "Infrastructure deployed"
    else
        print_warning "Infrastructure deployment skipped"
    fi
    
    cd ..
}

# Build container image
build_container() {
    echo -e "\n${YELLOW}Building container image...${NC}"
    
    # Get ACR details
    ACR_NAME=$(terraform -chdir=infrastructure output -raw container_registry_name 2>/dev/null || echo "")
    
    if [ -z "$ACR_NAME" ]; then
        print_error "Could not retrieve ACR name. Make sure Terraform has been applied."
        return 1
    fi
    
    ACR_URL="$ACR_NAME.azurecr.io"
    IMAGE_TAG="$(date +%Y%m%d%H%M%S)"
    
    # Build image
    docker build -t "$ACR_URL/$PROJECT_NAME:$IMAGE_TAG" .
    docker tag "$ACR_URL/$PROJECT_NAME:$IMAGE_TAG" "$ACR_URL/$PROJECT_NAME:latest"
    
    print_status "Container image built: $ACR_URL/$PROJECT_NAME:$IMAGE_TAG"
    
    # Push to ACR
    echo "Please authenticate with ACR..."
    az acr login --name "$ACR_NAME"
    
    docker push "$ACR_URL/$PROJECT_NAME:$IMAGE_TAG"
    docker push "$ACR_URL/$PROJECT_NAME:latest"
    
    print_status "Container image pushed to ACR"
}

# Deploy to AKS
deploy_to_aks() {
    echo -e "\n${YELLOW}Deploying to AKS...${NC}"
    
    # Get credentials
    RESOURCE_GROUP=$(terraform -chdir=infrastructure output -raw resource_group_name 2>/dev/null || echo "bill-processing-rg")
    AKS_CLUSTER=$(terraform -chdir=infrastructure output -raw aks_cluster_name 2>/dev/null || echo "${PROJECT_NAME}-aks")
    
    az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER"
    
    # Create namespace
    kubectl create namespace bill-processing --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s/deployment.yaml
    
    # Wait for deployment
    kubectl rollout status deployment/bill-processing -n bill-processing --timeout=5m
    
    print_status "Deployment to AKS completed"
}

# Setup monitoring
setup_monitoring() {
    echo -e "\n${YELLOW}Setting up monitoring...${NC}"
    
    # Create monitoring namespace
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply monitoring configuration
    kubectl apply -f monitoring/prometheus-rules.yaml
    
    print_status "Monitoring configured"
}

# Run tests
run_tests() {
    echo -e "\n${YELLOW}Running tests...${NC}"
    
    cd src/backend-api
    
    python -m pip install -r requirements.txt
    python -m pytest tests/ -v
    
    cd ../..
    
    print_status "Tests completed"
}

# Main execution
main() {
    check_prerequisites
    setup_azure_auth
    
    read -p "Deploy infrastructure? (yes/no): " deploy_infra
    if [ "$deploy_infra" == "yes" ]; then
        deploy_infrastructure
    fi
    
    read -p "Build and push container? (yes/no): " build_container_opt
    if [ "$build_container_opt" == "yes" ]; then
        build_container
    fi
    
    read -p "Deploy to AKS? (yes/no): " deploy_aks_opt
    if [ "$deploy_aks_opt" == "yes" ]; then
        deploy_to_aks
    fi
    
    read -p "Setup monitoring? (yes/no): " setup_monitoring_opt
    if [ "$setup_monitoring_opt" == "yes" ]; then
        setup_monitoring
    fi
    
    read -p "Run tests? (yes/no): " run_tests_opt
    if [ "$run_tests_opt" == "yes" ]; then
        run_tests
    fi
    
    echo -e "\n${GREEN}======================================================================"
    echo "Deployment completed successfully!"
    echo "=====================================================================${NC}\n"
}

# Run main function
main
