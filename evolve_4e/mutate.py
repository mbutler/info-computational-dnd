"""
Mutation and crossover for 4e entities.
Uses 4e rules as physics: mutations stay within plausible bounds, crossover blends two entities.
"""
import copy
import random
from typing import List, Optional, Tuple

from evolve_4e.entities import Monster, Power, MagicItem, Relic
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
from evolve_4e.names import (
    random_monster_name,
    random_power_name,
    random_item_name,
    FLAVOR_MONSTER,
    FLAVOR_POWER,
    FLAVOR_ITEM,
)


def _pick_many(rng: random.Random, pool: Tuple[str, ...], k: int, allow_empty: bool = True) -> List[str]:
    pool_list = list(pool)
    if allow_empty and k == 0:
        return []
    n = rng.randint(0 if allow_empty else 1, min(k, len(pool_list)))
    return rng.sample(pool_list, n)


# --- Monster ---
def mutate_monster(m: Monster, rng: random.Random, strength: float = 1.0) -> Monster:
    """In-place-ish: return a mutated copy. 4e math is reapplied when level/role change."""
    m = copy.deepcopy(m)
    if rng.random() < 0.4 * strength:
        m.level = max(1, min(30, m.level + rng.randint(-2, 2)))
    if rng.random() < 0.35 * strength:
        m.role = rng.choice(MONSTER_ROLES)
    if rng.random() < 0.3 * strength:
        m.origin = rng.choice(ORIGINS)
    if rng.random() < 0.5 * strength:
        # Add/remove one keyword
        if m.keywords and rng.random() < 0.4:
            m.keywords = [k for k in m.keywords if k != rng.choice(m.keywords)]
        else:
            new_k = rng.choice([k for k in KEYWORDS_MONSTER if k not in m.keywords])
            if new_k:
                m.keywords = list(m.keywords) + [new_k]
        m.keywords = list(dict.fromkeys(m.keywords))[:5]  # dedupe, cap 5
    if rng.random() < 0.25 * strength:
        m.name = random_monster_name(rng)
    if rng.random() < 0.2 * strength:
        m.flavor = rng.choice(FLAVOR_MONSTER)
    # Nudge stats slightly (art-time: allow small variance)
    if rng.random() < 0.4 * strength:
        m.ac = max(10, m.ac + rng.randint(-1, 1))
        m.fort = max(10, m.fort + rng.randint(-1, 1))
        m.ref = max(10, m.ref + rng.randint(-1, 1))
        m.will = max(10, m.will + rng.randint(-1, 1))
    if rng.random() < 0.3 * strength:
        m.hp = max(20, m.hp + rng.randint(-m.hp // 5, m.hp // 5))
    # Sync to math optionally (reign in drift)
    if rng.random() < 0.5:
        m.sync_to_math()
    return m


def crossover_monsters(a: Monster, b: Monster, rng: random.Random) -> Monster:
    """Blend two monsters into one (hybrid)."""
    level = (a.level + b.level) // 2
    level = max(1, min(30, level + rng.randint(-1, 1)))
    role = rng.choice([a.role, b.role])
    origin = rng.choice([a.origin, b.origin])
    keywords = list(dict.fromkeys(
        rng.sample(a.keywords + b.keywords, min(5, len(a.keywords) + len(b.keywords)))
        if (a.keywords or b.keywords) else []
    ))
    if not keywords:
        keywords = list(_pick_many(rng, KEYWORDS_MONSTER, 2))
    math = level_math(level, role)
    name = random_monster_name(rng)
    at_will = (a.at_will + b.at_will)[:3]
    encounter = (a.encounter + b.encounter)[:2]
    daily = (a.daily + b.daily)[:1]
    if not at_will:
        at_will = ["Basic melee or ranged attack"]
    flavor = rng.choice([a.flavor, b.flavor]) if (a.flavor or b.flavor) else rng.choice(FLAVOR_MONSTER)
    return Monster(
        name=name,
        level=level,
        role=role,
        origin=origin,
        keywords=keywords,
        ac=math.ac,
        fort=math.fort,
        ref=math.ref,
        will=math.will,
        hp=math.hp,
        at_will=at_will,
        encounter=encounter,
        daily=daily,
        traits=[],
        flavor=flavor,
    )


# --- Power ---
def _sync_power_math(p: Power) -> None:
    """Recompute attack and damage from level (4e physics)."""
    from evolve_4e.dnd4e_math import damage_expression, attack_vs_defense
    p.hit_damage = damage_expression(p.level, "standard")
    p.attack = f"+{attack_vs_defense(p.level, 'AC')} vs AC"


def mutate_power(p: Power, rng: random.Random, strength: float = 1.0) -> Power:
    p = copy.deepcopy(p)
    if rng.random() < 0.4 * strength:
        p.level = max(1, min(30, p.level + rng.randint(-2, 2)))
        _sync_power_math(p)
    if rng.random() < 0.3 * strength:
        p.power_type = rng.choice(POWER_TYPES)
    if rng.random() < 0.3 * strength:
        p.source = rng.choice(POWER_SOURCES)
    if rng.random() < 0.4 * strength:
        k = _pick_many(rng, KEYWORDS_POWER, 3)
        p.keywords = list(dict.fromkeys((p.keywords or []) + k))[:5]
    if rng.random() < 0.25 * strength:
        p.name = random_power_name(rng)
    if rng.random() < 0.2 * strength:
        p.flavor = rng.choice(FLAVOR_POWER)
    if rng.random() < 0.3:
        _sync_power_math(p)
    return p


def crossover_powers(a: Power, b: Power, rng: random.Random) -> Power:
    from evolve_4e.dnd4e_math import damage_expression, attack_vs_defense
    level = (a.level + b.level) // 2
    level = max(1, min(30, level))
    name = random_power_name(rng)
    power_type = rng.choice([a.power_type, b.power_type])
    kind = rng.choice([a.kind, b.kind])
    source = rng.choice([a.source, b.source])
    keywords = list(dict.fromkeys((a.keywords or []) + (b.keywords or [])))[:5]
    action = rng.choice([a.action, b.action])
    range_ = rng.choice([a.range, b.range])
    target = rng.choice([a.target, b.target])
    hit_damage = damage_expression(level, "standard")
    attack = f"+{attack_vs_defense(level, 'AC')} vs AC"
    hit_effect = rng.choice([a.hit_effect, b.hit_effect]) if (a.hit_effect or b.hit_effect) else ""
    return Power(
        name=name,
        level=level,
        power_type=power_type,
        kind=kind,
        source=source,
        keywords=keywords,
        action=action,
        range=range_,
        target=target,
        attack=attack,
        hit_damage=hit_damage,
        hit_effect=hit_effect,
        flavor=rng.choice([a.flavor, b.flavor]) if (a.flavor or b.flavor) else rng.choice(FLAVOR_POWER),
    )


# --- Magic item ---
def mutate_magic_item(item: MagicItem, rng: random.Random, strength: float = 1.0) -> MagicItem:
    item = copy.deepcopy(item)
    if rng.random() < 0.4 * strength:
        item.level = max(1, min(30, item.level + rng.randint(-2, 2)))
    if rng.random() < 0.3 * strength:
        item.slot = rng.choice(ITEM_SLOTS)
    if rng.random() < 0.25 * strength:
        item.name = random_item_name(rng)
    if rng.random() < 0.2 * strength:
        item.flavor = rng.choice(FLAVOR_ITEM)
    return item


def crossover_magic_items(a: MagicItem, b: MagicItem, rng: random.Random) -> MagicItem:
    level = (a.level + b.level) // 2
    level = max(1, min(30, level))
    return MagicItem(
        name=random_item_name(rng),
        level=level,
        slot=rng.choice([a.slot, b.slot]),
        property=a.property or b.property,
        power_use=rng.choice([a.power_use, b.power_use]) if (a.power_use or b.power_use) else "",
        power_text=a.power_text or b.power_text,
        flavor=rng.choice([a.flavor, b.flavor]) if (a.flavor or b.flavor) else rng.choice(FLAVOR_ITEM),
    )


# --- Relic ---
def mutate_relic(r: Relic, rng: random.Random, strength: float = 1.0) -> Relic:
    r = copy.deepcopy(r)
    if rng.random() < 0.4 * strength:
        r.level = max(15, min(30, r.level + rng.randint(-2, 2)))
    if rng.random() < 0.35 * strength:
        r.theme = rng.choice(RELIC_THEMES)
    if rng.random() < 0.25 * strength:
        r.name = random_item_name(rng)  # reuse item name style
    return r


def crossover_relics(a: Relic, b: Relic, rng: random.Random) -> Relic:
    level = (a.level + b.level) // 2
    level = max(15, min(30, level))
    return Relic(
        name=random_item_name(rng),
        level=level,
        theme=rng.choice([a.theme, b.theme]),
        property=a.property or b.property,
        purpose=a.purpose or b.purpose,
        concordance=a.concordance or b.concordance,
        discordance=a.discordance or b.discordance,
        flavor=rng.choice([a.flavor, b.flavor]) if (a.flavor or b.flavor) else "",
    )
