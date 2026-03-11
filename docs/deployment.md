# Deployment Notes

## Terraform

The Terraform scaffold under `infra/terraform` provisions the core Azure control-plane resources:

- resource group
- ADLS Gen2 storage account and container
- Key Vault
- Data Factory
- Azure Databricks workspace
- optional Event Hubs namespace and hub

Use `terraform.tfvars.example` as the starting point for environment-specific values.

## Databricks packaging

The `databricks/` folder contains a Databricks Asset Bundle starter:

- `bundle.yml` defines the bundle and workspace root path
- `resources/jobs.yml` defines job resources for the main pipeline and dashboard refresh
- `notebooks/01_run_pipeline.py` executes the end-to-end batch pipeline
- `notebooks/02_dashboard_refresh.py` builds the dashboard payload summary

This repo remains local-first, so the Databricks bundle is a packaging/deployment layer on top of the same Python modules used locally.

## Recommended next deployment steps

1. Build a wheel or workspace file sync strategy for `src/market_risk_platform`.
2. Add Databricks secrets / Key Vault-backed credentials for live ingestion.
3. Provide Databricks runtime dependencies so the `databricks` storage backend can write Delta tables via Spark.
4. Add job schedules and alert destinations in the Databricks bundle.
