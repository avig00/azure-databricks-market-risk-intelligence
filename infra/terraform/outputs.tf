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

