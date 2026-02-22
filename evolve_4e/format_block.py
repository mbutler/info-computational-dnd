"""
Pretty-print 4e stat blocks and entity writeups.
"""
from typing import List

from evolve_4e.entities import Monster, Power, MagicItem, Relic


def format_monster(m: Monster) -> str:
    lines = [
        f"━━━ {m.name.upper()} ━━━",
        f"Level {m.level} {m.role.capitalize()} {m.origin.capitalize()}",
        "",
    ]
    if m.keywords:
        lines.append("Keywords: " + ", ".join(m.keywords))
        lines.append("")
    lines.append(f"HP {m.hp}; Bloodied {m.hp // 2}")
    lines.append(f"AC {m.ac}, Fort {m.fort}, Ref {m.ref}, Will {m.will}")
    lines.append("")
    if m.traits:
        for t in m.traits:
            lines.append(f"◆ {t}")
        lines.append("")
    lines.append("Standard actions")
    for a in m.at_will:
        lines.append(f"  At-Will: {a}")
    for e in m.encounter:
        lines.append(f"  Encounter: {e}")
    for d in m.daily:
        lines.append(f"  Daily: {d}")
    if m.flavor:
        lines.append("")
        lines.append(f"— {m.flavor}")
    return "\n".join(lines)


def format_power(p: Power) -> str:
    lines = [
        f"◆ {p.name} (Level {p.level})",
        f"{p.power_type.capitalize()} · {p.source.capitalize()} {p.kind.capitalize()}",
        "",
    ]
    if p.keywords:
        lines.append("Keywords: " + ", ".join(p.keywords))
        lines.append("")
    lines.append(f"Action: {p.action} | Range: {p.range}")
    lines.append(f"Target: {p.target}")
    lines.append(f"Attack: {p.attack}")
    lines.append(f"Hit: {p.hit_damage} damage. {p.hit_effect}".strip())
    if p.miss_effect:
        lines.append(f"Miss: {p.miss_effect}")
    if p.effect_text:
        lines.append(f"Effect: {p.effect_text}")
    if p.flavor:
        lines.append("")
        lines.append(f"— {p.flavor}")
    return "\n".join(lines)


def format_magic_item(i: MagicItem) -> str:
    lines = [
        f"◆ {i.name}",
        f"Level {i.level} · {i.slot.capitalize()}",
        "",
    ]
    if i.property:
        lines.append(f"Property: {i.property}")
    if i.power_use and i.power_text:
        lines.append(f"Power ({i.power_use}): {i.power_text}")
    if i.flavor:
        lines.append("")
        lines.append(f"— {i.flavor}")
    return "\n".join(lines)


def format_relic(r: Relic) -> str:
    lines = [
        f"◆ {r.name} (Relic)",
        f"Level {r.level} · {r.theme.capitalize()}",
        "",
    ]
    if r.property:
        lines.append(f"Property: {r.property}")
    if r.purpose:
        lines.append(f"Purpose: {r.purpose}")
    if r.concordance:
        lines.append("Concordance (high):")
        for c in r.concordance:
            lines.append(f"  · {c}")
    if r.discordance:
        lines.append("Discordance (low):")
        for d in r.discordance:
            lines.append(f"  · {d}")
    if r.flavor:
        lines.append("")
        lines.append(f"— {r.flavor}")
    return "\n".join(lines)
