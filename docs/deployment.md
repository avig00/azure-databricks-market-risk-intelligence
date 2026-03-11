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
- `resources/jobs.yml` defines wheel-based jobs for the main pipeline, dashboard refresh, and a default simulation run
- `notebooks/01_run_pipeline.py` and `notebooks/02_dashboard_refresh.py` remain lightweight wrappers around package entrypoints
- the wheel artifact is built from the repo root using `pyproject.toml`

This repo remains local-first, so the Databricks bundle is a packaging/deployment layer on top of the same Python modules used locally.

## Recommended next deployment steps

1. Add Databricks secrets / Key Vault-backed credentials for live ingestion.
2. Provide cluster policies, schedules, and alert destinations in the Databricks bundle.
3. Configure environment-specific bundle targets for dev/staging/prod workspaces.
4. Replace notebook wrappers entirely once the wheel deployment path is validated in a workspace.
