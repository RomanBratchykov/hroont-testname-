"""Small explicit contracts shared by CLI and model tools; no model executes SQL."""

import math
import re
from datetime import date, datetime, timezone


def integer(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def number(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be finite in {minimum}..{maximum}")
    return float(value)


def object_params(parameters):
    if not isinstance(parameters, dict):
        raise ValueError("Parameters must be a JSON object")
    return parameters


def strings(value, name, allowed):
    if not isinstance(value, list) or not value or any(not isinstance(v, str) or v not in allowed for v in value):
        raise ValueError(f"{name} must be a nonempty list from {sorted(allowed)}")
    return list(dict.fromkeys(value))


def dates(parameters):
    try:
        start, end = date.fromisoformat(parameters["start"]), date.fromisoformat(parameters["end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("start and end must be ISO dates: YYYY-MM-DD") from exc
    if start > end or end >= datetime.now(timezone.utc).date():
        raise ValueError("Expected start <= end, with end before today (UTC)")
    if (end - start).days > 366 * 45:
        raise ValueError("Date range exceeds 45 years")
    return start, end


def request_ref(parameters):
    object_params(parameters)
    ref = parameters.get("request_id")
    if not isinstance(ref, str) or not ref or len(ref) > 128:
        raise ValueError("request_id must be a nonempty string, at most 128 characters")
    return ref


def schema_check(value, schema, path="arguments"):
    """Validate the subset of JSON Schema emitted by our own tool definitions."""
    kind = schema.get("type")
    if kind == "object":
        object_params(value)
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(props):
            raise ValueError(f"{path}: unknown properties {sorted(set(value)-set(props))}")
        if set(schema.get("required", [])) - set(value):
            raise ValueError(f"{path}: missing required properties")
        for key, item in value.items():
            if key in props:
                schema_check(item, props[key], path + "." + key)
    elif kind == "array":
        if not isinstance(value, list) or not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 1000):
            raise ValueError(f"{path}: invalid array length or type")
        for item in value:
            schema_check(item, schema["items"], path + "[]")
    elif kind in ("integer", "number"):
        validator = integer if kind == "integer" else number
        validator(value, path, schema.get("minimum", -1e308), schema.get("maximum", 1e308))
    elif kind == "boolean" and not isinstance(value, bool):
        raise ValueError(f"{path}: expected boolean")
    elif kind == "string":
        if not isinstance(value, str) or not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 10000):
            raise ValueError(f"{path}: invalid string length or type")
        if schema.get("pattern") and not re.fullmatch(schema["pattern"], value):
            raise ValueError(f"{path}: invalid string format")
        if schema.get("format") == "date":
            date.fromisoformat(value)
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: unsupported value")
