"""Small deterministic source-access summaries; detailed evidence stays outside model context."""

SOURCE_NAMES = {
    "power": "NASA POWER",
    "soilgrids": "ISRIC SoilGrids",
    "nasadem": "NASADEM",
    "hls": "NASA HLS",
    "gpm": "GPM IMERG",
    "faostat": "FAOSTAT",
}
STATUSES = {
    "available",
    "reachable",
    "partial",
    "unavailable",
    "metadata_only",
    "catalog_only",
    "no_coverage",
    "authentication_required",
    "not_configured",
}


def source_status_summary(result: dict) -> dict:
    sources = result.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 6:
        raise ValueError("Invalid source status result")
    rows = []
    seen = set()
    for source in sources:
        if not isinstance(source, dict):
            raise TypeError("Invalid source row")
        identifier, status = source.get("id"), source.get("status")
        if (
            identifier not in SOURCE_NAMES
            or identifier in seen
            or status not in STATUSES
        ):
            raise ValueError("Invalid source status")
        seen.add(identifier)
        row = {
            "id": identifier,
            "name": SOURCE_NAMES[identifier],
            "status": status,
            "checked_at": str(source.get("checked_at", ""))[:40],
        }
        checks = source.get("checks", [])
        if not isinstance(checks, list) or not all(
            isinstance(check, dict) for check in checks
        ):
            raise ValueError("Invalid probe evidence")
        failures = sorted({str(c.get("reason")) for c in checks if c.get("reason")})
        probe_statuses = sorted(
            {c.get("status") for c in checks if c.get("status") in STATUSES}
        )
        if probe_statuses:
            row["probe_statuses"] = probe_statuses
        elif source.get("probe_statuses"):
            row["probe_statuses"] = [
                status for status in source["probe_statuses"] if status in STATUSES
            ][:8]
        if failures:
            row["issues"] = ", ".join(failures)[:160]
        elif source.get("issues"):
            row["issues"] = str(source["issues"])[:160]
        rows.append(row)
    summary = {
        "kind": "source_status_summary",
        "sources": rows,
        "geometry": result.get("geometry"),
        "details_omitted": True,
        "limitation": "Access/metadata checks only, not raster extraction or scientific analysis. "
        "Full probe URLs, HTTP codes and limitations remain in Tool findings and the dashboard.",
    }
    if isinstance(result.get("nasa_open_api"), dict):
        summary["nasa_open_api"] = {
            key: str(result["nasa_open_api"].get(key, ""))[:180]
            for key in ("status", "reason", "checked_at")
        }
    return summary
