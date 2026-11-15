import importlib.util
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "ingest", Path(__file__).parents[1] / "scripts/ingest_data.py"
)
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


def test_actual_default_data_directory():
    assert ingest.DATA_DIR == ingest.PROJECT_ROOT / "rag/data"


def test_zip_traversal_is_rejected(tmp_path):
    with zipfile.ZipFile(tmp_path / "bad.zip", "w") as archive:
        archive.writestr("../outside.txt", "unsafe")
    with pytest.raises(ValueError):
        ingest.extract_all_zips(tmp_path)
    assert not (tmp_path / "outside.txt").exists()


def test_dates_are_not_invented_from_export_timestamp():
    assert ingest.source_metadata(
        "Kherson-20261115T091038Z-1-001/Kherson/readme.md"
    ) == {"region": "kherson", "start_year": None, "end_year": None}
    assert (
        ingest.source_metadata("Broadbalk Wheat 1968-2017/data.csv")["start_year"]
        == 1968
    )


def test_sql_resumes_each_file_and_preserves_existing_table(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    engine = create_engine("sqlite://")
    (tmp_path / "Kherson").mkdir()
    (tmp_path / "Kherson" / "first.csv").write_text("crop,yield\nwheat,3\n")
    ingest.ingest_sql(engine, tmp_path)
    first_tables = set(inspect(engine).get_table_names())
    ingest.ingest_sql(engine, tmp_path)
    assert set(inspect(engine).get_table_names()) == first_tables
    (tmp_path / "second.csv").write_text("crop,yield\nmaize,5\n")
    ingest.ingest_sql(engine, tmp_path)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM rag_ingestion_sources")
            ).scalar()
            == 2
        )
        assert (
            connection.execute(
                text(
                    "SELECT region FROM rag_ingestion_sources WHERE source_file='Kherson/first.csv'"
                )
            ).scalar()
            == "kherson"
        )
    assert len(inspect(engine).get_table_names()) == len(first_tables) + 1


def test_changed_sql_source_is_not_replaced(tmp_path):
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite://")
    source = tmp_path / "first.csv"
    source.write_text("crop\nwheat\n")
    ingest.ingest_sql(engine, tmp_path)
    with engine.connect() as connection:
        table = __import__("json").loads(
            connection.execute(
                text("SELECT table_names FROM rag_ingestion_sources")
            ).scalar()
        )[0]
    source.write_text("crop\nmaize\n")
    with pytest.raises(RuntimeError):
        ingest.ingest_sql(engine, tmp_path)
    with engine.connect() as connection:
        assert (
            connection.execute(text(f'SELECT crop FROM "{table}"')).scalar() == "wheat"
        )


def test_vector_partial_retry_uses_same_ids_and_only_marks_completion(
    tmp_path, monkeypatch
):
    import numpy as np

    class Embedder:
        def __init__(self, name, device):
            assert device == "cpu"

        def encode(self, chunks, **kwargs):
            return np.ones((len(chunks), 384))

    class Client:
        def __init__(self):
            self.points = {}
            self.fail = True
            self.calls = []

        def collection_exists(self, name):
            return True

        def retrieve(self, collection_name, ids):
            return [self.points[key] for key in ids if key in self.points]

        def upsert(self, collection_name, points, wait):
            self.calls.append([point.id for point in points])
            if self.fail:
                self.fail = False
                raise OSError("temporary store outage")
            self.points.update({point.id: point for point in points})

    monkeypatch.setattr(ingest, "SentenceTransformer", Embedder)
    (tmp_path / "Kherson.md").write_text("Crop rotation evidence")
    client = Client()
    with pytest.raises(RuntimeError):
        ingest.ingest_vector(client, tmp_path)
    assert not client.points
    ingest.ingest_vector(client, tmp_path)
    assert client.calls[0] == client.calls[1]
    assert len(client.points) == 2
    count = len(client.calls)
    ingest.ingest_vector(client, tmp_path)
    assert len(client.calls) == count
    chunks = [
        point
        for point in client.points.values()
        if not point.payload.get("ingestion_marker")
    ]
    assert chunks[0].payload["region"] == "kherson"
    assert chunks[0].payload["start_year"] is None


def test_malformed_jsonl_fails_source_instead_of_completing_partial_text(tmp_path):
    source = tmp_path / "broken.jsonl"
    source.write_text('{"crop": "wheat"}\ninvalid json\n')
    with pytest.raises(ValueError, match="line 2"):
        ingest._extract_jsonl_text(source)


def test_pdf_page_failure_fails_source(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    class Page:
        def extract_text(self):
            raise ValueError("unreadable page")

    source = tmp_path / "broken.pdf"
    source.write_bytes(b"%PDF")
    monkeypatch.setattr(
        ingest.pdfplumber,
        "open",
        lambda stream: nullcontext(SimpleNamespace(pages=[Page()])),
    )
    with pytest.raises(ValueError, match="page 1"):
        ingest._extract_pdf_text(source)


@pytest.mark.parametrize(
    "suffix,extractor",
    [(".jsonl", "_extract_jsonl_text"), (".pdf", "_extract_pdf_text")],
)
def test_parse_failure_never_writes_completion_and_is_retryable(
    tmp_path, monkeypatch, suffix, extractor
):
    from unittest.mock import Mock

    import numpy as np

    model = Mock()
    model.encode.return_value = np.ones((1, 384))
    monkeypatch.setattr(ingest, "SentenceTransformer", lambda *args, **kwargs: model)
    client = Mock()
    client.collection_exists.return_value = True
    client.retrieve.return_value = []
    (tmp_path / ("source" + suffix)).write_text("source bytes")
    monkeypatch.setattr(ingest, extractor, Mock(side_effect=ValueError("parse failed")))
    with pytest.raises(RuntimeError, match="1 source"):
        ingest.ingest_vector(client, tmp_path)
    client.upsert.assert_not_called()
    model.encode.assert_not_called()
    monkeypatch.setattr(ingest, extractor, lambda path: "Recovered complete source")
    ingest.ingest_vector(client, tmp_path)
    assert client.upsert.call_count == 2
    assert (
        client.upsert.call_args.kwargs["points"][0].payload["ingestion_marker"] is True
    )
