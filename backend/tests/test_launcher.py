"""Real local HTTP smoke test; the model server is an offline external-service fake."""

import contextlib
import json
import os
import signal
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def test_launcher_serves_chat_and_cancels_disconnected_turn(tmp_path):
    entered = threading.Event()
    release = threading.Event()

    class ModelHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["content-length"])))
            if payload["messages"][-1]["content"] == "Slow":
                entered.set()
                release.wait(10)
            body = json.dumps(
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello from local test",
                    },
                    "done": True,
                    "done_reason": "stop",
                    "prompt_eval_count": 10,
                    "eval_count": 5,
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)

    model = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
    thread = threading.Thread(target=model.serve_forever, daemon=True)
    thread.start()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "OLLAMA_URL": f"http://127.0.0.1:{model.server_port}",
        "DATABASE_PATH": str(tmp_path / "smoke.sqlite"),
        "LANGSMITH_TRACING": "false",
    }
    with (tmp_path / "server.log").open("w+") as log:
        process = subprocess.Popen(
            [
                "./run.sh",
                "--provider",
                "ollama",
                "--model",
                "offline-test",
                "--backend-only",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=5
            ) as client:
                for _ in range(100):
                    try:
                        ready = client.get("/api/health")
                        if ready.status_code == 200:
                            break
                    except httpx.RequestError:
                        pass
                    time.sleep(0.05)
                else:
                    log.seek(0)
                    raise AssertionError(log.read())
                assert ready.json()["model"] == "offline-test"
                response = client.post(
                    "/api/chat",
                    json={
                        "conversation_id": "a",
                        "request_id": "one",
                        "message": "Hello",
                    },
                )
                result = [json.loads(line) for line in response.text.splitlines()]
                assert result[-1]["content"] == "Hello from local test"
                with client.stream(
                    "POST",
                    "/api/chat",
                    json={
                        "conversation_id": "b",
                        "request_id": "slow",
                        "message": "Slow",
                    },
                ) as response:
                    iterator = response.iter_lines()
                    assert json.loads(next(iterator))["stage"] == "queued"
                    assert entered.wait(3)
                for _ in range(50):
                    if client.get("/api/health").json()["active"] == 0:
                        break
                    time.sleep(0.05)
                assert client.get("/api/health").json()["active"] == 0
                from backend.store import Store

                assert (
                    Store(tmp_path / "smoke.sqlite").run_record("slow")["status"]
                    == "cancelled"
                )
        finally:
            release.set()
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            model.shutdown()
            model.server_close()
            thread.join(timeout=5)
