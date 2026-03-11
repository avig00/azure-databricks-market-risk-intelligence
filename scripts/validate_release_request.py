#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys


def _normalize_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def validate_request(
    *,
    target: str,
    ref_name: str,
    apply_infra: bool,
    deploy_bundle: bool,
    required_env: list[str],
) -> dict[str, object]:
    errors: list[str] = []

    if target == "prod" and ref_name not in {"main", "master"}:
        errors.append("prod deployments are only allowed from main or master")

    if not apply_infra and not deploy_bundle:
        errors.append("at least one of apply_infra or deploy_bundle must be true")

    missing_env = [name for name in required_env if not os.getenv(name)]
    if missing_env:
        errors.append(f"missing required environment variables: {', '.join(missing_env)}")

    return {
        "target": target,
        "ref_name": ref_name,
        "apply_infra": apply_infra,
        "deploy_bundle": deploy_bundle,
        "required_env": required_env,
        "missing_env": missing_env,
        "valid": not errors,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate release workflow context and required environment variables")
    parser.add_argument("--target", required=True, choices=["dev", "prod"])
    parser.add_argument("--ref-name", required=True)
    parser.add_argument("--apply-infra", default="false")
    parser.add_argument("--deploy-bundle", default="false")
    parser.add_argument("--check-env", action="append", default=[])
    args = parser.parse_args()

    result = validate_request(
        target=args.target,
        ref_name=args.ref_name,
        apply_infra=_normalize_bool(args.apply_infra),
        deploy_bundle=_normalize_bool(args.deploy_bundle),
        required_env=args.check_env,
    )
    print(json.dumps(result))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
