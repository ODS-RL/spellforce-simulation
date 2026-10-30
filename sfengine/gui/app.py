"""Tkinter GUI character simulator with integrated context inspector."""

import json
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from typing import Dict, Optional

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..core.constants import (
    ATTRIBUTES,
    BASE_ATTRIBUTE_VALUE,
    MAX_CHARACTER_LEVEL,
    SCHOOL_GOVERNING_STATS,
    SCHOOL_TREE,
)
from ..core.models import CharacterBuild
from ..core.rules import RulesEngine
from .theme import (
    FONT_BOLD,
    FONT_HEADER,
    FONT_MONO,
    FONT_REGULAR,
    FONT_TITLE,
    THEME,
)
from ..optimizer.evaluator import BuildEvaluator
from ..optimizer.visualizer import BuildVisualizer

# Standard 3-letter stat display mappings
STAT_ABBREVIATIONS: Dict[str, str] = {
    "Strength": "STR",
    "Stamina": "STA",
    "Dexterity": "DEX",
    "Agility": "AGI",
    "Intelligence": "INT",
    "Wisdom": "WIS",
    "Charisma": "CHA",
}


class SpellForceSimulatorApp(tk.Tk):
    """Main desktop application window."""

    def __init__(self):
        super().__init__()
        self.title("SpellForce Character Simulator & Build Optimizer")
        self.geometry("1100x680")
        self.minsize(1000, 620)
        self.configure(bg=THEME["bg_dark"])

        # Intercept window closure to ensure graceful process termination
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.current_build = CharacterBuild(name="Champion of Eo", level=30)
        self.comparison_builds = [self.current_build]

        self.stat_widgets: Dict[str, Dict] = {}
        self.school_widgets: Dict[str, Dict] = {}
        self.spec_containers: Dict[str, tk.Frame] = {}
        self.spec_widgets: Dict[str, Dict] = {}
        self.canvas_widget: Optional[FigureCanvasTkAgg] = None

        self._init_styles()
        self._build_layout()
        self._update_all_views()

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=THEME["bg_dark"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=THEME["bg_medium"],
            foreground=THEME["text_secondary"],
            padding=[10, 4],
            font=FONT_BOLD,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", THEME["bg_card"])],
            foreground=[("selected", THEME["accent"])],
        )
        style.configure("TFrame", background=THEME["bg_dark"])

    def _build_layout(self):
        # Master Notebook Container
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Tab 1: Simulator View
        self.sim_tab = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.sim_tab, text="Character Simulator")
        self._build_simulator_tab()

        # Tab 2: Build Optimizer View
        self.opt_tab = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.opt_tab, text="Optimizer & Diagnostics")
        self._build_optimizer_tab()

    def _build_simulator_tab(self):
        # 2-Column Split: Left = Schools Tree (55%), Right = Stats & Inspector (45%)
        self.sim_tab.columnconfigure(0, weight=11)
        self.sim_tab.columnconfigure(1, weight=9)
        self.sim_tab.rowconfigure(0, weight=1)

        # Left Column: Combat Arts & Magic Schools
        self.skills_card = tk.LabelFrame(
            self.sim_tab,
            text=" Combat Arts & Magic Schools ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=6,
            pady=6,
        )
        self.skills_card.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._build_skills_tree()

        # Right Column Container
        self.right_container = tk.Frame(self.sim_tab, bg=THEME["bg_dark"])
        self.right_container.grid(
            row=0, column=1, sticky="nsew", padx=4, pady=4
        )
        self.right_container.columnconfigure(0, weight=1)
        self.right_container.rowconfigure(1, weight=1)

        # Right Top: Level Stepper & Resource Pools
        self._build_level_and_pools_card()

        # Right Middle: Attributes (Stats) Grid
        self._build_attributes_grid()

        # Right Bottom: Context Inspector & Actions
        self._build_inspector_card()

    def _build_level_and_pools_card(self):
        ctrl_card = tk.LabelFrame(
            self.right_container,
            text=" Avatar Progression & Resource Pools ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=8,
            pady=4,
        )
        ctrl_card.pack(fill=tk.X, pady=(0, 4))

        # Level Stepper Row
        lvl_row = tk.Frame(ctrl_card, bg=THEME["bg_card"])
        lvl_row.pack(fill=tk.X, pady=2)

        tk.Label(
            lvl_row,
            text="Level:",
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            font=FONT_BOLD,
        ).pack(side=tk.LEFT)

        self.level_var = tk.IntVar(value=self.current_build.level)
        tk.Button(
            lvl_row,
            text="◀",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
            width=2,
            pady=0,
            command=lambda: self._step_level(-1),
        ).pack(side=tk.LEFT, padx=3)

        self.lbl_level = tk.Label(
            lvl_row,
            textvariable=self.level_var,
            bg=THEME["bg_dark"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            width=3,
        )
        self.lbl_level.pack(side=tk.LEFT, padx=2)

        tk.Button(
            lvl_row,
            text="▶",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
            width=2,
            pady=0,
            command=lambda: self._step_level(1),
        ).pack(side=tk.LEFT, padx=3)

        # Quick Preset Buttons
        tk.Button(
            lvl_row,
            text="OoD (Lv30)",
            bg=THEME["bg_hover"],
            fg=THEME["text_secondary"],
            font=FONT_REGULAR,
            pady=0,
            command=lambda: self._set_level(30),
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            lvl_row,
            text="SotP (Lv50)",
            bg=THEME["bg_hover"],
            fg=THEME["text_secondary"],
            font=FONT_REGULAR,
            pady=0,
            command=lambda: self._set_level(50),
        ).pack(side=tk.LEFT)

        # Resource Pool Status Labels
        pools_row = tk.Frame(ctrl_card, bg=THEME["bg_card"])
        pools_row.pack(fill=tk.X, pady=(4, 2))

        self.lbl_stat_pool = tk.Label(
            pools_row,
            text="Stat Points: --",
            bg=THEME["bg_card"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
        )
        self.lbl_stat_pool.pack(side=tk.LEFT)

        self.lbl_skill_pool = tk.Label(
            pools_row,
            text="Skill Points: --",
            bg=THEME["bg_card"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
        )
        self.lbl_skill_pool.pack(side=tk.RIGHT)

        self.lbl_alert = tk.Label(
            ctrl_card,
            text="Status: Valid",
            bg=THEME["bg_card"],
            fg=THEME["success"],
            font=FONT_BOLD,
            anchor="w",
        )
        self.lbl_alert.pack(fill=tk.X, pady=(2, 0))

    def _build_attributes_grid(self):
        attr_card = tk.LabelFrame(
            self.right_container,
            text=" Attributes (Stats) ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=8,
            pady=4,
        )
        attr_card.pack(fill=tk.X, pady=2)

        # 7 Stats Tabular Grid Layout
        self.stat_widgets = {}
        for row_idx, attr in enumerate(ATTRIBUTES):
            abbr = STAT_ABBREVIATIONS[attr]

            lbl_name = tk.Label(
                attr_card,
                text=f"{abbr} ({attr}):",
                width=16,
                anchor="w",
                bg=THEME["bg_card"],
                fg=THEME["text_secondary"],
                font=FONT_REGULAR,
            )
            lbl_name.grid(row=row_idx, column=0, sticky="w", pady=1)
            lbl_name.bind(
                "<Enter>", lambda e, a=attr: self._inspect_attribute(a)
            )

            btn_sub = tk.Button(
                attr_card,
                text="-",
                width=2,
                pady=0,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                command=lambda a=attr: self._step_stat(a, -1),
            )
            btn_sub.grid(row=row_idx, column=1, padx=2, pady=1)

            val_lbl = tk.Label(
                attr_card,
                text="25",
                width=4,
                bg=THEME["bg_dark"],
                fg=THEME["text_primary"],
                font=FONT_MONO,
            )
            val_lbl.grid(row=row_idx, column=2, padx=2, pady=1)
            val_lbl.bind(
                "<Enter>", lambda e, a=attr: self._inspect_attribute(a)
            )

            btn_add = tk.Button(
                attr_card,
                text="+",
                width=2,
                pady=0,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                command=lambda a=attr: self._step_stat(a, 1),
            )
            btn_add.grid(row=row_idx, column=3, padx=2, pady=1)

            cap_lbl = tk.Label(
                attr_card,
                text="/ 98 (+0)",
                width=10,
                anchor="w",
                bg=THEME["bg_card"],
                fg=THEME["text_muted"],
                font=FONT_REGULAR,
            )
            cap_lbl.grid(row=row_idx, column=4, padx=4, pady=1)

            self.stat_widgets[attr] = {
                "val": val_lbl,
                "cap": cap_lbl,
                "btn_sub": btn_sub,
                "btn_add": btn_add,
            }

    def _build_inspector_card(self):
        self.inspector_card = tk.LabelFrame(
            self.right_container,
            text=" Integrated Context Inspector ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=8,
            pady=4,
        )
        self.inspector_card.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        self.insp_title = tk.Label(
            self.inspector_card,
            text="Inspection Details",
            bg=THEME["bg_card"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
            anchor="w",
        )
        self.insp_title.pack(fill=tk.X)

        self.insp_subtitle = tk.Label(
            self.inspector_card,
            text="Hover over any stat or skill node",
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
            font=FONT_REGULAR,
            anchor="w",
        )
        self.insp_subtitle.pack(fill=tk.X)

        self.insp_text = tk.Text(
            self.inspector_card,
            bg=THEME["bg_dark"],
            fg=THEME["text_secondary"],
            font=FONT_REGULAR,
            height=6,
            wrap="word",
            relief="flat",
            padx=6,
            pady=6,
        )
        self.insp_text.pack(fill=tk.BOTH, expand=True, pady=4)

        # Action Buttons Docked at Bottom
        btn_dock = tk.Frame(self.inspector_card, bg=THEME["bg_card"])
        btn_dock.pack(fill=tk.X, side=tk.BOTTOM, pady=2)

        tk.Button(
            btn_dock,
            text="Auto-Resolve Stats",
            bg=THEME["accent"],
            fg="white",
            font=FONT_BOLD,
            pady=2,
            command=self._auto_resolve_stats,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        tk.Button(
            btn_dock,
            text="Export JSON",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            font=FONT_REGULAR,
            pady=2,
            command=self._export_json,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        tk.Button(
            btn_dock,
            text="Import JSON",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            font=FONT_REGULAR,
            pady=2,
            command=self._import_json,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

    def _build_skills_tree(self):
        # Scrollable Canvas Container
        canvas = tk.Canvas(
            self.skills_card, bg=THEME["bg_card"], highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            self.skills_card, orient="vertical", command=canvas.yview
        )
        self.scroll_frame = tk.Frame(canvas, bg=THEME["bg_card"])

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.school_widgets = {}
        self.spec_containers = {}
        self.spec_widgets = {}

        for school, specs in SCHOOL_TREE.items():
            s_box = tk.Frame(
                self.scroll_frame,
                bg=THEME["bg_medium"],
                pady=2,
                padx=4,
                relief="groove",
                borderwidth=1,
            )
            s_box.pack(fill=tk.X, pady=2, padx=2)

            # Major School Row
            s_row = tk.Frame(s_box, bg=THEME["bg_medium"])
            s_row.pack(fill=tk.X)

            s_lbl = tk.Label(
                s_row,
                text=school,
                bg=THEME["bg_medium"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                anchor="w",
            )
            s_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            s_lbl.bind("<Enter>", lambda e, s=school: self._inspect_school(s))

            btn_s_sub = tk.Button(
                s_row,
                text="-",
                width=2,
                pady=0,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                command=lambda s=school: self._step_school(s, -1),
            )
            btn_s_sub.pack(side=tk.LEFT)

            s_val = tk.Label(
                s_row,
                text="0",
                width=3,
                bg=THEME["bg_dark"],
                fg=THEME["accent"],
                font=FONT_MONO,
            )
            s_val.pack(side=tk.LEFT, padx=2)
            s_val.bind("<Enter>", lambda e, s=school: self._inspect_school(s))

            btn_s_add = tk.Button(
                s_row,
                text="+",
                width=2,
                pady=0,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                command=lambda s=school: self._step_school(s, 1),
            )
            btn_s_add.pack(side=tk.LEFT)

            self.school_widgets[school] = {
                "val": s_val,
                "btn_add": btn_s_add,
                "btn_sub": btn_s_sub,
                "label": s_lbl,
            }

            # Sub-Specializations Container (Hidden by default when parent rank is 0)
            spec_frame = tk.Frame(s_box, bg=THEME["bg_medium"])
            self.spec_containers[school] = spec_frame

            for spec in specs:
                sp_row = tk.Frame(spec_frame, bg=THEME["bg_medium"])
                sp_row.pack(fill=tk.X, padx=12, pady=1)

                sp_lbl = tk.Label(
                    sp_row,
                    text=f"• {spec}",
                    bg=THEME["bg_medium"],
                    fg=THEME["text_secondary"],
                    font=FONT_REGULAR,
                    anchor="w",
                )
                sp_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
                sp_lbl.bind(
                    "<Enter>",
                    lambda e, sp=spec: self._inspect_specialization(sp),
                )

                btn_sp_sub = tk.Button(
                    sp_row,
                    text="-",
                    width=2,
                    pady=0,
                    bg=THEME["bg_card"],
                    fg=THEME["text_primary"],
                    command=lambda sp=spec: self._step_spec(sp, -1),
                )
                btn_sp_sub.pack(side=tk.LEFT)

                sp_val = tk.Label(
                    sp_row,
                    text="0",
                    width=3,
                    bg=THEME["bg_dark"],
                    fg=THEME["text_secondary"],
                    font=FONT_MONO,
                )
                sp_val.pack(side=tk.LEFT, padx=2)
                sp_val.bind(
                    "<Enter>",
                    lambda e, sp=spec: self._inspect_specialization(sp),
                )

                btn_sp_add = tk.Button(
                    sp_row,
                    text="+",
                    width=2,
                    pady=0,
                    bg=THEME["bg_card"],
                    fg=THEME["text_primary"],
                    command=lambda sp=spec: self._step_spec(sp, 1),
                )
                btn_sp_add.pack(side=tk.LEFT)

                self.spec_widgets[spec] = {
                    "val": sp_val,
                    "btn_add": btn_sp_add,
                    "btn_sub": btn_sp_sub,
                    "label": sp_lbl,
                }

    def _build_optimizer_tab(self):
        self.opt_tab.columnconfigure(0, weight=1)
        self.opt_tab.rowconfigure(0, weight=0)
        self.opt_tab.rowconfigure(1, weight=1)

        ctrl_bar = tk.Frame(
            self.opt_tab, bg=THEME["bg_medium"], pady=6, padx=10
        )
        ctrl_bar.grid(row=0, column=0, sticky="ew")

        tk.Button(
            ctrl_bar,
            text="Generate Diagnostic Suite",
            bg=THEME["accent"],
            fg="white",
            font=FONT_BOLD,
            command=self._render_optimizer_charts,
        ).pack(side=tk.LEFT, padx=5)

        self.lbl_opt_score = tk.Label(
            ctrl_bar,
            text="Efficiency: --",
            bg=THEME["bg_medium"],
            fg=THEME["success"],
            font=FONT_BOLD,
        )
        self.lbl_opt_score.pack(side=tk.LEFT, padx=15)

        self.chart_container = tk.Frame(self.opt_tab, bg=THEME["bg_dark"])
        self.chart_container.grid(
            row=1, column=0, sticky="nsew", padx=4, pady=4
        )

    # --- Interaction Logic: Hard Forward, Soft Backward ---

    def _step_stat(self, attr: str, delta: int):
        curr_invested = self.current_build.invested_attributes[attr]
        if delta > 0:
            allowed, reason = RulesEngine.can_increment_stat(
                self.current_build, attr
            )
            if not allowed:
                self.insp_title.config(text=f"Blocked: {attr}")
                self.insp_subtitle.config(text="Cannot increment stat point")
                self.insp_text.delete("1.0", tk.END)
                self.insp_text.insert(tk.END, f"⚠️ {reason}")
                return
            self.current_build.invested_attributes[attr] = curr_invested + 1
        else:
            self.current_build.invested_attributes[attr] = max(
                0, curr_invested - 1
            )

        self._update_all_views()
        self._inspect_attribute(attr)

    def _step_school(self, school: str, delta: int):
        curr_rank = self.current_build.schools.get(school, 0)
        if delta > 0:
            allowed, reason = RulesEngine.can_increment_school(
                self.current_build, school
            )
            if not allowed:
                self.insp_title.config(text=f"Blocked: {school}")
                self.insp_subtitle.config(text="Cannot increment school rank")
                self.insp_text.delete("1.0", tk.END)
                self.insp_text.insert(tk.END, f"⚠️ {reason}")
                return
            self.current_build.schools[school] = curr_rank + 1
        else:
            self.current_build.schools[school] = max(0, curr_rank - 1)

        self._update_all_views()
        self._inspect_school(school)

    def _step_spec(self, spec: str, delta: int):
        curr_rank = self.current_build.specializations.get(spec, 0)
        if delta > 0:
            allowed, reason = RulesEngine.can_increment_spec(
                self.current_build, spec
            )
            if not allowed:
                self.insp_title.config(text=f"Blocked: {spec}")
                self.insp_subtitle.config(
                    text="Cannot increment specialization rank"
                )
                self.insp_text.delete("1.0", tk.END)
                self.insp_text.insert(tk.END, f"⚠️ {reason}")
                return
            self.current_build.specializations[spec] = curr_rank + 1
        else:
            self.current_build.specializations[spec] = max(0, curr_rank - 1)

        self._update_all_views()
        self._inspect_specialization(spec)

    def _step_level(self, delta: int):
        """Soft backward de-leveling: retains points while flagging violations."""
        new_level = max(
            1, min(MAX_CHARACTER_LEVEL, self.current_build.level + delta)
        )
        self.current_build.level = new_level
        self.level_var.set(new_level)
        self._update_all_views()

    def _set_level(self, level: int):
        self.current_build.level = level
        self.level_var.set(level)
        self._update_all_views()

    def _auto_resolve_stats(self):
        min_invested = RulesEngine.calculate_minimum_required_stats(
            self.current_build
        )
        for attr, val in min_invested.items():
            self.current_build.invested_attributes[attr] = val
        self._update_all_views()
        messagebox.showinfo(
            "Auto-Resolve Complete",
            "Invested attributes adjusted to minimal prerequisites.",
        )

    # --- View Synchronizer & Progressive Disclosure ---

    def _update_all_views(self):
        report = RulesEngine.validate_build(self.current_build)
        cap = RulesEngine.get_stat_cap_for_level(self.current_build.level)

        # 1. Update Attributes
        for attr, w in self.stat_widgets.items():
            invested = self.current_build.invested_attributes[attr]
            total = BASE_ATTRIBUTE_VALUE + invested
            w["val"].config(text=str(total))
            w["cap"].config(text=f"/ {cap} (+{invested})")
            w["val"].config(
                fg=THEME["error"] if total > cap else THEME["text_primary"]
            )

        # 2. Update Schools & Progressive Disclosure
        for school, s_widgets in self.school_widgets.items():
            rank = self.current_build.schools.get(school, 0)
            s_widgets["val"].config(text=str(rank))
            container = self.spec_containers[school]

            if rank > 0:
                # Reveal sub-specializations
                if not container.winfo_ismapped():
                    container.pack(fill=tk.X, pady=(2, 4))
            else:
                # Hide sub-specializations if parent school is 0
                if container.winfo_ismapped():
                    container.pack_forget()

        # 3. Update Sub-Specializations
        for spec, sp_widgets in self.spec_widgets.items():
            rank = self.current_build.specializations.get(spec, 0)
            sp_widgets["val"].config(text=str(rank))

        # 4. Update Resource Pools
        stat_spent = report.stat_points_spent
        stat_max = report.stat_points_budget
        stat_rem = stat_max - stat_spent
        self.lbl_stat_pool.config(
            text=f"Stats: {stat_rem} rem ({stat_spent}/{stat_max})",
            fg=THEME["error"] if stat_rem < 0 else THEME["text_primary"],
        )

        skill_spent = report.skill_points_spent
        skill_max = report.skill_points_budget
        skill_rem = skill_max - skill_spent
        self.lbl_skill_pool.config(
            text=f"Skills: {skill_rem} rem ({skill_spent}/{skill_max})",
            fg=THEME["error"] if skill_rem < 0 else THEME["text_primary"],
        )

        # 5. Alert Status
        if report.is_valid:
            self.lbl_alert.config(
                text="Status: Valid Build", fg=THEME["success"]
            )
        else:
            issue_count = len(report.issues)
            self.lbl_alert.config(
                text=f"⚠️ {issue_count} Rule Violation(s) [Over Budget]",
                fg=THEME["error"],
            )

    # --- Inspector Feedback ---

    def _inspect_attribute(self, attr: str):
        total = self.current_build.get_effective_attribute(attr)
        cap = RulesEngine.get_stat_cap_for_level(self.current_build.level)
        invested = self.current_build.invested_attributes[attr]

        self.insp_title.config(text=f"Attribute: {attr}")
        self.insp_subtitle.config(
            text=f"Base: 25 | Invested: {invested} | Total: {total} / {cap}"
        )

        lines = [f"Natural Cap at Level {self.current_build.level}: {cap}\n"]
        if total > cap:
            lines.append(f"⚠️ EXCEEDS LEVEL CAP BY {total - cap} POINT(S)!\n")

        lines.append("Governed Schools & Dependencies:")
        for school, (s1, s2) in SCHOOL_GOVERNING_STATS.items():
            if attr in (s1, s2):
                curr_rank = self.current_build.schools.get(school, 0)
                next_rank = curr_rank + 1
                lines.append(f"• {school} (Current Rank: {curr_rank})")
                if next_rank <= 20:
                    _, _, req1, _, req2 = RulesEngine.get_skill_prerequisites(
                        school, next_rank
                    )
                    needed = req1 if s1 == attr else req2
                    lines.append(
                        f"  Next Rank {next_rank} requires: {attr} {needed}"
                    )

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    def _inspect_school(self, school: str):
        rank = self.current_build.schools.get(school, 0)
        max_rank = RulesEngine.get_max_skill_rank_for_level(
            self.current_build.level
        )
        self.insp_title.config(text=f"School: {school}")
        self.insp_subtitle.config(
            text=f"Current Rank: {rank} / Max Allowed: {max_rank}"
        )

        lines = []
        if rank > 0:
            req_lvl, s1, r1, s2, r2 = RulesEngine.get_skill_prerequisites(
                school, rank
            )
            lines.append(f"Rank {rank} Active:")
            lines.append(
                f"• Character Level: {self.current_build.level} (Requires {req_lvl})"
            )
            lines.append(
                f"• {s1}: {self.current_build.get_effective_attribute(s1)} (Requires {r1})"
            )
            lines.append(
                f"• {s2}: {self.current_build.get_effective_attribute(s2)} (Requires {r2})\n"
            )

        if rank < 20:
            next_rank = rank + 1
            n_lvl, n_s1, n_r1, n_s2, n_r2 = RulesEngine.get_skill_prerequisites(
                school, next_rank
            )
            lines.append(f"Requirements for Rank {next_rank}:")
            lines.append(
                f"• Character Level: {n_lvl} [{'OK' if self.current_build.level >= n_lvl else 'MISSING'}]"
            )
            curr1 = self.current_build.get_effective_attribute(n_s1)
            lines.append(
                f"• {n_s1}: {curr1}/{n_r1} [{'OK' if curr1 >= n_r1 else 'MISSING'}]"
            )
            curr2 = self.current_build.get_effective_attribute(n_s2)
            lines.append(
                f"• {n_s2}: {curr2}/{n_r2} [{'OK' if curr2 >= n_r2 else 'MISSING'}]"
            )

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    def _inspect_specialization(self, spec: str):
        parent = RulesEngine.get_parent_school_for_spec(spec)
        rank = self.current_build.specializations.get(spec, 0)
        parent_rank = self.current_build.schools.get(parent, 0)

        self.insp_title.config(text=f"Specialization: {spec}")
        self.insp_subtitle.config(
            text=f"Governing Parent: {parent} (Rank {parent_rank})"
        )

        lines = [
            f"Current Rank: {rank}",
            f"Parent School Ceiling: {parent_rank}",
            "Specializations are bounded by parent school rank.",
        ]
        if rank < parent_rank:
            lines.append(f"• Can be upgraded up to Rank {parent_rank}.")
        else:
            lines.append(
                f"• Must raise parent {parent} before upgrading {spec}."
            )

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    # --- Serialization & Charts ---

    def _export_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Files", "*.json")]
        )
        if path:
            with open(path, "w") as f:
                json.dump(self.current_build.to_dict(), f, indent=2)
            messagebox.showinfo("Export Successful", f"Build saved to {path}")

    def _import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if path:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self.current_build = CharacterBuild.from_dict(data)
                self.level_var.set(self.current_build.level)
                self._update_all_views()
                messagebox.showinfo(
                    "Import Successful",
                    f"Loaded build: {self.current_build.name}",
                )
            except Exception as e:
                messagebox.showerror(
                    "Import Error", f"Failed to load build: {str(e)}"
                )

    def _render_optimizer_charts(self):
        metrics = BuildEvaluator.evaluate(self.current_build)
        self.lbl_opt_score.config(
            text=f"Efficiency Score: {metrics.overall_score}/100"
        )

        if self.canvas_widget:
            self.canvas_widget.get_tk_widget().destroy()
            self.canvas_widget = None

        fig = BuildVisualizer.plot_comparative_suite([self.current_build])
        self.canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_container)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_close(self):
        """Ensures complete process and canvas teardown on window exit."""
        if self.canvas_widget:
            try:
                self.canvas_widget.get_tk_widget().destroy()
            except Exception:
                pass
        self.quit()
        self.destroy()
