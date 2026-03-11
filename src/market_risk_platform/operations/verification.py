from __future__ import annotations

from dataclasses import dataclass, asdict

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.dashboard.app import build_dashboard_payload, summarize_dashboard
from market_risk_platform.operations.health import build_health_report
from market_risk_platform.utils import read_dataset


@dataclass(frozen=True)
class RuntimeContractStatus:
    runtime_mode: str
    storage_backend: str
    supported: bool
    issues: list[str]
    required_secret_scope_keys: list[str]
    catalog_name: str


@dataclass(frozen=True)
class DeploymentVerificationReport:
    runtime_contract: RuntimeContractStatus
    verified_datasets: dict[str, dict[str, object]]
    model_artifacts: dict[str, bool]
    dashboard_summary_available: bool
    latest_stage_successful: bool
    checks_passed: bool


def build_runtime_contract_status(config: AppConfig | None = None) -> RuntimeContractStatus:
    config = config or load_config()
    issues: list[str] = []
    supported_runtime_modes = {"local", "databricks-dev", "databricks-prod"}
    if config.runtime_mode not in supported_runtime_modes:
        issues.append(f"unsupported runtime_mode={config.runtime_mode}")

    if config.runtime_mode == "local" and config.storage_backend != "local":
        issues.append("local runtime_mode requires STORAGE_BACKEND=local")

    if config.runtime_mode.startswith("databricks"):
        if config.storage_backend != "databricks":
            issues.append("databricks runtime_mode requires STORAGE_BACKEND=databricks")
        if not config.databricks_secret_scope:
            issues.append("databricks runtime_mode requires DATABRICKS_SECRET_SCOPE")
        if not config.fred_api_key_secret_key:
            issues.append("databricks runtime_mode requires FRED_API_KEY_SECRET_KEY")

    return RuntimeContractStatus(
        runtime_mode=config.runtime_mode,
        storage_backend=config.storage_backend,
        supported=not issues,
        issues=issues,
        required_secret_scope_keys=["FRED_API_KEY_SECRET_KEY"] if config.runtime_mode.startswith("databricks") else [],
        catalog_name=config.catalog.catalog,
    )


def _verify_dataset(contract_key: str, config: AppConfig) -> dict[str, object]:
    contract = config.dataset_contracts()[contract_key]
    dataset = read_dataset(contract, config)
    return {
        "table_name": contract.table_name,
        "rows": int(len(dataset)),
        "columns": list(dataset.columns),
        "location": contract.adls_path if config.storage_backend == "databricks" else str(contract.local_path),
    }


def build_deployment_verification_report(config: AppConfig | None = None) -> DeploymentVerificationReport:
    config = config or load_config()
    runtime_contract = build_runtime_contract_status(config)
    health = build_health_report(config)
    verified_datasets = {
        key: _verify_dataset(key, config)
        for key in [
            "gold_asset_risk_features",
            "gold_market_stress_signals",
            "gold_portfolio_risk_metrics",
            "features_asset_training",
            "features_portfolio_training",
        ]
    }
    dashboard_summary = summarize_dashboard(build_dashboard_payload())
    model_artifacts = {
        artifact_name: artifact_timestamp is not None
        for artifact_name, artifact_timestamp in health.latest_model_artifacts.items()
    }
    checks_passed = (
        runtime_contract.supported
        and all(item["rows"] > 0 for item in verified_datasets.values())
        and all(model_artifacts.values())
        and bool(dashboard_summary)
        and health.latest_successful_stage is not None
    )
    return DeploymentVerificationReport(
        runtime_contract=runtime_contract,
        verified_datasets=verified_datasets,
        model_artifacts=model_artifacts,
        dashboard_summary_available=bool(dashboard_summary),
        latest_stage_successful=health.latest_successful_stage is not None,
        checks_passed=checks_passed,
    )


def verification_report_dict(config: AppConfig | None = None) -> dict[str, object]:
    report = build_deployment_verification_report(config)
    payload = asdict(report)
    payload["runtime_contract"]["required_secret_scope_keys"] = report.runtime_contract.required_secret_scope_keys
    return payload
