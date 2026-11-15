"""One entry point for localhost preview, RAG + DB services, development, and provider testing."""

import argparse
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import venv
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
PYTHON = VENV_DIR / "Scripts/python.exe" if os.name == "nt" else VENV_DIR / "bin/python"


def _npm_cmd() -> str | None:
    return shutil.which("npm")


def _docker_cmd() -> str | None:
    return shutil.which("docker")


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_open(host, port, timeout=0.5):
            return True
        time.sleep(0.5)
    return False


def environment() -> dict[str, str]:
    env = os.environ.copy()
    for path in (ROOT / ".env", ROOT / "RAG/.env"):
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not key.strip().replace("_", "").isalnum():
                raise SystemExit(
                    f"Invalid .env assignment in {path.name} on line {number}."
                )
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            env.setdefault(key.strip(), value)
    return env


def select_provider(
    env: dict[str, str], provider: str | None, model: str | None
) -> None:
    selected = provider or env.get("MODEL_PROVIDER") or "deepseek"
    if selected not in {"ollama", "deepseek"}:
        raise SystemExit("MODEL_PROVIDER must be ollama or deepseek.")
    env["MODEL_PROVIDER"] = selected
    key, default = (
        ("OLLAMA_MODEL", "qwen3.5:4b")
        if selected == "ollama"
        else ("DEEPSEEK_MODEL", "deepseek-flash")
    )
    env["MODEL_NAME"] = model or env.get(key) or default


def ensure_env_file() -> None:
    destination = ROOT / ".env"
    try:
        with open(
            destination,
            "x",
            encoding="utf-8",
            opener=lambda path, flags: os.open(path, flags, 0o600),
        ) as handle:
            handle.write((ROOT / ".env.example").read_text(encoding="utf-8"))
    except FileExistsError:
        pass


def torch_install_args(system: str) -> list[str]:
    args = ["torch>=2.6,<3"]
    if system in {"Linux", "Windows"}:
        args += ["--index-url", "https://download.pytorch.org/whl/cpu"]
    return args


def runtime_checks() -> tuple[str, str]:
    if sys.version_info < (3, 12):
        raise SystemExit(
            "Python 3.12+ is required. Recreate .venv after installing a supported Python."
        )
    node, npm = shutil.which("node"), _npm_cmd()
    if not node or not npm:
        raise SystemExit("Install Node.js 22.18+ or 24+ with npm, then rerun --setup.")
    version = subprocess.run(
        [node, "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    parts = tuple(int(part) for part in re.findall(r"\d+", version)[:2])
    if not (parts >= (24, 0) or (22, 18) <= parts < (23, 0)):
        raise SystemExit("Node.js 22.18+ (22.x) or 24+ is required.")
    return node, npm


def database_prerequisites(env: dict[str, str]) -> bool:
    docker = _docker_cmd()
    if docker:
        compose = subprocess.run(
            [docker, "compose", "version"], capture_output=True, check=False
        )
        daemon = subprocess.run([docker, "info"], capture_output=True, check=False)
        if compose.returncode == daemon.returncode == 0:
            return True
    endpoints = (
        (env.get("DATABASE_URL", "postgresql://localhost:5432/kherson_crop_db"), 5432),
        (env.get("QDRANT_URL", "http://localhost:6333"), 6333),
    )
    return all(
        _port_open(urlparse(url).hostname or "localhost", urlparse(url).port or port)
        for url, port in endpoints
    )


def doctor() -> int:
    print(
        f"Platform: {platform.system()} {platform.machine()}; Python: {platform.python_version()}"
    )
    print(f"Disk free: {shutil.disk_usage(ROOT).free / 1024**3:.1f} GiB")
    try:
        memory = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        print(f"Physical memory: {memory / 1024**3:.1f} GiB")
    except (AttributeError, OSError, ValueError):
        print("Physical memory: unavailable on this platform")
    try:
        runtime_checks()
        runtime_ok = True
        print("Python/Node/npm: supported")
    except (SystemExit, OSError, subprocess.CalledProcessError) as exc:
        runtime_ok = False
        print(f"Runtime prerequisite: {exc}")
    stores_ok = database_prerequisites(environment())
    print(
        f"Docker Compose with running daemon, or reachable configured databases: {stores_ok}"
    )
    print(f"Project virtual environment: {PYTHON.exists()}")
    return 0 if runtime_ok and stores_ok and PYTHON.exists() else 1


def setup() -> None:
    _, npm = runtime_checks()
    ensure_env_file()
    if not database_prerequisites(environment()):
        raise SystemExit(
            "Start Docker Desktop/Engine with Compose, or provide running PostgreSQL and Qdrant at the configured localhost URLs. See docs/setup.md. Dependencies were not installed."
        )
    if not PYTHON.exists():
        try:
            venv.EnvBuilder(with_pip=True).create(VENV_DIR)
        except (subprocess.CalledProcessError, OSError) as exc:
            raise SystemExit(
                "Python venv/pip is unavailable. Install your OS Python venv package (python3-venv on Debian/Ubuntu), then rerun --setup."
            ) from exc
    subprocess.run(
        [str(PYTHON), "-m", "pip", "install", *torch_install_args(platform.system())],
        check=True,
        cwd=ROOT,
    )
    subprocess.run(
        [str(PYTHON), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
        check=True,
        cwd=ROOT,
    )
    subprocess.run([npm, "ci"], check=True, cwd=ROOT / "frontend")
    print(
        "Dependencies installed. Configure .env credentials/rates, then run ./run.sh (or .\\run.ps1). Database contents and embedding model downloads are prepared separately; see docs/setup.md."
    )


def _prepare_rag_services(env: dict[str, str], force_ingest: bool) -> bool:
    """Start Docker Postgres/Qdrant if available and ingest datasets if DBs are empty."""
    compose_file = ROOT / "RAG/docker-compose.yml"
    docker = _docker_cmd()
    pg_url = urlparse(
        env.get("DATABASE_URL", "postgresql://localhost:5432/kherson_crop_db")
    )
    qd_url = urlparse(env.get("QDRANT_URL", "http://localhost:6333"))
    pg_host, pg_port = pg_url.hostname or "localhost", pg_url.port or 5432
    qd_host, qd_port = qd_url.hostname or "localhost", qd_url.port or 6333
    if pg_url.scheme not in {
        "postgresql",
        "postgresql+psycopg2",
    } or qd_url.scheme not in {"http", "https"}:
        raise ValueError("Invalid RAG database URL scheme")
    if any(
        host not in {"localhost", "127.0.0.1", "::1"} for host in (pg_host, qd_host)
    ):
        raise ValueError("Launcher requires localhost RAG stores")
    env["POSTGRES_PORT"] = str(pg_port)
    env["QDRANT_PORT"] = str(qd_port)

    if docker and compose_file.exists():
        print("Ensuring PostgreSQL and Qdrant containers are running...", flush=True)
        res = subprocess.run(
            [docker, "compose", "-f", str(compose_file), "up", "-d"],
            cwd=ROOT / "RAG",
            env=env,
            check=False,
        )
        if res.returncode != 0:
            print(
                "Warning: `docker compose up -d` did not succeed. Continuing with existing services if available.",
                flush=True,
            )
        else:
            _wait_for_port(pg_host, pg_port, timeout=15.0)
            _wait_for_port(qd_host, qd_port, timeout=15.0)

    pg_ready = _port_open(pg_host, pg_port)
    qd_ready = _port_open(qd_host, qd_port)
    if not (pg_ready and qd_ready):
        print(
            f"RAG stores unavailable: PostgreSQL {pg_host}:{pg_port} ready={pg_ready}; Qdrant {qd_host}:{qd_port} ready={qd_ready}.",
            flush=True,
        )
    if force_ingest:
        if not (pg_ready and qd_ready):
            print(
                "Ingestion not started because both stores must be reachable. Main app remains available.",
                flush=True,
            )
        else:
            log_path = ROOT / "RAG/ingestion.log"
            with log_path.open("a") as log:
                subprocess.Popen(
                    [str(PYTHON), str(ROOT / "RAG/scripts/ingest_data.py")],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=os.name != "nt",
                )
            print(
                f"Indexing started independently; progress/errors: {log_path}",
                flush=True,
            )
    else:
        print(
            "Indexing is explicit: run ./run.sh --ingest or python RAG/scripts/ingest_data.py.",
            flush=True,
        )
    return pg_ready and qd_ready


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--setup", action="store_true", help="Install dependencies, then exit."
    )
    parser.add_argument(
        "--doctor", action="store_true", help="Read-only local prerequisite report."
    )
    parser.add_argument("--provider", choices=["ollama", "deepseek"])
    parser.add_argument(
        "--model", help="Exact installed Ollama model tag or DeepSeek model ID."
    )
    parser.add_argument("--phase", choices=["testing", "demo"])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--rag-port", type=int, default=8001)
    parser.add_argument(
        "--with-rag",
        action="store_true",
        help="Start Docker DBs and RAG service even with --backend-only.",
    )
    parser.add_argument(
        "--no-rag",
        action="store_true",
        help="Disable Docker DB startup and the RAG service.",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Start resumable ingestion independently; logs in RAG/ingestion.log.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--frontend-only",
        action="store_true",
        help="UI preview with no backend or model calls.",
    )
    mode.add_argument(
        "--backend-only",
        action="store_true",
        help="API only; do not build/start the frontend.",
    )
    mode.add_argument(
        "--dev", action="store_true", help="API plus Vite with live frontend updates."
    )
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    if not 1024 <= args.rag_port <= 65535:
        parser.error("--rag-port must be between 1024 and 65535")
    if args.rag_port == args.port:
        parser.error("--rag-port must differ from --port")
    if args.doctor:
        return doctor()
    if args.setup:
        setup()
        return 0

    env = environment()
    select_provider(env, args.provider, args.model)
    if args.phase:
        env["BUDGET_PHASE"] = args.phase

    env["VITE_CHAT_BACKEND"] = "off" if args.frontend_only else "on"
    env["API_PROXY_URL"] = f"http://127.0.0.1:{args.port}"
    # Disable optional framework tracing/telemetry for private local chat processing.
    env["LANGSMITH_TRACING"] = "false"
    env["LANGCHAIN_TRACING_V2"] = "false"

    npm = _npm_cmd()
    if not args.backend_only and not npm:
        raise SystemExit("npm is required for the frontend.")

    rag_port = int(env.get("RAG_PORT", str(args.rag_port)))
    if args.rag_port != 8001:
        rag_port = args.rag_port

    if not 1024 <= rag_port <= 65535 or rag_port == args.port:
        parser.error(
            "Configured RAG_PORT must be between 1024 and 65535 and differ from --port"
        )

    offline_test = args.model == "offline-test"
    start_rag = (
        not args.frontend_only
        and not args.no_rag
        and not offline_test
        and (not args.backend_only or args.with_rag)
    )

    if args.no_rag or offline_test:
        env.pop("RAG_URL", None)
    elif start_rag:
        env["RAG_URL"] = f"http://127.0.0.1:{rag_port}"

    if not args.frontend_only:
        if not PYTHON.exists():
            raise SystemExit("Run ./run.sh --setup (or .\\run.ps1 --setup) first.")
        provider = env.get("MODEL_PROVIDER", "ollama")
        if (
            provider == "deepseek"
            and not env.get("OPENAI_BASE_URL")
            and not all(
                env.get(key)
                for key in [
                    "DEEPSEEK_API_KEY",
                    "DEEPSEEK_INPUT_USD_PER_MILLION",
                    "DEEPSEEK_OUTPUT_USD_PER_MILLION",
                ]
            )
        ):
            raise SystemExit(
                "Set the DeepSeek key and both token rates in .env (or set OPENAI_BASE_URL for local DeepSeek)."
            )
        check = subprocess.run(
            [
                str(PYTHON),
                "-c",
                "from backend.config import Settings; Settings.from_env()",
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
        )
        if check.returncode:
            raise SystemExit(
                "Invalid backend configuration. Check provider, rates, URLs and limits in .env."
            )

    if start_rag:
        try:
            _prepare_rag_services(env, force_ingest=args.ingest)
        except (ValueError, OSError) as exc:
            print(
                f"RAG startup configuration failed: {exc}. Main app remains available.",
                flush=True,
            )
            start_rag = False
            env.pop("RAG_URL", None)

    if not (args.frontend_only or args.backend_only or args.dev):
        assert npm is not None
        subprocess.run(
            [npm, "run", "build"], check=True, cwd=ROOT / "frontend", env=env
        )

    processes: list[subprocess.Popen] = []
    rag_process = None

    def start(command: list[str], directory: Path) -> None:
        kwargs: dict = {"cwd": directory, "env": env}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        processes.append(subprocess.Popen(command, **kwargs))

    try:
        if start_rag:
            start(
                [
                    str(PYTHON),
                    "-m",
                    "uvicorn",
                    "RAG.app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(rag_port),
                    "--no-access-log",
                ],
                ROOT,
            )
        if start_rag:
            rag_process = processes.pop()
        if not args.frontend_only:
            start(
                [
                    str(PYTHON),
                    "-m",
                    "uvicorn",
                    "backend.api:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.port),
                    "--no-access-log",
                ],
                ROOT,
            )
        if args.frontend_only or args.dev:
            assert npm is not None
            start(
                [
                    npm,
                    "run",
                    "dev",
                    "--",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "5173",
                    "--strictPort",
                ],
                ROOT / "frontend",
            )
        address = (
            "http://127.0.0.1:5173"
            if args.frontend_only or args.dev
            else f"http://127.0.0.1:{args.port}"
        )
        if start_rag:
            print(
                f"RAG API starting at http://127.0.0.1:{rag_port}; readiness is reported by /health",
                flush=True,
            )
        print(f"Open {address} — Ctrl+C stops the app.", flush=True)
        while all(process.poll() is None for process in processes):
            if rag_process is not None and rag_process.poll() is not None:
                print(
                    f"RAG API unavailable (exit {rag_process.returncode}); main app remains running.",
                    flush=True,
                )
                rag_process = None
            time.sleep(0.2)
        return next(
            (
                process.returncode
                for process in processes
                if process.returncode is not None
            ),
            0,
        )
    except KeyboardInterrupt:
        return 0
    finally:
        if rag_process is not None:
            processes.append(rag_process)
        for process in processes:
            if process.poll() is None:
                if os.name == "nt" or not hasattr(os, "killpg"):
                    process.terminate()
                else:
                    os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == "nt" or not hasattr(os, "killpg"):
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    sys.exit(main())
