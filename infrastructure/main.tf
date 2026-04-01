# Terraform configuration for Bill Processing System
# Deploys all Azure resources

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  
  # Remote state configuration
  backend "azurerm" {
    resource_group_name  = "tf-state-rg"
    storage_account_name = "tfstatesa"
    container_name       = "tfstate"
    key                  = "bill-processing.tfstate"
  }
}

provider "azurerm" {
  features {}
  
  subscription_id = var.subscription_id
}

# Data source for current Azure context
data "azurerm_client_config" "current" {}

# Create resource group
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
  location = var.location
  
  tags = local.common_tags
}

# Storage Account (documents, logs)
resource "azurerm_storage_account" "main" {
  name                     = "${lower(var.project_name)}sa"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  
  tags = local.common_tags
}

# Blob container for raw documents
resource "azurerm_storage_container" "raw_documents" {
  name                  = "raw-documents"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Blob container for processed documents
resource "azurerm_storage_container" "processed_documents" {
  name                  = "processed-documents"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Service Bus Namespace
resource "azurerm_servicebus_namespace" "main" {
  name                = "${var.project_name}-sb"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  
  tags = local.common_tags
}

# Service Bus Topic
resource "azurerm_servicebus_topic" "bill_processing" {
  name                = "bill-processing"
  namespace_name      = azurerm_servicebus_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  
  enable_partitioning = true
}

# Service Bus Subscription
resource "azurerm_servicebus_subscription" "document_processor" {
  name                = "document-processor"
  namespace_name      = azurerm_servicebus_namespace.main.name
  topic_name          = azurerm_servicebus_topic.bill_processing.name
  resource_group_name = azurerm_resource_group.main.name
  
  max_delivery_count = 10
  lock_duration      = "PT1M"
}

# Dead Letter Queue
resource "azurerm_servicebus_queue" "dead_letter" {
  name                = "dead-letter"
  namespace_name      = azurerm_servicebus_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  
  dead_lettering_on_message_expiration = true
}

# Azure SQL Server
resource "azurerm_mssql_server" "main" {
  name                         = "${var.project_name}-sqlserver"
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  version                      = "12.0"
  administrator_login          = var.sql_admin_user
  administrator_login_password = var.sql_admin_password
  
  tags = local.common_tags
}

# Azure SQL Database
resource "azurerm_mssql_database" "main" {
  name           = "${var.project_name}-db"
  server_id      = azurerm_mssql_server.main.id
  collation      = "SQL_Latin1_General_CP1_CI_AS"
  license_type   = "LicenseIncluded"
  sku_name       = "S1"
  
  tags = local.common_tags
}

# Cosmos DB Account
resource "azurerm_cosmosdb_account" "main" {
  name                = "${var.project_name}-cosmos"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  
  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }
  
  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }
  
  tags = local.common_tags
}

# Cosmos DB Database
resource "azurerm_cosmosdb_sql_database" "main" {
  account_name            = azurerm_cosmosdb_account.main.name
  resource_group_name     = azurerm_resource_group.main.name
  name                    = "bill-database"
  throughput              = 400
}

# Cosmos DB Containers
resource "azurerm_cosmosdb_sql_container" "documents" {
  account_name            = azurerm_cosmosdb_account.main.name
  database_name           = azurerm_cosmosdb_sql_database.main.name
  name                    = "documents"
  resource_group_name     = azurerm_resource_group.main.name
  partition_key_path      = "/ingestion_id"
  
  indexing_policy {
    indexing_mode = "consistent"
    
    included_path {
      path = "/*"
    }
    
    excluded_path {
      path = "/_etag/?"
    }
  }
}

# App Service Plan
resource "azurerm_service_plan" "main" {
  name                = "${var.project_name}-asp"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = "B2"
  
  tags = local.common_tags
}

# App Service (Backend API)
resource "azurerm_linux_web_app" "main" {
  name                = "${var.project_name}-api"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main.id
  
  site_config {
    application_stack {
      python_version = "3.11"
    }
    
    always_on = true
  }
  
  app_settings = {
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "true"
    "APPINSIGHTS_INSTRUMENTATION_KEY"     = azurerm_application_insights.main.instrumentation_key
  }
  
  tags = local.common_tags
  
  depends_on = [
    azurerm_service_plan.main
  ]
}

# Azure Container Registry
resource "azurerm_container_registry" "main" {
  name                = "${replace(var.project_name, "-", "")}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = true
  
  tags = local.common_tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "${var.project_name}-ai"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  
  tags = local.common_tags
}

# Key Vault
resource "azurerm_key_vault" "main" {
  name                        = "${var.project_name}-kv"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id
    
    secret_permissions = [
      "Get", "Set", "Delete", "Purge", "List"
    ]
  }
  
  tags = local.common_tags
}

# Store secrets in Key Vault
resource "azurerm_key_vault_secret" "servicebus_connection" {
  name         = "servicebus-connection"
  value        = azurerm_servicebus_namespace.main.default_primary_connection_string
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "storage_account_key" {
  name         = "storage-account-key"
  value        = azurerm_storage_account.main.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.project_name}-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = var.project_name
  
  default_node_pool {
    name       = "default"
    node_count = 3
    vm_size    = "Standard_B2s"
    
    auto_scaling_enabled = true
    min_count            = 3
    max_count            = 10
  }
  
  identity {
    type = "SystemAssigned"
  }
  
  tags = local.common_tags
  
  depends_on = [
    azurerm_resource_group.main
  ]
}

# Attach ACR to AKS
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope              = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id       = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-law"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  
  tags = local.common_tags
}

# Local variables
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    CreatedAt   = timestamp()
  }
}
