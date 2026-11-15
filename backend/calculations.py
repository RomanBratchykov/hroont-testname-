"""Deterministic, bounded calculations on explicit inputs; no inferred scientific factors."""

import hashlib
import json
import re
from decimal import Decimal
from itertools import pairwise
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.config import ROOT

SCIENTIFIC_TOOLS = [
    "calculate_gross_margin",
    "calculate_crop_score",
    "validate_rotation",
    "calculate_rusle",
]
SCENARIO = json.loads(
    (ROOT / "input_data/john_showcase.json").read_text(encoding="utf-8")
)
NonNegative = Annotated[float, Field(ge=0, le=1e12, strict=True)]
Score = Annotated[float, Field(ge=0, le=100, strict=True)]


class Arguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, str_strip_whitespace=True, str_min_length=1
    )


class GrossMarginArgs(Arguments):
    crop: str = Field(min_length=1, max_length=60)
    yield_t_ha: NonNegative | None = None
    price_per_t: NonNegative | None = None
    variable_cost_per_ha: NonNegative | None = None
    area_ha: float | None = Field(default=None, gt=0, le=1e8, strict=True)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    price_year: int | None = Field(default=None, ge=1900, le=2100)
    use_configured_assumptions: bool = False


def _profile_number(facts, key):
    try:
        value = float(facts[key])
        return value if 0 <= value <= 1e12 else None
    except (KeyError, TypeError, ValueError):
        return None


def gross_margin(args: GrossMarginArgs, profile: dict) -> dict:
    crop = args.crop.strip().lower().replace(" ", "_").replace("-", "_")
    facts = profile.get("facts", {})
    configured = SCENARIO["economics"] if args.use_configured_assumptions else {}
    crop_inputs = configured.get("crop_assumptions", {}).get(crop, {})
    inputs, sources = {}, {}
    for key, scenario_key in [
        ("yield_t_ha", "yield"),
        ("price_per_t", "price"),
        ("variable_cost_per_ha", "variable_cost"),
    ]:
        value = getattr(args, key)
        source = "explicit calculation input"
        if value is None:
            value = _profile_number(facts, f"{crop}_{key}")
            source = f"saved profile: {crop}_{key}"
        if value is None and crop_inputs:
            value = crop_inputs[scenario_key]["value"]
            source = f"input_data/john_showcase.json: economics.crop_assumptions.{crop}.{scenario_key} (configured assumption)"
        inputs[key], sources[key] = value, source
    currency = args.currency or facts.get("currency") or configured.get("currency")
    year = (
        args.price_year
        or _profile_number(facts, "price_year")
        or configured.get("price_year")
    )
    area = args.area_ha
    if area is None:
        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*ha\s*", facts.get("field_area", ""), re.IGNORECASE
        )
        area = float(match[1]) if match and 0 < float(match[1]) <= 1e8 else None
    missing = [key for key, value in inputs.items() if value is None]
    if currency is None or not re.fullmatch(r"[A-Z]{3}", currency):
        missing.append("currency")
    if year is None or not 1900 <= year <= 2100 or int(year) != year:
        missing.append("price_year")
    if (
        args.use_configured_assumptions
        and crop_inputs
        and currency != configured["currency"]
    ):
        missing.append(
            "currency matching configured assumptions; no currency conversion is performed"
        )
    if any(
        "configured assumption" in sources[key]
        for key in ("price_per_t", "variable_cost_per_ha")
    ) and year != configured.get("price_year"):
        missing.append(
            "price_year matching configured monetary inputs; no inflation adjustment is performed"
        )
    basis = (
        "configured_assumptions"
        if any("configured assumption" in source for source in sources.values())
        else "supplied_inputs"
    )
    result = {
        "status": "insufficient_data" if missing else "computed",
        "crop": crop,
        "basis": basis,
        "inputs": inputs,
        "input_sources": sources,
        "missing_inputs": missing,
        "gross_margin_per_ha": None,
        "gross_margin_total": None,
        "yield_forecast": None,
        "method": "gross-margin-v1: yield_t_ha * price_per_t - variable_cost_per_ha",
        "period": str(int(year)) if year is not None and 1900 <= year <= 2100 else None,
        "limitations": "Conditional gross margin, not net profit or a yield forecast. Excludes fixed costs, tax and financing. Prices and variable costs must use the same currency and stated year. Configured values are assumptions, not market quotes. This arithmetic does not validate crop suitability.",
    }
    if missing:
        return result
    revenue = Decimal(str(inputs["yield_t_ha"])) * Decimal(str(inputs["price_per_t"]))
    margin = revenue - Decimal(str(inputs["variable_cost_per_ha"]))
    result["revenue_per_ha"] = {
        "value": float(round(revenue, 2)),
        "unit": f"{currency}/ha",
    }
    result["gross_margin_per_ha"] = {
        "value": float(round(margin, 2)),
        "unit": f"{currency}/ha",
    }
    result["area_ha"] = area
    if area is not None:
        result["gross_margin_total"] = {
            "value": float(round(margin * Decimal(str(area)), 2)),
            "unit": currency,
        }
    return result


class Component(Arguments):
    value: Score | None = None
    source: str = Field(min_length=1, max_length=200)
    method: str = Field(min_length=1, max_length=200)


class Constraint(Arguments):
    passed: bool | None = Field(default=None, strict=True)
    source: str = Field(min_length=1, max_length=200)


class CropScoreArgs(Arguments):
    crop: str = Field(min_length=1, max_length=60)
    components: dict[
        Literal["temperature", "water_climate", "soil", "rotation"], Component
    ] = Field(default_factory=dict)
    hard_constraints: dict[
        Literal["climate", "soil", "irrigation", "calendar", "rotation"], Constraint
    ] = Field(default_factory=dict)
    period: str = Field(default="supplied input scenario", min_length=1, max_length=100)


def crop_score(args: CropScoreArgs) -> dict:
    weights = {
        "temperature": 0.35,
        "water_climate": 0.35,
        "soil": 0.20,
        "rotation": 0.10,
    }
    missing = [
        key
        for key in weights
        if key not in args.components or args.components[key].value is None
    ]
    missing += [
        f"constraint:{key}"
        for key in ("climate", "soil", "irrigation", "calendar", "rotation")
        if key not in args.hard_constraints or args.hard_constraints[key].passed is None
    ]
    failed = [
        key for key, value in args.hard_constraints.items() if value.passed is False
    ]
    result = {
        "status": "blocked"
        if failed
        else "insufficient_data"
        if missing
        else "computed",
        "crop": args.crop,
        "score": None,
        "missing_inputs": missing,
        "failed_constraints": failed,
        "components": {
            key: value.model_dump() for key, value in args.components.items()
        },
        "hard_constraints": {
            key: value.model_dump() for key, value in args.hard_constraints.items()
        },
        "weights": weights,
        "method": "spec-section-8-weighted-screening-v1",
        "period": args.period,
        "source": "AGENTS/AgroResilience_Technical_Scientific_Specification_v1.1.docx.md section 8",
        "interpretation": "comparative_screening_not_probability",
        "limitations": "Prototype weighted arithmetic on sourced input scores after hard gates. Weights are illustrative and not regionally calibrated. Never invent components from monthly climate, NDVI or unknown soil data. This is not a crop-damage probability, yield forecast or validated recommendation.",
    }
    if not missing and not failed:
        result["score"] = {
            "value": round(
                sum(
                    args.components[key].value * weight
                    for key, weight in weights.items()
                ),
                4,
            ),
            "unit": "points (0-100)",
        }
    return result


class Factor(Arguments):
    value: NonNegative
    unit: str = Field(min_length=1, max_length=50)
    source: str = Field(min_length=1, max_length=200)
    method: str = Field(min_length=1, max_length=200)


class RusleCell(Arguments):
    cell_id: str = Field(min_length=1, max_length=80)
    area_ha: float = Field(gt=0, le=1e8, strict=True)
    R: Factor | None = None
    K: Factor | None = None
    LS: Factor | None = None
    C: Factor | None = None
    P: Factor | None = None


class RusleArgs(Arguments):
    period: str | None = Field(default=None, min_length=1, max_length=100)
    cells: list[RusleCell] = Field(default_factory=list, max_length=1000)


def rusle(args: RusleArgs) -> dict:
    units = {
        "R": "MJ mm/(ha h yr)",
        "K": "t ha h/(ha MJ mm)",
        "LS": "1",
        "C": "1",
        "P": "1",
    }
    missing = [] if args.period else ["common long-term averaging period"]
    if not args.cells:
        missing += list(units) + ["spatial cells with areas"]
    if len({cell.cell_id for cell in args.cells}) != len(args.cells):
        missing.append("unique cell identifiers")
    for cell in args.cells:
        for key, unit in units.items():
            factor = getattr(cell, key)
            if (
                factor is None
                or factor.unit != unit
                or (key in {"C", "P"} and factor.value > 1)
            ):
                missing.append(f"{cell.cell_id}:{key} with compatible units and value")
    result = {
        "status": "insufficient_data" if missing else "computed",
        "soil_loss_mean": None,
        "soil_loss_total": None,
        "missing_inputs": missing,
        "period": args.period,
        "method": "rusle-supplied-cell-factors-v1: A_i=R_i*K_i*LS_i*C_i*P_i; total=sum(A_i*area_i)",
        "source": "https://www.ars.usda.gov/southeast-area/oxford-ms/national-sedimentation-laboratory/watershed-physical-processes-research/docs/revised-universal-soil-loss-equation-106-description-of-rusle106c/",
        "input_summary": {
            "cell_count": len(args.cells),
            "units": units,
            "sources": sorted(
                {
                    getattr(cell, key).source
                    for cell in args.cells
                    for key in units
                    if getattr(cell, key) is not None
                }
            )[:20],
        },
        "input_sha256": hashlib.sha256(args.model_dump_json().encode()).hexdigest(),
        "limitations": "Conditional long-term sheet/rill water-erosion estimate for the supplied spatial support, not measured soil loss, wind/gully erosion or official RUSLE2. Factors must refer to co-located cells, compatible SI units and the same period; C must be erosivity-weighted. No factors are inferred from annual rainfall, NDVI, residue percentage or soil labels.",
    }
    if missing:
        return result
    total = sum(
        cell.R.value
        * cell.K.value
        * cell.LS.value
        * cell.C.value
        * cell.P.value
        * cell.area_ha
        for cell in args.cells
    )
    area = sum(cell.area_ha for cell in args.cells)
    result["soil_loss_total"] = {"value": round(total, 6), "unit": "t/yr"}
    result["soil_loss_mean"] = {"value": round(total / area, 6), "unit": "t/(ha yr)"}
    result["area_ha"] = area
    return result


class CropYear(Arguments):
    year: int = Field(ge=1900, le=2100)
    crop: str = Field(min_length=1, max_length=60)


class ReturnRule(Arguments):
    crops: list[str] = Field(min_length=1, max_length=20)
    minimum_years: int = Field(ge=1, le=50)
    source: str = Field(min_length=1, max_length=200)


class RotationArgs(Arguments):
    start_year: int = Field(ge=1900, le=2080)
    crops: list[str] = Field(min_length=1, max_length=20)
    history: list[CropYear] = Field(default_factory=list, max_length=50)
    return_rules: list[ReturnRule] = Field(default_factory=list, max_length=30)
    other_constraints: dict[
        Literal["climate", "soil", "irrigation", "calendar"], Constraint
    ] = Field(default_factory=dict)


def validate_rotation(args: RotationArgs) -> dict:
    missing = [
        f"constraint:{key}"
        for key in ("climate", "soil", "irrigation", "calendar")
        if key not in args.other_constraints
        or args.other_constraints[key].passed is None
    ]
    if any(row.year >= args.start_year for row in args.history) or len(
        {row.year for row in args.history}
    ) != len(args.history):
        missing.append("unambiguous prior harvest years before the planned rotation")
    covered = {crop for rule in args.return_rules for crop in rule.crops}
    missing += [
        f"documented return rule:{crop}" for crop in sorted(set(args.crops) - covered)
    ]
    violations = []
    for rule in args.return_rules:
        first = next(
            (
                args.start_year + i
                for i, crop in enumerate(args.crops)
                if crop in rule.crops
            ),
            None,
        )
        if first is not None:
            needed_years = set(range(first - rule.minimum_years + 1, args.start_year))
            missing_years = sorted(needed_years - {row.year for row in args.history})
            if missing_years:
                missing.append(
                    f"prior crop history for documented return rule: {missing_years}"
                )
        # Two copies check the cyclic last-year -> first-year boundary explicitly.
        occurrences = sorted(
            (row.year, row.crop) for row in args.history if row.crop in rule.crops
        )
        occurrences += [
            (args.start_year + i, crop)
            for i, crop in enumerate(args.crops * 2)
            if crop in rule.crops
        ]
        for (previous, prior_crop), (year, crop) in pairwise(occurrences):
            if year >= args.start_year and year - previous < rule.minimum_years:
                violations.append(
                    {
                        "previous_year": previous,
                        "year": year,
                        "previous_crop": prior_crop,
                        "crop": crop,
                        "gap_years": year - previous,
                        "required_years": rule.minimum_years,
                        "source": rule.source,
                    }
                )
    failed = [
        key for key, value in args.other_constraints.items() if value.passed is False
    ]
    return {
        "status": "blocked"
        if violations or failed
        else "insufficient_data"
        if missing
        else "passed",
        "feasible": False if violations or failed else None if missing else True,
        "violations": violations,
        "failed_constraints": failed,
        "missing_inputs": missing,
        "period": f"{args.start_year}-{args.start_year + len(args.crops) - 1}, cyclic",
        "method": "documented-return-interval-and-cyclic-boundary-v1",
        "rules": [rule.model_dump() for rule in args.return_rules],
        "limitations": "Checks supplied documented rules and prior years; no universal sunflower interval is assumed. Climate, soil, irrigation and sow/harvest feasibility need separate sourced checks. Passing these supplied rules is not regional agronomic validation.",
    }
