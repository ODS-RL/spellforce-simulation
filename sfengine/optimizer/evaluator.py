"""Discrete tier quantization and build efficiency scoring."""

from dataclasses import dataclass
from typing import Dict, List

from ..core.constants import (
    DISCRETE_SPELL_TIERS,
    MAX_SKILL_RANK,
)
from ..core.models import CharacterBuild
from ..core.rules import RulesEngine


@dataclass
class EfficiencyMetrics:
    """Detailed diagnostic breakdown of build efficiency."""

    overall_score: float
    stat_efficiency: float
    skill_efficiency: float
    stranded_skill_points: int
    obsolete_skill_points: int
    slack_stat_points: int
    productive_stat_points: int
    diagnostics: List[str]


class BuildEvaluator:
    """Evaluates mathematical effectiveness using discrete spell tiers and synergy."""

    @staticmethod
    def get_active_functional_rank(rank: int) -> int:
        """Finds highest reached discrete tier threshold."""
        if rank <= 0:
            return 0
        valid_tiers = [t for t in DISCRETE_SPELL_TIERS if t <= rank]
        return max(valid_tiers) if valid_tiers else 0

    @classmethod
    def evaluate(cls, build: CharacterBuild) -> EfficiencyMetrics:
        """Computes multi-dimensional efficiency score for a build."""
        report = RulesEngine.validate_build(build)
        diagnostics = []

        # 1. Skill Points Analysis
        total_spent_skill = report.skill_points_spent
        max_rank = RulesEngine.get_max_skill_rank_for_level(build.level)
        # Viability threshold: at Level 50, abilities below Rank 12 are obsolete
        viability_threshold = (
            12 if build.level >= 45 else max(2, int(max_rank * 0.5))
        )

        stranded_skill_pts = 0
        obsolete_skill_pts = 0
        active_skill_count = 0

        all_skills: Dict[str, int] = {}
        all_skills.update(build.schools)
        all_skills.update(build.specializations)

        for skill, rank in all_skills.items():
            if rank <= 0:
                continue
            active_skill_count += 1
            func_rank = cls.get_active_functional_rank(rank)
            stranded = rank - func_rank
            if stranded > 0:
                stranded_skill_pts += stranded
                diagnostics.append(
                    f"{skill}: Rank {rank} has {stranded} stranded point(s) "
                    f"beyond Tier {func_rank}"
                )

            if rank < viability_threshold:
                obsolete_skill_pts += rank
                diagnostics.append(
                    f"{skill}: Rank {rank} is below viability threshold "
                    f"{viability_threshold} for Level {build.level}"
                )

        # 2. Stat Points Analysis
        min_required_invested = RulesEngine.calculate_minimum_required_stats(
            build
        )
        productive_stats = sum(min_required_invested.values())
        actual_invested_stats = report.stat_points_spent
        slack_stat_pts = max(0, actual_invested_stats - productive_stats)

        # Stat Efficiency: ratio of productive stat points to total stat budget
        stat_eff = (
            (productive_stats / report.stat_points_budget)
            if report.stat_points_budget > 0
            else 0.0
        )
        stat_eff = min(1.0, stat_eff)

        # Skill Efficiency: functional tiers reached vs total skill points budget
        functional_skill_pts = max(
            0, total_spent_skill - stranded_skill_pts - obsolete_skill_pts
        )
        skill_eff = (
            (functional_skill_pts / report.skill_points_budget)
            if report.skill_points_budget > 0
            else 0.0
        )
        skill_eff = min(1.0, skill_eff)

        # Penalties for invalid builds (over-budget or unmet prerequisites)
        penalty = 0.0
        if not report.is_valid:
            penalty += (report.stat_deficit * 0.05) + (
                report.skill_deficit * 0.1
            )
            penalty += len(report.issues) * 0.15

        # Aggregate Score: Range roughly 0.0 to 100.0
        raw_score = (stat_eff * 45.0) + (skill_eff * 55.0) - (penalty * 20.0)
        overall_score = max(0.0, min(100.0, raw_score))

        return EfficiencyMetrics(
            overall_score=round(overall_score, 2),
            stat_efficiency=round(stat_eff * 100.0, 1),
            skill_efficiency=round(skill_eff * 100.0, 1),
            stranded_skill_points=stranded_skill_pts,
            obsolete_skill_points=obsolete_skill_pts,
            slack_stat_points=slack_stat_pts,
            productive_stat_points=productive_stats,
            diagnostics=diagnostics,
        )
