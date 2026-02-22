"""
Evolution loop: grow a population of entities via mutation and crossover.
Selection is art-time: we favor variety and "cool" (flavor, keyword richness).
"""
import random
from typing import Callable, List, TypeVar

from evolve_4e.entities import Monster, Power, MagicItem, Relic
from evolve_4e.dnd4e_math import level_math, MONSTER_ROLES, ORIGINS, KEYWORDS_MONSTER
from evolve_4e.mutate import (
    mutate_monster,
    crossover_monsters,
    mutate_power,
    crossover_powers,
    mutate_magic_item,
    crossover_magic_items,
    mutate_relic,
    crossover_relics,
)
from evolve_4e.names import (
    random_monster_name,
    random_power_name,
    random_item_name,
    FLAVOR_MONSTER,
    FLAVOR_POWER,
    FLAVOR_ITEM,
)
from evolve_4e.dnd4e_math import POWER_SOURCES, POWER_TYPES, ITEM_SLOTS, RELIC_THEMES

T = TypeVar("T")


def _score_monster(m: Monster) -> float:
    """Higher = cooler. Flavor, keyword count, role diversity."""
    s = 0.0
    if m.flavor:
        s += 0.5
    s += 0.1 * len(m.keywords)
    s += 0.1 * (len(m.at_will) + len(m.encounter) + len(m.daily))
    s += 0.05 * (m.level / 30.0)
    return s + random.random() * 0.3  # noise for variety


def _score_power(p: Power) -> float:
    if p.flavor:
        return 0.5 + 0.1 * len(p.keywords) + random.random() * 0.3
    return 0.1 * len(p.keywords) + random.random() * 0.3


def _score_item(i: MagicItem) -> float:
    if i.flavor or i.property:
        return 0.5 + random.random() * 0.3
    return random.random() * 0.3


def _score_relic(r: Relic) -> float:
    if r.concordance or r.discordance:
        return 0.5 + 0.1 * (len(r.concordance) + len(r.discordance)) + random.random() * 0.3
    return random.random() * 0.3


def _pick_many(rng: random.Random, pool: tuple, k: int) -> List[str]:
    pool_list = list(pool)
    n = rng.randint(0, min(k, len(pool_list)))
    return rng.sample(pool_list, n) if n else []


def _evolve_generations(
    rng: random.Random,
    initial: List[T],
    mutate_fn: Callable[[T, random.Random, float], T],
    crossover_fn: Callable[[T, T, random.Random], T],
    score_fn: Callable[[T], float],
    generations: int,
    population_size: int,
    mutation_strength: float = 1.0,
) -> List[T]:
    """Run a small GA: mutate and crossover, keep population_size, biased by score."""
    pop = list(initial)
    while len(pop) < population_size:
        pop.append(mutate_fn(rng.choice(pop), rng, mutation_strength))
    pop = pop[:population_size]

    for _ in range(generations - 1):
        scored = [(score_fn(e), e) for e in pop]
        scored.sort(key=lambda x: -x[0])
        # Keep top half + offspring
        keep = [e for _, e in scored[: population_size // 2]]
        while len(keep) < population_size:
            if rng.random() < 0.6 and len(keep) >= 2:
                a, b = rng.sample(keep, 2)
                child = crossover_fn(a, b, rng)
                keep.append(child)
            else:
                parent = rng.choice(keep)
                keep.append(mutate_fn(parent, rng, mutation_strength))
        pop = keep[:population_size]

    return pop


def _seed_monsters(rng: random.Random, n: int) -> List[Monster]:
    monsters = []
    for _ in range(n):
        level = rng.randint(1, 15)
        role = rng.choice(MONSTER_ROLES)
        origin = rng.choice(ORIGINS)
        keywords = list(_pick_many(rng, KEYWORDS_MONSTER, rng.randint(1, 4)))
        math = level_math(level, role)
        monsters.append(
            Monster(
                name=random_monster_name(rng),
                level=level,
                role=role,
                origin=origin,
                keywords=keywords,
                ac=math.ac,
                fort=math.fort,
                ref=math.ref,
                will=math.will,
                hp=math.hp,
                at_will=["Basic melee or ranged attack"],
                encounter=[],
                daily=[],
                flavor=rng.choice(FLAVOR_MONSTER) if rng.random() < 0.6 else "",
            )
        )
    return monsters


def _seed_powers(rng: random.Random, n: int) -> List[Power]:
    from evolve_4e.dnd4e_math import damage_expression, attack_vs_defense
    from evolve_4e.dnd4e_math import KEYWORDS_POWER

    powers = []
    for _ in range(n):
        level = rng.randint(1, 20)
        power_type = rng.choice(POWER_TYPES)
        source = rng.choice(POWER_SOURCES)
        keywords = list(_pick_many(rng, KEYWORDS_POWER, rng.randint(0, 3)))
        damage = damage_expression(level, "standard")
        attack_bonus = attack_vs_defense(level, "AC")
        powers.append(
            Power(
                name=random_power_name(rng),
                level=level,
                power_type=power_type,
                kind="attack",
                source=source,
                keywords=keywords,
                action="standard",
                range=rng.choice(["melee 1", "melee 2", "ranged 10", "close burst 3"]),
                target=rng.choice(["one creature", "one or two creatures", "each enemy in burst"]),
                attack=f"+{attack_bonus} vs AC",
                hit_damage=damage,
                hit_effect="",
                flavor=rng.choice(FLAVOR_POWER) if rng.random() < 0.5 else "",
            )
        )
    return powers


def _seed_items(rng: random.Random, n: int) -> List[MagicItem]:
    items = []
    for _ in range(n):
        level = rng.randint(1, 20)
        items.append(
            MagicItem(
                name=random_item_name(rng),
                level=level,
                slot=rng.choice(ITEM_SLOTS),
                property="",
                power_use="encounter" if rng.random() < 0.5 else "",
                power_text="",
                flavor=rng.choice(FLAVOR_ITEM) if rng.random() < 0.5 else "",
            )
        )
    return items


def _seed_relics(rng: random.Random, n: int) -> List[Relic]:
    relics = []
    for _ in range(n):
        level = rng.randint(15, 28)
        relics.append(
            Relic(
                name=random_item_name(rng),
                level=level,
                theme=rng.choice(RELIC_THEMES),
                property="",
                purpose="",
                concordance=["Grant a boon when concordance is high"] if rng.random() < 0.6 else [],
                discordance=["Punishment when discordance is low"] if rng.random() < 0.5 else [],
                flavor="",
            )
        )
    return relics


class Evolver:
    """Configurable evolver: seed, generations, population size."""

    def __init__(self, seed: int = 42, generations: int = 5, population_size: int = 20):
        self.rng = random.Random(seed)
        self.generations = generations
        self.population_size = population_size

    def evolve_monsters(self, n: int = 5) -> List[Monster]:
        initial = _seed_monsters(self.rng, max(2, self.population_size // 2))
        pop = _evolve_generations(
            self.rng,
            initial,
            mutate_monster,
            crossover_monsters,
            _score_monster,
            self.generations,
            self.population_size,
        )
        scored = [( _score_monster(e), e) for e in pop]
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:n]]

    def evolve_powers(self, n: int = 5) -> List[Power]:
        initial = _seed_powers(self.rng, max(2, self.population_size // 2))
        pop = _evolve_generations(
            self.rng,
            initial,
            mutate_power,
            crossover_powers,
            _score_power,
            self.generations,
            self.population_size,
        )
        scored = [(_score_power(e), e) for e in pop]
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:n]]

    def evolve_items(self, n: int = 5) -> List[MagicItem]:
        initial = _seed_items(self.rng, max(2, self.population_size // 2))
        pop = _evolve_generations(
            self.rng,
            initial,
            mutate_magic_item,
            crossover_magic_items,
            _score_item,
            self.generations,
            self.population_size,
        )
        scored = [(_score_item(e), e) for e in pop]
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:n]]

    def evolve_relics(self, n: int = 3) -> List[Relic]:
        initial = _seed_relics(self.rng, max(2, min(8, self.population_size // 2)))
        pop = _evolve_generations(
            self.rng,
            initial,
            mutate_relic,
            crossover_relics,
            _score_relic,
            self.generations,
            min(self.population_size, 12),
        )
        scored = [(_score_relic(e), e) for e in pop]
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:n]]


def evolve_monsters(seed: int = 42, n: int = 5, generations: int = 5) -> List[Monster]:
    return Evolver(seed=seed, generations=generations).evolve_monsters(n)


def evolve_powers(seed: int = 42, n: int = 5, generations: int = 5) -> List[Power]:
    return Evolver(seed=seed, generations=generations).evolve_powers(n)


def evolve_items(seed: int = 42, n: int = 5, generations: int = 5) -> List[MagicItem]:
    return Evolver(seed=seed, generations=generations).evolve_items(n)


def evolve_relics(seed: int = 42, n: int = 3, generations: int = 5) -> List[Relic]:
    return Evolver(seed=seed, generations=generations).evolve_relics(n)
