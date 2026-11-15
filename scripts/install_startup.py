"""Render/install Linux user startup services using this checkout's paths."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def quote(value: str | Path) -> str:
    text = str(value)
    if any(char in text for char in "\n\r\0"):
        raise ValueError("Service paths must not contain control characters")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def working_directory(value: Path) -> str:
    # Unlike ExecStart/Environment, WorkingDirectory does not strip surrounding quotes.
    quote(value)  # Validate control characters consistently.
    return str(value).replace("%", "%%")


def render_app_service(
    root: Path,
    python: Path,
    node_bin: Path,
    provider: str | None = None,
    native_databases: bool = False,
) -> str:
    if provider not in {None, "ollama", "deepseek"}:
        raise ValueError("Unsupported provider")
    dependencies = (
        " croptato-postgres.service croptato-qdrant.service" if native_databases else ""
    )
    override = f" --provider {provider}" if provider else ""
    path = str(node_bin) + os.pathsep + os.defpath
    return f"""[Unit]
Description=Croptato web application
After=network-online.target{dependencies}
Wants=network-online.target{dependencies}
StartLimitIntervalSec=120
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory={working_directory(root)}
Environment={quote("PATH=" + path)}
Environment=PYTHONUNBUFFERED=1
ExecStart={quote(python)} {quote(root / "scripts/run.py")} --port 5173{override}
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillMode=control-group

[Install]
WantedBy=default.target
"""


def render_native_services(root: Path, postgres_version: str = "16") -> dict[str, str]:
    pg = (
        root
        / ".runtime/postgres/usr/lib/postgresql"
        / postgres_version
        / "bin/postgres"
    )
    postgres = f"""[Unit]
Description=Croptato local PostgreSQL
After=network.target

[Service]
Type=simple
WorkingDirectory={working_directory(root)}
Environment={quote("LD_LIBRARY_PATH=" + str(root / ".runtime/postgres/usr/lib/x86_64-linux-gnu"))}
ExecStart={quote(pg)} -D {quote(root / "data/rag-postgres")} -k {quote(root / "data/rag-postgres-socket")} -h 127.0.0.1 -p 5432 -c jit=off -c unix_socket_permissions=0700
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGINT

[Install]
WantedBy=default.target
"""
    qdrant = f"""[Unit]
Description=Croptato local Qdrant
After=network.target

[Service]
Type=simple
WorkingDirectory={working_directory(root / ".runtime/qdrant")}
ExecStart={quote(root / ".runtime/qdrant/qdrant")} --config-path {quote(root / "data/qdrant-local.yaml")}
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=default.target
"""
    config = f"""log_level: WARN
telemetry_disabled: true
storage:
  storage_path: {json.dumps(str(root / "data/qdrant"))}
  snapshots_path: {json.dumps(str(root / "data/qdrant-snapshots"))}
service:
  host: 127.0.0.1
  http_port: 6333
  grpc_port: 6334
"""
    return {
        "croptato-postgres.service": postgres,
        "croptato-qdrant.service": qdrant,
        "qdrant-local.yaml": config,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["ollama", "deepseek"])
    parser.add_argument(
        "--native-databases",
        action="store_true",
        help="Use already-provisioned project-local Linux database binaries.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Preview files here without installing or enabling services.",
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Restart enabled services after installation.",
    )
    args = parser.parse_args()
    if not sys.platform.startswith("linux"):
        parser.error(
            "Automatic startup installation currently requires Linux/systemd. Use run.ps1 on Windows or run.sh on macOS."
        )
    python = ROOT / ".venv/bin/python"
    npm = shutil.which("npm")
    if not python.exists() or not npm:
        parser.error(
            "Run ./run.sh --setup first; Python environment and npm are required."
        )
    files = {
        "croptato.service": render_app_service(
            ROOT, python, Path(npm).parent, args.provider, args.native_databases
        )
    }
    if args.native_databases:
        versions = ROOT / ".runtime/postgres/usr/lib/postgresql"
        installed = sorted(versions.glob("*/bin/postgres")) if versions.exists() else []
        if not installed or not (ROOT / ".runtime/qdrant/qdrant").exists():
            parser.error(
                "Native database binaries must already be provisioned; use Docker Compose on a fresh laptop."
            )
        if not (ROOT / "data/rag-postgres/PG_VERSION").exists():
            parser.error("The native PostgreSQL database has not been initialized.")
        files.update(render_native_services(ROOT, installed[-1].parents[1].name))
    target = (
        args.output_dir
        or Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        / "systemd/user"
    )
    units = [name for name in files if name.endswith(".service")]
    if not args.output_dir:
        # Validate a staged copy before touching an existing boot configuration.
        with tempfile.TemporaryDirectory(prefix="croptato-units-") as staging:
            stage = Path(staging)
            for name in units:
                (stage / name).write_text(files[name])
            subprocess.run(
                [
                    "systemd-analyze",
                    "--user",
                    "verify",
                    *[str(stage / name) for name in units],
                ],
                check=True,
            )
    target.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        destination = (
            target / name
            if name.endswith(".service") or args.output_dir
            else ROOT / "data" / name
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)
    if args.output_dir:
        print(f"Preview written to {target}; no services changed.")
        return 0
    units = [name for name in files if name.endswith(".service")]
    subprocess.run(
        [
            "systemd-analyze",
            "--user",
            "verify",
            *[str(target / name) for name in units],
        ],
        check=True,
    )
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", *units], check=True)
    if args.start:
        if args.native_databases:
            subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "restart",
                    "croptato-postgres.service",
                    "croptato-qdrant.service",
                ],
                check=True,
            )
        subprocess.run(
            ["systemctl", "--user", "restart", "croptato.service"], check=True
        )
    print(
        "Startup services installed. Enable user lingering for startup before login: loginctl enable-linger "
        + os.environ.get("USER", "<user>")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
