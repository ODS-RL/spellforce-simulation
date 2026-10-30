"""Tkinter GUI character simulator with integrated context inspector."""

import ctypes
import json
import io
import os
import subprocess
import sys

from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageGrab
from tkinter import constants as tkc
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


STAT_ABBREVIATIONS: Dict[str, str] = {
    "Strength": "STR",
    "Stamina": "STA",
    "Dexterity": "DEX",
    "Agility": "AGI",
    "Intelligence": "INT",
    "Wisdom": "WIS",
    "Charisma": "CHA",
}

# -relief
# RAISED='raised'
# SUNKEN='sunken'
# FLAT='flat'
# RIDGE='ridge'
# GROOVE='groove'
# SOLID = 'solid'
GUI_RELIEF = tkc.GROOVE


def copy_image_to_clipboard(img: Image.Image) -> bool:
    """Copies a PIL image to the system clipboard across Windows, macOS, and Linux."""
    if sys.platform.startswith("win"):
        try:
            output = io.BytesIO()
            img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[
                14:
            ]  # Strip 14-byte BMP header to obtain CF_DIB
            output.close()

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            h_mem = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
            p_mem = kernel32.GlobalLock(h_mem)
            ctypes.memmove(p_mem, data, len(data))
            kernel32.GlobalUnlock(h_mem)

            if user32.OpenClipboard(None):
                user32.EmptyClipboard()
                user32.SetClipboardData(8, h_mem)  # CF_DIB = 8
                user32.CloseClipboard()
                return True
        except Exception:
            return False
    elif sys.platform == "darwin":
        try:
            temp_path = "/tmp/_sf_clipboard.png"
            img.save(temp_path, "PNG")
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'set the clipboard to (read (POSIX file "{temp_path}") as «class PNGf»)',
                ],
                check=True,
            )
            return True
        except Exception:
            return False
    else:
        # Linux (X11 xclip or Wayland wl-copy)
        for cmd in [
            ["xclip", "-selection", "clipboard", "-t", "image/png"],
            ["wl-copy", "-t", "image/png"],
        ]:
            try:
                output = io.BytesIO()
                img.save(output, format="PNG")
                subprocess.run(cmd, input=output.getvalue(), check=True)
                return True
            except Exception:
                continue
    return False


class RoundedButton(tk.Canvas):
    """Vector-rendered rounded rectangle button with hover and active states."""

    def __init__(
        self,
        parent,
        text: str,
        command: Optional[Callable] = None,
        width: int = 90,
        height: int = 26,
        radius: int = 8,
        bg_color: str = THEME["bg_card"],
        hover_color: str = THEME["bg_hover"],
        active_color: str = THEME["accent"],
        text_color: str = THEME["text_primary"],
        font: Tuple = FONT_BOLD,
        **kwargs,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent["bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            **kwargs,
        )
        self.text = text
        self.command = command
        self.w = width
        self.h = height
        self.radius = radius
        self.normal_bg = bg_color
        self.hover_bg = hover_color
        self.active_bg = active_color
        self.text_color = text_color
        self.font = font
        self.current_bg = bg_color

        self.bind("<Configure>", self._on_resize)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._render()

    def _on_resize(self, event):
        self.w = event.width
        self.h = event.height
        self._render()

    def _render(self):
        self.delete("all")
        r = self.radius
        w, h = self.w, self.h
        points = [
            r,
            0,
            w - r,
            0,
            w,
            0,
            w,
            r,
            w,
            h - r,
            w,
            h,
            w - r,
            h,
            r,
            h,
            0,
            h,
            0,
            h - r,
            0,
            r,
            0,
            0,
            r,
            0,
        ]
        self.create_polygon(
            points,
            smooth=True,
            fill=self.current_bg,
            outline=THEME["border"],
            width=1,
        )
        self.create_text(
            w / 2,
            h / 2,
            text=self.text,
            fill=self.text_color,
            font=self.font,
        )

    def _on_enter(self, _):
        self.current_bg = self.hover_bg
        self._render()

    def _on_leave(self, _):
        self.current_bg = self.normal_bg
        self._render()

    def _on_press(self, _):
        self.current_bg = self.active_bg
        self._render()

    def _on_release(self, _):
        self.current_bg = self.hover_bg
        self._render()
        if self.command:
            self.command()


class SpellForceSimulatorApp(tk.Tk):
    """Main desktop application window."""

    def __init__(self):
        super().__init__()
        self.title("SpellForce Character Simulator & Build Optimizer")
        self.geometry("1120x700")
        self.minsize(1000, 620)
        self.configure(bg=THEME["bg_dark"])

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.current_build = CharacterBuild(name="Champion of Eo", level=30)
        self.comparison_builds: List[CharacterBuild] = [self.current_build]

        self.stat_widgets: Dict[str, Dict] = {}
        self.school_widgets: Dict[str, Dict] = {}
        self.school_boxes: Dict[str, tk.Frame] = {}
        self.spec_containers: Dict[str, tk.Frame] = {}
        self.spec_widgets: Dict[str, Dict] = {}
        self.canvas_widget: Optional[FigureCanvasTkAgg] = None

        self._init_styles()
        self._build_layout()
        self._update_all_views()

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TNotebook",
            background=THEME["bg_dark"],
            relief=GUI_RELIEF,
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=THEME["bg_medium"],
            foreground=THEME["text_secondary"],
            padding=[12, 5],
            font=FONT_BOLD,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", THEME["bg_card"])],
            foreground=[("selected", THEME["accent"])],
        )

        # Dark Theme Scrollbar Configuration (Removes coarse light/white OS scrollbar)
        style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background="#2a2a2a",
            darkcolor="#181818",
            lightcolor="#3c3c3c",
            troughcolor="#181818",
            bordercolor="#181818",
            arrowcolor="#888888",
            relief=GUI_RELIEF,
            borderwidth=0,
        )
        style.map(
            "Vertical.TScrollbar",
            background=[
                ("active", THEME["accent"]),
                ("pressed", THEME["accent_hover"]),
            ],
            arrowcolor=[("active", "#ffffff")],
        )

    def _build_layout(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        # Tab switch hook to auto-update optimizer when focused
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Tab 1: Simulator View
        self.sim_tab = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.sim_tab, text="Character Simulator")
        self._build_simulator_tab()

        # Tab 2: Build Optimizer View
        self.opt_tab = tk.Frame(self.notebook, bg=THEME["bg_dark"])
        self.notebook.add(self.opt_tab, text="Optimizer & Diagnostics")
        self._build_optimizer_tab()

    def _build_simulator_tab(self):
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

        self._build_profile_and_pools_card()
        self._build_attributes_grid()
        self._build_inspector_card()

    def _build_profile_and_pools_card(self):
        ctrl_card = tk.LabelFrame(
            self.right_container,
            text=" Avatar Profile & Resource Pools ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=8,
            pady=4,
            relief=GUI_RELIEF,
            bd=0,
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        ctrl_card.pack(fill=tk.X, pady=(0, 4))

        # Avatar Profile Name Row
        name_row = tk.Frame(ctrl_card, bg=THEME["bg_card"])
        name_row.pack(fill=tk.X, pady=2)

        tk.Label(
            name_row,
            text="Profile:",
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            font=FONT_BOLD,
        ).pack(side=tk.LEFT)

        self.avatar_name_var = tk.StringVar(value=self.current_build.name)
        self.avatar_name_var.trace_add("write", self._on_avatar_name_changed)
        name_entry = tk.Entry(
            name_row,
            textvariable=self.avatar_name_var,
            bg=THEME["bg_dark"],
            fg=THEME["text_primary"],
            insertbackground="white",
            font=FONT_BOLD,
            width=14,
            relief=GUI_RELIEF,
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        name_entry.pack(side=tk.LEFT, padx=4)

        # Level Stepper
        tk.Label(
            name_row,
            text="Level:",
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"],
            font=FONT_BOLD,
        ).pack(side=tk.LEFT, padx=(3, 0))

        self.level_var = tk.IntVar(value=self.current_build.level)
        tk.Button(
            name_row,
            text="◀",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
            width=2,
            pady=0,
            relief=GUI_RELIEF,
            bd=0,
            highlightthickness=0,
            command=lambda: self._step_level(-1),
        ).pack(side=tk.LEFT, padx=1)

        self.lbl_level = tk.Label(
            name_row,
            textvariable=self.level_var,
            bg=THEME["bg_dark"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            width=3,
        )
        self.lbl_level.pack(side=tk.LEFT, padx=1)

        tk.Button(
            name_row,
            text="▶",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
            width=2,
            pady=0,
            relief=GUI_RELIEF,
            bd=0,
            highlightthickness=0,
            command=lambda: self._step_level(1),
        ).pack(side=tk.LEFT, padx=1)

        # Rounded Presets, Reset, and Screenshot Buttons
        RoundedButton(
            name_row,
            text="OoD (30)",
            width=62,
            height=22,
            command=lambda: self._set_level(30),
        ).pack(side=tk.LEFT, padx=2)

        RoundedButton(
            name_row,
            text="SotP (50)",
            width=62,
            height=22,
            command=lambda: self._set_level(50),
        ).pack(side=tk.LEFT, padx=2)

        RoundedButton(
            name_row,
            text="Reset",
            width=50,
            height=22,
            bg_color="#3a2020",
            hover_color="#5a2d2d",
            command=self._reset_build,
        ).pack(side=tk.LEFT, padx=2)

        RoundedButton(
            name_row,
            text="📷 Cap",
            width=55,
            height=22,
            bg_color=THEME["bg_hover"],
            hover_color=THEME["accent"],
            command=self._capture_screenshot,
        ).pack(side=tk.LEFT, padx=2)

        # Resource Pool Status Row
        pools_row = tk.Frame(ctrl_card, bg=THEME["bg_card"])
        pools_row.pack(fill=tk.X, pady=(3, 1))

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

        # Alert Banner (hoverable for full violation summary)
        self.lbl_alert = tk.Label(
            ctrl_card,
            text="Status: Valid",
            bg=THEME["bg_card"],
            fg=THEME["success"],
            font=FONT_BOLD,
            anchor="w",
            cursor="hand2",
        )
        self.lbl_alert.pack(fill=tk.X, pady=(2, 0))
        self.lbl_alert.bind(
            "<Enter>", lambda e: self._inspect_violations_summary()
        )

    def _build_attributes_grid(self):
        attr_card = tk.LabelFrame(
            self.right_container,
            text=" Attributes (Stats) ",
            bg=THEME["bg_card"],
            fg=THEME["accent"],
            font=FONT_HEADER,
            padx=8,
            pady=4,
            relief=GUI_RELIEF,
            bd=0,
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        attr_card.pack(fill=tk.X, pady=2)

        self.stat_widgets = {}
        for row_idx, attr in enumerate(ATTRIBUTES):
            abbr = STAT_ABBREVIATIONS[attr]

            row_frame = tk.Frame(attr_card, bg=THEME["bg_card"])
            row_frame.pack(fill=tk.X, pady=1)

            # Fixed grid layout guarantees identical column coordinates across all 7 rows
            row_frame.columnconfigure(0, minsize=125)
            row_frame.columnconfigure(1, minsize=26)
            row_frame.columnconfigure(2, minsize=34)
            row_frame.columnconfigure(3, minsize=26)
            row_frame.columnconfigure(4, weight=1)

            lbl_name = tk.Label(
                row_frame,
                text=f"{abbr} ({attr}):",
                anchor="w",
                bg=THEME["bg_card"],
                fg=THEME["text_secondary"],
                font=FONT_BOLD,
            )
            lbl_name.grid(row=0, column=0, sticky="w")
            lbl_name.bind(
                "<Enter>", lambda e, a=attr: self._inspect_attribute(a)
            )

            btn_sub = tk.Button(
                row_frame,
                text="-",
                width=2,
                pady=0,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                relief=GUI_RELIEF,
                bd=0,
                highlightthickness=0,
                command=lambda a=attr: self._step_stat(a, -1),
            )
            btn_sub.grid(row=0, column=1, padx=2)

            val_lbl = tk.Label(
                row_frame,
                text="25",
                width=4,
                bg=THEME["bg_dark"],
                fg=THEME["text_primary"],
                font=FONT_MONO,
            )
            val_lbl.grid(row=0, column=2, padx=2)
            val_lbl.bind(
                "<Enter>", lambda e, a=attr: self._inspect_attribute(a)
            )

            btn_add = tk.Button(
                row_frame,
                text="+",
                width=2,
                pady=0,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                relief=GUI_RELIEF,
                bd=0,
                highlightthickness=0,
                command=lambda a=attr: self._step_stat(a, 1),
            )
            btn_add.grid(row=0, column=3, padx=2)

            cap_lbl = tk.Label(
                row_frame,
                text="/ 98 (+0)",
                anchor="w",
                bg=THEME["bg_card"],
                fg=THEME["text_muted"],
                font=FONT_REGULAR,
            )
            cap_lbl.grid(row=0, column=4, sticky="w", padx=4)

            self.stat_widgets[attr] = {
                "frame": row_frame,
                "lbl_name": lbl_name,
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
            relief=GUI_RELIEF,
            bd=0,
            highlightthickness=1,
            highlightbackground=THEME["border"],
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
            text="Hover over any stat or skill node for requirements",
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
            relief=GUI_RELIEF,
            padx=6,
            pady=6,
        )
        self.insp_text.pack(fill=tk.BOTH, expand=True, pady=4)

        btn_dock = tk.Frame(
            self.inspector_card,
            # relief=GUI_RELIEF,
            bg=THEME["bg_card"],
        )
        btn_dock.pack(fill=tk.X, side=tk.BOTTOM, pady=3)

        RoundedButton(
            btn_dock,
            text="Auto-Resolve Stats",
            bg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            height=26,
            command=self._auto_resolve_stats,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        RoundedButton(
            btn_dock,
            text="Export JSON",
            bg_color=THEME["bg_hover"],
            hover_color=THEME["border"],
            height=26,
            command=self._export_json,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        RoundedButton(
            btn_dock,
            text="Import JSON",
            bg_color=THEME["bg_hover"],
            hover_color=THEME["border"],
            height=26,
            command=self._import_json,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

    def _build_skills_tree(self):
        self.skills_card.config(
            relief=GUI_RELIEF,
            bd=0,
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        canvas = tk.Canvas(
            self.skills_card, bg=THEME["bg_card"], highlightthickness=0, bd=0
        )
        # Binds the dark-styled ttk scrollbar
        scrollbar = ttk.Scrollbar(
            self.skills_card,
            orient="vertical",
            command=canvas.yview,
            style="Vertical.TScrollbar",
        )
        self.scroll_frame = tk.Frame(canvas, bg=THEME["bg_card"])

        canvas_window = canvas.create_window(
            (0, 0), window=self.scroll_frame, anchor="nw"
        )

        # Stretch child frame across full canvas width to eliminate empty margin
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.school_widgets = {}
        self.school_boxes = {}
        self.spec_containers = {}
        self.spec_widgets = {}

        for school, specs in SCHOOL_TREE.items():
            s_box = tk.Frame(
                self.scroll_frame,
                bg="#1a1a1a",
                pady=2,
                padx=4,
                relief=GUI_RELIEF,
                bd=0,
                highlightthickness=1,
                highlightbackground=THEME["border"],
            )
            s_box.pack(fill=tk.X, expand=True, pady=2, padx=2)
            self.school_boxes[school] = s_box

            # Strict 4-Column Grid Alignment for School Row
            s_row = tk.Frame(s_box, bg="#1a1a1a")
            s_row.pack(fill=tk.X)
            s_row.columnconfigure(0, weight=1)
            s_row.columnconfigure(1, minsize=26)
            s_row.columnconfigure(2, minsize=32)
            s_row.columnconfigure(3, minsize=26)

            s_lbl = tk.Label(
                s_row,
                text=school,
                bg="#1a1a1a",
                fg=THEME["text_muted"],
                font=FONT_BOLD,
                anchor="w",
            )
            s_lbl.grid(row=0, column=0, sticky="w")
            s_lbl.bind("<Enter>", lambda e, s=school: self._inspect_school(s))

            btn_s_sub = tk.Button(
                s_row,
                text="-",
                width=2,
                pady=0,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                relief=GUI_RELIEF,
                bd=0,
                highlightthickness=0,
                command=lambda s=school: self._step_school(s, -1),
            )
            btn_s_sub.grid(row=0, column=1, padx=2)
            btn_s_sub.bind(
                "<Enter>", lambda e, s=school: self._inspect_school_decrement(s)
            )

            s_val = tk.Label(
                s_row,
                text="0",
                width=3,
                bg=THEME["bg_dark"],
                fg=THEME["accent"],
                font=FONT_MONO,
            )
            s_val.grid(row=0, column=2, padx=2)
            s_val.bind("<Enter>", lambda e, s=school: self._inspect_school(s))

            btn_s_add = tk.Button(
                s_row,
                text="+",
                width=2,
                pady=0,
                bg=THEME["bg_hover"],
                fg=THEME["text_primary"],
                font=FONT_BOLD,
                relief=GUI_RELIEF,
                bd=0,
                highlightthickness=0,
                command=lambda s=school: self._step_school(s, 1),
            )
            btn_s_add.grid(row=0, column=3, padx=2)
            btn_s_add.bind(
                "<Enter>", lambda e, s=school: self._inspect_school_increment(s)
            )

            self.school_widgets[school] = {
                "box": s_box,
                "row": s_row,
                "val": s_val,
                "btn_add": btn_s_add,
                "btn_sub": btn_s_sub,
                "label": s_lbl,
            }

            # Sub-Specializations Container (Strict 4-Column Grid Alignment)
            spec_frame = tk.Frame(s_box, bg=THEME["bg_medium"])
            self.spec_containers[school] = spec_frame

            for spec in specs:
                sp_row = tk.Frame(spec_frame, bg=THEME["bg_medium"])
                sp_row.pack(fill=tk.X, expand=True, pady=1)
                sp_row.columnconfigure(0, weight=1)
                sp_row.columnconfigure(1, minsize=26)
                sp_row.columnconfigure(2, minsize=32)
                sp_row.columnconfigure(3, minsize=26)

                sp_lbl = tk.Label(
                    sp_row,
                    text=f"  • {spec}",
                    bg=THEME["bg_medium"],
                    fg=THEME["text_muted"],
                    font=FONT_REGULAR,
                    anchor="w",
                )
                sp_lbl.grid(row=0, column=0, sticky="w")
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
                    font=FONT_BOLD,
                    relief=GUI_RELIEF,
                    bd=0,
                    highlightthickness=0,
                    command=lambda sp=spec: self._step_spec(sp, -1),
                )
                btn_sp_sub.grid(row=0, column=1, padx=2)
                btn_sp_sub.bind(
                    "<Enter>",
                    lambda e, sp=spec: self._inspect_spec_decrement(sp),
                )

                sp_val = tk.Label(
                    sp_row,
                    text="0",
                    width=3,
                    bg=THEME["bg_dark"],
                    fg=THEME["text_muted"],
                    font=FONT_MONO,
                )
                sp_val.grid(row=0, column=2, padx=2)
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
                    font=FONT_BOLD,
                    relief=GUI_RELIEF,
                    bd=0,
                    highlightthickness=0,
                    command=lambda sp=spec: self._step_spec(sp, 1),
                )
                btn_sp_add.grid(row=0, column=3, padx=2)
                btn_sp_add.bind(
                    "<Enter>",
                    lambda e, sp=spec: self._inspect_spec_increment(sp),
                )

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

        RoundedButton(
            ctrl_bar,
            text="Refresh Plots",
            bg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            width=100,
            command=self._render_optimizer_charts,
        ).pack(side=tk.LEFT, padx=3)

        self.lbl_active_profile = tk.Label(
            ctrl_bar,
            text="Profile: Champion of Eo",
            bg=THEME["bg_medium"],
            fg=THEME["accent"],
            font=FONT_BOLD,
        )
        self.lbl_active_profile.pack(side=tk.LEFT, padx=10)

        # Interactive Frontier Axis Controls
        tk.Label(
            ctrl_bar,
            text="Frontier:",
            bg=THEME["bg_medium"],
            fg=THEME["text_secondary"],
            font=FONT_BOLD,
        ).pack(side=tk.LEFT, padx=(12, 2))

        self.combo_frontier_x = ttk.Combobox(
            ctrl_bar,
            values=list(SCHOOL_TREE.keys()),
            state="readonly",
            width=16,
            font=FONT_REGULAR,
        )
        self.combo_frontier_x.pack(side=tk.LEFT, padx=2)
        self.combo_frontier_x.bind(
            "<<ComboboxSelected>>", lambda e: self._render_optimizer_charts()
        )

        btn_swap = tk.Button(
            ctrl_bar,
            text="⇄",
            bg=THEME["bg_hover"],
            fg=THEME["text_primary"],
            font=FONT_BOLD,
            pady=0,
            width=2,
            relief=GUI_RELIEF,
            bd=0,
            command=self._swap_frontier_axes,
        )
        btn_swap.pack(side=tk.LEFT, padx=2)

        self.combo_frontier_y = ttk.Combobox(
            ctrl_bar,
            values=list(SCHOOL_TREE.keys()),
            state="readonly",
            width=16,
            font=FONT_REGULAR,
        )
        self.combo_frontier_y.pack(side=tk.LEFT, padx=2)
        self.combo_frontier_y.bind(
            "<<ComboboxSelected>>", lambda e: self._render_optimizer_charts()
        )

        RoundedButton(
            ctrl_bar,
            text="+ Add Build",
            width=85,
            bg_color=THEME["bg_hover"],
            command=self._add_comparison_build,
        ).pack(side=tk.LEFT, padx=3)

        RoundedButton(
            ctrl_bar,
            text="Clear",
            width=55,
            bg_color="#3a2020",
            hover_color="#5a2d2d",
            command=self._clear_comparison_builds,
        ).pack(side=tk.LEFT, padx=3)

        RoundedButton(
            ctrl_bar,
            text="📷 Cap",
            bg_color=THEME["bg_hover"],
            hover_color=THEME["border"],
            width=65,
            command=self._capture_screenshot,
        ).pack(side=tk.LEFT, padx=3)

        self.lbl_opt_score = tk.Label(
            ctrl_bar,
            text="Efficiency: --",
            bg=THEME["bg_medium"],
            fg=THEME["success"],
            font=FONT_BOLD,
        )
        self.lbl_opt_score.pack(side=tk.RIGHT, padx=10)

        self.chart_container = tk.Frame(self.opt_tab, bg=THEME["bg_dark"])
        self.chart_container.grid(
            row=1, column=0, sticky="nsew", padx=4, pady=4
        )

    # --- Interaction Logic: Progressive Cascading & Hard Constraints ---

    def _on_avatar_name_changed(self, *args):
        new_name = self.avatar_name_var.get().strip() or "Avatar"
        self.current_build.name = new_name
        self.lbl_active_profile.config(text=f"Profile: {new_name}")

    def _on_tab_changed(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab == "Optimizer & Diagnostics":
            self._render_optimizer_charts()

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
            allowed, reason, to_claim = RulesEngine.can_increment_school(
                self.current_build, school, auto_claim_stats=True
            )
            if not allowed:
                self.insp_title.config(text=f"Blocked: {school}")
                self.insp_subtitle.config(text="Cannot increment school rank")
                self.insp_text.delete("1.0", tk.END)
                self.insp_text.insert(tk.END, f"⚠️ {reason}")
                return
            # Auto-claim required governing stats
            for attr_name, stat_add in to_claim.items():
                self.current_build.invested_attributes[attr_name] += stat_add
            self.current_build.schools[school] = curr_rank + 1
        else:
            if curr_rank <= 0:
                return
            # Cascading reduction: clamp child abilities that exceed the lower parent rank
            released_pts, clamped = RulesEngine.calculate_cascaded_derank(
                self.current_build, school
            )
            self.current_build.schools[school] = curr_rank - 1
            for spec, new_r in clamped.items():
                self.current_build.specializations[spec] = new_r

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

    def _reset_build(self):
        """Resets the simulator state back to Level 1 with 0 points invested."""
        if messagebox.askyesno(
            "Reset Character Build",
            "Reset avatar back to Level 1 and refund all stat/skill points?",
        ):
            name = self.avatar_name_var.get().strip() or "New Avatar"
            self.current_build = CharacterBuild(name=name, level=1)
            self.level_var.set(1)
            self._update_all_views()

    def _capture_screenshot(self):
        """Captures window bounds, copies image to system clipboard, and saves to screenshots/."""
        self.update_idletasks()
        try:
            x = self.winfo_rootx()
            y = self.winfo_rooty()
            w = self.winfo_width()
            h = self.winfo_height()

            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))

            # Ensure screenshots directory exists
            os.makedirs("screenshots", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = (
                "".join(
                    c
                    for c in self.current_build.name
                    if c.isalnum() or c in ("-", "_")
                )
                or "Avatar"
            )
            filepath = os.path.join(
                "screenshots", f"{safe_name}_{timestamp}.png"
            )
            img.save(filepath, "PNG")

            copied = copy_image_to_clipboard(img)
            clip_msg = (
                "copied to clipboard"
                if copied
                else "clipboard unsupported on this OS"
            )

            self.insp_title.config(text="📷 Screenshot Captured")
            self.insp_subtitle.config(text=f"Status: {clip_msg}")
            self.insp_text.delete("1.0", tk.END)
            self.insp_text.insert(
                tk.END,
                f"✓ Snapshot successfully taken!\n\n"
                f"• Image {clip_msg}.\n"
                f"• Disk copy saved to:\n  {os.path.abspath(filepath)}",
            )
        except Exception as e:
            messagebox.showerror(
                "Screenshot Error", f"Failed to capture snapshot: {e}"
            )

    # --- View Synchronizer & Visual Polish ---

    def _update_all_views(self):
        report = RulesEngine.validate_build(self.current_build)
        cap = RulesEngine.get_stat_cap_for_level(self.current_build.level)
        broken_prereqs = RulesEngine.get_broken_prerequisites(
            self.current_build
        )

        # 1. Update Attributes with unconditionally rendered values and cohesive warning rows
        for attr, w in self.stat_widgets.items():
            invested = self.current_build.invested_attributes[attr]
            total = BASE_ATTRIBUTE_VALUE + invested

            # Synchronize displayed numeric value
            w["val"].config(text=str(total))

            if attr in broken_prereqs:
                # Broken prerequisite: highlight entire row in crimson
                w["frame"].config(bg="#4a1818")
                w["lbl_name"].config(bg="#4a1818", fg="#ff6b6b")
                w["val"].config(bg="#2d0f0f", fg="#ff6b6b")
                needed = max(req[1] for req in broken_prereqs[attr])
                w["cap"].config(
                    text=f"/ {cap} (+{invested}) ⚠️ Req {needed}",
                    bg="#4a1818",
                    fg="#ff6b6b",
                    font=FONT_BOLD,
                )
            elif total > cap:
                # Level cap exceeded
                w["frame"].config(bg=THEME["bg_card"])
                w["lbl_name"].config(
                    bg=THEME["bg_card"], fg=THEME["text_secondary"]
                )
                w["val"].config(bg=THEME["bg_dark"], fg=THEME["error"])
                w["cap"].config(
                    text=f"/ {cap} (+{invested}) ⚠️ Exceeds Cap",
                    bg=THEME["bg_card"],
                    fg=THEME["error"],
                    font=FONT_REGULAR,
                )
            else:
                # Normal state
                w["frame"].config(bg=THEME["bg_card"])
                w["lbl_name"].config(
                    bg=THEME["bg_card"], fg=THEME["text_secondary"]
                )
                w["val"].config(bg=THEME["bg_dark"], fg=THEME["text_primary"])
                w["cap"].config(
                    text=f"/ {cap} (+{invested})",
                    bg=THEME["bg_card"],
                    fg=THEME["text_muted"],
                    font=FONT_REGULAR,
                )

        # 2. Update Schools & Visual Hierarchy (Dim inactive, highlight active)
        for school, s_widgets in self.school_widgets.items():
            rank = self.current_build.schools.get(school, 0)
            s_widgets["val"].config(text=str(rank))
            container = self.spec_containers[school]
            box = self.school_boxes[school]
            row = s_widgets["row"]

            if rank > 0:
                # Active school: elevated dark slate and blue border
                box.config(bg="#252932", relief="ridge", borderwidth=1)
                row.config(bg="#252932")
                s_widgets["label"].config(
                    bg="#252932", fg=THEME["text_primary"], font=FONT_BOLD
                )
                s_widgets["val"].config(fg=THEME["accent"])
                if not container.winfo_ismapped():
                    container.pack(fill=tk.X, expand=True, pady=(2, 4))
            else:
                # Inactive school: dimmed palette
                box.config(bg="#181818", relief="flat", borderwidth=1)
                row.config(bg="#181818")
                s_widgets["label"].config(
                    bg="#181818", fg="#666666", font=FONT_REGULAR
                )
                s_widgets["val"].config(fg="#666666")
                if container.winfo_ismapped():
                    container.pack_forget()

        # 3. Update Sub-Specializations Mastery Colors
        for spec, sp_widgets in self.spec_widgets.items():
            parent = RulesEngine.get_parent_school_for_spec(spec)
            parent_rank = self.current_build.schools.get(parent, 0)
            rank = self.current_build.specializations.get(spec, 0)
            sp_widgets["val"].config(text=str(rank))

            if rank == 0:
                sp_widgets["label"].config(fg="#777777")
                sp_widgets["val"].config(fg="#777777")
            elif rank == parent_rank and parent_rank > 0:
                # Synchronized with parent ceiling: Emerald Green
                sp_widgets["label"].config(fg="#4ec9b0", font=FONT_BOLD)
                sp_widgets["val"].config(fg="#4ec9b0", font=FONT_BOLD)
            else:
                # In-progress: Gold / Amber
                sp_widgets["label"].config(fg="#dcdcaa", font=FONT_REGULAR)
                sp_widgets["val"].config(fg="#dcdcaa", font=FONT_BOLD)

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

        # 5. Alert Status Banner
        if report.is_valid:
            self.lbl_alert.config(
                text="Status: Valid Build (All rules satisfied)",
                fg=THEME["success"],
            )
        else:
            issue_count = len(report.issues)
            self.lbl_alert.config(
                text=f"⚠️ {issue_count} Rule Violation(s) [Hover for details]",
                fg=THEME["error"],
            )

    # --- Interactive Hover Diagnostics ---

    def _inspect_violations_summary(self):
        report = RulesEngine.validate_build(self.current_build)
        self.insp_title.config(text="Build Violations Diagnostic")
        self.insp_subtitle.config(
            text=f"Detected {len(report.issues)} issue(s) needing resolution"
        )

        lines = []
        if report.is_valid:
            lines.append("✓ Build conforms to all game mechanics constraints.")
        else:
            for idx, issue in enumerate(report.issues, 1):
                lines.append(f"{idx}. [{issue.category}] {issue.message}")

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    def _inspect_school_increment(self, school: str):
        curr_rank = self.current_build.schools.get(school, 0)
        max_rank = RulesEngine.get_max_skill_rank_for_level(
            self.current_build.level
        )
        next_rank = curr_rank + 1

        self.insp_title.config(
            text=f"Upgrade Preview: {school} (Rank {next_rank})"
        )
        self.insp_subtitle.config(
            text=f"Current: Rank {curr_rank} / Level Cap: {max_rank}"
        )

        if next_rank > 20:
            lines = ["• Reached absolute maximum rank (20)."]
        elif next_rank > max_rank:
            lines = [
                f"⚠️ Cannot upgrade: Exceeds Character Level {self.current_build.level} ceiling of {max_rank}."
            ]
        else:
            req_lvl, s1, r1, s2, r2 = RulesEngine.get_skill_prerequisites(
                school, next_rank
            )
            curr1 = self.current_build.get_effective_attribute(s1)
            curr2 = self.current_build.get_effective_attribute(s2)
            _, _, def1, _, _, def2, tot_def = (
                RulesEngine.get_school_stat_requirements(
                    self.current_build, school, next_rank
                )
            )

            lines = [f"Prerequisites for Rank {next_rank}:"]
            lines.append(
                f"• Character Level: {req_lvl} "
                f"[{'✓ OK' if self.current_build.level >= req_lvl else f'✗ DEFICIT: Need Lv {req_lvl}'}]"
            )
            lines.append(
                f"• {s1}: {curr1}/{r1} "
                f"[{'✓ OK' if def1 == 0 else f'Auto-allocates +{def1}'}]"
            )
            lines.append(
                f"• {s2}: {curr2}/{r2} "
                f"[{'✓ OK' if def2 == 0 else f'Auto-allocates +{def2}'}]"
            )

            lines.append("\nCost on Click:")
            lines.append("• 1 Skill Point")
            if tot_def > 0:
                lines.append(
                    f"• {tot_def} Stat Point(s) automatically claimed (+{def1} {s1}, +{def2} {s2})"
                )
            else:
                lines.append(
                    "• 0 Stat Points (Prerequisites already satisfied)"
                )

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    def _inspect_school_decrement(self, school: str):
        curr_rank = self.current_build.schools.get(school, 0)
        self.insp_title.config(text=f"Derank Preview: {school}")
        self.insp_subtitle.config(text=f"Current Rank: {curr_rank}")

        if curr_rank <= 0:
            lines = ["• School is already at Rank 0."]
        else:
            released_pts, clamped = RulesEngine.calculate_cascaded_derank(
                self.current_build, school
            )
            target_rank = curr_rank - 1
            lines = [f"Reducing {school} to Rank {target_rank}:"]
            lines.append(f"• Total Skill Points Released: +{released_pts}")

            if clamped:
                lines.append(
                    "\n⚠️ Cascading specializations will also be lowered:"
                )
                for spec, new_r in clamped.items():
                    old_r = self.current_build.specializations.get(spec, 0)
                    lines.append(f"  - {spec}: {old_r} ➔ {new_r}")

            if target_rank > 0:
                _, s1, r1, s2, r2 = RulesEngine.get_skill_prerequisites(
                    school, target_rank
                )
                lines.append(f"\nLowered Prerequisites at Rank {target_rank}:")
                lines.append(f"• {s1}: {r1} | {s2}: {r2}")

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    def _inspect_spec_increment(self, spec: str):
        parent = RulesEngine.get_parent_school_for_spec(spec)
        parent_rank = self.current_build.schools.get(parent, 0)
        curr_rank = self.current_build.specializations.get(spec, 0)
        next_rank = curr_rank + 1

        self.insp_title.config(text=f"Upgrade Preview: {spec}")
        self.insp_subtitle.config(
            text=f"Governing Parent: {parent} (Rank {parent_rank})"
        )

        lines = [f"Target: Rank {next_rank}"]
        if next_rank > parent_rank:
            lines.append(
                f"⚠️ Cannot upgrade: Bounded by parent {parent} (Rank {parent_rank})."
            )
            lines.append(f"Raise {parent} first to unlock higher {spec} ranks.")
        else:
            lines.append(
                f"• Allowed under parent ceiling ({next_rank} ≤ {parent_rank})."
            )
            lines.append("• Cost: 1 Skill Point")

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    def _inspect_spec_decrement(self, spec: str):
        curr_rank = self.current_build.specializations.get(spec, 0)
        self.insp_title.config(text=f"Derank Preview: {spec}")
        self.insp_subtitle.config(text=f"Current: Rank {curr_rank}")

        if curr_rank <= 0:
            lines = ["• Specialization is already at Rank 0."]
        else:
            lines = [
                f"Reducing {spec} to Rank {curr_rank - 1}:",
                "• Will refund 1 Skill Point.",
            ]

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    def _inspect_attribute(self, attr: str):
        total = self.current_build.get_effective_attribute(attr)
        cap = RulesEngine.get_stat_cap_for_level(self.current_build.level)
        invested = self.current_build.invested_attributes[attr]

        self.insp_title.config(text=f"Attribute: {attr}")
        self.insp_subtitle.config(
            text=f"Base: 25 | Invested: {invested} | Total: {total} / {cap}"
        )

        lines = [
            f"Natural Maximum at Level {self.current_build.level}: {cap}\n"
        ]
        if total > cap:
            lines.append(f"⚠️ EXCEEDS LEVEL CAP BY {total - cap} POINT(S)!\n")

        broken = RulesEngine.get_broken_prerequisites(self.current_build)
        if attr in broken:
            lines.append("⚠️ CRITICAL PREREQUISITE DEFICITS:")
            for school, req_val, act_val in broken[attr]:
                lines.append(
                    f"• {school} requires {attr} {req_val} (Current: {act_val}, Need +{req_val - act_val})"
                )
            lines.append("")

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
            lines.append(f"Next Rank {next_rank} Requirements:")
            lines.append(
                f"• Character Level: {n_lvl} [{'✓ OK' if self.current_build.level >= n_lvl else '✗ MISSING'}]"
            )
            curr1 = self.current_build.get_effective_attribute(n_s1)
            lines.append(
                f"• {n_s1}: {curr1}/{n_r1} [{'✓ OK' if curr1 >= n_r1 else '✗ MISSING'}]"
            )
            curr2 = self.current_build.get_effective_attribute(n_s2)
            lines.append(
                f"• {n_s2}: {curr2}/{n_r2} [{'✓ OK' if curr2 >= n_r2 else '✗ MISSING'}]"
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
        ]
        if rank < parent_rank:
            lines.append(f"• Can be upgraded up to Rank {parent_rank}.")
        else:
            lines.append(f"• Must raise parent {parent} to upgrade further.")

        self.insp_text.delete("1.0", tk.END)
        self.insp_text.insert(tk.END, "\n".join(lines))

    # --- Serialization & Comparison ---

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
                self.avatar_name_var.set(self.current_build.name)
                self.level_var.set(self.current_build.level)
                self.comparison_builds = [self.current_build]
                self._update_all_views()
                messagebox.showinfo(
                    "Import Successful",
                    f"Loaded build: {self.current_build.name}",
                )
            except Exception as e:
                messagebox.showerror(
                    "Import Error", f"Failed to load build: {str(e)}"
                )

    def _add_comparison_build(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if path:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                extra_build = CharacterBuild.from_dict(data)
                if len(self.comparison_builds) >= 4:
                    self.comparison_builds.pop()
                self.comparison_builds.append(extra_build)
                self._render_optimizer_charts()
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Failed to load comparison build: {e}"
                )

    def _clear_comparison_builds(self):
        self.comparison_builds = [self.current_build]
        self._render_optimizer_charts()

    def _swap_frontier_axes(self):
        """Swaps X and Y combobox values and refreshes the Pareto frontier plot."""
        x_val = self.combo_frontier_x.get()
        y_val = self.combo_frontier_y.get()
        self.combo_frontier_x.set(y_val)
        self.combo_frontier_y.set(x_val)
        self._render_optimizer_charts()

    def _render_optimizer_charts(self):
        self.comparison_builds[0] = self.current_build
        self.lbl_active_profile.config(
            text=f"Profile: {self.current_build.name}"
        )

        metrics = BuildEvaluator.evaluate(self.current_build)
        self.lbl_opt_score.config(
            text=f"Efficiency Score: {metrics.overall_score}/100"
        )

        # Dynamic school selection: auto-detect top 2 trained schools if unselected or identical
        all_schools = list(SCHOOL_TREE.keys())
        school_x = self.combo_frontier_x.get()
        school_y = self.combo_frontier_y.get()

        if not school_x or not school_y or school_x == school_y:
            trained = [
                s
                for s, r in sorted(
                    self.current_build.schools.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
                if r > 0
            ]
            if len(trained) >= 2:
                school_x, school_y = trained[0], trained[1]
            elif len(trained) == 1:
                school_x = trained[0]
                school_y = [s for s in all_schools if s != school_x][0]
            else:
                school_x = "Heavy Combat Arts"
                school_y = "White Magic"

            self.combo_frontier_x.set(school_x)
            self.combo_frontier_y.set(school_y)

        if self.canvas_widget:
            self.canvas_widget.get_tk_widget().destroy()
            self.canvas_widget = None

        fig = BuildVisualizer.plot_comparative_suite(
            self.comparison_builds,
            primary_school_pair=(school_x, school_y),
        )
        self.canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_container)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_close(self):
        if self.canvas_widget:
            try:
                self.canvas_widget.get_tk_widget().destroy()
            except Exception:
                pass
        self.quit()
        self.destroy()
