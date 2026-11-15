"""Deterministic historical exposure, coverage and cross-year season analysis."""

import calendar
import json
from datetime import date, timedelta
from statistics import median

from .contracts import number, object_params
from .pipeline import connection, query

REQUIRED = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN")


def distribution(values):
    values = sorted(values)
    if not values:
        return dict(n=0, median=None, minimum=None, maximum=None, p10=None, p25=None, p75=None, p90=None)

    def percentile(q):
        position = (len(values) - 1) * q
        index = int(position)
        return values[index] + (values[min(index + 1, len(values) - 1)] - values[index]) * (position - index)

    return dict(n=len(values), median=median(values), minimum=values[0], maximum=values[-1],
                p10=percentile(.1), p25=percentile(.25), p75=percentile(.75), p90=percentile(.9))


def exposure(days, start, end, heat, frost, dry):
    expected = (end - start).days + 1
    series = [days.get((start + timedelta(days=i)).isoformat(), {}) for i in range(expected)]
    valid = [d for d in series if all(d.get(v) is not None for v in REQUIRED)]
    missing_by_variable = {v: sum(d.get(v) is None for d in series) for v in REQUIRED}
    complete = len(valid) == expected
    result = dict(start=start.isoformat(), end=end.isoformat(), expected_days=expected,
        valid_days=len(valid), coverage=len(valid)/expected, complete=complete,
        missing_by_variable=missing_by_variable)
    if not complete:
        return dict(result, precipitation_mm=None, heat_days=None, frost_days=None, longest_dry_spell_days=None)
    longest, streak = 0, 0
    for day in series:
        streak = streak + 1 if day["PRECTOTCORR"] < dry else 0
        longest = max(longest, streak)
    return dict(result, precipitation_mm=sum(d["PRECTOTCORR"] for d in series),
        heat_days=sum(d["T2M_MAX"] >= heat for d in series),
        frost_days=sum(d["T2M_MIN"] < frost for d in series), longest_dry_spell_days=longest)


def analyze(db, parameters):
    object_params(parameters)
    heat = number(parameters.get("heat_threshold", 35), "heat_threshold", -80, 80)
    frost = number(parameters.get("frost_threshold", 0), "frost_threshold", -80, 80)
    dry = number(parameters.get("dry_threshold", 1), "dry_threshold", 0, 1000)
    records = query(db, {k: v for k, v in parameters.items() if k in ("request_id", "start", "end")} |
                    {"kind": "observation", "limit": 100000})
    if len(records) == 100000:
        raise ValueError("Analysis exceeds 100000 records; narrow the date range")
    conn = connection(db)
    try:
        request = dict(conn.execute("SELECT * FROM requests WHERE id=?", (parameters["request_id"],)).fetchone())
    finally:
        conn.close()
    if request["source"] != "power":
        raise ValueError("Climate analysis requires a NASA POWER request")
    original = json.loads(request["parameters"])
    start = max(date.fromisoformat(original["start"]), date.fromisoformat(parameters.get("start", original["start"])))
    end = min(date.fromisoformat(original["end"]), date.fromisoformat(parameters.get("end", original["end"])))
    if start > end:
        raise ValueError("Analysis range does not intersect the collected dates")
    days = {}
    for record in records:
        days.setdefault(record["observed_at"], {})[record["variable"]] = record["value"]
    years, excluded, annual_windows, monthly = [], [], [], []
    for year in range(start.year, end.year + 1):
        item = dict(year=year, **exposure(days, date(year, 1, 1), date(year, 12, 31), heat, frost, dry))
        annual_windows.append(item)
        if item["complete"]:
            years.append(item)
        else:
            excluded.append(dict(year=year, reason="incomplete daily coverage or missing required variables",
                                 coverage=item["coverage"], missing_by_variable=item["missing_by_variable"]))
        for month in range(1, 13):
            first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
            if last < start or first > end:
                continue
            monthly.append(dict(month=f"{year}-{month:02d}", **exposure(days, first, last, heat, frost, dry)))
    baseline = median([r["precipitation_mm"] for r in years]) if years else None
    for item in years:
        item["rain_anomaly"] = (item["precipitation_mm"] - baseline)/baseline if baseline else None
    seasons = []
    specs = parameters.get("seasons", [])
    if not isinstance(specs, list) or len(specs) > 20:
        raise ValueError("seasons must be a list of at most 20 windows")
    for spec in specs:
        object_params(spec)
        name = spec.get("name")
        if not isinstance(name, str) or not 1 <= len(name) <= 100:
            raise ValueError("Season name must be 1..100 characters")
        try:
            sm, sd = map(int, spec["start"].split("-"))
            em, ed = map(int, spec["end"].split("-"))
            date(2001, sm, sd), date(2001, em, ed)
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise ValueError("Season start/end must be MM-DD, excluding February 29") from exc
        cross_year = (sm, sd) > (em, ed)
        windows = []
        for year in range(start.year, end.year + 1):
            first, last = date(year-int(cross_year), sm, sd), date(year, em, ed)
            if last < start or first > end:
                continue
            windows.append(dict(harvest_year=year, **exposure(days, first, last, heat, frost, dry)))
        seasons.append(dict(name=name, windows=windows,
            rainfall=distribution([w["precipitation_mm"] for w in windows if w["complete"]])))
    full = exposure(days, start, end, heat, frost, dry)
    return dict(request_id=parameters["request_id"], period=full, years=years,
        annual_windows=annual_windows, monthly=monthly, seasons=seasons, excluded_years=excluded,
        n=len(years), median_annual_precipitation_mm=baseline,
        annual_rainfall=distribution([r["precipitation_mm"] for r in years]),
        thresholds=dict(heat_c=heat, frost_c=frost, dry_mm=dry),
        provenance=dict(source="NASA POWER", fetched_at=request["fetched_at"], source_url=request["source_url"],
                        latitude=original["latitude"], longitude=original["longitude"], calendar="UTC"),
        caveats=["Heuristic thresholds; historical exposure is not crop damage probability",
                 "Coarse gridded meteorology; not field measurements or a 30-year climate normal",
                 "Incomplete windows have null metrics and are excluded from distributions"])
