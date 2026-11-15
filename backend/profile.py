"""Validated, farmer-reported profile updates; persistence is separate from verification."""

import json
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

FactKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
FactValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    facts: dict[FactKey, FactValue] = Field(default_factory=dict, max_length=40)
    boundary: list[list[float]] | None = Field(default=None, min_length=4, max_length=5)

    @model_validator(mode="after")
    def valid_update(self):
        if not self.facts and self.boundary is None:
            raise ValueError("Provide profile facts or a field boundary to save.")
        if len(json.dumps(self.facts, ensure_ascii=False).encode()) > 8000:
            raise ValueError("Profile facts must fit within 8 KB.")
        if self.boundary is None:
            return self
        points = self.boundary
        if any(len(point) != 2 or not -180 <= point[0] <= 180 or not -85 <= point[1] <= 85 for point in points):
            raise ValueError("Use [longitude, latitude] pairs within the supported WGS84 map range.")
        if len(points) == 5 and points[-1] == points[0]:
            points = points[:-1]
        if len(points) != 4 or len({tuple(point) for point in points}) != 4:
            raise ValueError("Supply four distinct corners in boundary order.")
        if max(p[0] for p in points) - min(p[0] for p in points) >= 180:
            raise ValueError("Date-line-crossing fields are not supported.")

        def cross(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        def intersects(a, b, c, d):
            return cross(a, b, c) * cross(a, b, d) <= 0 and cross(c, d, a) * cross(c, d, b) <= 0

        if (any(cross(points[i], points[(i + 1) % 4], points[(i + 2) % 4]) == 0 for i in range(4))
                or intersects(*points) or intersects(points[1], points[2], points[3], points[0])):
            raise ValueError("Boundary edges must not cross or form a zero-area field.")
        self.boundary = points
        return self
