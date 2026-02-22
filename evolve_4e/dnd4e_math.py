"""
D&D 4e rules as "physics" for evolution.
Level-based scaling (MM3-style), roles, origins, keywords.
"""
from dataclasses import dataclass
from typing import List, Tuple

# --- Level scaling (MM3-ish) ---
def defense_ac(level: int, role: str = "standard") -> int:
    base = 14 + level
    if role == "soldier":
        return base + 2
    if role == "brute":
        return base - 1
    if role == "lurker" or role == "skirmisher":
        return base
    if role == "controller" or role == "artillery":
        return base - 1
    return base


def defense_other(level: int, stat: str, role: str = "standard") -> int:
    """Fort, Ref, Will: 12 + level, with role tweaks."""
    base = 12 + level
    if stat == "fort":
        if role == "brute":
            return base + 2
        if role == "soldier":
            return base + 1
    if stat == "ref":
        if role in ("lurker", "skirmisher"):
            return base + 2
        if role == "artillery":
            return base + 1
    if stat == "will":
        if role == "controller":
            return base + 2
        if role == "leader":
            return base + 1
    return base


def hp_per_level(role: str) -> int:
    """HP per level (× level, plus base)."""
    table = {
        "brute": 10,
        "soldier": 8,
        "standard": 8,
        "skirmisher": 6,
        "lurker": 6,
        "controller": 6,
        "artillery": 6,
        "leader": 8,
    }
    return table.get(role, 8)


def hp_base(role: str) -> int:
    """Base HP at level 1 (before adding level × hp_per_level)."""
    table = {
        "brute": 40,
        "soldier": 28,
        "standard": 28,
        "skirmisher": 24,
        "lurker": 24,
        "controller": 24,
        "artillery": 24,
        "leader": 28,
    }
    return table.get(role, 28)


def monster_hp(level: int, role: str) -> int:
    return hp_base(role) + level * hp_per_level(role)


def damage_expression(level: int, role: str = "standard", is_aoe: bool = False) -> str:
    """Rough damage dice + mod. Standard single-target ~ 8+level; brutes higher."""
    if is_aoe:
        # 6 + level*3/4 equivalent: smaller dice
        n = 1
        d = 6
        mod = level + 4
    else:
        mod = 8 + level
        if role == "brute":
            mod = int(mod * 1.35)
        if role == "artillery":
            mod = int(mod * 1.15)
        n = 2
        d = 6
    return f"{n}d{d}+{mod}"


def attack_vs_defense(level: int, vs: str = "AC") -> int:
    """Attack bonus vs defense (for power writeups). +5 at 1, +1/level."""
    base = 5 + level
    if vs in ("Ref", "Will"):
        base += 2
    elif vs == "Fort":
        base += 1
    return base


# --- Role / origin / keyword tables (for mutation and flavor) ---
MONSTER_ROLES = (
    "brute",
    "soldier",
    "lurker",
    "skirmisher",
    "controller",
    "artillery",
    "leader",
)

ORIGINS = (
    "natural",
    "elemental",
    "shadow",
    "fey",
    "immortal",
    "undead",
    "construct",
    "aberrant",
)

KEYWORDS_MONSTER = (
    "beast",
    "humanoid",
    "dragon",
    "demon",
    "devil",
    "elemental",
    "undead",
    "construct",
    "fey",
    "shadow",
    "reptile",
    "spider",
    "cold",
    "fire",
    "poison",
    "fear",
    "teleportation",
    "mount",
    "swarm",
)

POWER_SOURCES = ("arcane", "divine", "martial", "primal", "psionic", "shadow", "elemental")

POWER_TYPES = ("at-will", "encounter", "daily")
POWER_KINDS = ("attack", "utility")

KEYWORDS_POWER = (
    "acid",
    "augmentable",
    "aura",
    "beast",
    "charm",
    "cold",
    "fear",
    "fire",
    "force",
    "healing",
    "illusion",
    "implement",
    "lightning",
    "necrotic",
    "poison",
    "polymorph",
    "psychic",
    "radiant",
    "rage",
    "reliable",
    "spirit",
    "summoning",
    "teleportation",
    "thunder",
    "weapon",
    "zone",
)

ITEM_SLOTS = (
    "arms",
    "feet",
    "hands",
    "head",
    "neck",
    "ring",
    "waist",
    "weapon",
    "wondrous",
)

ITEM_CATEGORIES = ("weapon", "armor", "implement", "wondrous", "relic")

RELIC_THEMES = ("primordial", "divine", "arcane", "aberrant", "elemental", "shadow", "fey")


@dataclass
class LevelMath:
    """Precomputed 4e math for a given level and role."""
    level: int
    role: str
    ac: int
    fort: int
    ref: int
    will: int
    hp: int
    damage: str
    attack_ac: int
    attack_other: int

    @classmethod
    def for_monster(cls, level: int, role: str) -> "LevelMath":
        return cls(
            level=level,
            role=role,
            ac=defense_ac(level, role),
            fort=defense_other(level, "fort", role),
            ref=defense_other(level, "ref", role),
            will=defense_other(level, "will", role),
            hp=monster_hp(level, role),
            damage=damage_expression(level, role),
            attack_ac=attack_vs_defense(level, "AC"),
            attack_other=attack_vs_defense(level, "Ref"),
        )


def level_math(level: int, role: str = "standard") -> LevelMath:
    return LevelMath.for_monster(level, role)
