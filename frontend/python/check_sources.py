"""Opt-in live probes: python3 check_sources.py. Never run as part of unit tests."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from agrodata.pipeline import CMR, PRODUCTS, now


def probe(item):
    name, url = item
    try:
        with urlopen(Request(url, headers={"User-Agent": "AgroResilience/0.2.0"}), timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = response.read(2_000_000)
            result = dict(source=name, status="reachable", http_status=response.status, content_type=content_type)
            if "json" in content_type:
                data = json.loads(payload)
                if "feed" in data:
                    result["sample_count"] = len(data["feed"].get("entry", []))
                elif "data" in data:
                    result["sample_count"] = len(data["data"])
                    result["sample_keys"] = list(data["data"][0]) if data["data"] else []
                else:
                    result["sample_keys"] = list(data)
            elif "xml" in content_type:
                result["service_exception"] = b"ExceptionReport" in payload or b"ServiceException" in payload
            return result
    except Exception as exc:
        return dict(source=name, status="unavailable", error=f"{type(exc).__name__}: {exc}")


def main():
    probes = {}
    for source, (product, version) in PRODUCTS.items():
        params = dict(short_name=product, version=version, point="36.2304,49.9935", page_size=1)
        if source not in ("nasadem", "srtm"):
            params["temporal"] = "2025-01-01T00:00:00Z,2025-01-02T23:59:59Z"
        if source.startswith("hls"):
            params["temporal"] = "2025-04-01T00:00:00Z,2025-04-30T23:59:59Z"
        probes[source] = CMR + "?" + urlencode(params)
    probes["faostat_legacy"] = "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL?area=230&item=15&element=5510&year=2023&page_size=1"
    probes["faostat_current_without_token"] = "https://faostatservices.fao.org/api/v1/en/data/QCL?area=230&item=15&element=5510&year=2023&output_type=objects"
    probes["soilgrids_wcs"] = "https://maps.isric.org/mapserv?map=/map/clay.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities"
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(probe, probes.items()))
    report = dict(checked_at=now(), probes=results)
    Path("data").mkdir(exist_ok=True)
    Path("data/source-checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
