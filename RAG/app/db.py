"""PostgreSQL helper for querying ingested crop, yield, nutrient, and soil tables."""

from __future__ import annotations

import datetime
import logging
import math
import os
import re
import threading
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

RAG_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = RAG_ROOT.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(RAG_ROOT / ".env")

DEFAULT_DATABASE_URL = "postgresql+psycopg2://agro_user:agro_password@localhost:5432/kherson_crop_db"

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "for",
        "from",
        "get",
        "give",
        "have",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "please",
        "show",
        "tell",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "with",
        "would",
    }
)

_DOMAIN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "wheat": ("broadbalk", "grain", "straw", "wheat", "yld", "crop"),
    "grain": ("broadbalk", "grain", "wheat", "yield"),
    "straw": ("broadbalk", "straw", "wheat"),
    "broadbalk": ("broadbalk", "bk", "wheat", "grain", "straw"),
    "corn": ("corn", "maize", "hoytville", "wooster", "cimmyt", "texcoco"),
    "maize": ("corn", "maize", "cimmyt", "texcoco"),
    "soybean": ("soybean", "hoytville", "wooster"),
    "yield": ("yield", "cropyield", "yld", "harvest", "production"),
    "soil": ("soil", "soilparameter", "ph", "organic", "carbon", "clay", "sand", "silt", "moisture"),
    "ph": ("soil", "soilparameter", "ph"),
    "nutrient": ("nutrient", "nutr", "element", "trace", "nitrogen", "phosphorus", "potassium", "fym", "mg", "na"),
    "nitrogen": ("nitrogen", "n_factor", "nutrient", "fertilizer", "urea"),
    "phosphorus": ("phosphorus", "p_factor", "nutrient", "phosphate"),
    "potassium": ("potassium", "k_factor", "nutrient", "potash"),
    "fertilizer": ("fym", "factor", "management", "nutrient", "rape_cake"),
    "manure": ("fym", "factor", "management"),
    "rotation": ("rotation", "kherson", "marchfeld", "management", "sequence", "crop"),
    "kherson": ("kherson", "rotation", "marchfeld", "crop"),
    "marchfeld": ("marchfeld", "cropyield", "soilparameter", "management"),
    "cimmyt": ("cimmyt", "texcoco", "dat_h9texcoco"),
    "texcoco": ("cimmyt", "texcoco", "dat_h9texcoco"),
    "climate": ("climate", "weather", "rain", "precip", "temp", "drought", "kherson"),
    "drought": ("climate", "soil", "kherson", "rotation"),
}

_FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|COPY|EXECUTE|CALL|ATTACH|PRAGMA)\b",
    re.IGNORECASE,
)


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL


def _serialize_value(value: Any) -> Any:
    """Convert SQLAlchemy / pandas / Decimal / datetime values into JSON-safe primitives."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (str, int, bool)):
        return value
    return str(value)


def _validate_readonly_sql(sql_query: str) -> str:
    """Validate that a SQL string is a single read-only SELECT statement."""
    if not sql_query or not isinstance(sql_query, str):
        raise ValueError("SQL query must be a non-empty string.")
    stripped = sql_query.strip()
    if ";" in stripped:
        raise ValueError("Multiple SQL statements or semicolons are not permitted.")
    if not re.match(r"^SELECT\b", stripped, re.IGNORECASE):
        raise ValueError("Only SELECT queries are permitted.")
    if _FORBIDDEN_SQL_PATTERN.search(stripped):
        raise ValueError("Query contains forbidden SQL keywords.")
    return stripped


class PostgresHelper:
    """Lazy-initialized read-only query helper over PostgreSQL crop/soil tables."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url
        self._engine: Engine | None = None
        self._lock = threading.Lock()

    @property
    def database_url(self) -> str:
        return self._database_url or get_database_url()

    def get_engine(self) -> Engine:
        with self._lock:
            if self._engine is None:
                url = self.database_url
                kwargs: dict[str, Any] = {"pool_pre_ping": True}
                if url.startswith("postgresql"):
                    kwargs["connect_args"] = {"connect_timeout": 3}
                self._engine = create_engine(url, **kwargs)
            return self._engine

    def list_tables(self) -> list[str]:
        try:
            engine = self.get_engine()
            inspector = inspect(engine)
            schema = "public" if engine.dialect.name == "postgresql" else None
            return sorted(inspector.get_table_names(schema=schema))
        except (SQLAlchemyError, OSError) as exc:
            logger.warning("Failed to list PostgreSQL tables: %s", exc)
            return []

    def check_status(self) -> dict[str, Any]:
        try:
            engine = self.get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            tables = self.list_tables()
            return {
                "connected": True,
                "table_count": len(tables),
                "tables": tables[:30],
            }
        except (SQLAlchemyError, OSError) as exc:
            logger.warning("PostgreSQL health check failed: %s", exc)
            return {
                "connected": False,
                "table_count": 0,
                "tables": [],
                "error": str(exc),
            }

    def get_table_schemas(self, max_tables: int = 50) -> dict[str, list[str]]:
        try:
            engine = self.get_engine()
            inspector = inspect(engine)
            schema = "public" if engine.dialect.name == "postgresql" else None
            tables = sorted(inspector.get_table_names(schema=schema))[:max_tables]
            schemas: dict[str, list[str]] = {}
            for table in tables:
                cols = inspector.get_columns(table, schema=schema)
                schemas[table] = [str(col["name"]) for col in cols]
            return schemas
        except (SQLAlchemyError, OSError) as exc:
            logger.warning("Failed to inspect PostgreSQL schemas: %s", exc)
            return {}

    def execute_readonly_query(
        self,
        sql_query: str,
        params: dict[str, Any] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clean_sql = _validate_readonly_sql(sql_query)
        safe_limit = max(1, min(int(limit), 200))
        engine = self.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(clean_sql), params or {})
            keys = list(result.keys())
            rows = result.fetchmany(safe_limit)
            return [
                {col: _serialize_value(val) for col, val in zip(keys, row)}
                for row in rows
            ]

    def _expand_keywords(self, query: str) -> set[str]:
        raw_tokens = re.findall(r"[a-z0-9_]+", query.lower())
        keywords: set[str] = set()
        for token in raw_tokens:
            if len(token) < 2 or token in _STOP_WORDS:
                continue
            keywords.add(token)
            for syn in _DOMAIN_SYNONYMS.get(token, ()):
                keywords.add(syn)
        return keywords

    def query_relevant_sql_data(
        self,
        query: str,
        max_tables: int = 4,
        rows_per_table: int = 8,
    ) -> list[dict[str, Any]]:
        if not query or not query.strip() or max_tables <= 0:
            return []

        try:
            schemas = self.get_table_schemas(max_tables=100)
            if not schemas:
                return []

            keywords = self._expand_keywords(query)
            scored: list[tuple[int, str]] = []
            for table_name, cols in schemas.items():
                table_lower = table_name.lower()
                cols_lower = " ".join(c.lower() for c in cols)
                score = 0
                for kw in keywords:
                    if kw in table_lower:
                        score += 3
                    if kw in cols_lower:
                        score += 1
                if score > 0:
                    scored.append((score, table_name))

            scored.sort(key=lambda item: (-item[0], item[1]))
            selected_tables = [name for _, name in scored[:max_tables]]

            if not selected_tables:
                priority_hints = ("yield", "soil", "crop", "kherson", "marchfeld", "nutrient", "element")
                fallback = [
                    name
                    for name in schemas
                    if any(hint in name.lower() for hint in priority_hints)
                ]
                selected_tables = (fallback or list(schemas.keys()))[:max_tables]

            engine = self.get_engine()
            preparer = engine.dialect.identifier_preparer
            results: list[dict[str, Any]] = []
            safe_rows = max(1, min(int(rows_per_table), 25))

            with engine.connect() as conn:
                for table_name in selected_tables:
                    quoted_table = preparer.quote_identifier(table_name)
                    count_row = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}")).scalar()
                    total_rows = int(count_row or 0)
                    res = conn.execute(
                        text(f"SELECT * FROM {quoted_table} LIMIT :limit"),
                        {"limit": safe_rows},
                    )
                    keys = list(res.keys())
                    fetched = res.fetchall()
                    sample_rows = [
                        {col: _serialize_value(val) for col, val in zip(keys, row)}
                        for row in fetched
                    ]
                    results.append(
                        {
                            "table": table_name,
                            "columns": schemas.get(table_name, keys),
                            "row_count": total_rows,
                            "sample_rows": sample_rows,
                        }
                    )
            return results
        except (SQLAlchemyError, OSError) as exc:
            logger.warning("PostgreSQL query_relevant_sql_data failed: %s", exc)
            return []


_default_db = PostgresHelper()


def check_postgres_status() -> dict[str, Any]:
    """Check PostgreSQL connectivity and list ingested tables."""
    return _default_db.check_status()


def list_tables() -> list[str]:
    """Return sorted list of tables in PostgreSQL."""
    return _default_db.list_tables()


def get_table_schemas(max_tables: int = 50) -> dict[str, list[str]]:
    """Return mapping of PostgreSQL table names to column names."""
    return _default_db.get_table_schemas(max_tables=max_tables)


def execute_readonly_query(
    sql_query: str,
    params: dict[str, Any] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Execute a validated read-only SELECT query against PostgreSQL."""
    return _default_db.execute_readonly_query(sql_query, params=params, limit=limit)


def query_relevant_sql_data(
    query: str,
    max_tables: int = 4,
    rows_per_table: int = 8,
) -> list[dict[str, Any]]:
    """Find and sample relevant crop/soil PostgreSQL tables for a natural-language query."""
    return _default_db.query_relevant_sql_data(
        query, max_tables=max_tables, rows_per_table=rows_per_table
    )
