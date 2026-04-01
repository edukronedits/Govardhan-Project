# Terraform outputs

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.main.name
}

output "service_bus_namespace" {
  description = "Service Bus namespace"
  value       = azurerm_servicebus_namespace.main.name
}

output "sql_server_name" {
  description = "SQL Server name"
  value       = azurerm_mssql_server.main.name
}

output "sql_database_name" {
  description = "SQL Database name"
  value       = azurerm_mssql_database.main.name
}

output "cosmos_db_endpoint" {
  description = "Cosmos DB endpoint"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "app_service_url" {
  description = "App Service URL"
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "container_registry_name" {
  description = "Container Registry name"
  value       = azurerm_container_registry.main.name
}

output "container_registry_url" {
  description = "Container Registry URL"
  value       = azurerm_container_registry.main.login_server
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

output "application_insights_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.main.name
}

output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.main.id
}
