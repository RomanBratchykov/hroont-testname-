"""Offline HTML reports, deterministic chart templates and CSV/JSON exports."""

import csv
import html
import json
from datetime import date
from pathlib import Path

from .analysis import analyze
from .contracts import object_params, strings
from .pipeline import connection, encoded, query

CARDS = {"rainfall", "temperature", "heat_frost", "dry_spells", "seasons", "quality"}


def esc(value):
    return html.escape(str(value), quote=True)


def display(value):
    return "Немає даних" if value is None else f"{value:,.2f}" if isinstance(value, float) else esc(value)


def chart(labels, values, unit, color="#155dfc", bars=False):
    valid = [v for v in values if v is not None]
    if not valid:
        return '<p class="empty">Недостатньо повних даних для цього графіка.</p>'
    minimum, maximum = min(valid), max(valid)
    if bars:
        minimum = min(0, minimum)
    padding = (maximum-minimum) * .08 or 1
    lo, hi = minimum-padding, maximum+padding
    width = 880
    dated = []
    for label in labels:
        try:
            dated.append(date.fromisoformat(str(label)[:10] if len(str(label)) >= 10 else str(label) + "-01").toordinal())
        except ValueError:
            dated = list(range(len(labels)))
            break
    span = max(dated)-min(dated) if dated else 0
    xs = [70 + width*(v-min(dated))/(span or 1) for v in dated]
    fragments = []
    for i in range(5):
        value = lo+(hi-lo)*i/4
        y = 240-i*50
        fragments.append(f'<line x1="65" x2="965" y1="{y}" y2="{y}" stroke="#e5e7eb"/><text x="58" y="{y+4}" text-anchor="end">{value:.1f}</text>')
    last = None
    for i, value in enumerate(values):
        if value is None:
            last = None
            continue
        x, y = xs[i], 240-200*(value-lo)/(hi-lo)
        title = f"{esc(labels[i])}: {display(value)} {esc(unit)}"
        if bars:
            bottom = 240-200*(0-lo)/(hi-lo)
            fragments.append(f'<rect x="{x-3:.2f}" y="{min(y,bottom):.2f}" width="6" height="{max(abs(bottom-y),1):.2f}" fill="{color}"><title>{title}</title></rect>')
        else:
            if last:
                fragments.append(f'<line x1="{last[0]:.2f}" y1="{last[1]:.2f}" x2="{x:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="2"/>')
            fragments.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" fill="{color}"><title>{title}</title></circle>')
        last = (x, y)
    ticks = sorted({0, len(labels)//2, len(labels)-1})
    for index in ticks:
        fragments.append(f'<text x="{xs[index]:.2f}" y="270" text-anchor="middle">{esc(labels[index])}</text>')
    return f'<p class="unit">{esc(unit)}</p><svg viewBox="0 0 1000 290" role="img" aria-label="Часовий ряд, {esc(unit)}">' + "".join(fragments) + "</svg>"


def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>' + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>" + "".join(
        "<tr>" + "".join(f"<td>{display(value)}</td>" for value in row) + "</tr>" for row in rows) + "</tbody></table></div>"


def write_page(output, title, body):
    document = f'''<!doctype html><html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6fb;color:#101828;font:16px/1.55 system-ui,sans-serif}}main{{max-width:1200px;margin:auto;padding:32px 24px}}header{{padding:20px 0 30px}}h1{{font-size:clamp(28px,4vw,44px);line-height:1.15;letter-spacing:-.04em;margin:12px 0}}h2{{font-size:22px;margin:0 0 16px}}.eyebrow{{color:#155dfc;font-weight:700;letter-spacing:.08em;font-size:12px}}.muted,.unit{{color:#667085}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px;margin-bottom:24px}}.metric,section{{background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:24px;margin-bottom:20px}}.grid .metric{{margin:0}}.metric strong{{display:block;font-size:30px;line-height:1.4}}.metric span{{color:#667085;font-size:14px}}.warning{{padding:16px 20px;background:#fff3db;border-left:4px solid #e99c17;border-radius:8px;margin-bottom:20px}}svg{{width:100%;height:auto;min-width:360px}}svg text{{font:12px system-ui;fill:#667085}}.chart{{overflow-x:auto}}.unit{{font-size:13px;margin:0}}.table-scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #eee;white-space:nowrap}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}.empty{{color:#667085;padding:24px;background:#f9fafb}}summary{{cursor:pointer}}footer{{padding:20px 0;color:#667085;font-size:13px}}@media print{{body{{background:white}}section{{break-inside:avoid}}main{{padding:0}}}}
</style></head><body><main><header><div class="eyebrow">AGRORESILIENCE · ХАРКІВСЬКА ОБЛАСТЬ</div><h1>{esc(title)}</h1><p class="muted">Відтворюваний аналіз історичних даних для аграрних рішень</p></header>{body}<footer>Груба сітка джерел не замінює польові вимірювання. Ці показники описують історичний клімат, а не прогноз урожайності чи прибутку.</footer></main></body></html>'''
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(document, encoding="utf-8")


def export_csv(db, parameters, output):
    parameters = object_params(parameters)
    # Full bounded export, never silently export only the first default page.
    records = query(db, dict(parameters, limit=100000, offset=0))
    if len(records) == 100000:
        raise ValueError("Export may be truncated; narrow the date range")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    fields = ["request_id", "source", "observed_at", "variable", "value", "unit", "kind", "metadata"]
    with open(output, "w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            safe = {k: encoded(v) if isinstance(v, dict) else v for k, v in record.items()}
            # Excel may execute formula-like strings even when CSV quoting is used.
            for key, value in safe.items():
                if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
                    safe[key] = "'" + value
            writer.writerow(safe)
    return dict(output=str(output), count=len(records))


def dashboard(db, parameters, output):
    object_params(parameters)
    if parameters.get("variable"):
        records = query(db, dict(parameters, kind="observation", limit=100000, offset=0))
        if len(records) == 100000:
            raise ValueError("Dashboard may be truncated; narrow the date range")
        values = [r["value"] for r in records if r["value"] is not None]
        if len({r["unit"] for r in records}) > 1:
            raise ValueError("Cannot aggregate incompatible units")
        summary = dict(n=len(values), missing=len(records)-len(values), mean=sum(values)/len(values) if values else None,
                       minimum=min(values) if values else None, maximum=max(values) if values else None)
        body = '<section><h2>Огляд показника</h2><pre>' + esc(encoded(summary)) + '</pre><div class="chart">' + chart(
            [r["observed_at"] or str(i) for i, r in enumerate(records)], [r["value"] for r in records], records[0]["unit"] if records else "") + '</div></section>'
        body += '<section><h2>Дані</h2>' + table(["Дата", "Показник", "Значення", "Одиниця"],
            [[r[k] for k in ("observed_at", "variable", "value", "unit")] for r in records]) + '</section>'
        body += '<section><details><summary>Походження</summary><pre>' + esc(encoded(records[0]["metadata"] if records else {})) + '</pre></details></section>'
        write_page(output, parameters.get("title", parameters["variable"]), body)
        return dict(output=str(output), summary=summary)

    cards = strings(parameters.get("cards", ["rainfall", "temperature", "heat_frost", "dry_spells", "seasons", "quality"]), "cards", CARDS)
    analysis = analyze(db, parameters)
    period = analysis["period"]
    summary = {k: period[k] for k in ("start", "end", "coverage", "precipitation_mm", "heat_days", "frost_days", "longest_dry_spell_days")}
    provenance = analysis["provenance"]
    body = f'<p class="muted">Точка: {provenance["latitude"]}, {provenance["longitude"]} · {esc(period["start"])} — {esc(period["end"])} · UTC</p>'
    body += '<div class="grid">' + "".join(f'<div class="metric"><span>{esc(label)}</span><strong>{display(value)}</strong><span>{esc(unit)}</span></div>' for label, value, unit in [
        ("Повнота даних", round(period["coverage"]*100, 1), "% днів"),
        ("Опади за період", period["precipitation_mm"], "мм"),
        ("Спекотні дні", period["heat_days"], f'максимум ≥ {analysis["thresholds"]["heat_c"]} °C'),
        ("Найдовший сухий період", period["longest_dry_spell_days"], "днів")]) + '</div>'
    if not period["complete"]:
        body += '<div class="warning">Є пропущені дані або відсутні потрібні змінні. Суми та показники для неповних вікон не розраховуються.</div>'
    if analysis["excluded_years"]:
        body += '<div class="warning">Неповні календарні роки виключено з річних порівнянь: ' + ", ".join(str(y["year"]) for y in analysis["excluded_years"]) + '.</div>'
    if analysis["n"] < 10:
        body += f'<div class="warning">Повних років у вибірці: {analysis["n"]}. Коротка історія обмежує оцінку кліматичної мінливості; це опис даних, а не прогноз ризику.</div>'
    monthly = analysis["monthly"]
    if "rainfall" in cards:
        body += '<section><h2>Опади за місяцями</h2><div class="chart">' + chart([m["month"] for m in monthly], [m["precipitation_mm"] for m in monthly], "мм / повний місяць", bars=True) + '</div></section>'
    if "temperature" in cards:
        records = query(db, dict(request_id=parameters["request_id"], variable="T2M", kind="observation", start=period["start"], end=period["end"], limit=100000))
        body += '<section><h2>Середня добова температура</h2><div class="chart">' + chart([r["observed_at"] for r in records], [r["value"] for r in records], "°C", color="#d97706") + '</div></section>'
    for card, title, metric, color in [("heat_frost", "Спекотні дні за місяцями", "heat_days", "#dc2626"),
            ("heat_frost", "Морозні дні за місяцями", "frost_days", "#0891b2"),
            ("dry_spells", "Найдовший сухий період у кожному місяці", "longest_dry_spell_days", "#a16207")]:
        if card in cards:
            body += f'<section><h2>{title}</h2><div class="chart">' + chart([m["month"] for m in monthly], [m[metric] for m in monthly], "днів", color=color, bars=True) + '</div></section>'
    if "seasons" in cards:
        for season in analysis["seasons"]:
            body += '<section><h2>' + esc(season["name"]) + '</h2>' + table(
                ["Рік урожаю", "Початок", "Кінець", "Покриття, %", "Опади, мм", "Спека, днів", "Сухий період, днів"],
                [[w["harvest_year"], w["start"], w["end"], round(w["coverage"]*100, 1), w["precipitation_mm"], w["heat_days"], w["longest_dry_spell_days"]] for w in season["windows"]]) + '</section>'
    if "quality" in cards:
        body += '<section><h2>Повнота даних за місяцями</h2>' + table(["Місяць", "Очікувано днів", "Повних днів", "Покриття, %"],
            [[m["month"], m["expected_days"], m["valid_days"], round(m["coverage"]*100, 1)] for m in monthly]) + '</section>'
    body += '<section><details><summary>Джерела, параметри та обмеження</summary><pre>' + esc(encoded(dict(provenance=provenance, thresholds=analysis["thresholds"], caveats=analysis["caveats"]))) + '</pre></details></section>'
    write_page(output, parameters.get("title", "Кліматичний огляд поля"), body)
    return dict(output=str(output), summary=summary, cards=cards)
