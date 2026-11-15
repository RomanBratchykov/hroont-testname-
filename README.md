# AgroResilience · Croptato

## If the website does not open, run the app on your computer

You can use the app locally if the hosted website is unavailable. Render is not required for this fallback; the chat connects directly to the hosted DeepSeek API.

1. Download this repository as a ZIP and extract it, or clone it. You need the **whole project**, not just the script.
2. Install **Python 3.12+** with pip/venv and **Node.js 22.18+ (22.x) or 24+** with npm. On Ubuntu/Linux Mint, install `python3-venv` if needed. Have an internet connection and a funded **DeepSeek API key** ready.
3. Open a terminal in the extracted project folder and run the command for your computer.

**Windows — PowerShell or Command Prompt:**

```powershell
py -3 start_deepseek.py
```

**Linux or macOS — Terminal:**

```bash
python3 start_deepseek.py
```

4. On the first run, enter your DeepSeek API key when asked; it will not be shown as you type. Enter the current input and output prices in USD per million tokens from [DeepSeek’s pricing page](https://api-docs.deepseek.com/quick_start/pricing/) for the configured model (`deepseek-flash` by default). Use uncached input and the highest applicable rates for conservative cost tracking. Existing settings in `.env` are reused.
5. Wait for installation and the frontend build to finish, then open **http://127.0.0.1:8000** in your browser. Keep the terminal open while using the app. Press **Ctrl+C** to stop it.

**What the script does:** it creates a project Python environment, installs missing app dependencies, saves entered credentials in the private, Git-ignored `.env` file, builds the web interface, and starts the app on your computer using DeepSeek. It needs no Render account, Docker, Ollama or local GPU for this default mode. Chat requests use your DeepSeek credit; starting the app alone does not send a paid model request. The API key stays on the backend.

The local fallback includes chat, supported file attachments, John’s saved example profile and the example dashboard. Retrieval from the scientific document/database collection is optional and needs additional setup; it is not enabled by this command.

**If startup fails:** read the terminal message. For missing Python or Node, install the prerequisites above and rerun. To reinstall app dependencies, add `--setup`. If port 8000 is occupied, add `--port 8080` and open **http://127.0.0.1:8080**. A rejected API key or exhausted DeepSeek balance must be corrected in your DeepSeek account. See [detailed setup and optional retrieval](docs/setup.md). Linux has been tested; Windows/macOS launch paths are provided but have not been verified on those operating systems.

## What the app does and its scientific limits

Croptato helps farmers discuss their field, review supplied information and explore example crop rotations with Soily, a DeepSeek-powered assistant. It can explain available evidence, identify missing inputs and show the saved demonstration dashboard.

The project is designed to preserve scientific accuracy through explicit sources, units, time periods and data-quality limitations, and by separating model explanations from deterministic calculations. NASA POWER represents historical gridded climate, not a field-station observation or a forecast. Missing measurements must not become invented values or zeros.

**This version is a demonstration, not a scientifically validated decision system.** John’s field, example rotations and saved dashboard are synthetic. The main chat does not yet run the separate climate-analysis/dashboard pipeline or produce validated agronomic recommendations. DeepSeek answers can be wrong and need checking against their sources. Scientific safeguards do not establish field-level accuracy; real recommendations require suitable data, connected calculations and regional validation.

The sections below cover advanced setup, providers and development. Run commands from the project folder.

## First setup

```bash
./run.sh --setup
```

On Windows PowerShell:

```powershell
.\run.ps1 --setup
```

Setup creates `.env` automatically if it is missing and preserves existing settings.

For the existing tunnel, set `PUBLIC_ORIGIN=https://gravitydefiers.dpdns.org` in `.env`.
Start the production app on the tunnel’s configured port, then run the tunnel in another terminal:

```bash
./run.sh --port 5173
cloudflared tunnel run gravitydefiers
```

The public origin allows only that hostname and browser origin. This demo shares one workspace;
use Cloudflare Access to restrict who can reach it.

## Test with local Ollama

Start Ollama separately (`ollama serve` if it is not already running).
Use `ollama list` to find an installed model. Pick one that supports tools and thinking.
The launcher does not download models.

```bash
./run.sh --provider ollama --model qwen3.5:4b-q4_K_M 
```

Open **http://127.0.0.1:8000**. The app builds the frontend and serves it with the API.
Use the preview entry to open the chat. Fast/Auto/Reasoning controls response mode;
the provider is chosen by the launch command. Ctrl+C stops the app.

## Test with DeepSeek

Edit `.env`: set `DEEPSEEK_API_KEY` and both token rates using the
[current pricing](https://api-docs.deepseek.com/quick_start/pricing/).
Use uncached input and the highest output rate applicable to your selected model/mode.

```bash
./run.sh --provider deepseek --model deepseek-flash
```

To use a local DeepSeek model (e.g., `deepseek-r1:8b` via Ollama's OpenAI-compatible `/v1` API), set `OPENAI_BASE_URL=http://localhost:11434/v1` and `DEEPSEEK_MODEL=deepseek-r1:8b` in `.env` (no paid API rates required), or run:

```bash
./run.sh --provider deepseek --model deepseek-r1:8b
```

The launcher defaults to the DeepSeek API; use `--provider ollama` for local inference. Full mode starts RAG on port 8001 and uses Docker Compose or existing local PostgreSQL/Qdrant services. Indexing is explicit and resumable: add `--ingest` and monitor `RAG/ingestion.log`. `--no-rag` disables retrieval; `--with-rag` enables it with `--backend-only`. See [portable setup](docs/setup.md) for dependencies and `--doctor`.

Testing has a **$3** limit. To use the separate **$2 demo** allowance:

```bash
./run.sh --provider deepseek --phase demo
```

Spending and in-flight reservations are saved in `data/orchestrator.sqlite`.
Uncertain/cancelled paid calls retain their reservations to avoid accidental overspending.
Do not delete this database to reset chat history; use **Clear history** in the app.
There is no automatic provider fallback.

## Other run modes

```bash
./run.sh --frontend-only                 # UI preview, no backend/model calls; port 5173
./run.sh --provider ollama --dev          # API + frontend live reload; port 5173
./run.sh --provider ollama --backend-only # API only; port 8000
./run.sh --provider ollama --port 8080    # Built app on a different local port
```

Guest access is the default: each browser gets a private server-side workspace, identified by
an HttpOnly cookie retained for 30 days. Browsers sharing cookies share a workspace; use different
browser profiles or devices for separate users. Clearing cookies loses access to that guest history.
DeepSeek accepts up to 50 active guests by default. Set `MAX_ACTIVE_USERS` (1–10000) to change
this limit. A slot expires after 30 minutes without a chat API request, unless a model request
is still running. Ollama has no guest limit. Both providers process four model requests at a
time by default; other turns wait in the queue. Set `MODEL_CONCURRENCY` (1–64) to change that
per-process limit. For example, `MAX_ACTIVE_USERS=100` and `MODEL_CONCURRENCY=8` admit 100
active guests while processing eight turns at once. Restart the backend after changing these
settings. `/api/health` reports both limits. These settings do not establish tested throughput;
actual capacity depends on the server and provider. Spending limits remain unchanged.
Chat ownership is checked on the server, including history clearing and model tool access.
Existing chats without an owner remain stored but are not exposed to new guests.
Frontend-only history stays in browser storage and is separate from server history.

## Two API endpoints

- `GET /api/health`: configuration, selected provider/model, capacity and spending; does not call a model.
- `POST /api/chat`: send, list, read, rename, delete or clear chats. Sending streams newline-delimited JSON
  events (`status`, `answer`, `error`); model text arrives when the model call finishes.

```bash
curl -N http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"action":"send","conversation_id":"test","request_id":"turn-1","message":"Hello","mode":"fast"}'
```

Use a new `request_id` for each turn. Repeating a completed request returns its saved answer.
Closing/reloading the browser or pressing Stop cancels unfinished processing; it never resumes automatically.
A provider may still bill a request already sent. Chats expire after 30 days of inactivity.

## Files, translation and future scripts

Attach `.md`, `.txt`, `.json`, `.geojson`, `.csv` or `.tsv` through the picker, drag-and-drop,
or clipboard file paste. Text must be UTF-8 and JSON must be valid. Images, PDFs, spreadsheets
and other formats are rejected with instructions to paste relevant text or export a supported
text format. No binary uploads are sent to DeepSeek. Limits: 10 MB/file, three files,
15 MB combined encoded request, 24 KB combined extracted text. Text is supplied directly,
not indexed as RAG.

To display a field, open the dashboard's **Show a field boundary** form and paste four
`[longitude, latitude]` pairs in boundary order, or a GeoJSON Polygon. A repeated closing
coordinate is accepted. Valid polygon JSON in chat or an attached text file also displays
an inline map. The map fits the boundary automatically; crossing edges, duplicate corners,
out-of-range coordinates and zero-area shapes are rejected. Boundaries are farmer-provided
and unverified, and do not change the separately selected climate query point.

The app limits the entire serialized model request to 32 KB by default, including policy,
tool schemas, history, reasoning continuation and tool results. A small user message can
therefore still trigger the limit. Older turns are removed first; oversized tool results
are replaced in model context with an explicit omission notice, while full results remain
in **Tool findings**. If the continuation still cannot fit, the app returns a partial result
with the available findings. Context overflow logs record byte counts, not private content.

Soily can persist farmer-provided facts and field boundaries using `save_user_info`, and read
them with `read_user_info`. Personal state displays this saved profile, separate from John's
synthetic example. The dashboard's **Save field** button persists the displayed polygon and
loads it on subsequent visits. Saving records farmer-reported information, not verification.
Profiles are stored in SQLite and scoped to the existing private browser session cookie;
they survive new chats, page reloads, chat-history deletion and server restarts. Clearing or
losing that cookie loses access; there is no cross-device login account. Only confirmed server
writes are described as saved. The welcome introduction appears only on the first chat screen
and is dismissed when navigating to other pages.

Opening Field dashboard automatically loads NASA POWER climate coverage and checks the data
source APIs. Selecting another point or displaying a new boundary refreshes both; leaving the
dashboard cancels pending requests. A saved boundary's center is used for its point-based
climate query. Manual load/check buttons remain available for retries.

English works immediately. Non-English input requires a configured LibreTranslate-compatible `TRANSLATION_URL`;
otherwise the app asks for English without sending detected non-English text to the model. Language detection is local and heuristic; short ambiguous Latin text is treated as English. Short translations
have a one-second timeout; larger inputs have 30 seconds. This is a limit, not a measured speed guarantee.
Translation status appears beside the mascot; Settings can hide that notice.

Scientific scripts/datasets, embeddings, validated Personal state extraction and charts will be added later.
The available tools include saved profile read/write, chat history, capability checks and climate/source retrieval. Register future approved tools in
`backend/tools.py`; the model cannot create scripts or execute shell commands. The loop allows at most
six model calls and ten tool executions, with configurable parallel turns and one active turn per chat.
The app must explain missing evidence rather than invent scientific results.

## Checks

```bash
.venv/bin/python -m pytest backend/tests
.venv/bin/python -m ruff check backend scripts
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run lint
```

Provider formats follow the official [Ollama chat API](https://docs.ollama.com/api/chat) and
[DeepSeek tool calling](https://api-docs.deepseek.com/guides/tool_calls/) documentation.

## Start Croptato automatically

Generate Linux startup units using `scripts/install_startup.py`; it discovers this checkout’s Python and Node paths. It serves the built app on port 5173 and can install user-owned native database units on this PC. Docker is the portable database option on a fresh laptop. Enable user lingering for startup before login. Ollama and Cloudflared remain separate services.

```bash
.venv/bin/python scripts/install_startup.py --native-databases --provider ollama --start
```

For hosted DeepSeek, configure the private `.env` key and both current per-million-token rates, then run the installer with `--provider deepseek --start`. The launcher defaults to DeepSeek and stops with a configuration error when credentials are missing; use `--provider ollama` explicitly for local inference.

```bash
systemctl --user status croptato.service
journalctl --user -u croptato.service -f
systemctl --user restart croptato.service
systemctl --user disable --now croptato.service
```

## Judges’ test workspace

The site opens directly with a Soily introduction on every page load; there is no login screen.
All visitors can view John’s shared test profile (`/#/personal-state`) and saved example dashboard
(`/#/dashboard`) without using a model slot. Visitor chats remain private guest sessions.
The shared example is saved in `input_data/john_showcase.json`, bundled with the site and supplied
to Soily’s context. It survives server restarts and can be downloaded from the dashboard.
John is a test persona. Kherson, the synthetic 30-ha rainfed field, and the three example rotations
follow the technical specification; none is a validated scientific recommendation.
Chat can discuss hypothetical changes but cannot overwrite the shared example. Editing the JSON
and restarting the app publishes an updated example. Scientific analysis is not connected.
