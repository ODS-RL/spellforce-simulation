"""Tkinter GUI character simulator with integrated context inspector."""

import json

from typing import Dict, Optional

import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import filedialog, messagebox, ttk

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


class SpellForceSimulatorApp(tk.Tk):
    """Main desktop application window."""

    def __init__(self):
        super().__init__()
        self.title("SpellForce Character Simulator & Build Optimizer")
        self.geometry("1400x900")
        self.configure(bg=THEME["bg_dark"])

        self.current_build = CharacterBuild(name="Champion of Eo", level=30)
        self.comparison_builds = [self.current_build]

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
            padding=[12, 6],
            font=FONT_BOLD,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", THEME["bg_card"])],
            foreground=[("selected", THEME["accent"])],
        )
        style.configure("TFrame", background=THEME["bg_dark"])
        style.configure(
            "Card.TFrame",
            background=THEME["bg_card"],
            relief="solid",
            borderwidth=1,
        )

    def _build_layout(self):
        # 1. Top Global Navigation / Header Bar
        self.header_frame = tk.Frame(
            self, bg=THEME["bg_medium"], height=70, padx=15, pady=8
        )
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        self._build_header()

        # 2. Main Tabs Notebook (Simulator vs Optimizer)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Simulator View
        self.sim_tab = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.sim_tab, text="Character Simulator")
        self._build_simulator_tab()

        # Tab 2: Build Optimizer & Visualizer View
        self.opt_tab = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.opt_tab, text="Optimizer & Diagnostics")
        self._build_optimizer_tab()

    def _build_header(self):
        # Build Name & Level Stepper
        name_lbl = tk.Label(
            self.header_frame,
            text="Avatar Level:",
            bg=THEME["bg_medium"],
            fg=THEME["text_secondary"],
            font=FONT_BOLD,
        )
        name_lbl.pack(side=tk.LEFT, padx=5)

        self.level_var = tk.IntVar(value=self.current_build.level)
        self.btn_lvl_down = tk.Button(
            self.header_frame,
            text="◀",
            bg=THEME["bg_card"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
            width=2,
            command=lambda: self._step_level(-1),
        )
        self.btn_lvl_down.pack(side=tk.LEFT)

        self.lbl_level = tk.Label(
            self.header_frame,
            textvariable=self.level_var,
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_TITLE,
            width=3,
        )
        self.lbl_level.pack(side=tk.LEFT, padx=2)

        self.btn_lvl_up = tk.Button(
            self.header_frame,
            text="▶",
            bg=THEME["bg_card"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
            width=2,
            command=lambda: self._step_level(1),
        )
        self.btn_lvl_up.pack(side=tk.LEFT)

        # Campaign Presets
        tk.Button(
            self.header_frame,
            text="Preset: OoD (Lv30)",
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            font=FONT_REGULAR,
            command=lambda: self._set_level(30),
        ).pack(side=tk.LEFT, padx=10)
        tk.Button(
            self.header_frame,
            text="Preset: SotP (Lv50)",
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            font=FONT_REGULAR,
            command=lambda: self._set_level(50),
        ).pack(side=tk.LEFT)

        # Resource Pool Status Cards
        self.lbl_stat_pool = tk.Label(
            self.header_frame,
            text="Stat Points: --",
            bg=THEME["bg_medium"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
        )
        self.lbl_stat_pool.pack(side=tk.LEFT, padx=20)

        self.lbl_skill_pool = tk.Label(
            self.header_frame,
            text="Skill Points: --",
            bg=THEME["bg_medium"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
        )
        self.lbl_skill_pool.pack(side=tk.LEFT, padx=10)

        # Status Alert Banner
        self.lbl_alert = tk.Label(
            self.header_frame,
            text="Status: Valid",
            bg=THEME["bg_medium"],
            fg=THEME["success"],
            font=FONT_BOLD,
        )
        self.lbl_alert.pack(side=tk.RIGHT, padx=15)

    def _build_simulator_tab(self):
        # 3-Column Layout: Left (Attributes), Center (Skill Trees), Right (Context Inspector)
        self.sim_tab.columnconfigure(0, weight=3)
        self.sim_tab.columnconfigure(1, weight=5)
        self.sim_tab.columnconfigure(2, weight=4)
        self.sim_tab.rowconfigure(0, weight=1)

        # Col 1: Attributes Panel
        self.attr_card = tk.LabelFrame(
            self.sim_tab,
            text=" Attributes (Stats) ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=10,
            pady=10,
        )
        self.attr_card.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._build_attributes_panel()

        # Col 2: Skills & Specializations Panel
        self.skills_card = tk.LabelFrame(
            self.sim_tab,
            text=" Combat Arts & Magic Schools ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=10,
            pady=10,
        )
        self.skills_card.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._build_skills_panel()

        # Col 3: Integrated Context Inspector (No floating popups)
        self.inspector_card = tk.LabelFrame(
            self.sim_tab,
            text=" Integrated Context Inspector ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=10,
            pady=10,
        )
        self.inspector_card.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        self._build_inspector_panel()

    def _build_attributes_panel(self):
        self.stat_widgets = {}
        for attr in ATTRIBUTES:
            row = tk.Frame(self.attr_card, bg=THEME["bg_card"], pady=6)
            row.pack(fill=tk.X)

            lbl = tk.Label(
                row,
                text=f"{attr[:4].upper()}:",
                width=5,
                anchor="w",
                bg=THEME["bg_card"],
                fg=THEME["text_secondary"],
                font=FONT_BOLD,
            )
            lbl.pack(side=tk.LEFT)
            lbl.bind("<Enter>", lambda e, a=attr: self._inspect_attribute(a))

            btn_sub = tk.Button(
                row,
                text="-",
                width=2,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                command=lambda a=attr: self._step_stat(a, -1),
            )
            btn_sub.pack(side=tk.LEFT, padx=2)

            val_lbl = tk.Label(
                row,
                text="25",
                width=4,
                bg=THEME["bg_dark"],
                fg=THEME["text_primary"],
                font=FONT_MONO,
            )
            val_lbl.pack(side=tk.LEFT, padx=3)
            val_lbl.bind(
                "<Enter>", lambda e, a=attr: self._inspect_attribute(a)
            )

            btn_add = tk.Button(
                row,
                text="+",
                width=2,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                command=lambda a=attr: self._step_stat(a, 1),
            )
            btn_add.pack(side=tk.LEFT, padx=2)

            cap_lbl = tk.Label(
                row,
                text="/ 98",
                bg=THEME["bg_card"],
                fg=THEME["text_muted"],
                font=FONT_REGULAR,
            )
            cap_lbl.pack(side=tk.LEFT, padx=5)

            self.stat_widgets[attr] = {
                "val": val_lbl,
                "cap": cap_lbl,
                "btn_sub": btn_sub,
                "btn_add": btn_add,
            }

        # Auto-Solver Button
        tk.Button(
            self.attr_card,
            text="Auto-Resolve Minimal Stats",
            bg=THEME["accent"],
            fg="white",
            font=FONT_BOLD,
            pady=6,
            command=self._auto_resolve_stats,
        ).pack(fill=tk.X, side=tk.BOTTOM, pady=10)

    def _build_skills_panel(self):
        # Scrollable Canvas for 7 Schools & 22 Specializations
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

        self.skill_widgets = {}
        for school, specs in SCHOOL_TREE.items():
            s_box = tk.Frame(
                self.scroll_frame,
                bg=THEME["bg_medium"],
                pady=4,
                padx=5,
                relief="groove",
                borderwidth=1,
            )
            s_box.pack(fill=tk.X, pady=4, padx=2)

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
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
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
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                command=lambda s=school: self._step_school(s, 1),
            )
            btn_s_add.pack(side=tk.LEFT)

            self.skill_widgets[school] = {
                "val": s_val,
                "btn_add": btn_s_add,
                "btn_sub": btn_s_sub,
                "label": s_lbl,
            }

            # Sub-Specializations Indented Under School
            for spec in specs:
                sp_row = tk.Frame(s_box, bg=THEME["bg_medium"])
                sp_row.pack(fill=tk.X, padx=15, pady=1)

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
                    bg=THEME["bg_card"],
                    fg=THEME["text_primary"],
                    command=lambda sp=spec: self._step_spec(sp, 1),
                )
                btn_sp_add.pack(side=tk.LEFT)

                self.skill_widgets[spec] = {
                    "val": sp_val,
                    "btn_add": btn_sp_add,
                    "btn_sub": btn_sp_sub,
                    "label": sp_lbl,
                }

    def _build_inspector_panel(self):
        # Seamlessly integrated inspector (replaces pop-up tooltips)
        self.insp_title = tk.Label(
            self.inspector_card,
            text="Inspection Details",
            bg=THEME["bg_card"],
            fg=THEME["text_primary"],
            font=FONT_TITLE,
        )
        self.insp_title.pack(anchor="w", pady=(0, 5))

        self.insp_type = tk.Label(
            self.inspector_card,
            text="Hover over any stat or skill node",
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
            font=FONT_REGULAR,
        )
        self.insp_type.pack(anchor="w")

        ttk.Separator(self.inspector_card).pack(fill=tk.X, pady=8)

        self.insp_text = tk.Text(
            self.inspector_card,
            bg=THEME["bg_dark"],
            fg=THEME["text_secondary"],
            font=FONT_REGULAR,
            wrap="word",
            relief="flat",
            padx=8,
            pady=8,
        )
        self.insp_text.pack(fill=tk.BOTH, expand=True)

        # Save/Load buttons
        btn_box = tk.Frame(self.inspector_card, bg=THEME["bg_card"])
        btn_box.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        tk.Button(
            btn_box,
            text="Export Build JSON",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            command=self._export_json,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(
            btn_box,
            text="Import Build JSON",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            command=self._import_json,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

    def _build_optimizer_tab(self):
        self.opt_tab.columnconfigure(0, weight=1)
        self.opt_tab.rowconfigure(0, weight=0)
        self.opt_tab.rowconfigure(1, weight=1)

        # Control Bar
        ctrl_bar = tk.Frame(
            self.opt_tab, bg=THEME["bg_medium"], pady=8, padx=10
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

        # Matplotlib Canvas Container
        self.chart_container = tk.Frame(self.opt_tab, bg=THEME["bg_dark"])
        self.chart_container.grid(
            row=1, column=0, sticky="nsew", padx=5, pady=5
        )
        self.canvas_widget = None

    # --- Interaction & Inspection Logic ---

    def _inspect_attribute(self, attr: str):
        total = self.current_build.get_effective_attribute(attr)
        cap = RulesEngine.get_stat_cap_for_level(self.current_build.level)
        invested = self.current_build.invested_attributes[attr]

        self.insp_title.config(text=f"Attribute: {attr}")
        self.insp_type.config(
            text=f"Base: 25 | Invested: {invested} | Total: {total} / {cap}"
        )

        lines = [
            f"Natural Maximum at Level {self.current_build.level}: {cap}\n"
        ]
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
        self.insp_type.config(
            text=f"Current Rank: {rank} / Max Allowed: {max_rank}"
        )

        lines = []
        if rank > 0:
            req_lvl, s1, r1, s2, r2 = RulesEngine.get_skill_prerequisites(
                school, rank
            )
            lines.append(f"Current Rank {rank} Status:")
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
            lines.append(f"Requirements for Next Rank {next_rank}:")
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
        self.insp_type.config(
            text=f"Governing Parent: {parent} (Rank {parent_rank})"
        )

        lines = [
            f"Current Rank: {rank}",
            f"Parent School Ceiling: {parent_rank}",
            f"Sub-specializations cannot exceed their parent school rank.",
        ]
        if rank < parent_rank:
            lines.append(
                f"• Can be raised up to {parent_rank} without further parent investment."
            )
        else:
            lines.append(
                f"• Must raise parent {parent} before upgrading {spec}."
            )

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    # --- Allocation Steppers ---

    def _step_level(self, delta: int):
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

    def _step_stat(self, attr: str, delta: int):
        curr = self.current_build.invested_attributes[attr]
        new_val = max(0, curr + delta)
        self.current_build.invested_attributes[attr] = new_val
        self._update_all_views()
        self._inspect_attribute(attr)

    def _step_school(self, school: str, delta: int):
        curr = self.current_build.schools.get(school, 0)
        new_rank = max(0, min(20, curr + delta))
        self.current_build.schools[school] = new_rank
        self._update_all_views()
        self._inspect_school(school)

    def _step_spec(self, spec: str, delta: int):
        curr = self.current_build.specializations.get(spec, 0)
        new_rank = max(0, min(20, curr + delta))
        self.current_build.specializations[spec] = new_rank
        self._update_all_views()
        self._inspect_specialization(spec)

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

    # --- View Synchronizer ---

    def _update_all_views(self):
        report = RulesEngine.validate_build(self.current_build)
        cap = RulesEngine.get_stat_cap_for_level(self.current_build.level)

        # Update Stat Displays
        for attr, w in self.stat_widgets.items():
            invested = self.current_build.invested_attributes[attr]
            total = BASE_ATTRIBUTE_VALUE + invested
            w["val"].config(text=str(total))
            w["cap"].config(text=f"/ {cap}")
            w["val"].config(
                fg=THEME["error"] if total > cap else THEME["text_primary"]
            )

        # Update Skill Displays
        for name, w in self.skill_widgets.items():
            if name in self.current_build.schools:
                rank = self.current_build.schools[name]
            else:
                rank = self.current_build.specializations[name]
            w["val"].config(text=str(rank))

        # Update Pools & Header
        stat_spent = report.stat_points_spent
        stat_max = report.stat_points_budget
        stat_rem = stat_max - stat_spent
        self.lbl_stat_pool.config(
            text=f"Stat Points: {stat_rem} rem ({stat_spent}/{stat_max})",
            fg=THEME["error"] if stat_rem < 0 else THEME["text_primary"],
        )

        skill_spent = report.skill_points_spent
        skill_max = report.skill_points_budget
        skill_rem = skill_max - skill_spent
        self.lbl_skill_pool.config(
            text=f"Skill Points: {skill_rem} rem ({skill_spent}/{skill_max})",
            fg=THEME["error"] if skill_rem < 0 else THEME["text_primary"],
        )

        # Status Alert Banner
        if report.is_valid:
            self.lbl_alert.config(
                text="Status: Valid Build", fg=THEME["success"]
            )
        else:
            issue_count = len(report.issues)
            self.lbl_alert.config(
                text=f"⚠️ {issue_count} Rule Violation(s)", fg=THEME["error"]
            )

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

        # Clear existing canvas if present
        if self.canvas_widget:
            self.canvas_widget.get_tk_widget().destroy()

        fig = BuildVisualizer.plot_comparative_suite([self.current_build])
        self.canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_container)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
