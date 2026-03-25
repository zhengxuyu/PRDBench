# -*- coding: utf-8 -*-
"""Fare rules and calculator — billing core logic."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class FareRule:
    """Distance-based fare rule segment.

    Attributes:
        min_km: Lower bound of this tier (inclusive).
        max_km: Upper bound of this tier (exclusive). None = no upper bound.
        base_fare: Fixed fare charged at the start of this tier (CNY).
        step_km: Kilometres per additional yuan after base_fare. 0 = no steps.
    """
    min_km: float
    max_km: Optional[float]
    base_fare: float
    step_km: float = 0.0

    def fare_for_distance(self, distance_km: float) -> float:
        """Compute the fare contribution for *distance_km* under this rule.

        Args:
            distance_km: Total trip distance in km.

        Returns:
            Fare in CNY.
        """
        if distance_km <= self.min_km:
            return self.base_fare
        excess = distance_km - self.min_km
        if self.step_km > 0:
            import math
            return self.base_fare + math.floor(excess / self.step_km)
        return self.base_fare


# Beijing Metro standard fare schedule (2024)
BEIJING_FARE_RULES: list[FareRule] = [
    FareRule(min_km=0,   max_km=6,    base_fare=3.0, step_km=0),
    FareRule(min_km=6,   max_km=12,   base_fare=4.0, step_km=0),
    FareRule(min_km=12,  max_km=32,   base_fare=5.0, step_km=10),
    FareRule(min_km=32,  max_km=None, base_fare=7.0, step_km=20),
]

AIRPORT_EXPRESS_FARE = 35.0  # CNY flat rate


class FareCalculator:
    """Computes the fare for a given trip distance.

    Args:
        rules: Ordered list of FareRule objects (sorted by min_km ascending).
               Defaults to Beijing Metro standard schedule.
    """

    def __init__(self, rules: Optional[list[FareRule]] = None) -> None:
        self.rules = rules if rules is not None else BEIJING_FARE_RULES

    def calculate(
        self,
        distance_km: float,
        is_airport_express: bool = False,
    ) -> float:
        """Return the fare in CNY for a trip of *distance_km* kilometres.

        Args:
            distance_km: Total shortest-path distance.
            is_airport_express: If True, return the flat airport express rate.

        Returns:
            Fare amount in CNY.
        """
        if is_airport_express:
            return AIRPORT_EXPRESS_FARE

        if distance_km <= 0:
            return 0.0

        # Find the applicable tier
        applicable: Optional[FareRule] = None
        for rule in self.rules:
            if rule.max_km is None or distance_km <= rule.max_km:
                applicable = rule
                break
        if applicable is None:
            applicable = self.rules[-1]

        return applicable.fare_for_distance(distance_km)
