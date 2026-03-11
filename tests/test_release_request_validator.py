from __future__ import annotations

import json
import subprocess
import sys


def test_release_request_validator_accepts_dev_release() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_request.py",
            "--target",
            "dev",
            "--ref-name",
            "feature/market-risk",
            "--deploy-bundle",
            "true",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["valid"] is True


def test_release_request_validator_rejects_prod_from_feature_branch() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_request.py",
            "--target",
            "prod",
            "--ref-name",
            "feature/market-risk",
            "--deploy-bundle",
            "true",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert "prod deployments are only allowed" in payload["errors"][0]


def test_release_request_validator_reports_missing_env() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_request.py",
            "--target",
            "dev",
            "--ref-name",
            "main",
            "--apply-infra",
            "true",
            "--check-env",
            "ARM_CLIENT_ID",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["missing_env"] == ["ARM_CLIENT_ID"]
