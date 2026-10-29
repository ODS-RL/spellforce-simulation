"""Pareto frontier solver for hybrid school combinations."""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..core.constants import (
    BASE_ATTRIBUTE_VALUE,
    MAX_CHARACTER_LEVEL,
    SCHOOL_GOVERNING_STATS,
    SKILL_REQUIREMENTS_MATRIX,
)
from ..core.rules import RulesEngine


@dataclass
class ParetoSolution:
    """Represents a feasible Pareto-optimal rank allocation for two schools."""

    school_a_rank: int
    school_b_rank: int
    required_stat_points: int
    is_feasible: bool
    governing_stats_summary: Dict[str, int]


class HybridParetoSolver:
    """Computes the exact feasibility frontier between any two major schools."""

    @classmethod
    def solve_frontier(
        cls,
        school_a: str,
        school_b: str,
        target_char_level: int = MAX_CHARACTER_LEVEL,
    ) -> List[ParetoSolution]:
        """Calculates all possible rank pairings (0-20) and identifies the Pareto boundary."""
        stat_budget = RulesEngine.get_stat_points_budget(target_char_level)
        max_stat_cap = RulesEngine.get_stat_cap_for_level(target_char_level)
        max_skill_rank = RulesEngine.get_max_skill_rank_for_level(
            target_char_level
        )

        s1_a, s2_a = SCHOOL_GOVERNING_STATS[school_a]
        s1_b, s2_b = SCHOOL_GOVERNING_STATS[school_b]

        solutions: List[ParetoSolution] = []

        for rank_a in range(0, max_skill_rank + 1):
            req_a = (
                SKILL_REQUIREMENTS_MATRIX[school_a].get(rank_a, (25, 25))
                if rank_a > 0
                else (25, 25)
            )
            for rank_b in range(0, max_skill_rank + 1):
                req_b = (
                    SKILL_REQUIREMENTS_MATRIX[school_b].get(rank_b, (25, 25))
                    if rank_b > 0
                    else (25, 25)
                )

                # Union required attributes taking into account shared governing stats
                combined_stats = {
                    s1_a: req_a[0],
                    s2_a: req_a[1],
                }
                combined_stats[s1_b] = max(
                    combined_stats.get(s1_b, 25), req_b[0]
                )
                combined_stats[s2_b] = max(
                    combined_stats.get(s2_b, 25), req_b[1]
                )

                # Check stat cap feasibility
                cap_violation = any(
                    val > max_stat_cap for val in combined_stats.values()
                )

                # Total invested points needed
                total_invested_needed = sum(
                    val - BASE_ATTRIBUTE_VALUE
                    for val in combined_stats.values()
                )

                is_feasible = (not cap_violation) and (
                    total_invested_needed <= stat_budget
                )

                solutions.append(
                    ParetoSolution(
                        school_a_rank=rank_a,
                        school_b_rank=rank_b,
                        required_stat_points=total_invested_needed,
                        is_feasible=is_feasible,
                        governing_stats_summary=combined_stats,
                    )
                )

        return solutions

    @classmethod
    def get_max_balanced_ranks(
        cls, school_a: str, school_b: str, char_level: int = MAX_CHARACTER_LEVEL
    ) -> Tuple[int, int]:
        """Finds highest symmetric rank pairing attainable simultaneously."""
        frontier = cls.solve_frontier(school_a, school_b, char_level)
        feasible_symmetric = [
            sol.school_a_rank
            for sol in frontier
            if sol.is_feasible and sol.school_a_rank == sol.school_b_rank
        ]
        max_rank = max(feasible_symmetric) if feasible_symmetric else 0
        return max_rank, max_rank
