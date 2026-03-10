terraform {
  required_version = ">= 1.6.0"
}

locals {
  tags = {
    project = "azure-databricks-market-risk-intelligence"
    owner   = "avig00"
  }
}

# Azure resources are intentionally scaffolded in this milestone.
# Expand with azurerm resources for storage, key vault, data factory,
# and Databricks workspace integrations in a cloud-enabled environment.

