"""
Name parts and flavor snippets for generating cool entity names and text.
Art-time "cheat" tables so output feels cohesive and fun.
"""
import random
from typing import List, Tuple

# Monster name building blocks
MONSTER_PREFIXES = (
    "Ash", "Bone", "Cinder", "Dread", "Gloom", "Iron", "Shadow", "Thorn",
    "Void", "Warp", "Blight", "Frost", "Storm", "Venom", "Soul", "Rust",
    "Grim", "Wither", "Blight", "Hollow", "Rime", "Ember", "Chill", "Rotten",
)
MONSTER_CORES = (
    "Stalker", "Walker", "Shambler", "Hunter", "Reaver", "Warden", "Sentinel",
    "Titan", "Beast", "Horror", "Fiend", "Wraith", "Specter", "Devourer",
    "Scourge", "Herald", "Scion", "Spawn", "Child", "Lord", "Knight", "Maw",
    "Crawler", "Dancer", "Weaver", "Keeper", "Eater", "Drinker", "Binder",
)
MONSTER_SUFFIXES = (
    "", " of the Deep", " Eternal", " Unbound", " the Hungry", " the Fallen",
    " Ascendant", " Prime", " Ancient", " Forgotten", " Sundered",
)

# Power names
POWER_VERBS = (
    "Strike", "Smite", "Rend", "Sunder", "Cleave", "Lunge", "Surge", "Rush",
    "Grasp", "Crush", "Scatter", "Scorch", "Freeze", "Shock", "Blast", "Burst",
    "Stride", "Leap", "Fade", "Reap", "Harvest", "Consume", "Unmake", "Bind",
)
POWER_NOUNS = (
    "Steel", "Flame", "Shadow", "Light", "Thunder", "Ice", "Soul", "Blood",
    "Fate", "Doom", "Dawn", "Dusk", "Storm", "Void", "Chain", "Fang", "Claw",
)

# Item names
ITEM_ADJECTIVES = (
    "Vicious", "Serpentine", "Spectral", "Adamantine", "Phoenix", "Void-touched",
    "Thunder-forged", "Soul-drinker", "Frostbite", "Emberheart", "Shadow-weave",
)
ITEM_NOUNS = (
    "Blade", "Gauntlets", "Crown", "Cloak", "Amulet", "Ring", "Belt", "Boots",
    "Staff", "Orb", "Tome", "Shard", "Eye", "Heart", "Fang", "Scale",
)

# Flavor one-liners (short)
FLAVOR_MONSTER = (
    "It moves like smoke and strikes like iron.",
    "Where it walks, the light dies.",
    "Born in the deep places where the world forgets.",
    "Its hunger is older than the gods.",
    "The first of its kind, and the last.",
    "It remembers the world before the dawn war.",
    "Wounds close in its presence; so do throats.",
)
FLAVOR_POWER = (
    "You channel primal fury into a single blow.",
    "Shadow and steel become one.",
    "The strike leaves a trail of frost.",
    "Your weapon hums with stored lightning.",
)
FLAVOR_ITEM = (
    "Warm to the touch even in the coldest crypt.",
    "Whispers in a language no one living speaks.",
    "The gem at its center never stops bleeding.",
)


def random_monster_name(rng: random.Random) -> str:
    p = rng.choice(MONSTER_PREFIXES)
    c = rng.choice(MONSTER_CORES)
    s = rng.choice(MONSTER_SUFFIXES)
    return f"{p} {c}{s}".strip()


def random_power_name(rng: random.Random) -> str:
    v = rng.choice(POWER_VERBS)
    n = rng.choice(POWER_NOUNS)
    return f"{v} of {n}"


def random_item_name(rng: random.Random) -> str:
    adj = rng.choice(ITEM_ADJECTIVES)
    noun = rng.choice(ITEM_NOUNS)
    return f"{adj} {noun}"
