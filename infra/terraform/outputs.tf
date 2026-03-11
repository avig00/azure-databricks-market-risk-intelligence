output "resource_group_name" {
  value = azurerm_resource_group.platform.name
}

output "storage_account_name" {
  value = azurerm_storage_account.lakehouse.name
}

output "storage_container_name" {
  value = azurerm_storage_container.lakehouse.name
}

output "databricks_workspace_url" {
  value = azurerm_databricks_workspace.platform.workspace_url
}

output "key_vault_uri" {
  value = azurerm_key_vault.platform.vault_uri
}

output "bundle_environment_name" {
  value = var.environment_name
}

output "bundle_catalog_name" {
  value = var.catalog_name
}

output "bundle_adls_prefix" {
  value = var.adls_prefix
}

output "bundle_secret_scope" {
  value = var.databricks_secret_scope
}

output "bundle_fred_api_key_secret_key" {
  value = var.fred_api_key_secret_key
}

output "bundle_notification_email" {
  value = var.notification_email
}
