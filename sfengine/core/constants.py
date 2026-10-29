"""Constants and lookup matrices for SpellForce: Platinum Edition.

Encodes progression schedules, attribute caps, and school requirements for:
- The Order of Dawn (OoD: Levels 1-30)
- The Breath of Winter (BoW: Levels 1-30)
- The Shadow of the Phoenix (SotP: Levels 31-50)
"""

from typing import Dict, List, Tuple

# Base attribute starting value for all characters
BASE_ATTRIBUTE_VALUE: int = 25

# Starting bonus stat points at Character Level 1
LEVEL_1_STAT_BONUS: int = 30

# Stat points gained per level up (Levels 2-50)
STAT_POINTS_PER_LEVEL: int = 5

# Starting skill points at Character Level 1
LEVEL_1_SKILL_POINTS: int = 2

# Skill points gained per level up (Levels 2-50)
SKILL_POINTS_PER_LEVEL: int = 2

# Maximum achievable character level
MAX_CHARACTER_LEVEL: int = 50

# Maximum achievable skill rank
MAX_SKILL_RANK: int = 20

# The 7 Core Primary Attributes
ATTRIBUTES: Tuple[str, ...] = (
    "Strength",
    "Stamina",
    "Dexterity",
    "Agility",
    "Intelligence",
    "Wisdom",
    "Charisma",
)

# School Names and their Sub-Specializations
SCHOOL_TREE: Dict[str, List[str]] = {
    "Light Combat Arts": [
        "Piercing Weapons",
        "Light Blade Weapons",
        "Light Blunt Weapons",
        "Light Armor",
    ],
    "Heavy Combat Arts": [
        "Heavy Blade Weapons",
        "Heavy Blunt Weapons",
        "Heavy Armor",
        "Shields",
    ],
    "Range Combat Arts": [
        "Bow",
        "Crossbow",
    ],
    "White Magic": [
        "Life",
        "Nature",
        "Boons",
    ],
    "Black Magic": [
        "Death",
        "Necromancy",
        "Curses",
    ],
    "Elemental Magic": [
        "Fire",
        "Ice",
        "Earth",
    ],
    "Mind Magic": [
        "Enchantment",
        "Offensive",
        "Defensive",
    ],
}

# Governing stats for each Major School: (Primary Stat, Secondary Stat)
SCHOOL_GOVERNING_STATS: Dict[str, Tuple[str, str]] = {
    "Light Combat Arts": ("Dexterity", "Agility"),
    "Heavy Combat Arts": ("Strength", "Stamina"),
    "Range Combat Arts": ("Strength", "Dexterity"),
    "White Magic": ("Wisdom", "Charisma"),
    "Black Magic": ("Intelligence", "Wisdom"),
    "Elemental Magic": ("Intelligence", "Wisdom"),
    "Mind Magic": ("Intelligence", "Charisma"),
}

# Maximum Skill Level unlocked by Character Level: Dict[CharacterLevel, MaxSkillRank]
LEVEL_TO_MAX_SKILL: Dict[int, int] = {
    1: 1, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4, 9: 4, 10: 5,
    11: 5, 12: 6, 13: 6, 14: 6, 15: 7, 16: 7, 17: 8, 18: 8, 19: 8, 20: 9,
    21: 9, 22: 10, 23: 10, 24: 10, 25: 11, 26: 11, 27: 11, 28: 12, 29: 12, 30: 12,
    31: 13, 32: 13, 33: 14, 34: 14, 35: 14, 36: 15, 37: 15, 38: 16, 39: 16, 40: 16,
    41: 17, 42: 17, 43: 17, 44: 18, 45: 18, 46: 19, 47: 19, 48: 20, 49: 20, 50: 20,
}

# Minimum Character Level required for a given Skill Rank (1-20)
# Note: BM and MM Rank 12 require Level 29 because stat cap at Lv28 is 94 while 95 is needed.
SKILL_RANK_MIN_CHAR_LEVEL: Dict[int, int] = {
    1: 1, 2: 2, 3: 5, 4: 7, 5: 10, 6: 12, 7: 15, 8: 17, 9: 20, 10: 22,
    11: 25, 12: 28, 13: 31, 14: 33, 15: 36, 16: 38, 17: 41, 18: 43, 19: 46, 20: 48,
}

# Attribute Requirements Matrix for each School across Ranks 1 to 20
# Format: Dict[SchoolName, Dict[SkillRank, Tuple[Stat1_Req, Stat2_Req]]]
SKILL_REQUIREMENTS_MATRIX: Dict[str, Dict[int, Tuple[int, int]]] = {
    "Light Combat Arts": {
        1: (25, 25), 2: (26, 26), 3: (28, 27), 4: (30, 29), 5: (33, 31),
        6: (37, 34), 7: (40, 37), 8: (45, 41), 9: (50, 45), 10: (56, 50),
        11: (62, 55), 12: (70, 60), 13: (74, 65), 14: (78, 70), 15: (82, 75),
        16: (86, 80), 17: (90, 85), 18: (94, 90), 19: (98, 95), 20: (102, 100),
    },
    "Heavy Combat Arts": {
        1: (25, 25), 2: (26, 26), 3: (29, 29), 4: (32, 32), 5: (35, 35),
        6: (40, 40), 7: (45, 45), 8: (51, 51), 9: (57, 57), 10: (64, 64),
        11: (72, 72), 12: (80, 80), 13: (84, 84), 14: (88, 88), 15: (92, 92),
        16: (96, 96), 17: (100, 100), 18: (104, 104), 19: (108, 108), 20: (112, 112),
    },
    "Range Combat Arts": {
        1: (25, 25), 2: (31, 33), 3: (32, 36), 4: (33, 39), 5: (34, 42),
        6: (36, 45), 7: (38, 48), 8: (41, 52), 9: (44, 56), 10: (47, 60),
        11: (51, 65), 12: (55, 70), 13: (59, 75), 14: (63, 80), 15: (67, 85),
        16: (71, 90), 17: (75, 95), 18: (79, 100), 19: (83, 105), 20: (87, 110),
    },
    "White Magic": {
        1: (25, 25), 2: (33, 26), 3: (36, 27), 4: (39, 29), 5: (42, 31),
        6: (45, 34), 7: (48, 37), 8: (52, 41), 9: (56, 45), 10: (60, 50),
        11: (65, 55), 12: (70, 60), 13: (74, 64), 14: (78, 68), 15: (82, 72),
        16: (86, 76), 17: (90, 80), 18: (94, 84), 19: (98, 88), 20: (102, 92),
    },
    "Black Magic": {
        1: (25, 25), 2: (26, 26), 3: (28, 27), 4: (31, 29), 5: (35, 31),
        6: (40, 34), 7: (46, 37), 8: (54, 41), 9: (62, 45), 10: (72, 50),
        11: (83, 55), 12: (95, 60), 13: (99, 64), 14: (103, 68), 15: (107, 72),
        16: (111, 76), 17: (115, 80), 18: (119, 84), 19: (123, 88), 20: (127, 92),
    },
    "Elemental Magic": {
        1: (25, 25), 2: (26, 26), 3: (29, 29), 4: (32, 32), 5: (35, 35),
        6: (40, 40), 7: (45, 45), 8: (51, 51), 9: (57, 57), 10: (64, 64),
        11: (72, 72), 12: (80, 80), 13: (84, 84), 14: (88, 88), 15: (92, 92),
        16: (96, 96), 17: (100, 100), 18: (104, 104), 19: (108, 108), 20: (112, 112),
    },
    "Mind Magic": {
        1: (25, 25), 2: (26, 26), 3: (28, 28), 4: (30, 31), 5: (33, 35),
        6: (37, 40), 7: (40, 46), 8: (45, 54), 9: (50, 62), 10: (56, 72),
        11: (62, 83), 12: (70, 95), 13: (74, 99), 14: (78, 103), 15: (82, 107),
        16: (86, 111), 17: (90, 115), 18: (94, 119), 19: (98, 123), 20: (102, 127),
    },
}

# Discrete tiers where major spell scrolls or major abilities unlock
DISCRETE_SPELL_TIERS: Tuple[int, ...] = (1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20)

