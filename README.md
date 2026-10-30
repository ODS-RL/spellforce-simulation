# SpellForce Engine (`sfengine`): Character Ability Simulator & Build Optimizer

An analytical simulation environment, interactive GUI character builder, and combinatorial build optimizer for **SpellForce: Platinum Edition** (encompassing *The Order of Dawn*, *The Breath of Winter*, and *The Shadow of the Phoenix*).

The application models the progression mechanics for character levels 1 through 50, evaluates hybrid class viability under strict point budgets, and visualizes Pareto trade-off frontiers without requiring brute-force in-game leveling.

---

## 1. System Overview & Core Philosophy

In *SpellForce*, character growth is governed by non-linear constraints:
* Primary attributes act as hard gates for combat and magic schools.
* Major schools bound their child specializations (`Specialization Rank ≤ Parent School Rank`).
* Resource budgets expand across two distinct eras: **The Order of Dawn / Breath of Winter** (Levels 1–30, Skill Ranks 1–12) and **The Shadow of the Phoenix** (Levels 31–50, Skill Ranks 13–20).

Hybrid builds (such as Paladins, Battlemages, and Arcane Archers) face severe mathematical tension because their governing attributes are often disjoint. Investing across multiple disparate stats risks stranding points in sub-threshold ranks or failing high-level prerequisite checks. 

`sfengine` formalizes these rules into a deterministic validation engine, interactive desktop simulator, and combinatorial optimizer.

---

## 2. Mathematical Foundations & Game Mechanics

### 2.1 Resource Accumulation Schedules

For an Avatar at Character Level $L \in [1, 50]$:

#### Attribute (Stat) Point Budget
At Level 1, characters start with a baseline of **25 points** in all 7 attributes (175 base points) plus **30 bonus spendable points**. Each level-up from 2 to 50 awards **5 spendable stat points**:
$$B_{\text{stat}}(L) = 30 + 5 \times (L - 1)$$
* At Level 30 (OoD/BoW Cap): $B_{\text{stat}}(30) = 175 \text{ spendable points}$ (Total stat sum = $175 + 175 = 350$).
* At Level 50 (SotP / Platinum Cap): $B_{\text{stat}}(50) = 275 \text{ spendable points}$ (Total stat sum = $175 + 275 = 450$).

#### Base Attribute Cap Formula
Across all 50 levels, the maximum natural value to which any single primary attribute can be raised is:
$$\text{Cap}_{\text{stat}}(L) = 40 + 2 \times (L - 1)$$
* Level 1: $\text{Cap} = 40$
* Level 30: $\text{Cap} = 98$
* Level 50: $\text{Cap} = 138$

#### Skill Point Budget
At Level 1, characters receive **2 skill points**. Each level-up awards **2 skill points**:
$$B_{\text{skill}}(L) = 2 \times L$$
* At Level 30: $B_{\text{skill}}(30) = 60 \text{ skill points}$ (Allows up to $5$ skills maxed to Rank 12: $5 \times 12 = 60$).
* At Level 50: $B_{\text{skill}}(50) = 100 \text{ skill points}$ (Allows up to $5$ skills maxed to Rank 20: $5 \times 20 = 100$).

#### Maximum Skill Rank Ceiling
Skill ranks are gated discretely by character level:
$$
M(L) = \begin{cases} 
1 & L = 1 \\
2 & 2 \le L \le 4 \\
3 & 5 \le L \le 6 \\
4 & 7 \le L \le 9 \\
5 & 10 \le L \le 11 \\
6 & 12 \le L \le 14 \\
7 & 15 \le L \le 16 \\
8 & 17 \le L \le 19 \\
9 & 20 \le L \le 21 \\
10 & 22 \le L \le 24 \\
11 & 25 \le L \le 27 \\
12 & 28 \le L \le 30 \quad (\text{Note: Black/Mind Magic Rank 12 requires } L \ge 29) \\
13 & 31 \le L \le 32 \\
14 & 33 \le L \le 35 \\
15 & 36 \le L \le 37 \\
16 & 38 \le L \le 40 \\
17 & 41 \le L \le 43 \\
18 & 44 \le L \le 45 \\
19 & 46 \le L \le 47 \\
20 & 48 \le L \le 50 
\end{cases}
$$

---

### 2.2 Primary Attribute Mechanics & Derived Formulas

```
┌───────────────┬───────────────────────────────┬──────────────────────────────────────────┐
│ Attribute     │ Primary Gameplay Influence    │ Engine Formula / Mechanics Impact        │
├───────────────┼───────────────────────────────┼──────────────────────────────────────────┤
│ Strength      │ Physical Melee Weapon Damage  │ Linear multiplier in damage numerator    │
│ Stamina       │ Maximum Hit Points (HP)       │ Scaled by Level Health Factor            │
│ Dexterity     │ Attack Accuracy / Hit Chance  │ Evaluated against target Agility         │
│ Agility       │ Evasion / Defensive Hit Check │ Evaluated against attacker Dexterity     │
│ Intelligence  │ Mana Regeneration Rate        │ Periodic mana recovery per tick          │
│ Wisdom        │ Maximum Mana Pool             │ Scaled by Level Mana Factor              │
│ Charisma      │ Spell Potency & Trade Prices  │ Multiplier on White/Mind Magic & barter  │
└───────────────┴───────────────────────────────┴──────────────────────────────────────────┘
```

#### Physical Melee Damage Output
Melee damage depends strictly on Weapon Base Damage, Attacker Strength, Level-Scaled Weapon Factor, and Target Armor:
$$\text{Damage} = \text{Factor}_{\text{weapon}}(L) \times \text{Damage}_{\text{weapon}} \times \frac{\text{Strength}}{\text{Target Armor} \times 0.01 + 1} \times \text{Modifier}_{\text{enemy}}$$
* $\text{Factor}_{\text{weapon}}(L)$ scales from $50\%$ at Level 1 up to $200\%$ at Level 30, peaking at $350\%$ at Level 50. Melee damage scales directly with invested Strength, whereas combat skill ranks serve primarily as gear equip prerequisites.

#### Hit Points (HP) Pool
$$\text{HP} = \left\lfloor \frac{\text{Stamina} \times \text{Factor}_{\text{health}}(L)}{100} \right\rfloor$$
* $\text{Factor}_{\text{health}}$ increases from $100$ at Level 1 to $1,390$ at Level 30, and reaches $3,500$ at Level 50.

#### Mana Pool
$$\text{Mana} = \left\lfloor \frac{\text{Wisdom} \times \text{Factor}_{\text{mana}}(L)}{100} \right\rfloor$$
* $\text{Factor}_{\text{mana}}$ scales from $100$ at Level 1 to $226$ at Level 30, reaching $316$ at Level 50.

#### Mana Regeneration Tick
Mana restores periodically (approximately every 6 seconds):
$$\text{Mana Restored Per Tick} = \left\lfloor \frac{2L + \text{Intelligence}}{10} \right\rfloor$$

#### Charisma Spell Potency Multiplier
For White Magic (Life, Nature, Boons) and Mind Magic (Enchantment):
$$\text{Multiplier}_{\text{spell}} = \frac{\text{Charisma} + 15}{50}$$
*(At 135 Charisma, spell effects are amplified by $3.0\times$)*.

#### Merchant Discount & Sell Markup
$$\text{Trade Modifier} = \text{clamp}\left(0,\, \frac{\text{Charisma} - 30}{5},\, 10\right)\%$$
*(Grants up to a 10% buy discount and sell bonus at 80+ Charisma)*.

---

### 2.3 Governing Stat Matrix for Major Schools

To train a Major School to Rank $k$, the character must meet both governing attribute thresholds:

```
┌────────────────────┬─────────────────────────┬───────────────────────┬───────────────────────┐
│ Major School       │ Governing Stats         │ Rank 12 Reqs (Lv30)   │ Rank 20 Reqs (Lv50)   │
├────────────────────┼─────────────────────────┼───────────────────────┼───────────────────────┤
│ Light Combat Arts  │ Dexterity / Agility     │ Dex 70 / Agi 60       │ Dex 102 / Agi 100     │
│ Heavy Combat Arts  │ Strength / Stamina      │ Str 80 / Sta 80       │ Str 112 / Sta 112     │
│ Range Combat Arts  │ Strength / Dexterity    │ Str 55 / Dex 70       │ Str 87  / Dex 110     │
│ White Magic        │ Wisdom / Charisma       │ Wis 70 / Cha 60       │ Wis 102 / Cha 92      │
│ Black Magic        │ Intelligence / Wisdom   │ Int 95 / Wis 60       │ Int 127 / Wis 92      │
│ Elemental Magic    │ Intelligence / Wisdom   │ Int 80 / Wis 80       │ Int 112 / Wis 112     │
│ Mind Magic         │ Intelligence / Charisma │ Int 70 / Cha 95       │ Int 102 / Cha 127     │
└────────────────────┴─────────────────────────┴───────────────────────┴───────────────────────┘
```

---

## 3. The Hybrid Tension Problem & Mathematical Proof

When combining combat arts with magic schools, players encounter conflicting attribute dependencies. Because primary stats start at 25 and cannot exceed 138 at Level 50, allocating points across non-overlapping governing stats introduces mathematical limits on achievable skill ranks.

### 3.1 Impossibility Proof: The Paladin (Heavy Combat + White Magic)
* Available Stat Points at Level 50: **275 spendable points**.
* **Heavy Combat Arts Rank 20:** Requires $\text{Str} \ge 112$, $\text{Sta} \ge 112$.
  $$\text{Cost}_{\text{HCA20}} = (112 - 25) + (112 - 25) = 87 + 87 = 174 \text{ points}$$
* **White Magic Rank 20:** Requires $\text{Wis} \ge 102$, $\text{Cha} \ge 92$.
  $$\text{Cost}_{\text{WM20}} = (102 - 25) + (92 - 25) = 77 + 67 = 144 \text{ points}$$
* **Combined Cost:**
  $$\text{Cost}_{\text{Total}} = 174 + 144 = 318 \text{ points} > 275 \text{ points available}$$
* **Conclusion:** It is **strictly impossible** for an Avatar to attain Rank 20 in both Heavy Combat Arts and White Magic.
  * If $\text{HCA} = 20 \implies \text{Remaining points} = 275 - 174 = 101 \implies \mathbf{\max(\text{WM}) = 14}$ (Costs 96 points).
  * If $\text{WM} = 20 \implies \text{Remaining points} = 275 - 144 = 131 \implies \mathbf{\max(\text{HCA}) = 14}$ (Costs 126 points).
  * If balanced symmetrically: $\mathbf{\max(\text{HCA}, \text{WM}) = (17, 17)}$, which costs $150 + 120 = 270 \text{ points}$ (leaving 5 surplus points).

### 3.2 Shared Attribute Synergies
Conversely, builds that share governing attributes reduce point pressure:
* **Battlemage (Black Magic + Elemental Magic):** Both schools depend entirely on $\text{Int}$ and $\text{Wis}$. At Level 50, meeting Black Magic Rank 20 ($\text{Int } 127, \text{Wis } 92$) requires 169 stat points. With 106 stat points remaining, Elemental Magic can concurrently reach **Rank 18** ($\text{Int } 104, \text{Wis } 104$, costing 158 points total).
* **Arcane Archer (Range Combat + Mind Magic):** Disjoint dependencies ($\text{Str/Dex}$ vs $\text{Int/Cha}$) require spreading points across 4 distinct attributes, enforcing strict rank trade-offs along the Pareto frontier.

---

## 4. Optimization Engine & Build Evaluation Metrics

Rather than simulating tick-by-tick combat encounters, the optimizer models point efficiency using discrete tier quantization, stranded cost penalties, and prerequisite slack.

### 4.1 Discrete Spell Tier Quantization
Spell scrolls and combat abilities unlock at discrete ranks:
$$\mathcal{T} = \{1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20\}$$

For any allocated skill rank $k_s$, its **functional tier** is the highest unlocked breakpoint:
$$k_s^* = \max \{ t \in \mathcal{T} \mid t \le k_s \}$$

Any ranks invested between tiers ($k_s - k_s^*$) represent **stranded points** that do not unlock new scroll tiers or abilities. Furthermore, in *The Breath of Winter* and *The Shadow of the Phoenix*, **Almightiness Spells** require all three sub-specializations to match the parent school's rank. An uneven sub-school (e.g., Fire 16, Ice 16, Earth 14) strands points above Rank 14 for Almightiness casting.

### 4.2 Build Efficiency Objective Function $\Phi(\text{Build})$

$$\Phi(S, \mathbf{A}) = \left( w_{\text{stat}} \cdot \mathcal{E}_{\text{stat}} + w_{\text{skill}} \cdot \mathcal{E}_{\text{skill}} - \mathcal{P}_{\text{stranded}} - \mathcal{P}_{\text{obsolete}} - \mathcal{P}_{\text{violation}} \right)$$

Where:
1. **Stat Utilization Efficiency ($\mathcal{E}_{\text{stat}}$):**
   $$\mathcal{E}_{\text{stat}} = \frac{\sum_{a \in \mathcal{A}} \left(\max_{s \in S} \text{ReqStat}(s, k_s, a) - 25\right)}{B_{\text{stat}}(L)}$$
   Measures the proportion of the stat budget directly satisfying active skill prerequisites.
2. **Skill Tier Efficiency ($\mathcal{E}_{\text{skill}}$):**
   $$\mathcal{E}_{\text{skill}} = \frac{\sum_{s \in S} k_s^*}{B_{\text{skill}}(L)}$$
   Measures points allocated to discrete functional tiers against the total skill budget.
3. **Stranded Point Penalty ($\mathcal{P}_{\text{stranded}}$):**
   $$\mathcal{P}_{\text{stranded}} = \sum_{s \in S} (k_s - k_s^*)$$
4. **Obsolete Rank Penalty ($\mathcal{P}_{\text{obsolete}}$):**
   Low-tier abilities (e.g., Rank 4 at Level 50) have negligible hit chance, high enemy resist rates, and low base values against Level 45–50 enemies. For an endgame character ($L \ge 45$), abilities below viability threshold $\tau(L) = 12$ are penalized:
   $$\mathcal{P}_{\text{obsolete}} = \sum_{s \in S} k_s \cdot \mathbb{I}(k_s < \tau(L))$$
5. **Rule Violation Penalty ($\mathcal{P}_{\text{violation}}$):**
   Imposes substantial penalties for overspent stat/skill budgets, exceeded level caps, or unmet prerequisites.

---

## 5. Software Architecture

The codebase follows an Object-Oriented design separated into three core sub-packages:

```text
spellforce-simulation/
├── sfengine/
│   ├── core/
│   │   ├── constants.py       # Progression matrices, governing stats, discrete tiers
│   │   ├── models.py          # Domain dataclasses: CharacterBuild, ValidationReport
│   │   └── rules.py           # Game mechanics rules engine & validation logic
│   ├── optimizer/
│   │   ├── evaluator.py       # Discrete tier quantization & efficiency scoring
│   │   ├── solver.py          # HybridParetoSolver combinatorial frontier solver
│   │   └── visualizer.py      # Object-oriented Matplotlib 4-panel diagnostic suite
│   ├── gui/
│   │   ├── app.py             # Desktop Tkinter GUI with context inspection
│   │   └── theme.py           # Dark UI styling, color palettes, and typography
│   └── __init__.py
├── main.py                    # Application entrypoint
├── pyproject.toml             # Packaging metadata & dependency definitions
└── README.md                  # Comprehensive architectural documentation
```

### 5.1 Sub-Package Responsibilities

#### `sfengine.core`
* **`constants.py`**: Immutable lookup tables mapping Character Levels ($1 \dots 50$) to Max Stat Caps, Max Skill Ceilings, and Stat Prerequisite pairs for all 7 Major Schools across Ranks 1 to 20.
* **`models.py`**: Clean dataclasses representing character state (`CharacterBuild`), rule infractions (`ValidationIssue`), and comprehensive diagnostic reports (`ValidationReport`). Includes JSON serialization helpers.
* **`rules.py`**: Authoritative validation methods:
  * `can_increment_stat`, `can_increment_school`, `can_increment_spec`: Hard gating logic on allocation.
  * `calculate_cascaded_derank`: Determines cascading sub-specialization clamping and refunded points.
  * `get_broken_prerequisites`: Returns the exact attribute deficits caused by under-invested stats relative to active skills.

#### `sfengine.optimizer`
* **`evaluator.py`**: Evaluates active functional tiers, tallies stranded points, and computes the 0–100 Build Efficiency Score.
* **`solver.py`**: Iterates through the $21 \times 21$ rank matrix for any pair of Major Schools, checks feasibility against the Level 50 stat budget ($275$) and stat caps ($138$), and generates the Pareto boundary.
* **`visualizer.py`**: Generates a 4-panel diagnostic figure using Matplotlib's Object-Oriented API (`Figure`), completely isolated from Pyplot global state.

#### `sfengine.gui`
* **`app.py`**: High-performance Tkinter desktop application featuring non-destructive de-leveling, real-time hover previews, visual hierarchy dimming, and synchronized comparative diagnostics.
* **`theme.py`**: Dark mode palette with specific semantic accents: `#4ec9b0` (Success / Synchronized), `#dcdcaa` (Warning / In-Progress), `#ff6b6b` (Broken Prerequisite / Error), and `#007acc` (Interactive Accent).

---

## 6. Graphical User Interface (GUI) Mechanics

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  SpellForce Character Simulator & Build Optimizer                                          [—][口][✕] │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [ Character Simulator ] [ Optimizer & Diagnostics ]                                                    │
├───────────────────────────────────────────────────┬────────────────────────────────────────────────────┤
│  Combat Arts & Magic Schools                      │  Avatar Profile & Resource Pools                   │
│ ┌───────────────────────────────────────────────┐ │  Profile: [ Paladin           ] Level: ◀ [30] ▶   │
│ │ Heavy Combat Arts (Active)       [-] [12] [+] │ │  Stats: 9 rem (166/175)        Skills: 30 rem      │
│ │   • Heavy Blade Weapons (Maxed)  [-] [12] [+] │ │  Status: Valid Build                               │
│ │   • Shields             (Amber)  [-] [ 8] [+] │ ├────────────────────────────────────────────────────┤
│ ├───────────────────────────────────────────────┤ │  Attributes (Stats)                                │
│ │ Light Combat Arts (Dimmed)       [-] [ 0] [+] │ │  STR (Strength):     [-] [ 80 ] [+] / 98 (+55)     │
│ │ Range Combat Arts (Dimmed)       [-] [ 0] [+] │ │  STA (Stamina):      [-] [ 80 ] [+] / 98 (+55)     │
│ │ White Magic       (Dimmed)       [-] [ 0] [+] │ │  WIS (Wisdom):       [-] [ 44 ] [+] / 98 (+19) ⚠️  │
│ └───────────────────────────────────────────────┘ ├────────────────────────────────────────────────────┤
│                                                   │  Integrated Context Inspector                      │
│                                                   │  Upgrade Preview: Heavy Combat Arts (Rank 13)      │
│                                                   │  • Character Level: 31 [✗ DEFICIT: Need Lv 31]     │
│                                                   │  • STR: 80/84 [✗ DEFICIT: Need +4]                 │
│                                                   │  • STA: 80/84 [✗ DEFICIT: Need +4]                 │
│                                                   │ ┌──────────────────┬─────────────┬───────────────┐ │
│                                                   │ │ Auto-Resolve     │ Export JSON │ Import JSON   │ │
│                                                   │ └──────────────────┴─────────────┴───────────────┘ │
└───────────────────────────────────────────────────┴────────────────────────────────────────────────────┘
```

### 6.1 "Hard Forward, Soft Backward" Constraint Protocol
* **Hard Gating on Increment (`+`):** The simulator actively blocks spending points if budgets are exhausted, caps are reached, or prerequisites are missing. If an upgrade is illegal, the `+` button click is rejected, and the Context Inspector explains the exact blocker.
* **Soft Preservation on De-Leveling (`◀`):** When stepping character level down (e.g., from 50 to 30), existing allocations are **not deleted**. Instead, the build enters an over-budget state, resource counters turn negative in red, and offending nodes are visually highlighted until corrected with `-` clicks.

### 6.2 Progressive Disclosure & Visual Hierarchy
* **Inactive School Dimming:** Schools at Rank 0 are rendered in dark muted gray (`#181818`), reducing visual clutter.
* **Child Specialization Unfolding:** Sub-specializations remain hidden until their parent school reaches Rank 1 or higher.
* **Specialization Mastery Coloring:**
  * **Muted Gray (`#777777`):** Unallocated (Rank 0).
  * **Amber / Gold (`#dcdcaa`):** In progress ($0 < \text{Rank} < \text{Parent Rank}$).
  * **Emerald Green (`#4ec9b0`):** Synchronized at parent ceiling ($\text{Rank} = \text{Parent Rank}$).
* **Strict 4-Column Alignment:** Stepper controls (`[-]`, `[Val]`, `[+]`) use fixed-width grid columns across all rows, maintaining clean vertical alignment.

### 6.3 Cascading Derank on School Downgrade
When clicking `-` on a parent school, any child specialization whose rank exceeds the lowered school rank is automatically clamped to match. The exact number of released points (from the school and all clamped sub-skills) is computed and refunded instantly.

### 6.4 Real-Time Context Inspector
Hovering over any UI control updates the integrated Context Inspector panel:
* **Hovering `+` on a School:** Previews next rank requirements, displaying green `[✓ OK]` or red `[✗ DEFICIT: Need +X]` tags for Character Level and Governing Stats.
* **Hovering `-` on a School:** Previews refunded skill points, lists any sub-specializations that will be clamped, and shows lowered stat requirements.
* **Broken Stat Alerting:** If a stat is reduced below an active skill's prerequisite, the attribute row turns dark crimson (`#4a1818`) with red text (`#ff6b6b`), displaying the required value. Hovering the alert banner displays a categorized summary of all active rule violations.

---

## 7. The 4-Panel Diagnostic Suite

Switching to the **Optimizer & Diagnostics** tab automatically synchronizes with the active simulator profile and renders a 4-panel analytical chart:

```
┌───────────────────────────────────────┬───────────────────────────────────────┐
│ 1. Attribute Radar vs Level 50 Cap    │ 2. Hybrid Pareto Frontier Curve       │
│    (Polar comparison of all 7 stats   │    (Feasible trade-off space for two  │
│     against the natural 138 stat cap) │     schools; plots build position)    │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ 3. Point Efficiency & Loss Breakdown  │ 4. Platinum Progression Trajectory    │
│    (Stacked bars: productive stats,   │    (Resource accumulation curves from │
│     slack, stranded, and obsolete pts)│     Level 1 to 50, marking OoD cap)   │
└───────────────────────────────────────┴───────────────────────────────────────┘
```

1. **Attribute Radar vs Level 50 Cap:** Overlays invested primary attributes against the natural cap ($138$). Supports comparing up to 4 loaded builds simultaneously.
2. **Hybrid Pareto Frontier Curve:** Plots School A Rank vs School B Rank. Marks the feasible trade-off space in green and infeasible region in dark red, placing the active build's coordinate directly onto the curve.
3. **Point Efficiency & Loss Breakdown:** Deconstructs allocations into productive stats, surplus stats, stranded skill points (between spell tiers), and obsolete ranks.
4. **Platinum Progression Trajectory:** Shows stat and skill point budget curves across levels 1–50, highlighting the transition from the base campaign (Level 30) into the expansion era (Level 50).

---

## 8. Installation & Usage

### 8.1 Prerequisites
* Python 3.11 or higher
* `tkinter` (included with standard Python installations on Windows and macOS; on Linux, install via `sudo apt-get install python3-tk`)

### 8.2 Installation
Clone the repository and install runtime dependencies:

```bash
git clone https://github.com/ODS-RL/spellforce-simulation.git
cd spellforce-simulation
pip install -e .
```

*Direct dependencies installed: `matplotlib>=3.8`, `numpy>=1.26`.*

### 8.3 Running the Application

```bash
python main.py
```

### 8.4 Build Serialization (JSON Format)
Builds can be saved and loaded via the **Export JSON** and **Import JSON** buttons:

```json
{
  "name": "Paladin",
  "level": 30,
  "invested_attributes": {
    "Strength": 55,
    "Stamina": 55,
    "Dexterity": 0,
    "Agility": 0,
    "Intelligence": 0,
    "Wisdom": 37,
    "Charisma": 19
  },
  "schools": {
    "Light Combat Arts": 0,
    "Heavy Combat Arts": 12,
    "Range Combat Arts": 0,
    "White Magic": 6,
    "Black Magic": 0,
    "Elemental Magic": 0,
    "Mind Magic": 0
  },
  "specializations": {
    "Heavy Blade Weapons": 12,
    "Heavy Armor": 12,
    "Shields": 0,
    "Life": 6,
    "Boons": 6
  }
}
```

---

## 9. Architectural Optimizations

1. **$O(1)$ Prerequisite Verification:**
   Pre-computed requirement matrices in `constants.py` replace dynamic condition trees with constant-time tuple lookups. Broken prerequisite checks evaluate only actively trained schools ($K \le 7$), keeping frame budgets under 2ms during rapid clicking.
2. **Deterministic Matplotlib Teardown:**
   Isolating diagnostic charts into standalone `matplotlib.figure.Figure` instances decouples GUI event loops from Pyplot's global state machine, preventing process deadlocks upon application exit.
3. **Progressive Widget Mapping:**
   Sub-specialization frames are retained in memory and dynamically toggled using `pack()` and `pack_forget()`, avoiding expensive widget destruction and recreation during interactive tree browsing.
