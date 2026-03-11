from __future__ import annotations

from pathlib import Path


def test_bundle_contains_secret_and_notification_variables() -> None:
    bundle_text = Path("databricks/bundle.yml").read_text()
    assert "databricks_secret_scope" in bundle_text
    assert "fred_api_key_secret_key" in bundle_text
    assert "cluster_policy_id" in bundle_text
    assert "notification_email" in bundle_text


def test_jobs_use_bundle_variables_for_secret_scope_and_notifications() -> None:
    jobs_text = Path("databricks/resources/jobs.yml").read_text()
    assert 'DATABRICKS_SECRET_SCOPE: "{{job.parameters.databricks_secret_scope}}"' in jobs_text
    assert 'FRED_API_KEY_SECRET_KEY: "{{job.parameters.fred_api_key_secret_key}}"' in jobs_text
    assert "email_notifications:" in jobs_text
    assert "policy_id: ${var.cluster_policy_id}" in jobs_text
