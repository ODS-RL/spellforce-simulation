"""Matplotlib diagnostic plotting suite for comparative build analysis."""

import math
from typing import List, Tuple

from matplotlib.figure import Figure
import numpy as np

from ..core.constants import ATTRIBUTES
from ..core.models import CharacterBuild
from ..core.rules import RulesEngine
from .evaluator import BuildEvaluator
from .solver import HybridParetoSolver


class BuildVisualizer:
    """Generates comprehensive diagnostic charts for builds using pure OO figures."""

    @staticmethod
    def plot_comparative_suite(
        builds: List[CharacterBuild],
        primary_school_pair: Tuple[str, str] = (
            "Heavy Combat Arts",
            "White Magic",
        ),
    ) -> Figure:
        """Generates a 4-panel diagnostic figure comparing character builds."""
        # Explicit Figure instance prevents pyplot thread-locking on window close
        fig = Figure(figsize=(12, 8), facecolor="#1e1e1e")

        # Explicit margins prevent title, legend, and axis clipping
        fig.subplots_adjust(
            top=0.92,
            bottom=0.09,
            left=0.07,
            right=0.95,
            hspace=0.38,
            wspace=0.28,
        )

        school_a, school_b = primary_school_pair

        # 1. Subplot: Attribute Radar Comparison
        ax1 = fig.add_subplot(221, polar=True)
        ax1.set_facecolor("#252526")
        BuildVisualizer._render_radar(ax1, builds)

        # 2. Subplot: Hybrid Pareto Frontier Curve
        ax2 = fig.add_subplot(222)
        ax2.set_facecolor("#252526")
        BuildVisualizer._render_pareto(ax2, builds, school_a, school_b)

        # 3. Subplot: Point Allocation & Stranded Points
        ax3 = fig.add_subplot(223)
        ax3.set_facecolor("#252526")
        BuildVisualizer._render_point_breakdown(ax3, builds)

        # 4. Subplot: Level 1-50 Progression & Expansion Trajectory
        ax4 = fig.add_subplot(224)
        ax4.set_facecolor("#252526")
        BuildVisualizer._render_progression_trajectory(
            ax4, builds[0] if builds else None
        )

        fig.tight_layout()
        return fig

    @staticmethod
    def _render_radar(ax, builds: List[CharacterBuild]):
        categories = list(ATTRIBUTES)
        n = len(categories)
        angles = [i / float(n) * 2 * math.pi for i in range(n)]
        angles += angles[:1]

        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=8, color="#cccccc")
        ax.tick_params(colors="#888888")

        cap_val = RulesEngine.get_stat_cap_for_level(50)
        ax.plot(
            angles,
            [cap_val] * (n + 1),
            color="#555555",
            linestyle="--",
            linewidth=1,
            label=f"Lv50 Cap ({cap_val})",
        )

        colors = ["#4fc1ff", "#4ec9b0", "#ce9178", "#dcdcaa"]
        for idx, build in enumerate(builds[:4]):
            values = [
                build.get_effective_attribute(attr) for attr in categories
            ]
            values += values[:1]
            color = colors[idx % len(colors)]
            ax.plot(angles, values, color=color, linewidth=2, label=build.name)
            ax.fill(angles, values, color=color, alpha=0.15)

        ax.set_title(
            "Attribute Distribution vs Level 50 Cap",
            color="#ffffff",
            pad=10,
            fontsize=10,
        )
        ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=7)

    @staticmethod
    def _render_pareto(
        ax, builds: List[CharacterBuild], school_a: str, school_b: str
    ):
        frontier = HybridParetoSolver.solve_frontier(school_a, school_b, 50)
        feasible_x = [sol.school_a_rank for sol in frontier if sol.is_feasible]
        feasible_y = [sol.school_b_rank for sol in frontier if sol.is_feasible]
        infeasible_x = [
            sol.school_a_rank for sol in frontier if not sol.is_feasible
        ]
        infeasible_y = [
            sol.school_b_rank for sol in frontier if not sol.is_feasible
        ]

        ax.scatter(
            infeasible_x,
            infeasible_y,
            color="#5a1d1d",
            alpha=0.3,
            s=20,
            label="Infeasible Space",
        )
        ax.scatter(
            feasible_x,
            feasible_y,
            color="#1e4e2e",
            alpha=0.6,
            s=30,
            label="Feasible Space",
        )

        # Add discrete OoD / BoW Rank 12 cap reference markers
        ax.axvline(
            x=12,
            color="#dcdcaa",
            linestyle=":",
            linewidth=1,
            alpha=0.6,
            label="OoD Cap (Rank 12)",
        )
        ax.axhline(
            y=12,
            color="#dcdcaa",
            linestyle=":",
            linewidth=1,
            alpha=0.6,
        )

        colors = ["#4fc1ff", "#4ec9b0", "#ce9178", "#dcdcaa"]
        for idx, build in enumerate(builds[:4]):
            ra = build.schools.get(school_a, 0)
            rb = build.schools.get(school_b, 0)
            ax.scatter(
                ra,
                rb,
                color=colors[idx % len(colors)],
                s=100,
                edgecolors="white",
                linewidth=1.2,
                zorder=5,
                label=f"{build.name} ({ra}, {rb})",
            )

        ax.set_xlabel(f"{school_a} Rank", color="#cccccc", fontsize=8)
        ax.set_ylabel(f"{school_b} Rank", color="#cccccc", fontsize=8)
        ax.set_title(
            f"Hybrid Frontier: {school_a} vs {school_b}",
            color="#ffffff",
            fontsize=10,
        )
        ax.grid(True, linestyle=":", color="#444444")
        ax.legend(
            fontsize=7, loc="upper right", facecolor="#1e1e1e", framealpha=0.8
        )

        colors = ["#4fc1ff", "#4ec9b0", "#ce9178", "#dcdcaa"]
        for idx, build in enumerate(builds[:4]):
            ra = build.schools.get(school_a, 0)
            rb = build.schools.get(school_b, 0)
            ax.scatter(
                ra,
                rb,
                color=colors[idx % len(colors)],
                s=100,
                edgecolors="white",
                linewidth=1.2,
                zorder=5,
                label=f"{build.name} ({ra}, {rb})",
            )

        ax.set_xlabel(f"{school_a} Rank", color="#cccccc", fontsize=8)
        ax.set_ylabel(f"{school_b} Rank", color="#cccccc", fontsize=8)
        ax.set_title(
            f"Hybrid Frontier: {school_a} vs {school_b}",
            color="#ffffff",
            fontsize=10,
        )
        ax.grid(True, linestyle=":", color="#444444")
        ax.legend(fontsize=7, loc="lower left")

    @staticmethod
    def _render_point_breakdown(ax, builds: List[CharacterBuild]):
        names = [b.name for b in builds[:4]]
        if not names:
            return
        x = np.arange(len(names))
        width = 0.2

        productive = []
        stranded = []
        obsolete = []
        slack = []

        for b in builds[:4]:
            m = BuildEvaluator.evaluate(b)
            productive.append(m.productive_stat_points)
            slack.append(m.slack_stat_points)
            stranded.append(m.stranded_skill_points * 2)
            obsolete.append(m.obsolete_skill_points * 2)

        ax.bar(
            x - width * 1.5,
            productive,
            width,
            label="Productive Stats",
            color="#4ec9b0",
        )
        ax.bar(
            x - width * 0.5,
            slack,
            width,
            label="Surplus Stats",
            color="#4fc1ff",
        )
        ax.bar(
            x + width * 0.5,
            stranded,
            width,
            label="Stranded Pts",
            color="#dcdcaa",
        )
        ax.bar(
            x + width * 1.5,
            obsolete,
            width,
            label="Obsolete Pts",
            color="#f44747",
        )

        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=8, color="#cccccc")
        ax.set_title(
            "Point Efficiency & Loss Breakdown", color="#ffffff", fontsize=10
        )
        ax.grid(True, linestyle=":", color="#444444", axis="y")
        ax.legend(fontsize=7)

    @staticmethod
    def _render_progression_trajectory(ax, build: CharacterBuild):
        if not build:
            return
        levels = list(range(1, 51))
        stat_budgets = [
            RulesEngine.get_stat_points_budget(lvl) for lvl in levels
        ]
        skill_budgets = [
            RulesEngine.get_skill_points_budget(lvl) for lvl in levels
        ]

        ax.plot(
            levels,
            stat_budgets,
            color="#4fc1ff",
            linewidth=2,
            label="Stat Points Budget",
        )
        ax.plot(
            levels,
            skill_budgets,
            color="#4ec9b0",
            linewidth=2,
            label="Skill Points Budget",
        )

        ax.axvline(
            x=30,
            color="#dcdcaa",
            linestyle="--",
            linewidth=1.2,
            label="OoD/BoW Cap (Lv30)",
        )

        ax.set_xlabel("Character Level", color="#cccccc", fontsize=8)
        ax.set_ylabel("Accumulated Points", color="#cccccc", fontsize=8)
        ax.set_title(
            "Platinum Progression Trajectory (1-50)",
            color="#ffffff",
            fontsize=10,
        )
        ax.grid(True, linestyle=":", color="#444444")
        ax.legend(fontsize=7, loc="upper left")
