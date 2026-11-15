# Quick fallback when hosting is unavailable

Download or clone the complete repository. Install Python 3.12+ (3.12 recommended) with pip/venv and Node.js 22.18+ (22.x) or 24+ with npm. Internet and funded DeepSeek API access are required. No local model or GPU is needed for the default fallback.

From the project folder on Linux/macOS:

```bash
python3 start_deepseek.py
```

On Windows:

```powershell
py -3 start_deepseek.py
```

The launcher installs missing backend/frontend dependencies, privately prompts for a missing DeepSeek key, and asks for missing input/output USD-per-million token rates from the official pricing page. It saves entered settings in the ignored `.env` file, preserving other settings (mode 0600 on POSIX; Windows follows account ACLs). You can instead configure these variables beforehand. It builds the frontend and prints the local URL, normally `http://127.0.0.1:8000`. Ctrl+C stops the app. The API key stays on the backend. Starting the app makes no paid inference request; chatting uses DeepSeek credit and the configured app budget.

Use `--setup` to reinstall dependencies, `--setup-only` to install without starting or configuring credentials, or `--port 8080` if port 8000 is occupied. Copy source and input data between computers, not `.venv` or `node_modules`. The launcher reuses the existing app and selects hosted DeepSeek even if the copied environment points to Ollama or a Render URL.

The default fallback includes chat, attachments and the saved synthetic example dashboard; it does not start retrieval databases or download embedding models. For the full retrieval setup, use `--with-rag`; this requires Docker Compose or running local PostgreSQL/Qdrant, full dependencies and separately indexed source data. No startup service is installed. This workflow is tested on Linux; Windows/macOS launch paths are provided but have not been run on those operating systems.

## Render hostname errors

Set `PUBLIC_ORIGIN` to the exact HTTPS URL you open, without a trailing slash, and redeploy. If it is empty, the backend automatically uses Render's `RENDER_EXTERNAL_URL`. Explicit custom domains take precedence. Unrelated hosts and browser origins remain rejected. This code must be pushed to the deployed branch before Render can use the fix.

# Portable local setup

Use the same checkout on Linux, macOS or Windows. Install Python 3.12 or newer with venv/pip, Node.js 22.18+ (22.x) or 24+ with npm, and Docker Engine/Desktop with the Compose plugin. Start Docker before setup. No NVIDIA GPU is required: embeddings use CPU PyTorch. Availability of binary wheels still depends on your Python version and CPU architecture; use a mainstream 64-bit Python supported by PyTorch. A Python released before its dependencies have wheels may require an older supported Python or native build tools.

Do not copy `.venv`, `frontend/node_modules`, model caches or installed services between machines. Recreate them on each machine. Copy private `.env` settings securely if needed, keeping machine-specific paths out of the file.

```bash
./run.sh --doctor
./run.sh --setup
```

Windows PowerShell equivalents:

```powershell
.\run.ps1 --doctor
.\run.ps1 --setup
```

`--doctor` reads runtime/platform, memory (where available), free disk and database prerequisite facts. It prints no credentials, installs nothing, and returns a nonzero status for missing prerequisites. `--setup` checks runtimes and database prerequisites, creates `.env` from `.env.example` only if absent (mode 0600 on POSIX), installs CPU torch, the root `requirements.txt` (backend lock plus RAG dependencies), then runs `npm ci`. Existing `.env` content is preserved. Windows file access follows your account ACLs. Setup requires internet access and sufficient space for dependencies, container images, documents and model caches. It does not download embedding models, index documents or verify provider credentials.

Docker is the recommended cross-platform database path. If Docker is unavailable, install PostgreSQL and Qdrant yourself and start both on the localhost addresses/ports in `.env`. Setup accepts reachable configured databases; a TCP check does not prove credentials/schema/readiness. The launcher supports localhost stores only. Native service installation is OS-specific; copying a Linux service to Windows/macOS will not install a service there.

The launcher defaults to `deepseek`. Only an explicit `--provider ollama` selects Ollama; an old `MODEL_PROVIDER=ollama` in the shell or `.env` does not change the launcher default. Model selection is `--model`, then `DEEPSEEK_MODEL` or `OLLAMA_MODEL`, then `deepseek-flash` or `qwen3.5:4b`. Legacy `MODEL_NAME` is not used by the launcher, preventing an old local model tag from reaching a cloud API. Direct backend invocation retains its own existing configuration behavior.

For hosted DeepSeek, leave `OPENAI_BASE_URL` empty and configure `DEEPSEEK_API_KEY` plus both current input/output token rates in `.env`. Starting the app does not test a paid request. For a local OpenAI-compatible DeepSeek server, set `OPENAI_BASE_URL` and its explicit `DEEPSEEK_MODEL`. For Ollama, install/start Ollama and pull your chosen model first:

```bash
./run.sh --provider ollama --model qwen3.5:4b
```

Start the full app with `./run.sh` / `.\run.ps1`. RAG startup uses Docker Compose where available, otherwise existing local stores. Indexing is explicit: `./run.sh --ingest`; monitor `RAG/ingestion.log`. The first embedding-model use may download model weights. Keep PostgreSQL, Qdrant and model servers private. Use `--no-rag` for the main application without database retrieval, or `--frontend-only` for a UI preview.

The dependency declarations and launcher branches target Linux, macOS and Windows; this change was verified on Linux only. It does not promise every Python/OS/CPU combination has upstream binary wheels. No Windows or macOS physical-machine installation was performed.


## Linux automatic startup

Use `.venv/bin/python scripts/install_startup.py --start` to generate units from this checkout’s paths. Use `--output-dir <directory>` to preview without changing services. A provider override such as `--provider ollama` is explicit; otherwise the launcher’s DeepSeek default applies. For this PC’s already-provisioned native database binaries, add `--native-databases`. That option is Linux-specific and requires the initialized local databases and binaries; it does not download them on another laptop. Other machines should normally use the supplied localhost-bound Docker Compose stack.

The installer validates staged units before replacing an existing boot configuration. Enable user lingering with `loginctl enable-linger <your-user>` for startup before login. Windows/macOS automatic startup remains OS-specific; their run scripts are provided for interactive startup.

`OLLAMA_CONTEXT_TOKENS` defaults to 16384 to accommodate the profile and retrieved evidence; adjust it for the chosen local model and RAM/VRAM. Hosted DeepSeek needs no local generation GPU. Embedding retrieval uses CPU on every supported platform.

## Stop automatic startup

Stop the web app now and prevent startup at login/boot:

```bash
systemctl --user disable --now croptato.service
```

Optionally stop its dedicated database services too (data is preserved):

```bash
systemctl --user disable --now croptato-postgres.service croptato-qdrant.service
```

This leaves manual `./run.sh` startup available. Deleting the installer script would not disable already-installed services.

## DeepSeek workflow smoke test

After configuring the private DeepSeek key and both token rates, explicitly run:

```bash
.venv/bin/python scripts/test_deepseek.py --live
# Also exercise the configured local retrieval service and existing indexed data:
.venv/bin/python scripts/test_deepseek.py --live --with-rag
```

Without `--live`, no API calls are made. The test uses the saved synthetic John profile, a separate SQLite chat/budget database, and a $0.10 local reservation cap. It checks fast answers, history/capability tool calls and thinking mode. The cap assumes configured token rates cover the actual API rates; the provider account balance is independent. It saves `result.json`, `trace.jsonl` and a visual `run-dashboard.html` under `data/deepseek-smoke/`. A passing run still requires reviewing the model's scientific caveats. Reference retrieval is separate from scientific computation; climate calculations and dashboard editing are not connected to the main orchestrator. This test does not add them or modify the shared example dashboard.
