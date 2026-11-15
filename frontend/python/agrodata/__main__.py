import argparse
import json
import sys
import sqlite3

from .pipeline import collect, query, dashboard
from .analysis import analyze
from .assets import download, sample_soil
from .workflow import run, inspect_run
from .report import export_csv
from .tools import definitions
from .rasters import process_hls, process_dem


def main():
    parser = argparse.ArgumentParser(description="AgroResilience JSON tool interface")
    parser.add_argument("action", choices=["tools", "run", "inspect-run", "collect", "query", "analyze", "dashboard", "export-csv", "download", "sample-soil", "process-hls", "process-dem"])
    parser.add_argument("--params", help="JSON file; '-' for stdin")
    parser.add_argument("--db", default="data/agro.sqlite3")
    parser.add_argument("--output", help="Output filename (dashboard.html or export.csv by default)")
    parser.add_argument("--assets-dir", default="data/assets")
    parser.add_argument("--reports-dir", default="data/reports")
    args = parser.parse_args()
    try:
        if args.action == "tools":
            print(json.dumps(definitions(), ensure_ascii=False))
            return 0
        if not args.params:
            raise ValueError("--params is required for this action")
        if args.params == "-":
            parameters = json.load(sys.stdin)
        else:
            with open(args.params, encoding="utf-8") as stream:
                parameters = json.load(stream)
        if args.action == "dashboard":
            result = dashboard(args.db, parameters, args.output or "data/dashboard.html")
        elif args.action == "run":
            result = run(args.db, parameters, args.reports_dir)
        elif args.action == "inspect-run":
            result = inspect_run(args.db, parameters)
        elif args.action == "export-csv":
            result = export_csv(args.db, parameters, args.output or "data/export.csv")
        elif args.action == "download":
            result = download(args.db, parameters, args.assets_dir)
        elif args.action == "sample-soil":
            result = sample_soil(args.db, parameters)
        elif args.action == "process-hls":
            result = process_hls(args.db, parameters)
        elif args.action == "process-dem":
            result = process_dem(args.db, parameters)
        else:
            result = {"collect": collect, "query": query, "analyze": analyze}[args.action](args.db, parameters)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        if args.action == "collect" and any(r["status"] == "error" for r in result.values()):
            return 1
        if args.action == "run" and result["status"] != "completed":
            return 1
        return 0
    except (ValueError, KeyError, OSError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
