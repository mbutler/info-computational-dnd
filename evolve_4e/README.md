# Evolve 4e

A **simpler**, art-first system inspired by the E3 "Turing Gas" project. Here we **grow** D&D 4e entities—monsters, powers, magic items, relics—using the 4e rules as **primitive physics**.

- **Physics**: Level-based math (MM3-style): AC/Fort/Ref/Will, HP, damage expressions, attack bonuses. Roles (brute, soldier, lurker, etc.) and keywords shape the stats.
- **Evolution**: Small populations are **mutated** (level, role, keywords, flavor) and **crossed** (two monsters → one hybrid). Selection favors variety and flavor, not combat simulation.
- **Output**: Ready-to-use stat blocks and writeups you can drop into a game or document.

No simulation soup, no DNA tape VM—just **cool entities** that obey 4e scaling.

## Quick start

From the repo root:

```bash
python run_evolve.py
```

Defaults: 3 monsters, 3 powers, 2 magic items, 1 relic.

```bash
python run_evolve.py --monsters 5 --seed 123 --gen 8
python run_evolve.py --all 10
```

## Package layout

- `dnd4e_math.py` — Level scaling, roles, origins, keywords (the "physics").
- `entities.py` — `Monster`, `Power`, `MagicItem`, `Relic` dataclasses.
- `names.py` — Name parts and flavor snippets (the "cheat" tables).
- `mutate.py` — Mutation and crossover per entity type.
- `evolve.py` — Evolution loop and `Evolver`; seed generation.
- `format_block.py` — Pretty-print stat blocks.

## Using from code

```python
from evolve_4e import Evolver, format_monster, format_power

ev = Evolver(seed=42, generations=6)
for m in ev.evolve_monsters(5):
    print(format_monster(m))
```

You can also import `evolve_monsters`, `evolve_powers`, etc., or use the entity and mutation APIs directly to plug into your own pipelines.
