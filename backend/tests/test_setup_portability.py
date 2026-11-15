import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("launcher", ROOT / "scripts/run.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_default_provider_ignores_legacy_local_model():
    env = {"MODEL_NAME": "qwen3.5:4b"}
    launcher.select_provider(env, None, None)
    assert env["MODEL_PROVIDER"] == "deepseek"
    assert env["MODEL_NAME"] == "deepseek-flash"


def test_explicit_provider_and_model_win():
    env = {"MODEL_PROVIDER": "deepseek", "OLLAMA_MODEL": "qwen3.5:4b"}
    launcher.select_provider(env, "ollama", "custom:4b")
    assert env["MODEL_NAME"] == "custom:4b"
    assert env["MODEL_PROVIDER"] == "ollama"


def test_create_env_preserves_existing_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    (tmp_path / ".env.example").write_text("MODEL_PROVIDER=deepseek\n")
    launcher.ensure_env_file()
    assert (tmp_path / ".env").read_text() == "MODEL_PROVIDER=deepseek\n"
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=private\n")
    launcher.ensure_env_file()
    assert (tmp_path / ".env").read_text() == "DEEPSEEK_API_KEY=private\n"


def test_torch_index_is_platform_specific():
    assert "--index-url" in launcher.torch_install_args("Linux")
    assert "--index-url" in launcher.torch_install_args("Windows")
    assert "--index-url" not in launcher.torch_install_args("Darwin")


def test_setup_stops_before_install_without_database_prerequisites(monkeypatch):
    import pytest

    monkeypatch.setattr(launcher, "runtime_checks", lambda: ("node", "npm"))
    monkeypatch.setattr(launcher, "ensure_env_file", lambda: None)
    monkeypatch.setattr(launcher, "environment", dict)
    monkeypatch.setattr(launcher, "database_prerequisites", lambda env: False)
    with pytest.raises(SystemExit, match="Start Docker"):
        launcher.setup()


def test_ollama_environment_does_not_override_deepseek_default():
    env = {"MODEL_PROVIDER": "ollama", "OLLAMA_MODEL": "local:7b"}
    launcher.select_provider(env, None, None)
    assert env["MODEL_PROVIDER"] == "deepseek"
    assert env["MODEL_NAME"] == "deepseek-flash"
