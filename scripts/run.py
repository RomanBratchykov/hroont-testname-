"""One entry point for localhost preview, development, and provider testing."""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/bin/python"


def environment():
    env = os.environ.copy()
    path = ROOT / ".env"
    if path.exists():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not key.strip().replace("_", "").isalnum():
                raise SystemExit(f"Invalid .env assignment on line {number}.")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            env.setdefault(key.strip(), value)
    return env


def setup():
    if not PYTHON.exists():
        try:
            venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
        except (subprocess.CalledProcessError, OSError) as exc:
            raise SystemExit(
                "Python venv/pip is unavailable. On Linux Mint install python3-venv, then rerun --setup."
            ) from exc
    check = subprocess.run(
        [str(PYTHON), "-m", "pip", "--version"], check=False, capture_output=True
    )
    if check.returncode:
        raise SystemExit(
            "The .venv has no pip. Install python3-venv and run .venv/bin/python -m ensurepip, then rerun --setup."
        )
    subprocess.run(
        [
            str(PYTHON),
            "-m",
            "pip",
            "install",
            "-r",
            str(ROOT / "backend/requirements.lock.txt"),
        ],
        check=True,
        cwd=ROOT,
    )
    subprocess.run(["npm", "ci"], check=True, cwd=ROOT / "frontend")
    print("Setup complete. Run ./run.sh --provider ollama --model YOUR_INSTALLED_MODEL")


def main():
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
    if not args.backend_only and not shutil.which("npm"):
        raise SystemExit("npm is required for the frontend.")
    if not args.frontend_only:
        if not PYTHON.exists():
            raise SystemExit("Run ./run.sh --setup first.")
        provider = env.get("MODEL_PROVIDER", "ollama")
        if provider == "deepseek" and not all(
            env.get(key)
            for key in [
                "DEEPSEEK_API_KEY",
                "DEEPSEEK_INPUT_USD_PER_MILLION",
                "DEEPSEEK_OUTPUT_USD_PER_MILLION",
            ]
        ):
            raise SystemExit(
                "Set the DeepSeek key and both token rates in .env first (see .env.example)."
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
    if not (args.frontend_only or args.backend_only or args.dev):
        subprocess.run(
            ["npm", "run", "build"], check=True, cwd=ROOT / "frontend", env=env
        )
    processes = []

    def start(command, directory):
        processes.append(
            subprocess.Popen(command, cwd=directory, env=env, start_new_session=True)
        )

    try:
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
            start(
                [
                    "npm",
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
                os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    sys.exit(main())
