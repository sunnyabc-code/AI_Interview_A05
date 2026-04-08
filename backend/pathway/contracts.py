from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

WeaknessType = Literal["technical", "expression", "logic", "communication", "adaptability"]
TaskType = Literal["resource", "question", "practice", "review"]


@dataclass
class WeaknessItem:
    key: str
    weakness_type: WeaknessType
    severity: float
    trend: float
    evidence: List[str] = field(default_factory=list)


@dataclass
class ProfileSnapshot:
    user_id: int
    technical_score: Optional[float]
    expression_score: Optional[float]
    dimensions: Dict[str, Optional[float]]
    weaknesses: List[WeaknessItem]
    strengths: List[str]
    confidence_level: float


@dataclass
class CandidateResource:
    source_type: Literal["learning_resource", "question", "template", "external_link"]
    source_id: Optional[int]
    title: str
    reason: str
    estimated_minutes: int
    tags: List[str] = field(default_factory=list)
    base_score: float = 0.0


@dataclass
class PathTask:
    day_index: int
    task_type: TaskType
    title: str
    reason: str
    estimated_minutes: int
    source_type: str
    source_id: Optional[int]
    priority: int


@dataclass
class PathPlan:
    user_id: int
    cycle_days: int
    goal_summary: str
    expected_gain: Dict[str, float]
    tasks: List[PathTask]
    generation_meta: Dict[str, object] = field(default_factory=dict)
