"""Data schemas and domain models for character representations."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .constants import (
    ATTRIBUTES,
    BASE_ATTRIBUTE_VALUE,
    SCHOOL_TREE,
)


@dataclass
class ValidationIssue:
    """Represents a specific rule or budget violation in a character build."""

    category: str  # 'STAT_CAP', 'STAT_BUDGET', 'SKILL_BUDGET', 'PREREQUISITE', 'DEPENDENCY'
    target: str  # Name of the stat or skill involved
    message: str  # Human-readable diagnostic description


@dataclass
class ValidationReport:
    """Contains full diagnostic state of a character build."""

    is_valid: bool
    stat_points_spent: int
    stat_points_budget: int
    skill_points_spent: int
    skill_points_budget: int
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def stat_deficit(self) -> int:
        """Returns stat points over budget (0 if within budget)."""
        return max(0, self.stat_points_spent - self.stat_points_budget)

    @property
    def skill_deficit(self) -> int:
        """Returns skill points over budget (0 if within budget)."""
        return max(0, self.skill_points_spent - self.skill_points_budget)


@dataclass
class CharacterBuild:
    """Represents a character's complete allocation state."""

    name: str = "New Avatar"
    level: int = 1
    # Invested points on top of base 25 for each attribute
    invested_attributes: Dict[str, int] = field(
        default_factory=lambda: {attr: 0 for attr in ATTRIBUTES}
    )
    # Ranks for major schools (0 to 20)
    schools: Dict[str, int] = field(
        default_factory=lambda: {school: 0 for school in SCHOOL_TREE}
    )
    # Ranks for sub-specializations (0 to 20)
    specializations: Dict[str, int] = field(
        default_factory=lambda: {
            spec: 0 for specs in SCHOOL_TREE.values() for spec in specs
        }
    )

    def get_effective_attribute(self, attr_name: str) -> int:
        """Calculates total base stat value (Base 25 + Invested Points)."""
        return BASE_ATTRIBUTE_VALUE + self.invested_attributes.get(attr_name, 0)

    def to_dict(self) -> Dict:
        """Serializes build state to standard dictionary for JSON export."""
        return {
            "name": self.name,
            "level": self.level,
            "invested_attributes": self.invested_attributes.copy(),
            "schools": self.schools.copy(),
            "specializations": self.specializations.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CharacterBuild":
        """Reconstructs CharacterBuild from serialized dictionary."""
        build = cls(
            name=data.get("name", "Imported Avatar"),
            level=data.get("level", 1),
        )
        for attr, val in data.get("invested_attributes", {}).items():
            if attr in build.invested_attributes:
                build.invested_attributes[attr] = int(val)
        for school, rank in data.get("schools", {}).items():
            if school in build.schools:
                build.schools[school] = int(rank)
        for spec, rank in data.get("specializations", {}).items():
            if spec in build.specializations:
                build.specializations[spec] = int(rank)
        return build
