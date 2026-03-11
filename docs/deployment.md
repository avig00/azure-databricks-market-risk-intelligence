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

The `infra/terraform/env/dev.tfvars` and `infra/terraform/env/prod.tfvars` files are aligned with the Databricks `dev` and `prod` bundle targets. They define matching values for:

- environment name
- catalog name
- ADLS prefix
- secret scope name
- notification email

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
- Secret scope/key names, notification email, and cluster policy ID are now bundle variables instead of hard-coded job config.

## Terraform to Bundle handoff

Use the helper script to translate Terraform outputs into Databricks bundle variables:

```bash
cd infra/terraform
terraform output -json > /tmp/market-risk-tf-output.json
cd ../..
python3 scripts/render_bundle_vars.py /tmp/market-risk-tf-output.json
```

That command prints `--var="key=value"` arguments that can be appended to `databricks bundle deploy`.

For a higher-level helper that assembles the full deploy command:

```bash
python3 scripts/deploy_bundle.py --target dev --var-file env/dev.tfvars
```

Add `--execute` to actually run the Databricks deploy once the CLI is configured in your environment.

## Recommended next deployment steps

1. Validate the `dev` and `prod` bundle targets in a real Databricks workspace.
2. Extend CI into a credentialed deploy pipeline for approved branches or tags.
3. Add richer notification routing and on-success alerting if needed.
4. Replace notebook wrappers entirely once the wheel deployment path is validated in a workspace.

## CI

The repository now includes a GitHub Actions workflow at `.github/workflows/ci.yml` that:

- installs the package and dev dependencies
- builds the wheel artifact
- checks Terraform formatting
- runs the Python test suite
- smoke-tests the Terraform-to-bundle helper scripts

There is also a manual deployment workflow at `.github/workflows/deploy.yml` that separates:

- package and Terraform plan
- optional Terraform apply
- optional Databricks bundle validation/deploy preparation

It is designed to run with GitHub environment secrets such as Azure service principal credentials and Databricks host/token values.
