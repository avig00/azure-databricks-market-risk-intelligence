# Release Runbook

## Promotion order

1. Run CI and confirm package, Terraform formatting, and helper validation pass.
2. Run deploy workflow for `dev` with Terraform plan enabled.
3. If required, apply `dev` infrastructure.
4. Validate Databricks bundle in `dev`.
5. Run post-deploy checks:
   - `health-check` returns recent dataset freshness
   - `verify-deployment` returns `checks_passed`
   - `dashboard-summary` succeeds
   - wheel-based jobs install and start cleanly
6. Promote the same configuration to `prod` only after `dev` passes unchanged.

## Rollback guidance

- Infrastructure rollback:
  - inspect the Terraform plan/apply logs in the deploy workflow
  - run a corrective `terraform plan` before another `apply`
- Databricks rollback:
  - inspect the bundle validate/deploy output
  - redeploy the last known-good wheel artifact and bundle target variables
- Data/runtime rollback:
  - inspect `pipeline_runs.jsonl` under the configured log root
  - confirm the latest successful stage and artifact timestamps with `health-check`
  - confirm dataset/model/dashboard verification with `verify-deployment`

## Verification commands

```bash
PYTHONPATH=src python -m market_risk_platform.main health-check
PYTHONPATH=src python -m market_risk_platform.main verify-deployment
PYTHONPATH=src python -m market_risk_platform.main dashboard-summary
```
