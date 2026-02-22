"""
D&D 4e entity types we can evolve: monsters, powers, magic items, relics.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from evolve_4e.dnd4e_math import (
    level_math,
    MONSTER_ROLES,
    ORIGINS,
    KEYWORDS_MONSTER,
    POWER_SOURCES,
    POWER_TYPES,
    KEYWORDS_POWER,
    ITEM_SLOTS,
    RELIC_THEMES,
)


class EntityKind(str, Enum):
    MONSTER = "monster"
    POWER = "power"
    MAGIC_ITEM = "magic_item"
    RELIC = "relic"


@dataclass
class Monster:
    """A 4e monster stat block (evolvable)."""
    name: str
    level: int
    role: str
    origin: str
    keywords: List[str]
    # Stats from 4e math (can be mutated slightly)
    ac: int
    fort: int
    ref: int
    will: int
    hp: int
    # Powers as short names; full text can be generated
    at_will: List[str] = field(default_factory=list)
    encounter: List[str] = field(default_factory=list)
    daily: List[str] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)
    # Flavor
    flavor: str = ""

    def __post_init__(self) -> None:
        if not self.at_will:
            self.at_will = ["Basic melee or ranged attack"]
        if self.role not in MONSTER_ROLES:
            self.role = "standard"
        if self.origin not in ORIGINS:
            self.origin = "natural"

    def sync_to_math(self) -> None:
        """Recompute stats from level/role (4e physics)."""
        m = level_math(self.level, self.role)
        self.ac = m.ac
        self.fort = m.fort
        self.ref = m.ref
        self.will = m.will
        self.hp = m.hp


@dataclass
class Power:
    """A 4e power (at-will, encounter, daily)."""
    name: str
    level: int
    power_type: str  # at-will, encounter, daily
    kind: str  # attack, utility
    source: str
    keywords: List[str]
    # Effect
    action: str  # standard, move, minor, free, immediate
    range: str  # melee 1, ranged 10, close burst 3, etc.
    target: str
    attack: str  # vs AC, vs Ref, etc.
    hit_damage: str  # 2d6+5, etc.
    hit_effect: str = ""
    miss_effect: str = ""
    effect_text: str = ""
    flavor: str = ""

    def __post_init__(self) -> None:
        if self.power_type not in POWER_TYPES:
            self.power_type = "at-will"
        if self.source not in POWER_SOURCES:
            self.source = "martial"


@dataclass
class MagicItem:
    """A 4e magic item."""
    name: str
    level: int
    slot: str
    property: str = ""
    power_use: str = ""  # encounter, daily, etc.
    power_text: str = ""
    flavor: str = ""


@dataclass
class Relic:
    """A 4e relic/artifact."""
    name: str
    level: int  # typically 15+
    theme: str
    property: str = ""
    purpose: str = ""
    concordance: List[str] = field(default_factory=list)
    discordance: List[str] = field(default_factory=list)
    flavor: str = ""
