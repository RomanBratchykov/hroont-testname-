"""Offline visual report of observable Ollama requests and tool execution."""
import html
import json
from pathlib import Path
from urllib.parse import quote


def esc(value):
    return html.escape(str(value), quote=True)


def details(label, value):
    return f'<details><summary>{esc(label)}</summary><pre>{esc(json.dumps(value, ensure_ascii=False, indent=2))}</pre></details>'


def render(events, directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    requests = [e['data'] for e in events if e['stage'] == 'request']
    results = [e['data'] for e in events if e['stage'] == 'tool_result']
    errors = [e['data'] for e in events if e['stage'] == 'error']
    tool_errors = [r for r in results if r['result'].get('error') or r['result'].get('status') in ('failed', 'partial')]
    finished = [e['data'] for e in events if e['stage'] == 'finished']
    status = 'Failed' if errors else (finished[-1]['status'].replace('_', ' ').title() if finished else 'In progress')
    model = requests[0].get('model', 'Unknown') if requests else 'Unknown'
    messages = requests[0].get('messages', []) if requests else []
    prompt = next((m.get('content', '') for m in messages if m.get('role') == 'user'), '')
    elapsed = max((e.get('elapsed_seconds', 0) for e in events), default=0)
    cards = ''.join(f'<article class="metric"><span>{esc(label)}</span><strong>{esc(value)}</strong></article>'
                    for label, value in [('Run status', status), ('Model requests', len(requests)),
                                         ('Tools executed', len(results)), ('Issues', len(errors) + len(tool_errors))])
    sizes = [len(json.dumps(r, ensure_ascii=False).encode()) for r in requests]
    chart = '<p class="muted">No model requests recorded.</p>'
    if sizes:
        maximum = max(sizes)
        bars = []
        for i, size in enumerate(sizes):
            y = 12 + i * 44
            width = size / maximum * 570
            bars.append(f'<text x="0" y="{y+18}">Turn {i+1}</text><rect x="70" y="{y}" width="{width:.1f}" height="26" rx="5"/><text x="{width+80:.1f}" y="{y+18}">{size/1024:.1f} KB</text>')
        chart = f'<svg role="img" aria-label="Request size in kilobytes for each Ollama turn" viewBox="0 0 750 {len(sizes)*44+20}">' + ''.join(bars) + '</svg>'
    timeline = []
    for index, event in enumerate(events):
        stage, data = event['stage'], event['data']
        label = {'request': 'Information sent to Ollama', 'response': 'Ollama response',
                 'tool_result': 'Python tool result', 'error': 'Execution error', 'finished': 'Run finished'}.get(stage, stage)
        text = ''
        if stage == 'response':
            text = data.get('content', '') or ', '.join(c.get('function', {}).get('name', '?') for c in data.get('tool_calls', []))
        elif stage == 'tool_result':
            text = data['name']
        elif stage == 'error':
            text = str(data)
        time = f"{event['elapsed_seconds']:.1f}s" if 'elapsed_seconds' in event else 'Time unavailable'
        timeline.append(f'<li class="event {esc(stage)}"><div class="event-heading"><b>{index+1:02d} · {esc(label)}</b><span>{esc(time)}</span></div><p class="answer">{esc(text)}</p>{details("Inspect exact payload", data)}</li>')
    links = []
    metrics = []
    for item in results:
        result = item['result']
        paths = dict(result.get('artifacts') or {})
        if result.get('output'):
            paths['dashboard'] = result['output']
        for name, value in paths.items():
            try:
                path = Path(value).resolve()
                relative = path.relative_to(directory)
                if path.is_file() and path.suffix.lower() in {'.html', '.json', '.csv'}:
                    links.append(f'<a class="artifact" href="{esc(quote(relative.as_posix()))}">{esc(name)} ↗<small>{esc(relative)}</small></a>')
            except (ValueError, TypeError, OSError):
                continue
        summary = result.get('summary') or {}
        if summary:
            rows = []
            for key, value in summary.items():
                if isinstance(value, (dict, list)):
                    continue
                if value is None:
                    shown = 'Not available'
                elif key == 'coverage' and isinstance(value, (int, float)):
                    shown = f'{value*100:.1f}%'
                else:
                    shown = str(value)
                rows.append(f'<tr><th scope="row">{esc(key.replace("_", " "))}</th><td>{esc(shown)}</td></tr>')
            metrics.append(f'<article><h3>{esc(item["name"])}</h3><table>{"".join(rows)}</table></article>')
    warning = '<p class="warning">Tool failures or partial results occurred. Inspect the timeline before using the model explanation.</p>' if tool_errors else ''
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ollama · Run dashboard</title>
<style>
:root{color-scheme:dark;font-family:Inter,system-ui,sans-serif;background:#0b1119;color:#e6edf5}*{box-sizing:border-box}body{margin:0}main{max-width:1200px;margin:auto;padding:48px 28px}header{display:flex;justify-content:space-between;gap:24px;align-items:start}h1{font-size:clamp(30px,5vw,48px);letter-spacing:-.04em;margin:10px 0}h2{font-size:20px;margin:0 0 24px}h3{font-size:15px;color:#85dcb5}.eyebrow{font-size:12px;letter-spacing:.15em;color:#85dcb5;text-transform:uppercase}.muted,small{color:#94a6ba}header p{max-width:720px;line-height:1.6}.badge{border:1px solid #385443;border-radius:30px;padding:10px 18px;color:#98ebc4;white-space:nowrap}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:30px 0}.metric,section{background:#121d2a;border:1px solid #253447;border-radius:16px;padding:24px}.metric span{display:block;color:#94a6ba;font-size:13px}.metric strong{display:block;font-size:28px;margin-top:16px}.layout{display:grid;grid-template-columns:1.25fr 1fr;gap:20px}section{margin-bottom:20px}.wide{grid-column:1/-1}svg{width:100%;max-height:600px}svg rect{fill:#63d9ad}svg text{fill:#bfccdb;font:13px system-ui}.flow{display:flex;flex-wrap:wrap;gap:12px;color:#85dcb5;font-size:14px;padding:12px 0 24px}.flow span{padding:10px 15px;background:#1c3040;border-radius:8px}ol{list-style:none;padding:0;margin:0}.event{padding:20px 0 20px 22px;border-left:2px solid #345770}.event.tool_result{border-color:#63d9ad}.event.error{border-color:#ff998f}.event-heading{display:flex;justify-content:space-between;gap:16px;font-size:14px}.event-heading span{color:#94a6ba;font-size:12px}.answer{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6;font-size:14px}details{margin:12px 0}summary{color:#91bce8;cursor:pointer;font-size:13px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b141f;padding:16px;border-radius:8px;max-height:360px;overflow:auto;font-size:12px}.artifact{display:block;padding:16px;border:1px solid #345770;border-radius:10px;color:#85dcb5;text-decoration:none;margin:10px 0}.artifact small{display:block;margin-top:8px;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:10px 0;border-bottom:1px solid #253447;text-align:left}th{font-weight:400;color:#94a6ba}td{text-align:right}.warning{padding:16px;border:1px solid #ae773e;border-radius:10px;color:#ffd39c}footer{color:#94a6ba;font-size:12px;line-height:1.7}@media(max-width:760px){main{padding:24px 16px}.cards{grid-template-columns:repeat(2,1fr)}.layout{display:block}header{display:block}.badge{display:inline-block}.metric,section{padding:18px}.metric strong{font-size:22px}}
</style><main>'''
    document += f'<header><div><div class="eyebrow">Local inference · Execution observatory</div><h1>From information to insight</h1><p class="muted">An observable record of what Ollama receives, which tools it selects, and what Python produces.</p><p><b>{esc(model)}</b> <span class="muted">· {elapsed:.1f}s recorded</span></p></div><span class="badge">{esc(status)}</span></header>'
    document += f'<div class="cards">{cards}</div>{warning}<div class="flow"><span>01 · Input</span>→<span>02 · Ollama</span>→<span>03 · Python tools</span>→<span>04 · Visual reports</span></div><div class="layout">'
    document += f'<section><h2>Context sent per turn</h2>{chart}<p class="muted">Serialized request size, including instructions, history and tool definitions. Bytes are not token counts.</p></section>'
    document += f'<section><h2>Your task</h2><p class="answer">{esc(prompt) or "No task recorded."}</p>{details("Initial instructions and tool schemas", requests[0] if requests else {})}</section>'
    document += '<section><h2>Generated reports</h2>' + (''.join(dict.fromkeys(links)) or '<p class="muted">No verified report files yet. Reports appear after a successful dashboard tool call.</p>') + '</section>'
    document += '<section><h2>Computed results</h2>' + (''.join(metrics) or '<p class="muted">No computed summaries recorded yet. Tool payloads remain available in the timeline.</p>') + '</section>'
    document += '<section class="wide"><h2>Execution timeline</h2><ol>' + ''.join(timeline) + '</ol></section></div><footer>Refresh this file to see the latest recorded stage while a run is active. This dashboard shows observable messages and tool execution; it does not expose internal model reasoning. Climate plots are in the generated reports. Missing values are not zero.</footer></main></html>'
    path = directory / 'run-dashboard.html'
    temporary = directory / 'run-dashboard.tmp'
    temporary.write_text(document, encoding='utf-8')
    temporary.replace(path)
    return path
