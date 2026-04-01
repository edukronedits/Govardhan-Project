# Terraform variables

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "bill-processing"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "sql_admin_user" {
  description = "SQL Server admin username"
  type        = string
  default     = "sqladmin"
}

variable "sql_admin_password" {
  description = "SQL Server admin password"
  type        = string
  sensitive   = true
}

variable "container_image_version" {
  description = "Container image version tag"
  type        = string
  default     = "latest"
}

variable "app_service_sku" {
  description = "App Service SKU"
  type        = string
  default     = "B2"
}

variable "aks_node_count" {
  description = "Initial number of AKS nodes"
  type        = number
  default     = 3
}

variable "aks_vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_B2s"
}
