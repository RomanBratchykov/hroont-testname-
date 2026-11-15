import importlib
from decimal import Decimal

import pytest


def starter():
    return importlib.import_module("start_deepseek")


def test_cloud_environment_ignores_copied_local_endpoint():
    module = starter()
    env = module.cloud_environment(
        {
            "OPENAI_BASE_URL": "http://localhost:11434/v1",
            "MODEL_PROVIDER": "ollama",
            "MODEL_NAME": "local:4b",
        }
    )
    assert env["MODEL_PROVIDER"] == "deepseek"
    assert env["MODEL_NAME"] == "deepseek-flash"
    assert env["OPENAI_BASE_URL"] == ""
    assert env["PUBLIC_ORIGIN"] == ""


def test_saved_settings_preserve_other_secrets_and_replace_blank_values(tmp_path):
    module = starter()
    path = tmp_path / ".env"
    path.write_text("OTHER_SECRET=keep-me\nDEEPSEEK_API_KEY=\n# comment\n")
    module.save_settings(
        path, {"DEEPSEEK_API_KEY": "sk-test", "DEEPSEEK_INPUT_USD_PER_MILLION": ".30"}
    )
    assert "OTHER_SECRET=keep-me" in path.read_text()
    assert "DEEPSEEK_API_KEY=sk-test" in path.read_text()
    assert path.read_text().count("DEEPSEEK_API_KEY=") == 1
    assert "# comment" in path.read_text()
    if __import__("os").name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600


def test_invalid_rate_rejected_before_startup():
    module = starter()
    for value in ("NaN", "Infinity", "0", "-1", "wrong"):
        with pytest.raises(ValueError):
            module.rate(value)
    assert module.rate(".30") == Decimal(".30")
