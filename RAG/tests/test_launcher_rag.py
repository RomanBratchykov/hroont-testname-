import importlib.util
from pathlib import Path
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location(
    "launcher", Path(__file__).parents[2] / "scripts/run.py"
)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_partial_stores_are_unavailable_and_do_not_ingest(monkeypatch):
    monkeypatch.setattr(launcher, "_docker_cmd", lambda: None)
    monkeypatch.setattr(launcher, "_port_open", lambda host, port: port == 5432)
    process = Mock()
    monkeypatch.setattr(launcher.subprocess, "Popen", process)
    assert not launcher._prepare_rag_services({}, force_ingest=True)
    process.assert_not_called()


def test_ordinary_restart_does_not_index(monkeypatch):
    monkeypatch.setattr(launcher, "_docker_cmd", lambda: None)
    monkeypatch.setattr(launcher, "_port_open", lambda host, port: True)
    process = Mock()
    monkeypatch.setattr(launcher.subprocess, "Popen", process)
    assert launcher._prepare_rag_services({}, force_ingest=False)
    process.assert_not_called()


def test_url_ports_control_store_checks(monkeypatch):
    monkeypatch.setattr(launcher, "_docker_cmd", lambda: None)
    ports = []
    monkeypatch.setattr(
        launcher, "_port_open", lambda host, port: ports.append(port) or True
    )
    assert launcher._prepare_rag_services(
        {
            "DATABASE_URL": "postgresql://localhost:5544/db",
            "QDRANT_URL": "http://localhost:6444",
        },
        False,
    )
    assert ports == [5544, 6444]
