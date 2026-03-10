variable "location" {
  description = "Azure region for the platform resources."
  type        = string
  default     = "southcentralus"
}

variable "resource_group_name" {
  description = "Resource group name for Azure infrastructure."
  type        = string
  default     = "rg-market-risk-intelligence"
}

variable "storage_account_name" {
  description = "Globally unique storage account name."
  type        = string
  default     = "mriskintelstorage01"
}

variable "storage_container_name" {
  description = "ADLS Gen2 container for lakehouse data."
  type        = string
  default     = "market-risk"
}

variable "key_vault_name" {
  description = "Azure Key Vault name."
  type        = string
  default     = "kv-market-risk-intel"
}

variable "data_factory_name" {
  description = "Azure Data Factory instance name."
  type        = string
  default     = "adf-market-risk-intel"
}

variable "databricks_workspace_name" {
  description = "Azure Databricks workspace name."
  type        = string
  default     = "adb-market-risk-intel"
}

variable "databricks_sku" {
  description = "Azure Databricks pricing tier."
  type        = string
  default     = "premium"
}

variable "tenant_id" {
  description = "Azure tenant ID used by Key Vault."
  type        = string
}

variable "enable_eventhub" {
  description = "Whether to provision Event Hubs resources for streaming ingestion."
  type        = bool
  default     = false
}

variable "eventhub_namespace_name" {
  description = "Event Hubs namespace name."
  type        = string
  default     = "evh-market-risk-intel"
}

variable "eventhub_name" {
  description = "Event Hub name for market signals."
  type        = string
  default     = "market-signal-events"
}
