terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

locals {
  tags = {
    project = "azure-databricks-market-risk-intelligence"
    owner   = "avig00"
  }
}

resource "azurerm_resource_group" "platform" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

resource "azurerm_storage_account" "lakehouse" {
  name                            = var.storage_account_name
  resource_group_name             = azurerm_resource_group.platform.name
  location                        = azurerm_resource_group.platform.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = local.tags
}

resource "azurerm_storage_container" "lakehouse" {
  name                  = var.storage_container_name
  storage_account_id    = azurerm_storage_account.lakehouse.id
  container_access_type = "private"
}

resource "azurerm_key_vault" "platform" {
  name                          = var.key_vault_name
  location                      = azurerm_resource_group.platform.location
  resource_group_name           = azurerm_resource_group.platform.name
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  purge_protection_enabled      = false
  soft_delete_retention_days    = 7
  public_network_access_enabled = true
  tags                          = local.tags
}

resource "azurerm_data_factory" "platform" {
  name                = var.data_factory_name
  location            = azurerm_resource_group.platform.location
  resource_group_name = azurerm_resource_group.platform.name
  tags                = local.tags
}

resource "azurerm_databricks_workspace" "platform" {
  name                        = var.databricks_workspace_name
  resource_group_name         = azurerm_resource_group.platform.name
  location                    = azurerm_resource_group.platform.location
  sku                         = var.databricks_sku
  managed_resource_group_name = "${var.resource_group_name}-databricks-managed"
  tags                        = local.tags
}

resource "azurerm_eventhub_namespace" "platform" {
  count               = var.enable_eventhub ? 1 : 0
  name                = var.eventhub_namespace_name
  location            = azurerm_resource_group.platform.location
  resource_group_name = azurerm_resource_group.platform.name
  sku                 = "Standard"
  capacity            = 1
  tags                = local.tags
}

resource "azurerm_eventhub" "market_signals" {
  count             = var.enable_eventhub ? 1 : 0
  name              = var.eventhub_name
  namespace_id      = azurerm_eventhub_namespace.platform[0].id
  partition_count   = 2
  message_retention = 1
}
