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

- `bundle.yml` defines the bundle, wheel artifact, and separate `dev` / `prod` targets
- `resources/jobs.yml` defines wheel-based jobs for the main pipeline, dashboard refresh, and a default simulation run
- `notebooks/01_run_pipeline.py` and `notebooks/02_dashboard_refresh.py` remain lightweight wrappers around package entrypoints
- the wheel artifact is built from the repo root using `pyproject.toml`

This repo remains local-first, so the Databricks bundle is a packaging/deployment layer on top of the same Python modules used locally.

## Runtime configuration

- Jobs pass `MARKET_RISK_ENV`, `CONFIG_PROFILE`, `CATALOG_NAME`, `STORAGE_BACKEND`, and `ADLS_PREFIX` as runtime environment values.
- The `dev` target uses `finance_dev` and `lakehouse/dev`; the `prod` target uses `finance_prod` and `lakehouse/prod`.
- FRED credentials can come from `FRED_API_KEY` directly or from Databricks secrets via `DATABRICKS_SECRET_SCOPE` and `FRED_API_KEY_SECRET_KEY`.

## Recommended next deployment steps

1. Validate the `dev` and `prod` bundle targets in a real Databricks workspace.
2. Replace hard-coded secret scope/key names in the bundle with workspace variables or secret references.
3. Provide cluster policies, alert destinations, and notification settings in the Databricks bundle.
4. Replace notebook wrappers entirely once the wheel deployment path is validated in a workspace.
