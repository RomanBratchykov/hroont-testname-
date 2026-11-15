from pathlib import Path

import pytest

from scripts.install_startup import render_app_service, render_native_services


def test_startup_uses_current_laptop_paths_and_preserves_provider_override():
    root = Path("/tmp/another laptop/Croptato")
    text = render_app_service(
        root, root / ".venv/bin/python", Path("/opt/node/bin"), "ollama"
    )
    assert "/home/roman" not in text
    assert "WorkingDirectory=/tmp/another laptop/Croptato" in text
    assert "--provider ollama" in text
    assert 'Environment="PATH=/opt/node/bin:' in text
    default = render_app_service(root, root / ".venv/bin/python", Path("/opt/node/bin"))
    assert "--provider" not in default


def test_native_services_are_local_only_and_use_current_data_paths():
    rendered = render_native_services(Path("/tmp/Croptato"))
    assert "-h 127.0.0.1 -p 5432" in rendered["croptato-postgres.service"]
    assert "127.0.0.1" in rendered["qdrant-local.yaml"]
    assert "/tmp/Croptato/data/qdrant" in rendered["qdrant-local.yaml"]
    assert "/home/roman" not in str(rendered)


def test_invalid_service_path_cannot_inject_another_directive():
    with pytest.raises(ValueError):
        render_app_service(
            Path("/tmp/bad\nExecStart=oops"), Path("/usr/bin/python3"), Path("/usr/bin")
        )
