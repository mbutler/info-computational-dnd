#!/usr/bin/env python3
"""
Evolve 4e: grow D&D 4e monsters, powers, magic items, and relics.

Uses 4e rules as "physics" — level math, roles, keywords — and evolves
entities via mutation and crossover. Art-first: we favor cool, flavorful
output over simulation rigor.

Usage:
  python run_evolve.py                    # 3 monsters, 3 powers, 2 items, 1 relic
  python run_evolve.py --monsters 5       # 5 monsters only
  python run_evolve.py --seed 123 --gen 8  # different seed, more generations
  python run_evolve.py --all 10           # 10 of each entity type
"""
import argparse
import sys

# Run from repo root so evolve_4e package is found
sys.path.insert(0, ".")

from evolve_4e import Evolver, format_monster, format_power, format_magic_item, format_relic


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Evolve D&D 4e entities (monsters, powers, items, relics)."
    )
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--gen", type=int, default=5, help="Evolution generations")
    ap.add_argument("--monsters", type=int, default=0, help="Number of monsters to evolve")
    ap.add_argument("--powers", type=int, default=0, help="Number of powers to evolve")
    ap.add_argument("--items", type=int, default=0, help="Number of magic items to evolve")
    ap.add_argument("--relics", type=int, default=0, help="Number of relics to evolve")
    ap.add_argument(
        "--all",
        type=int,
        metavar="N",
        default=0,
        help="Evolve N of each type (overrides individual counts if set)",
    )
    args = ap.parse_args()

    n_monsters = args.monsters
    n_powers = args.powers
    n_items = args.items
    n_relics = args.relics
    if args.all > 0:
        n_monsters = n_powers = n_items = args.all
        n_relics = max(1, args.all // 2)

    if n_monsters == 0 and n_powers == 0 and n_items == 0 and n_relics == 0:
        n_monsters = 3
        n_powers = 3
        n_items = 2
        n_relics = 1

    ev = Evolver(seed=args.seed, generations=args.gen)

    if n_monsters > 0:
        print("\n" + "=" * 60)
        print(" EVOLVED MONSTERS")
        print("=" * 60)
        for m in ev.evolve_monsters(n_monsters):
            print(format_monster(m))
            print()

    if n_powers > 0:
        print("\n" + "=" * 60)
        print(" EVOLVED POWERS")
        print("=" * 60)
        for p in ev.evolve_powers(n_powers):
            print(format_power(p))
            print()

    if n_items > 0:
        print("\n" + "=" * 60)
        print(" EVOLVED MAGIC ITEMS")
        print("=" * 60)
        for i in ev.evolve_items(n_items):
            print(format_magic_item(i))
            print()

    if n_relics > 0:
        print("\n" + "=" * 60)
        print(" EVOLVED RELICS")
        print("=" * 60)
        for r in ev.evolve_relics(n_relics):
            print(format_relic(r))
            print()


if __name__ == "__main__":
    main()
