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

The launcher selects the provider in this order: `--provider`, `MODEL_PROVIDER` from your shell or `.env`, then `deepseek`. Model selection is `--model`, then `DEEPSEEK_MODEL` or `OLLAMA_MODEL`, then `deepseek-flash` or `qwen3.5:4b`. Legacy `MODEL_NAME` is not used by the launcher, preventing an old local model tag from reaching a cloud API. Direct backend invocation retains its own existing configuration behavior.

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
