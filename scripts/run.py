"""One entry point for localhost preview, RAG + DB services, development, and provider testing."""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
PYTHON = (
    VENV_DIR / "Scripts/python.exe" if os.name == "nt" else VENV_DIR / "bin/python"
)


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
                raise SystemExit(f"Invalid .env assignment in {path.name} on line {number}.")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            env.setdefault(key.strip(), value)
    return env


def setup() -> None:
    if not PYTHON.exists():
        try:
            venv.EnvBuilder(with_pip=True).create(VENV_DIR)
        except (subprocess.CalledProcessError, OSError) as exc:
            raise SystemExit(
                "Python venv/pip is unavailable. On Linux Mint install python3-venv, then rerun --setup."
            ) from exc
    check = subprocess.run(
        [str(PYTHON), "-m", "pip", "--version"], check=False, capture_output=True
    )
    if check.returncode:
        raise SystemExit(
            "The .venv has no pip. Install python3-venv and run python -m ensurepip, then rerun --setup."
        )
    pip_args = [
        str(PYTHON),
        "-m",
        "pip",
        "install",
        "-r",
        str(ROOT / "backend/requirements.lock.txt"),
    ]
    rag_req = ROOT / "RAG/requirements.txt"
    if rag_req.exists():
        pip_args.extend(["-r", str(rag_req)])
    subprocess.run(pip_args, check=True, cwd=ROOT)

    npm = _npm_cmd()
    if not npm:
        raise SystemExit("npm is required to install frontend dependencies.")
    subprocess.run([npm, "ci"], check=True, cwd=ROOT / "frontend")
    print("Setup complete. Run ./run.sh (or .\\run.ps1 on Windows) to start the app.")


def _prepare_rag_services(env: dict[str, str], force_ingest: bool) -> bool:
    """Start Docker Postgres/Qdrant if available and ingest datasets if DBs are empty."""
    compose_file = ROOT / "RAG/docker-compose.yml"
    docker = _docker_cmd()
    pg_host = env.get("POSTGRES_HOST", "localhost")
    pg_port = int(env.get("POSTGRES_PORT", "5432"))
    qd_host = env.get("QDRANT_HOST", "localhost")
    qd_port = int(env.get("QDRANT_PORT", "6333"))

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
    if pg_ready or qd_ready:
        ingest_script = ROOT / "RAG/scripts/ingest_data.py"
        if ingest_script.exists():
            cmd = [str(PYTHON), str(ingest_script)]
            if not force_ingest:
                cmd.append("--if-empty")
            print("Checking RAG dataset ingestion status...", flush=True)
            subprocess.run(cmd, cwd=ROOT, env=env, check=False)
    else:
        print(
            "Warning: PostgreSQL (5432) and Qdrant (6333) are not reachable; RAG will start in degraded mode.",
            flush=True,
        )
    return pg_ready or qd_ready


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--setup", action="store_true", help="Install dependencies, then exit."
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
        help="Force running RAG/scripts/ingest_data.py before starting.",
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
    if args.setup:
        setup()
        return 0

    env = environment()
    if args.provider:
        env["MODEL_PROVIDER"] = args.provider
    if args.model:
        env["MODEL_NAME"] = args.model
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
        _prepare_rag_services(env, force_ingest=args.ingest)

    if not (args.frontend_only or args.backend_only or args.dev):
        assert npm is not None
        subprocess.run(
            [npm, "run", "build"], check=True, cwd=ROOT / "frontend", env=env
        )

    processes: list[subprocess.Popen] = []

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
                f"RAG API running at http://127.0.0.1:{rag_port}",
                flush=True,
            )
        print(f"Open {address} — Ctrl+C stops the app.", flush=True)
        while all(process.poll() is None for process in processes):
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
