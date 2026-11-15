"""ETL pipeline for extracting nested archives and ingesting datasets into PostgreSQL and Qdrant."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import uuid
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pdfplumber
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://agro_user:agro_password@localhost:5432/kherson_crop_db",
)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "agronomy_knowledge")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
BATCH_SIZE = 64

TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin1")
NA_VALUES = [".", " .", ". "]
MAX_TABLE_NAME_LEN = 60


def _long_path(path: Path) -> Path:
    """Return a Windows extended-length path (\\\\?\\) when running on Windows."""
    resolved = path.resolve()
    if os.name == "nt":
        raw = str(resolved)
        if not raw.startswith("\\\\?\\"):
            if raw.startswith("\\\\"):
                return Path("\\\\?\\UNC\\" + raw.lstrip("\\"))
            return Path("\\\\?\\" + raw)
    return resolved


def extract_all_zips(data_dir: Path = DATA_DIR) -> None:
    """Recursively extract all .zip archives under data_dir into sibling folders."""
    logger.info("Step 0: Scanning '%s' for zip archives...", data_dir)
    if not data_dir.exists():
        logger.warning("Data directory '%s' does not exist. Skipping zip extraction.", data_dir)
        return

    processed_zips: set[Path] = set()
    extracted_count = 0

    while True:
        zip_files = sorted(
            p for p in data_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".zip"
        )
        new_zips = [p for p in zip_files if p.resolve() not in processed_zips]
        if not new_zips:
            break

        for zip_path in new_zips:
            resolved_zip = zip_path.resolve()
            processed_zips.add(resolved_zip)
            target_dir = zip_path.with_suffix("")
            try:
                target_dir_long = _long_path(target_dir)
                target_dir_long.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(_long_path(zip_path), "r") as zf:
                    zf.extractall(str(target_dir_long))
                extracted_count += 1
                logger.info(
                    "Extracted '%s' -> '%s'",
                    zip_path.relative_to(data_dir),
                    target_dir.relative_to(data_dir),
                )
            except (zipfile.BadZipFile, OSError, ValueError) as exc:
                logger.warning("Skipping corrupted or unreadable zip '%s': %s", zip_path, exc)

    logger.info("Step 0 complete: Extracted %d zip archive(s).", extracted_count)


def _sanitize_identifier(raw: str, max_len: int = MAX_TABLE_NAME_LEN, prefix: str = "t_", fallback: str = "table") -> str:
    """Sanitize a string into a lowercase alphanumeric+underscore identifier."""
    cleaned = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"{prefix}{cleaned}"
    return cleaned[:max_len].rstrip("_") or fallback


def _build_unique_table_name(
    file_path: Path,
    data_dir: Path,
    used_names: set[str],
    sheet_name: str | None = None,
) -> str:
    """Create a collision-free PostgreSQL table name (<= 60 chars)."""
    rel_path = file_path.relative_to(data_dir)
    stem_part = _sanitize_identifier(file_path.stem, max_len=MAX_TABLE_NAME_LEN, fallback="data")

    parts: list[str] = []
    if rel_path.parent != Path("."):
        parent_part = _sanitize_identifier(rel_path.parent.name, max_len=24, fallback="")
        if parent_part and parent_part != stem_part:
            parts.append(parent_part)
    parts.append(stem_part)

    if sheet_name:
        sheet_part = _sanitize_identifier(sheet_name, max_len=20, fallback="sheet")
        parts.append(sheet_part)

    base = _sanitize_identifier("_".join(parts), max_len=MAX_TABLE_NAME_LEN, fallback="table")
    candidate = base
    counter = 2
    while candidate in used_names:
        suffix = f"_{counter}"
        candidate = f"{base[: MAX_TABLE_NAME_LEN - len(suffix)].rstrip('_')}{suffix}"
        counter += 1

    used_names.add(candidate)
    return candidate


def _sanitize_columns(columns: pd.Index) -> list[str]:
    """Sanitize and deduplicate DataFrame column names for PostgreSQL."""
    seen: dict[str, int] = {}
    result: list[str] = []
    for idx, col in enumerate(columns):
        base = _sanitize_identifier(str(col), max_len=63, prefix="c_", fallback=f"col_{idx}")
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count > 1:
            suffix = f"_{count}"
            col_name = f"{base[: 63 - len(suffix)].rstrip('_')}{suffix}"
        else:
            col_name = base
        result.append(col_name)
    return result


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Replace dot placeholders with NaN and sanitize column names."""
    cleaned = df.replace(to_replace=r"^\s*\.\s*$", value=np.nan, regex=True)
    cleaned.columns = _sanitize_columns(cleaned.columns)
    return cleaned


def _detect_csv_separator(header_line: str) -> str | None:
    """Infer CSV delimiter from header line, returning None for pandas auto-detection."""
    semi_count = header_line.count(";")
    comma_count = header_line.count(",")
    if semi_count > comma_count:
        return ";"
    if comma_count > 0:
        return ","
    return None


def _read_csv_flexible(file_path: Path) -> pd.DataFrame:
    """Read a CSV trying common encodings and inferring ';' vs ',' delimiters."""
    long_p = _long_path(file_path)
    last_exc: Exception | None = None

    for encoding in TEXT_ENCODINGS:
        try:
            with open(long_p, "r", encoding=encoding) as f:
                header_line = ""
                for line in f:
                    if line.strip():
                        header_line = line
                        break

            sep = _detect_csv_separator(header_line)
            with open(long_p, "r", encoding=encoding) as f:
                if sep is None:
                    df = pd.read_csv(
                        f,
                        sep=None,
                        engine="python",
                        na_values=NA_VALUES,
                        keep_default_na=True,
                    )
                else:
                    df = pd.read_csv(
                        f,
                        sep=sep,
                        na_values=NA_VALUES,
                        keep_default_na=True,
                        low_memory=False,
                    )
            return _clean_dataframe(df)
        except UnicodeDecodeError as exc:
            last_exc = exc
            continue

    raise ValueError(f"Unable to decode CSV with supported encodings: {last_exc}")


def ingest_sql(engine: Engine, data_dir: Path = DATA_DIR) -> None:
    """Traverse data_dir for .csv and .xlsx files and load tables into PostgreSQL."""
    logger.info("Step 1: Scanning '%s' for CSV and Excel files...", data_dir)
    if not data_dir.exists():
        logger.warning("Data directory '%s' does not exist. Skipping SQL ingestion.", data_dir)
        return

    tabular_files = sorted(
        p
        for p in data_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".csv", ".xlsx"}
    )

    used_table_names: set[str] = set()
    tables_loaded = 0

    for file_path in tabular_files:
        rel_display = file_path.relative_to(data_dir)
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            try:
                df = _read_csv_flexible(file_path)
                if len(df.columns) == 0:
                    logger.warning("Skipping empty CSV '%s'.", rel_display)
                    continue
                table_name = _build_unique_table_name(file_path, data_dir, used_table_names)
                df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=1000)
                tables_loaded += 1
                logger.info("Loaded CSV '%s' -> table '%s' (%d rows).", rel_display, table_name, len(df))
            except Exception as exc:  # noqa: BLE001 — per-file ETL recovery.
                logger.warning("Failed to ingest CSV '%s': %s", rel_display, exc)

        elif suffix == ".xlsx":
            try:
                with open(_long_path(file_path), "rb") as f:
                    sheets: dict[str, pd.DataFrame] = pd.read_excel(
                        f,
                        sheet_name=None,
                        na_values=NA_VALUES,
                        keep_default_na=True,
                        engine="openpyxl",
                    )
            except Exception as exc:  # noqa: BLE001 — per-file ETL recovery.
                logger.warning("Failed to open Excel workbook '%s': %s", rel_display, exc)
                continue

            multi_sheet = len(sheets) > 1
            for sheet_name, raw_df in sheets.items():
                try:
                    if raw_df.empty and len(raw_df.columns) == 0:
                        logger.warning("Skipping empty sheet '%s' in '%s'.", sheet_name, rel_display)
                        continue
                    df = _clean_dataframe(raw_df)
                    if len(df.columns) == 0:
                        continue
                    table_name = _build_unique_table_name(
                        file_path,
                        data_dir,
                        used_table_names,
                        sheet_name=sheet_name if multi_sheet else None,
                    )
                    df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=1000)
                    tables_loaded += 1
                    logger.info(
                        "Loaded Excel '%s' [sheet: %s] -> table '%s' (%d rows).",
                        rel_display,
                        sheet_name,
                        table_name,
                        len(df),
                    )
                except Exception as exc:  # noqa: BLE001 — per-sheet ETL recovery.
                    logger.warning(
                        "Failed to ingest sheet '%s' from '%s': %s",
                        sheet_name,
                        rel_display,
                        exc,
                    )

    logger.info("Step 1 complete: Loaded %d table(s) into PostgreSQL.", tables_loaded)


def _read_text_with_fallback(file_path: Path) -> str:
    """Read a text file trying UTF-8 and common Windows/Latin encodings."""
    long_p = _long_path(file_path)
    last_exc: Exception | None = None
    for encoding in TEXT_ENCODINGS:
        try:
            with open(long_p, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError as exc:
            last_exc = exc
    raise ValueError(f"Unable to decode text file: {last_exc}")


def _format_json_value(value: Any) -> str:
    """Format nested JSON values into compact readable strings."""
    if isinstance(value, dict):
        return ", ".join(f"{k}={_format_json_value(v)}" for k, v in value.items())
    if isinstance(value, list):
        return "; ".join(_format_json_value(item) for item in value)
    return str(value)


def _format_json_record(record: Any) -> str:
    """Format a parsed JSONL line into readable key-value text."""
    if isinstance(record, dict):
        lines = [f"{key}: {_format_json_value(val)}" for key, val in record.items()]
        return "\n".join(lines)
    return _format_json_value(record)


def _extract_jsonl_text(file_path: Path) -> str:
    """Parse JSONL records and format each object as readable key-value text."""
    raw_text = _read_text_with_fallback(file_path)
    records: list[str] = []
    for line_num, line in enumerate(raw_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
            formatted = _format_json_record(obj)
            if formatted.strip():
                records.append(formatted)
        except json.JSONDecodeError as exc:
            logger.warning("Skipping malformed JSON line %d in '%s': %s", line_num, file_path.name, exc)
    return "\n\n---\n\n".join(records)


def _extract_pdf_text(file_path: Path) -> str:
    """Extract text from all readable pages of a PDF using pdfplumber."""
    pages_text: list[str] = []
    with open(_long_path(file_path), "rb") as f, pdfplumber.open(f) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_text.append(page_text.strip())
            except Exception as exc:  # noqa: BLE001 — per-page PDF extraction recovery.
                logger.warning(
                    "Failed to extract page %d from PDF '%s': %s",
                    page_idx,
                    file_path.name,
                    exc,
                )
    return "\n\n".join(pages_text)


def ingest_vector(qdrant_client: QdrantClient, data_dir: Path = DATA_DIR) -> None:
    """Extract text from .jsonl, .md, and .pdf files, chunk, embed, and upsert into Qdrant."""
    logger.info("Step 2: Scanning '%s' for JSONL, Markdown, and PDF files...", data_dir)
    if not data_dir.exists():
        logger.warning("Data directory '%s' does not exist. Skipping vector ingestion.", data_dir)
        return

    if not qdrant_client.collection_exists(QDRANT_COLLECTION):
        qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s'.", QDRANT_COLLECTION)
    else:
        logger.info("Using existing Qdrant collection '%s'.", QDRANT_COLLECTION)

    logger.info("Loading embedding model '%s'...", EMBEDDING_MODEL_NAME)
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    text_files = sorted(
        p
        for p in data_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".jsonl", ".md", ".pdf"}
    )

    total_chunks = 0
    files_indexed = 0

    for file_path in text_files:
        rel_source = file_path.relative_to(data_dir).as_posix()
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".jsonl":
                content = _extract_jsonl_text(file_path)
            elif suffix == ".md":
                content = _read_text_with_fallback(file_path)
            elif suffix == ".pdf":
                content = _extract_pdf_text(file_path)
            else:
                continue
        except Exception as exc:  # noqa: BLE001 — per-file parsing recovery.
            logger.warning("Failed to parse '%s': %s", rel_source, exc)
            continue

        if not content.strip():
            logger.warning("No extractable text found in '%s'. Skipping.", rel_source)
            continue

        chunks = text_splitter.split_text(content)
        if not chunks:
            continue

        try:
            for start in range(0, len(chunks), BATCH_SIZE):
                batch_chunks = chunks[start : start + BATCH_SIZE]
                embeddings = model.encode(batch_chunks, show_progress_bar=False)
                points = [
                    PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{rel_source}::{start + offset}")),
                        vector=embedding.tolist(),
                        payload={"source_file": rel_source, "text": chunk},
                    )
                    for offset, (chunk, embedding) in enumerate(zip(batch_chunks, embeddings))
                ]
                qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=points)

            files_indexed += 1
            total_chunks += len(chunks)
            logger.info("Indexed '%s' (%d chunk(s)).", rel_source, len(chunks))
        except Exception as exc:  # noqa: BLE001 — per-file embedding/upsert recovery.
            logger.warning("Failed to embed/upsert chunks for '%s': %s", rel_source, exc)

    logger.info(
        "Step 2 complete: Indexed %d file(s) and %d chunk(s) into Qdrant collection '%s'.",
        files_indexed,
        total_chunks,
        QDRANT_COLLECTION,
    )


def _postgres_has_tables(engine: Engine) -> bool:
    try:
        tables = inspect(engine).get_table_names(schema="public")
        return len(tables) > 0
    except Exception as exc:  # noqa: BLE001 — treat unreachable DB as unpopulated.
        logger.warning("Could not inspect PostgreSQL tables: %s", exc)
        return False


def _qdrant_has_points(client: QdrantClient, collection: str) -> bool:
    try:
        if not client.collection_exists(collection):
            return False
        info = client.get_collection(collection)
        return int(getattr(info, "points_count", 0) or 0) > 0
    except Exception as exc:  # noqa: BLE001 — treat unreachable Qdrant as unpopulated.
        logger.warning("Could not inspect Qdrant collection '%s': %s", collection, exc)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest AgroResilience datasets into PostgreSQL and Qdrant.")
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Only ingest PostgreSQL or Qdrant if the respective store is empty.",
    )
    args = parser.parse_args()

    logger.info("Connecting to PostgreSQL...")
    sql_engine = create_engine(DATABASE_URL)
    logger.info("Connecting to Qdrant at '%s'...", QDRANT_URL)
    qdrant = QdrantClient(url=QDRANT_URL)

    try:
        need_sql = True
        need_qdrant = True
        if args.if_empty:
            need_sql = not _postgres_has_tables(sql_engine)
            need_qdrant = not _qdrant_has_points(qdrant, QDRANT_COLLECTION)
            if not need_sql and not need_qdrant:
                logger.info("Databases already populated; skipping ingestion.")
                raise SystemExit(0)

        logger.info("Starting ETL ingestion pipeline...")
        extract_all_zips(DATA_DIR)

        if need_sql:
            ingest_sql(sql_engine, DATA_DIR)
        else:
            logger.info("PostgreSQL already has ingested tables; skipping SQL step.")

        if need_qdrant:
            ingest_vector(qdrant, DATA_DIR)
        else:
            logger.info("Qdrant collection '%s' already populated; skipping vector step.", QDRANT_COLLECTION)

        logger.info("ETL pipeline finished.")
    finally:
        sql_engine.dispose()
