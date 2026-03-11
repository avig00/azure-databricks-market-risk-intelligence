from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class SparkAdapter(ABC):
    @abstractmethod
    def read_dataset(self, table_name: str, storage_path: str) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def write_dataset(self, table_name: str, storage_path: str, dataframe: pd.DataFrame) -> str:
        raise NotImplementedError


class PysparkDeltaAdapter(SparkAdapter):
    def __init__(self) -> None:
        from pyspark.sql import SparkSession

        self.spark = SparkSession.getActiveSession() or SparkSession.builder.appName(
            "market-risk-platform-delta-backend"
        ).enableHiveSupport().getOrCreate()

    def _ensure_schema(self, table_name: str) -> None:
        catalog, schema, _ = table_name.split(".", maxsplit=2)
        self.spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
        self.spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

    def read_dataset(self, table_name: str, storage_path: str) -> pd.DataFrame:
        try:
            return self.spark.table(table_name).toPandas()
        except Exception:
            return self.spark.read.format("delta").load(storage_path).toPandas()

    def write_dataset(self, table_name: str, storage_path: str, dataframe: pd.DataFrame) -> str:
        self._ensure_schema(table_name)
        spark_frame = self.spark.createDataFrame(dataframe)
        (
            spark_frame.write.format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .option("path", storage_path)
            .saveAsTable(table_name)
        )
        return table_name

