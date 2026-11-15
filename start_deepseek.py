"""Portable local DeepSeek launcher. Requires Python 3.12+ and Node 22.18+/24+."""

import argparse
import getpass
import os
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from scripts import run as launcher

ROOT = Path(__file__).resolve().parent


def cloud_environment(env):
    env = dict(env)
    launcher.select_provider(env, "deepseek", None)
    # This entry point explicitly selects hosted inference and local browser access.
    env.update(OPENAI_BASE_URL="", PUBLIC_ORIGIN="", RENDER_EXTERNAL_URL="")
    return env


def rate(value):
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Token rate must be a positive finite number.") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("Token rate must be a positive finite number.")
    return number


def save_settings(path, updates):
    if any("\n" in value or "\r" in value for value in updates.values()):
        raise ValueError("Settings must occupy one line.")
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    result = []
    for line in lines:
        key = line.partition("=")[0].strip()
        if key in updates:
            if key in remaining:
                result.append(key + "=" + remaining.pop(key))
        else:
            result.append(line)
    result.extend(key + "=" + value for key, value in remaining.items())
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".env-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("\n".join(result) + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure(env):
    updates = {}
    if not env.get("DEEPSEEK_API_KEY"):
        if not sys.stdin.isatty():
            raise ValueError(
                "Set DEEPSEEK_API_KEY in .env, or start in a terminal to enter it privately."
            )
        key = getpass.getpass("DeepSeek API key (saved in your private .env): ").strip()
        if (
            not key
            or any(char.isspace() for char in key)
            or any(char in key for char in "\"'")
        ):
            raise ValueError("API key must be nonempty without spaces or quotes.")
        updates["DEEPSEEK_API_KEY"] = key
    for name in ("INPUT", "OUTPUT"):
        variable = f"DEEPSEEK_{name}_USD_PER_MILLION"
        value = env.get(variable)
        if not value:
            if not sys.stdin.isatty():
                raise ValueError(
                    f"Set {variable} in .env. See https://api-docs.deepseek.com/quick_start/pricing/"
                )
            value = input(
                f"{name.title()} USD per million tokens from DeepSeek pricing: "
            ).strip()
            updates[variable] = value
        rate(value)
    if updates:
        save_settings(ROOT / ".env", updates)
        env.update(updates)
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--setup", action="store_true", help="Reinstall dependencies before starting"
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Install dependencies without starting or asking for a key",
    )
    parser.add_argument(
        "--with-rag",
        action="store_true",
        help="Include retrieval; requires Docker or existing local databases",
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be 1024..65535")
    try:
        launcher.runtime_checks()
        launcher.ensure_env_file()
        env = cloud_environment(launcher.environment())
        if not args.setup_only:
            env = configure(env)
        ready = False
        if launcher.PYTHON.exists() and (ROOT / "frontend/node_modules").exists():
            probe = subprocess.run(
                [
                    str(launcher.PYTHON),
                    "-c",
                    "import backend.api; import RAG.app.main"
                    if args.with_rag
                    else "import backend.api",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                check=False,
            )
            ready = probe.returncode == 0
        if args.setup or args.setup_only or not ready:
            launcher.setup(with_rag=args.with_rag)
        if args.setup_only:
            return 0
        command = [
            str(launcher.PYTHON),
            str(ROOT / "scripts/run.py"),
            "--provider",
            "deepseek",
            "--port",
            str(args.port),
        ]
        if not args.with_rag:
            command.append("--no-rag")
        print(
            "Starting the local app with hosted DeepSeek. Ctrl+C stops it.", flush=True
        )
        return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode
    except KeyboardInterrupt:
        return 0
    except subprocess.CalledProcessError as exc:
        print(
            f"Setup failed (exit {exc.returncode}). Check the installation output and rerun with --setup.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError, EOFError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
