# -*- coding: utf-8 -*-
"""Station and Line data structures — core domain models."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Station:
    """Represents a single metro station.

    Attributes:
        station_id: Unique station identifier (e.g. "BJW01").
        name: Human-readable station name (e.g. "西直门").
        line_ids: Set of line IDs this station belongs to (transfer stations
                  belong to multiple lines).
        coords: (latitude, longitude) in decimal degrees. None if unknown.
    """
    station_id: str
    name: str
    line_ids: set[str] = field(default_factory=set)
    coords: Optional[tuple[float, float]] = None

    def is_transfer(self) -> bool:
        """Return True if this station serves more than one line."""
        return len(self.line_ids) > 1


@dataclass
class Line:
    """Represents a single metro line.

    Attributes:
        line_id: Unique line identifier (e.g. "L1" for Line 1).
        name: Human-readable line name (e.g. "Line 1").
        stations: Ordered list of station IDs along this line.
        is_airport_express: True if flat-rate airport pricing applies.
        flat_fare: Flat fare in CNY for airport express lines. None otherwise.
    """
    line_id: str
    name: str
    stations: list[str] = field(default_factory=list)
    is_airport_express: bool = False
    flat_fare: Optional[float] = None
