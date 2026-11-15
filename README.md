# AgroResilience local test app

Requires Python 3.12+, Node 22.18+ and npm. On Linux Mint, Python setup also needs `python3-venv`.
Run commands from this folder.

## First setup

```bash
./run.sh --setup
cp .env.example .env
```

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

Connected modes share one local demo administrator workspace. The preview login is not
real authentication. All services bind to localhost; there is no hosting/tunnel setup.
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

Attach `.md`, `.txt`, `.json` or `.xlsx`. Files are parsed locally into text; no binary uploads
are sent to DeepSeek. Limits: 10 MB/file, three files, 15 MB combined encoded request,
24 KB combined extracted text. Unsupported, oversized and macro-containing files are rejected.
Excel formulas are preserved as text, not evaluated. Text is supplied directly, not indexed as RAG.

English works immediately. Non-English input requires a configured LibreTranslate-compatible `TRANSLATION_URL`;
otherwise the app asks for English without sending detected non-English text to the model. Language detection is local and heuristic; short ambiguous Latin text is treated as English. Short translations
have a one-second timeout; larger inputs have 30 seconds. This is a limit, not a measured speed guarantee.
Translation status appears beside the mascot; Settings can hide that notice.

Scientific scripts/datasets, embeddings, validated Personal state extraction and charts will be added later.
The available tools currently read chat history and report capabilities. Register future approved tools in
`backend/tools.py`; the model cannot create scripts or execute shell commands. The loop allows at most
six model calls and ten tool executions, with four active turns and one active turn per chat.
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
