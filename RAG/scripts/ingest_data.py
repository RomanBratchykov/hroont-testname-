"""ETL pipeline for extracting nested archives and ingesting datasets into PostgreSQL and Qdrant."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import stat
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
from sqlalchemy import create_engine, inspect, text
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

DATA_DIR = Path(os.getenv("RAG_DATA_DIR", str(PROJECT_ROOT / "rag" / "data")))

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
    """Extract nested ZIPs with traversal, symlink, size and nesting limits."""
    if not data_dir.is_dir():
        raise ValueError(f"Data directory does not exist: {data_dir}")
    processed: set[Path] = set()
    total_bytes = 0
    total_members = 0
    for depth in range(9):
        archives = sorted(
            p
            for p in data_dir.rglob("*")
            if p.suffix.lower() == ".zip" and p not in processed
        )
        if not archives:
            return
        if depth == 8:
            raise ValueError("ZIP nesting exceeds eight levels")
        for archive in archives:
            processed.add(archive)
            target = archive.with_suffix("").resolve()
            if not target.is_relative_to(data_dir.resolve()):
                raise ValueError("Archive extraction target escapes data directory")
            with zipfile.ZipFile(archive) as zipped:
                members = zipped.infolist()
                for member in members:
                    destination = (target / member.filename).resolve()
                    if (
                        not destination.is_relative_to(target)
                        or "\\" in member.filename
                        or stat.S_ISLNK(member.external_attr >> 16)
                    ):
                        raise ValueError(f"Unsafe ZIP member: {member.filename}")
                    total_bytes += member.file_size
                    total_members += 1
                    if (
                        member.file_size > 512 * 1024**2
                        or total_bytes > 4 * 1024**3
                        or total_members > 50000
                    ):
                        raise ValueError("ZIP extraction resource limit exceeded")
                for member in members:
                    destination = target / member.filename
                    if member.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    # Existing complete files are preserved across restarts.
                    if (
                        destination.exists()
                        and destination.stat().st_size == member.file_size
                    ):
                        continue
                    temporary = destination.with_name(destination.name + ".extracting")
                    with zipped.open(member) as source, temporary.open("wb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                    temporary.replace(destination)


def source_metadata(source: str) -> dict[str, Any]:
    """Use explicit source labels only; Drive export timestamps are not coverage dates."""
    label = re.sub(r"-\d{8}T\d{6}Z-\d+-\d+", "", source)
    region = next(
        (
            name
            for token, name in (
                ("kherson", "Kherson"),
                ("broadbalk", "United Kingdom"),
                ("texcoco", "Mexico"),
                ("marchfeld", "Austria"),
            )
            if token in label.lower()
        ),
        None,
    )
    match = re.search(r"(?<!\d)((?:19|20)\d{2})[-–]((?:19|20)\d{2})(?!\d)", label)
    start, end = (int(match[1]), int(match[2])) if match else (None, None)
    return {
        "region": region.lower() if region else None,
        "start_year": start,
        "end_year": end,
    }


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sanitize_identifier(
    raw: str,
    max_len: int = MAX_TABLE_NAME_LEN,
    prefix: str = "t_",
    fallback: str = "table",
) -> str:
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
    stem_part = _sanitize_identifier(
        file_path.stem, max_len=MAX_TABLE_NAME_LEN, fallback="data"
    )

    parts: list[str] = []
    if rel_path.parent != Path("."):
        parent_part = _sanitize_identifier(
            rel_path.parent.name, max_len=24, fallback=""
        )
        if parent_part and parent_part != stem_part:
            parts.append(parent_part)
    parts.append(stem_part)

    if sheet_name:
        sheet_part = _sanitize_identifier(sheet_name, max_len=20, fallback="sheet")
        parts.append(sheet_part)

    base = _sanitize_identifier(
        "_".join(parts), max_len=MAX_TABLE_NAME_LEN, fallback="table"
    )
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
        base = _sanitize_identifier(
            str(col), max_len=63, prefix="c_", fallback=f"col_{idx}"
        )
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
                        sep=",",
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
    """Commit each source and its manifest atomically; never replace existing tables."""
    failures = []
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS rag_ingestion_sources (source_file TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, table_names TEXT NOT NULL, region TEXT, start_year INTEGER, end_year INTEGER)"
            )
        )
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".xlsx"}:
            continue
        source = path.relative_to(data_dir).as_posix()
        digest = fingerprint(path)
        metadata = source_metadata(source)
        try:
            with engine.begin() as connection:
                previous = connection.execute(
                    text(
                        "SELECT fingerprint FROM rag_ingestion_sources WHERE source_file=:source"
                    ),
                    {"source": source},
                ).scalar()
                if previous == digest:
                    continue
                if previous:
                    raise ValueError(
                        "Previously ingested source changed; explicit migration required"
                    )
                sheets = (
                    {"data": _read_csv_flexible(path)}
                    if path.suffix.lower() == ".csv"
                    else pd.read_excel(
                        path, sheet_name=None, engine="openpyxl", na_values=NA_VALUES
                    )
                )
                tables = []
                for sheet, raw in sheets.items():
                    df = _clean_dataframe(raw)
                    if not len(df.columns):
                        continue
                    identity = hashlib.sha256(
                        f"{source}::{sheet}".encode()
                    ).hexdigest()[:16]
                    table = (
                        f"rag_{_sanitize_identifier(path.stem, max_len=35)}_{identity}"
                    )
                    for key, value in {"source_file": source, **metadata}.items():
                        df[f"_rag_{key}"] = value
                    df.to_sql(
                        table, connection, if_exists="fail", index=False, chunksize=1000
                    )
                    tables.append(table)
                connection.execute(
                    text(
                        "INSERT INTO rag_ingestion_sources (source_file, fingerprint, table_names, region, start_year, end_year) VALUES (:source_file, :fingerprint, :table_names, :region, :start_year, :end_year)"
                    ),
                    {
                        "source_file": source,
                        "fingerprint": digest,
                        "table_names": json.dumps(tables),
                        **metadata,
                    },
                )
                logger.info("Loaded %s (%d tables)", source, len(tables))
        except Exception as exc:  # noqa: BLE001 — preserve other sources and report failed exit.
            failures.append(source)
            logger.error("Failed SQL source %s: %s", source, exc)
    if failures:
        raise RuntimeError(f"SQL ingestion failed for {len(failures)} source(s)")


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
            raise ValueError(
                f"Malformed JSON line {line_num} in '{file_path.name}'"
            ) from exc
    return "\n\n---\n\n".join(records)


def _extract_pdf_text(file_path: Path) -> str:
    """Extract every PDF page; any parser failure invalidates the source."""
    pages_text: list[str] = []
    with open(_long_path(file_path), "rb") as f, pdfplumber.open(f) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_text.append(page_text.strip())
            except Exception as exc:
                raise ValueError(
                    f"Failed to extract page {page_idx} from PDF '{file_path.name}'"
                ) from exc
    return "\n\n".join(pages_text)


def ingest_vector(qdrant_client: QdrantClient, data_dir: Path = DATA_DIR) -> None:
    """Extract text from .jsonl, .md, and .pdf files, chunk, embed, and upsert into Qdrant."""
    logger.info("Step 2: Scanning '%s' for JSONL, Markdown, and PDF files...", data_dir)
    if not data_dir.exists():
        logger.warning(
            "Data directory '%s' does not exist. Skipping vector ingestion.", data_dir
        )
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
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    text_files = sorted(
        p
        for p in data_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".jsonl", ".md", ".pdf"}
    )

    failures = []
    total_chunks = 0
    files_indexed = 0

    for file_path in text_files:
        rel_source = file_path.relative_to(data_dir).as_posix()
        suffix = file_path.suffix.lower()
        digest = fingerprint(file_path)
        marker_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"manifest::{rel_source}"))
        existing = qdrant_client.retrieve(
            collection_name=QDRANT_COLLECTION, ids=[marker_id]
        )
        if existing and existing[0].payload.get("fingerprint") == digest:
            continue
        if existing:
            raise ValueError(
                f"Previously indexed source changed; explicit migration required: {rel_source}"
            )

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
            failures.append(rel_source)
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
                        id=str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL, f"{rel_source}::{start + offset}"
                            )
                        ),
                        vector=embedding.tolist(),
                        payload={
                            "source_file": rel_source,
                            "text": chunk,
                            "fingerprint": digest,
                            **source_metadata(rel_source),
                        },
                    )
                    for offset, (chunk, embedding) in enumerate(
                        zip(batch_chunks, embeddings)
                    )
                ]
                qdrant_client.upsert(
                    collection_name=QDRANT_COLLECTION, points=points, wait=True
                )

            # Completion marker is written only after all deterministic chunks succeeded.
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=marker_id,
                        vector=[0.0] * EMBEDDING_DIM,
                        payload={
                            "source_file": rel_source,
                            "fingerprint": digest,
                            "ingestion_marker": True,
                        },
                    )
                ],
                wait=True,
            )
            files_indexed += 1
            total_chunks += len(chunks)
            logger.info("Indexed '%s' (%d chunk(s)).", rel_source, len(chunks))
        except Exception as exc:  # noqa: BLE001 — per-file embedding/upsert recovery.
            failures.append(rel_source)
            logger.warning(
                "Failed to embed/upsert chunks for '%s': %s", rel_source, exc
            )

    logger.info(
        "Step 2 complete: Indexed %d file(s) and %d chunk(s) into Qdrant collection '%s'.",
        files_indexed,
        total_chunks,
        QDRANT_COLLECTION,
    )

    if failures:
        raise RuntimeError(f"Vector ingestion failed for {len(failures)} source(s)")


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
    parser = argparse.ArgumentParser(
        description="Ingest AgroResilience datasets into PostgreSQL and Qdrant."
    )
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Deprecated compatibility alias; always resumes individual sources.",
    )
    parser.add_argument("--sql-only", action="store_true")
    parser.add_argument("--vector-only", action="store_true")
    args = parser.parse_args()
    if args.sql_only and args.vector_only:
        parser.error("Choose only one store")
    extract_all_zips(args.data_dir)
    errors = []
    if not args.vector_only:
        engine = create_engine(DATABASE_URL)
        try:
            ingest_sql(engine, args.data_dir)
        except Exception as exc:
            logger.exception("SQL ingestion failed")
            errors.append(str(exc))
        finally:
            engine.dispose()
    if not args.sql_only:
        try:
            ingest_vector(QdrantClient(url=QDRANT_URL, timeout=60), args.data_dir)
        except Exception as exc:
            logger.exception("Vector ingestion failed")
            errors.append(str(exc))
    if errors:
        raise SystemExit(1)
    logger.info("ETL pipeline finished")
