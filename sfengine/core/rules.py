"""Game mechanics rules engine and non-destructive validator."""

from typing import Dict, Tuple

from .constants import (
    BASE_ATTRIBUTE_VALUE,
    LEVEL_1_SKILL_POINTS,
    LEVEL_1_STAT_BONUS,
    LEVEL_TO_MAX_SKILL,
    MAX_CHARACTER_LEVEL,
    SCHOOL_GOVERNING_STATS,
    SCHOOL_TREE,
    SKILL_POINTS_PER_LEVEL,
    SKILL_RANK_MIN_CHAR_LEVEL,
    SKILL_REQUIREMENTS_MATRIX,
    STAT_POINTS_PER_LEVEL,
)
from .models import (
    CharacterBuild,
    ValidationIssue,
    ValidationReport,
)


class RulesEngine:
    """Authoritative validation and game mechanics calculation engine."""

    @staticmethod
    def get_stat_cap_for_level(char_level: int) -> int:
        """Calculates maximum base stat cap at given character level.

        Formula: 40 + 2 * (char_level - 1)
        """
        clamped_level = max(1, min(MAX_CHARACTER_LEVEL, char_level))
        return 40 + 2 * (clamped_level - 1)

    @staticmethod
    def get_stat_points_budget(char_level: int) -> int:
        """Calculates total spendable stat points accumulated up to character level.

        Formula: 30 + 5 * (char_level - 1)
        """
        clamped_level = max(1, min(MAX_CHARACTER_LEVEL, char_level))
        return LEVEL_1_STAT_BONUS + STAT_POINTS_PER_LEVEL * (clamped_level - 1)

    @staticmethod
    def get_skill_points_budget(char_level: int) -> int:
        """Calculates total spendable skill points accumulated up to character level.

        Formula: 2 * char_level
        """
        clamped_level = max(1, min(MAX_CHARACTER_LEVEL, char_level))
        return LEVEL_1_SKILL_POINTS + SKILL_POINTS_PER_LEVEL * (
            clamped_level - 1
        )

    @staticmethod
    def get_max_skill_rank_for_level(char_level: int) -> int:
        """Retrieves absolute maximum skill rank achievable at character level."""
        clamped_level = max(1, min(MAX_CHARACTER_LEVEL, char_level))
        return LEVEL_TO_MAX_SKILL.get(clamped_level, 1)

    @classmethod
    def get_skill_prerequisites(
        cls, school_name: str, rank: int
    ) -> Tuple[int, str, int, str, int]:
        """Returns prerequisite requirements for a major school rank.

        Returns:
            Tuple[min_char_level, stat1_name, stat1_req, stat2_name, stat2_req]
        """
        if rank <= 0:
            return 0, "", 0, "", 0
        min_char_level = SKILL_RANK_MIN_CHAR_LEVEL.get(rank, 1)
        # Edge case: BM and MM Rank 12 require Level 29 because stat cap at 28 is 94
        if rank == 12 and school_name in ("Black Magic", "Mind Magic"):
            min_char_level = 29

        stat1_name, stat2_name = SCHOOL_GOVERNING_STATS[school_name]
        reqs = SKILL_REQUIREMENTS_MATRIX[school_name].get(rank, (25, 25))
        return min_char_level, stat1_name, reqs[0], stat2_name, reqs[1]

    @classmethod
    def get_parent_school_for_spec(cls, spec_name: str) -> str:
        """Finds parent major school for a given sub-specialization."""
        for school, specs in SCHOOL_TREE.items():
            if spec_name in specs:
                return school
        raise ValueError(f"Unknown specialization: {spec_name}")

    @classmethod
    def validate_build(cls, build: CharacterBuild) -> ValidationReport:
        """Performs non-destructive validation of a character build state."""
        issues = []
        stat_budget = cls.get_stat_points_budget(build.level)
        skill_budget = cls.get_skill_points_budget(build.level)
        max_stat_cap = cls.get_stat_cap_for_level(build.level)
        max_skill_cap = cls.get_max_skill_rank_for_level(build.level)

        # 1. Stat Point Budget Validation
        stat_points_spent = sum(build.invested_attributes.values())
        if stat_points_spent > stat_budget:
            issues.append(
                ValidationIssue(
                    category="STAT_BUDGET",
                    target="Stats Pool",
                    message=(
                        f"Stat points over budget: {stat_points_spent}/{stat_budget} "
                        f"(Deficit: {stat_points_spent - stat_budget})"
                    ),
                )
            )

        # 2. Stat Cap Validations
        for attr, invested in build.invested_attributes.items():
            total_stat = BASE_ATTRIBUTE_VALUE + invested
            if total_stat > max_stat_cap:
                issues.append(
                    ValidationIssue(
                        category="STAT_CAP",
                        target=attr,
                        message=(
                            f"{attr} value {total_stat} exceeds Level {build.level} "
                            f"cap of {max_stat_cap}"
                        ),
                    )
                )

        # 3. Skill Point Budget Validation
        skill_points_spent = sum(build.schools.values()) + sum(
            build.specializations.values()
        )
        if skill_points_spent > skill_budget:
            issues.append(
                ValidationIssue(
                    category="SKILL_BUDGET",
                    target="Skills Pool",
                    message=(
                        f"Skill points over budget: {skill_points_spent}/{skill_budget} "
                        f"(Deficit: {skill_points_spent - skill_budget})"
                    ),
                )
            )

        # 4. Major School Validations
        for school, rank in build.schools.items():
            if rank <= 0:
                continue
            if rank > max_skill_cap:
                issues.append(
                    ValidationIssue(
                        category="SKILL_CAP",
                        target=school,
                        message=(
                            f"{school} Rank {rank} exceeds Level {build.level} "
                            f"skill cap of {max_skill_cap}"
                        ),
                    )
                )

            req_lvl, s1_name, s1_req, s2_name, s2_req = (
                cls.get_skill_prerequisites(school, rank)
            )
            if build.level < req_lvl:
                issues.append(
                    ValidationIssue(
                        category="PREREQUISITE",
                        target=school,
                        message=(
                            f"{school} Rank {rank} requires Character Level {req_lvl} "
                            f"(Current: {build.level})"
                        ),
                    )
                )
            actual_s1 = build.get_effective_attribute(s1_name)
            if actual_s1 < s1_req:
                issues.append(
                    ValidationIssue(
                        category="PREREQUISITE",
                        target=school,
                        message=(
                            f"{school} Rank {rank} requires {s1_name} {s1_req} "
                            f"(Current: {actual_s1})"
                        ),
                    )
                )
            actual_s2 = build.get_effective_attribute(s2_name)
            if actual_s2 < s2_req:
                issues.append(
                    ValidationIssue(
                        category="PREREQUISITE",
                        target=school,
                        message=(
                            f"{school} Rank {rank} requires {s2_name} {s2_req} "
                            f"(Current: {actual_s2})"
                        ),
                    )
                )

        # 5. Specialization Validations
        for spec, rank in build.specializations.items():
            if rank <= 0:
                continue
            parent = cls.get_parent_school_for_spec(spec)
            parent_rank = build.schools.get(parent, 0)
            if rank > parent_rank:
                issues.append(
                    ValidationIssue(
                        category="DEPENDENCY",
                        target=spec,
                        message=(
                            f"{spec} Rank {rank} cannot exceed parent {parent} "
                            f"Rank {parent_rank}"
                        ),
                    )
                )
            if rank > max_skill_cap:
                issues.append(
                    ValidationIssue(
                        category="SKILL_CAP",
                        target=spec,
                        message=(
                            f"{spec} Rank {rank} exceeds Level {build.level} "
                            f"cap of {max_skill_cap}"
                        ),
                    )
                )

        return ValidationReport(
            is_valid=len(issues) == 0,
            stat_points_spent=stat_points_spent,
            stat_points_budget=stat_budget,
            skill_points_spent=skill_points_spent,
            skill_points_budget=skill_budget,
            issues=issues,
        )

    @classmethod
    def calculate_minimum_required_stats(
        cls, build: CharacterBuild
    ) -> Dict[str, int]:
        """Calculates minimal invested stat values needed to satisfy current skills."""
        min_base_needed = {
            attr: BASE_ATTRIBUTE_VALUE for attr in build.invested_attributes
        }
        for school, rank in build.schools.items():
            if rank <= 0:
                continue
            _, s1, req1, s2, req2 = cls.get_skill_prerequisites(school, rank)
            if req1 > min_base_needed[s1]:
                min_base_needed[s1] = req1
            if req2 > min_base_needed[s2]:
                min_base_needed[s2] = req2

        # Convert base requirements to invested points (Value - 25)
        return {
            attr: max(0, min_base_needed[attr] - BASE_ATTRIBUTE_VALUE)
            for attr in min_base_needed
        }
