# Terraform Scaffold

This directory contains starter Azure resource definitions for:

- Azure Data Lake Storage Gen2
- Azure Key Vault
- Azure Data Factory
- Azure Databricks workspace
- Optional Azure Event Hubs for streaming signals

Usage:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
```

Environment-aligned examples:

```bash
terraform plan -var-file=env/dev.tfvars
terraform plan -var-file=env/prod.tfvars
```

Notes:

- `tenant_id` must be set for Key Vault.
- `storage_account_name`, `key_vault_name`, and Event Hubs namespace names must be globally unique in Azure.
- Event Hubs resources are controlled by `enable_eventhub`.
- `catalog_name`, `adls_prefix`, `databricks_secret_scope`, and `notification_email` are intended to line up with the Databricks bundle target values.
