"""Pydantic request/response models for the Confused? API."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CriterionIn(BaseModel):
    id: Optional[str] = None
    name: str
    weight: float = 0
    type: Literal["benefit", "cost"] = "benefit"


class OptionIn(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    scores: Dict[str, float] = Field(default_factory=dict)


class ConstraintIn(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    target: str
    operator: str = "<="
    value: float = 0
    hard: bool = True
    enabled: bool = True


class DecisionIn(BaseModel):
    id: Optional[str] = None
    title: str
    category: str = "custom"
    criteria: List[CriterionIn] = Field(default_factory=list)
    options: List[OptionIn] = Field(default_factory=list)
    constraints: List[ConstraintIn] = Field(default_factory=list)


class WhatIfIn(BaseModel):
    baseline: DecisionIn
    weights: Dict[str, float] = Field(default_factory=dict)
    disable_constraints: List[str] = Field(default_factory=list)
    disable_options: List[str] = Field(default_factory=list)


class CheckpointIn(BaseModel):
    label: str
    state: DecisionIn


class PlayIn(BaseModel):
    ops: List[Dict[str, Any]] = Field(default_factory=list)
    mode: str = "max"
    values: Optional[List[float]] = None
    labels: Optional[List[str]] = None
    nodes: Optional[List[str]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    capacity: int = 8


class ImportIn(BaseModel):
    mode: Literal["urls", "samples"] = "urls"
    urls: List[str] = Field(default_factory=list)
    criteria: List[str] = Field(default_factory=list)


class MatchIn(BaseModel):
    criteria: List[str] = Field(default_factory=list)
    phrases: List[str] = Field(default_factory=list)


class ProfileIn(BaseModel):
    category: str
    weights: Dict[str, float] = Field(default_factory=dict)
    criteria: List[Dict[str, Any]] = Field(default_factory=list)


class DuelAnswer(BaseModel):
    a: str
    b: str
    winner: str


class DuelsIn(BaseModel):
    decision: DecisionIn
    n: int = 6


class LearnIn(BaseModel):
    decision: DecisionIn
    answers: List[DuelAnswer] = Field(default_factory=list)
