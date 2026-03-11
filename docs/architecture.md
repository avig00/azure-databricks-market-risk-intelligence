# Architecture Notes

This implementation is local-first and Databricks-compatible.

- Local storage materializes datasets under `data/local/{layer}` using the configured `LOCAL_STORAGE_FORMAT` (`parquet` by default).
- Logical table names mirror Unity Catalog naming such as `finance.gold.asset_risk_features`.
- Azure resource placeholders are carried through configuration only in the early milestones.
- Streaming is scaffolded for future Azure Event Hubs or Databricks Structured Streaming integration.
- `USE_SAMPLE_DATA=true` runs a deterministic local sample provider for repeatable development and tests.
- `USE_SAMPLE_DATA=false` switches ingestion to live Yahoo Finance and FRED providers. FRED requires `FRED_API_KEY`.
- Dashboard consumers read only from Gold datasets and trained model artifacts; they do not recompute analytics.
- Model artifacts are written locally under the configured artifact root, but the folder structure is intended to map cleanly to MLflow or Databricks-managed artifact storage later.

## Azure-owned components in this repo

- ADLS path placeholders and container naming in config
- Key Vault placeholder names for secrets resolution
- Terraform scaffolding under `infra/terraform`
- Data Factory / Event Hubs integration points in docs and streaming scaffold

## Databricks-owned components in this repo

- Medallion dataset contracts and Unity Catalog-compatible table names
- Spark-compatible logical pipeline stages: Bronze, Silver, Gold
- Feature store and ML stage boundaries
- Databricks job-friendly stage entrypoints via `python -m market_risk_platform.main`

## Execution patterns

- `run-all` builds Bronze, Silver, Gold, features, and both ML models in sequence for local validation or scheduled batch jobs.
- `simulate --assets ... --weights ... --horizon ...` provides a thin command-line interface for scenario testing.
- `dashboard-summary` returns the latest Gold-layer dashboard payload for lightweight health checks or API wrapping.
- The Streamlit dashboard reads persisted datasets and model artifacts rather than training or transforming inline.
- The storage layer is format-aware so local development can use Parquet now without changing upstream dataset contracts or downstream consumers.
- `STORAGE_BACKEND=databricks` now routes dataset reads and writes through a Spark/Delta adapter, while `STORAGE_BACKEND=local` keeps using local files.
