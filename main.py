import argparse
import json
import math
import os
import random
import time
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TextIO, Tuple

SEED = 42
SOUP_SIZE = 1024
DNA_LENGTH = 32
MAX_STEPS_PER_TURN = 64
MAX_GRANTED_STEPS = 12
TARGET_INTERACTIONS = 10_000_000

# Correlated cooperation gate for symbiogenesis.
COOP_WINDOW = 50
COOP_THRESHOLD = 8
MERGE_CHANCE = 0.35

INSTRUCTIONS = {
    0x01: "ROLL_D20",
    0x02: "TARGET_DEFENSE",
    0x03: "SIPHON_HP",
    0x04: "HEAL_SURGE",
    0x05: "SECOND_WIND",
    0x06: "MARK_TARGET",
    0x07: "PUSH_PULL",
    0x08: "BLOODIED_TRIGGER",
    0x09: "GRANT_ACTION",
    0x0A: "SYMBIO_MERGE",
    0x0B: "SIGNAL_SIGNALHOOD",
    0x0C: "REPLICATE",
    0x0D: "ACTION_POINT",
    0x0E: "REST",
}
DNA_BYTES = list(INSTRUCTIONS.keys())
ROLE_OPCODE_GROUPS = {
    "striker": {0x01, 0x02, 0x03, 0x07},
    "defender": {0x04, 0x05, 0x06, 0x08, 0x0E},
    "leader": {0x09, 0x0A, 0x0B, 0x0D},
}


@dataclass
class Entity:
    entity_id: int
    rng: random.Random
    dna: Optional[List[int]] = None
    max_hp: int = field(init=False)
    hp: int = field(init=False)
    surges_max: int = field(init=False)
    surges: int = field(init=False)
    str_mod: int = field(init=False)
    defenses: Dict[str, int] = field(init=False)
    second_wind_turns: int = 0
    marked_by: Optional[int] = None
    mark_turns: int = 0
    signal: Optional[int] = None
    action_points: int = 1

    def __post_init__(self) -> None:
        self.max_hp = self.rng.randint(24, 40)
        self.hp = self.max_hp
        self.surges_max = self.rng.randint(4, 8)
        self.surges = self.surges_max
        self.str_mod = self.rng.randint(0, 4)
        self.defenses = {
            "ac": 10 + self.rng.randint(0, 5),
            "fort": 10 + self.rng.randint(0, 5),
            "ref": 10 + self.rng.randint(0, 5),
            "will": 10 + self.rng.randint(0, 5),
        }
        if self.dna is None:
            self.dna = [self.rng.choice(DNA_BYTES) for _ in range(DNA_LENGTH)]

    @property
    def is_bloodied(self) -> bool:
        return self.hp <= (self.max_hp // 2)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def effective_defense(self, defense_name: str, distance: int) -> int:
        base = self.defenses[defense_name]
        if self.second_wind_turns > 0:
            base += 2
        # Distance acts as a simple niche-overlap penalty bonus.
        return base + max(0, distance - 1)

    def upkeep(self) -> None:
        if self.second_wind_turns > 0:
            self.second_wind_turns -= 1
        if self.mark_turns > 0:
            self.mark_turns -= 1
            if self.mark_turns == 0:
                self.marked_by = None


class E3Simulation:
    def __init__(self, seed: int = SEED, soup_size: int = SOUP_SIZE) -> None:
        self.rng = random.Random(seed)
        self.interaction_count = 0
        self.operation_count = 0
        self.total_merges = 0
        self.total_replications = 0
        self.total_cooperations = 0
        self.total_grants = 0
        self.total_bloodied_checks = 0
        self.total_bloodied_jumps = 0
        self.next_entity_id = 0
        self.soup = [self._new_entity() for _ in range(soup_size)]
        # Directed cooperation memory: (a, b) -> list of interaction indices.
        self.coop_memory: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        self.artifact_dir: Optional[str] = None
        self.snapshot_dir: Optional[str] = None
        self.snapshot_top_n = 16
        self.snapshot_sample_n = 48
        self.events_file: Optional[TextIO] = None

    def configure_observability(
        self,
        artifact_dir: str,
        snapshot_top_n: int = 16,
        snapshot_sample_n: int = 48,
    ) -> None:
        self.artifact_dir = artifact_dir
        self.snapshot_dir = os.path.join(artifact_dir, "snapshots")
        self.snapshot_top_n = max(1, snapshot_top_n)
        self.snapshot_sample_n = max(0, snapshot_sample_n)
        os.makedirs(self.snapshot_dir, exist_ok=True)
        events_path = os.path.join(artifact_dir, "events.jsonl")
        self.events_file = open(events_path, "w", encoding="utf-8")

    def close(self) -> None:
        if self.events_file:
            self.events_file.close()
            self.events_file = None

    def _new_entity(self, dna: Optional[List[int]] = None) -> Entity:
        entity = Entity(entity_id=self.next_entity_id, rng=self.rng, dna=dna)
        self.next_entity_id += 1
        return entity

    def _record_cooperation(self, actor: Entity, target: Entity) -> None:
        self.total_cooperations += 1
        key = (actor.entity_id, target.entity_id)
        history = self.coop_memory[key]
        history.append(self.interaction_count)
        cutoff = self.interaction_count - COOP_WINDOW
        while history and history[0] < cutoff:
            history.pop(0)

    def _mutual_coop_score(self, a: Entity, b: Entity) -> int:
        ab = len(self.coop_memory[(a.entity_id, b.entity_id)])
        ba = len(self.coop_memory[(b.entity_id, a.entity_id)])
        return min(ab, ba)

    def _merge_entities(self, a: Entity, b: Entity) -> Entity:
        split_a = len(a.dna) // 2
        split_b = len(b.dna) // 2
        merged_dna = a.dna[:split_a] + b.dna[split_b:]
        if len(merged_dna) < DNA_LENGTH:
            merged_dna.extend(self.rng.choice(DNA_BYTES) for _ in range(DNA_LENGTH - len(merged_dna)))
        merged_dna = merged_dna[:DNA_LENGTH]
        child = self._new_entity(dna=merged_dna)
        child.max_hp = min(70, (a.max_hp + b.max_hp) // 2 + 6)
        child.hp = min(child.max_hp, max(1, (a.hp + b.hp) // 2))
        child.surges_max = min(12, max(2, (a.surges_max + b.surges_max) // 2 + 1))
        child.surges = min(child.surges_max, max(1, (a.surges + b.surges) // 2))
        child.str_mod = min(6, max(a.str_mod, b.str_mod))
        child.defenses = {
            k: min(20, max(a.defenses[k], b.defenses[k]) + 1) for k in a.defenses
        }
        return child

    def _classify_role(self, entity: Entity) -> str:
        role_scores = {
            role: sum(1 for opcode in entity.dna if opcode in opcodes)
            for role, opcodes in ROLE_OPCODE_GROUPS.items()
        }
        total_role_opcodes = sum(role_scores.values())
        if total_role_opcodes == 0:
            return "hybrid"
        top_role = max(role_scores, key=role_scores.get)
        dominance = role_scores[top_role] / total_role_opcodes
        if dominance < 0.45:
            return "hybrid"
        return top_role

    def _entity_coop_score(self, entity_id: int) -> int:
        score = 0
        for (a_id, b_id), history in self.coop_memory.items():
            if a_id == entity_id or b_id == entity_id:
                score += len(history)
        return score

    def _entity_motifs(self, entity: Entity, coop_score: int) -> Dict[str, bool]:
        counts = Counter(entity.dna)
        return {
            "unkillable_loop_signature": (
                counts[0x08] >= 1 and counts[0x0D] >= 1 and counts[0x04] >= 2
            ),
            "signal_convention_signature": counts[0x0B] >= 3,
            "parasitic_signature": counts[0x0C] >= 3 and counts[0x03] <= 1 and counts[0x04] <= 1,
            "merge_ready_signature": counts[0x0A] >= 2 and coop_score >= COOP_THRESHOLD,
            "orchestrator_signature": counts[0x09] >= 2 and counts[0x0B] >= 2,
            "fortress_signature": (counts[0x04] + counts[0x05] + counts[0x06] + counts[0x0E]) >= 8,
            "burst_predator_signature": (counts[0x01] + counts[0x02] + counts[0x03] + counts[0x0D]) >= 8,
        }

    def _entity_score(self, entity: Entity, coop_score: int) -> float:
        hp_term = entity.hp / max(1, entity.max_hp)
        surge_term = entity.surges / max(1, entity.surges_max)
        role = self._classify_role(entity)
        role_bonus = 0.2 if role != "hybrid" else 0.0
        return hp_term + surge_term + (0.03 * coop_score) + role_bonus

    def _dna_tokens(self, dna: List[int]) -> List[str]:
        return [f"0x{opcode:02X}:{INSTRUCTIONS.get(opcode, 'UNKNOWN')}" for opcode in dna]

    def _log_event(self, event_type: str, payload: Dict[str, object]) -> None:
        if not self.events_file:
            return
        event = {
            "interaction": self.interaction_count,
            "event_type": event_type,
            **payload,
        }
        self.events_file.write(json.dumps(event) + "\n")

    def write_genome_snapshot(self, metrics: Dict[str, float], tag: str = "checkpoint") -> None:
        if not self.snapshot_dir:
            return
        entities = list(self.soup)
        coop_scores = {entity.entity_id: self._entity_coop_score(entity.entity_id) for entity in entities}
        scored = sorted(
            entities,
            key=lambda e: self._entity_score(e, coop_scores[e.entity_id]),
            reverse=True,
        )
        top_entities = scored[: self.snapshot_top_n]
        remaining = [entity for entity in entities if entity not in top_entities]
        sample_count = min(self.snapshot_sample_n, len(remaining))
        sampled_entities = self.rng.sample(remaining, sample_count) if sample_count > 0 else []
        selected = top_entities + sampled_entities

        role_counts = Counter(self._classify_role(entity) for entity in entities)
        dna_counts = Counter(tuple(entity.dna) for entity in entities)
        dominant_dna_count = max(dna_counts.values()) if dna_counts else 0
        dominant_dna_share = dominant_dna_count / len(entities) if entities else 0.0
        motif_counts = Counter()
        selected_payload = []
        for entity in selected:
            coop_score = coop_scores[entity.entity_id]
            motifs = self._entity_motifs(entity, coop_score)
            motif_counts.update(name for name, present in motifs.items() if present)
            selected_payload.append(
                {
                    "entity_id": entity.entity_id,
                    "role": self._classify_role(entity),
                    "hp": entity.hp,
                    "max_hp": entity.max_hp,
                    "surges": entity.surges,
                    "surges_max": entity.surges_max,
                    "defenses": entity.defenses,
                    "signal": entity.signal,
                    "coop_score": coop_score,
                    "dna": entity.dna,
                    "dna_tokens": self._dna_tokens(entity.dna),
                    "motifs": motifs,
                    "score": round(self._entity_score(entity, coop_score), 4),
                }
            )

        discoveries: List[str] = []
        if dominant_dna_share > 0.6:
            discoveries.append("Genome monoculture detected: one DNA dominates over 60% of the soup.")
        if metrics.get("signal_convention_strength", 0.0) > 0.35:
            discoveries.append("Strong social convention detected: one signal byte appears widely shared.")
        if metrics.get("merge_rate", 0.0) > 0.002:
            discoveries.append("Merge wave active: symbiogenesis is currently frequent.")
        if metrics.get("grant_rate", 0.0) > 0.05:
            discoveries.append("Coordination spike: entities frequently grant immediate peer actions.")
        if motif_counts["unkillable_loop_signature"] > 0:
            discoveries.append("Potential unkillable-loop genomes observed in sampled entities.")
        if motif_counts["parasitic_signature"] > 0:
            discoveries.append("Parasitic replicator-like genomes detected in sampled entities.")

        snapshot = {
            "tag": tag,
            "interaction": self.interaction_count,
            "metrics": metrics,
            "population_summary": {
                "size": len(entities),
                "role_counts": dict(role_counts),
                "dominant_dna_share": dominant_dna_share,
                "top_sampled_motifs": dict(motif_counts),
                "discoveries": discoveries,
            },
            "selected_entities": selected_payload,
        }
        filename = f"{tag}_{self.interaction_count:012d}.json"
        path = os.path.join(self.snapshot_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

    def _prune_all_coop_memory(self) -> None:
        cutoff = self.interaction_count - COOP_WINDOW
        stale_keys = []
        for key, history in self.coop_memory.items():
            while history and history[0] < cutoff:
                history.pop(0)
            if not history:
                stale_keys.append(key)
        for key in stale_keys:
            del self.coop_memory[key]

    def collect_metrics(self) -> Dict[str, float]:
        zip_size = self.get_complexity()
        ops_density = self.ops_per_interaction()

        role_counts = {"striker": 0, "defender": 0, "leader": 0, "hybrid": 0}
        dna_signatures = set()
        opcode_counts = defaultdict(int)
        replicate_specialists = 0
        hp_ratio_sum = 0.0
        signal_counts = defaultdict(int)

        for entity in self.soup:
            role_counts[self._classify_role(entity)] += 1
            signature = tuple(entity.dna)
            dna_signatures.add(signature)
            hp_ratio_sum += entity.hp / max(1, entity.max_hp)
            if entity.signal is not None:
                signal_counts[entity.signal] += 1
            replicate_count = sum(1 for op in entity.dna if op == 0x0C)
            if replicate_count >= 3:
                replicate_specialists += 1
            for opcode in entity.dna:
                opcode_counts[opcode] += 1

        soup_size = len(self.soup)
        role_entropy = 0.0
        for count in role_counts.values():
            if count > 0:
                p = count / soup_size
                role_entropy -= p * math.log2(p)

        total_opcodes = sum(opcode_counts.values())
        opcode_entropy = 0.0
        if total_opcodes > 0:
            for count in opcode_counts.values():
                p = count / total_opcodes
                opcode_entropy -= p * math.log2(p)

        self._prune_all_coop_memory()
        undirected_pairs = set()
        mutual_pairs = 0
        for a_id, b_id in self.coop_memory:
            pair = (min(a_id, b_id), max(a_id, b_id))
            undirected_pairs.add(pair)
        for a_id, b_id in undirected_pairs:
            if (a_id, b_id) in self.coop_memory and (b_id, a_id) in self.coop_memory:
                mutual_pairs += 1
        cooperation_index = (mutual_pairs / len(undirected_pairs)) if undirected_pairs else 0.0

        dominant_signal_ratio = 0.0
        if signal_counts:
            dominant_signal_ratio = max(signal_counts.values()) / soup_size

        return {
            "interaction": float(self.interaction_count),
            "zip_size": float(zip_size),
            "ops_per_interaction": float(ops_density),
            "merge_rate": self.total_merges / max(1, self.interaction_count),
            "replication_rate": self.total_replications / max(1, self.interaction_count),
            "cooperation_index": cooperation_index,
            "bloodied_branch_rate": self.total_bloodied_jumps / max(1, self.total_bloodied_checks),
            "mean_hp_ratio": hp_ratio_sum / soup_size,
            "genotype_diversity": len(dna_signatures) / soup_size,
            "opcode_entropy": opcode_entropy,
            "role_entropy": role_entropy,
            "striker_frac": role_counts["striker"] / soup_size,
            "defender_frac": role_counts["defender"] / soup_size,
            "leader_frac": role_counts["leader"] / soup_size,
            "hybrid_frac": role_counts["hybrid"] / soup_size,
            "replicator_frac": replicate_specialists / soup_size,
            "signal_convention_strength": dominant_signal_ratio,
            "grant_rate": self.total_grants / max(1, self.interaction_count),
        }

    def _execute_turn(
        self,
        actor: Entity,
        target: Entity,
        distance: int,
        max_steps: int = MAX_STEPS_PER_TURN,
        allow_grant_action: bool = True,
    ) -> Dict[str, object]:
        stack: List[int] = []
        ip = 0
        steps = 0
        replicate = False
        merge_requested = False

        while steps < max_steps and actor.alive and target.alive and ip < len(actor.dna):
            byte = actor.dna[ip]
            instr = INSTRUCTIONS.get(byte)
            self.operation_count += 1
            steps += 1

            if instr == "ROLL_D20":
                stack.append(self.rng.randint(1, 20))

            elif instr == "TARGET_DEFENSE":
                roll = stack.pop() if stack else 0
                selector = stack.pop() % 4 if stack else 0
                defense_name = ("ac", "fort", "ref", "will")[selector]
                defense_value = target.effective_defense(defense_name, distance)
                stack.append(1 if roll >= defense_value else 0)

            elif instr == "SIPHON_HP":
                # Signal-mediated de-escalation: infer peer intent and skip aggression.
                if target.signal == 0x03:
                    self._record_cooperation(actor, target)
                elif stack and stack.pop() == 1:
                    damage = self.rng.randint(1, 6) + actor.str_mod
                    if actor.marked_by is not None and actor.marked_by != target.entity_id:
                        damage = max(0, damage - 2)
                    drained = min(damage, target.hp)
                    target.hp -= drained
                    actor.hp = min(actor.max_hp + 15, actor.hp + drained)

            elif instr == "HEAL_SURGE":
                # Canonical homeostasis primitive: spend surge to heal 25% max HP.
                if actor.surges > 0:
                    actor.surges -= 1
                    actor.hp = min(actor.max_hp, actor.hp + max(1, actor.max_hp // 4))

            elif instr == "SECOND_WIND":
                actor.second_wind_turns = 1

            elif instr == "MARK_TARGET":
                target.marked_by = actor.entity_id
                target.mark_turns = 1

            elif instr == "PUSH_PULL":
                delta = -1 if (stack and stack.pop() % 2 == 0) else 1
                distance = min(5, max(0, distance + delta))

            elif instr == "BLOODIED_TRIGGER":
                self.total_bloodied_checks += 1
                if actor.is_bloodied:
                    self.total_bloodied_jumps += 1
                    jump_operand = actor.dna[(ip + 1) % len(actor.dna)]
                    ip = jump_operand % len(actor.dna)
                    continue

            elif instr == "GRANT_ACTION":
                # True immediate peer execution (parallel control-layer behavior).
                if allow_grant_action and actor.hp > 1:
                    self.total_grants += 1
                    actor.hp -= 1
                    self._record_cooperation(actor, target)
                    granted = self._execute_turn(
                        target,
                        actor,
                        distance,
                        max_steps=MAX_GRANTED_STEPS,
                        allow_grant_action=False,
                    )
                    if granted["replicate"]:
                        replicate = True
                    if granted["merge_requested"]:
                        merge_requested = True

            elif instr == "SYMBIO_MERGE":
                mutual_score = self._mutual_coop_score(actor, target)
                if mutual_score >= COOP_THRESHOLD and self.rng.random() < MERGE_CHANCE:
                    merge_requested = True

            elif instr == "SIGNAL_SIGNALHOOD":
                # Broadcast next byte as convention signal.
                actor.signal = actor.dna[(ip + 1) % len(actor.dna)]
                self._record_cooperation(actor, target)

            elif instr == "REPLICATE":
                if actor.hp > 15:
                    actor.hp -= 15
                    replicate = True

            elif instr == "ACTION_POINT":
                if actor.action_points > 0:
                    actor.action_points -= 1
                    ip = 0
                    continue

            elif instr == "REST":
                actor.surges = min(actor.surges_max, actor.surges + 1)

            ip += 1

        return {
            "replicate": replicate,
            "merge_requested": merge_requested,
            "distance": distance,
        }

    def run_interaction(self) -> None:
        a, b = self.rng.sample(self.soup, 2)
        self.interaction_count += 1
        distance = self.rng.randint(0, 2)
        respawn_ids: List[int] = []

        result_a = self._execute_turn(a, b, distance)
        result_b = self._execute_turn(b, a, result_a["distance"])

        if result_a["merge_requested"] or result_b["merge_requested"]:
            idx_a = self.soup.index(a)
            idx_b = self.soup.index(b)
            mutual_score = self._mutual_coop_score(a, b)
            if result_a["merge_requested"] and not result_b["merge_requested"]:
                merged = self._merge_entities(a, b)
                self.soup[idx_a] = merged
                self.total_merges += 1
                self._log_event(
                    "merge",
                    {
                        "initiator": "a",
                        "parent_a_id": a.entity_id,
                        "parent_b_id": b.entity_id,
                        "child_id": merged.entity_id,
                        "mutual_coop_score": mutual_score,
                    },
                )
            elif result_b["merge_requested"] and not result_a["merge_requested"]:
                merged = self._merge_entities(b, a)
                self.soup[idx_b] = merged
                self.total_merges += 1
                self._log_event(
                    "merge",
                    {
                        "initiator": "b",
                        "parent_a_id": b.entity_id,
                        "parent_b_id": a.entity_id,
                        "child_id": merged.entity_id,
                        "mutual_coop_score": mutual_score,
                    },
                )
            else:
                # If both request merge, choose one parent to preserve.
                if self.rng.random() < 0.5:
                    merged = self._merge_entities(a, b)
                    self.soup[idx_a] = merged
                    initiator = "both_a_kept"
                else:
                    merged = self._merge_entities(b, a)
                    self.soup[idx_b] = merged
                    initiator = "both_b_kept"
                self.total_merges += 1
                self._log_event(
                    "merge",
                    {
                        "initiator": initiator,
                        "parent_a_id": a.entity_id,
                        "parent_b_id": b.entity_id,
                        "child_id": merged.entity_id,
                        "mutual_coop_score": mutual_score,
                    },
                )
        else:
            if result_a["replicate"]:
                replace_idx = self.rng.randrange(len(self.soup))
                replaced = self.soup[replace_idx]
                child = self._new_entity(dna=list(a.dna))
                self.soup[replace_idx] = child
                self.total_replications += 1
                self._log_event(
                    "replicate",
                    {
                        "parent_id": a.entity_id,
                        "child_id": child.entity_id,
                        "replaced_entity_id": replaced.entity_id,
                    },
                )
            if result_b["replicate"]:
                replace_idx = self.rng.randrange(len(self.soup))
                replaced = self.soup[replace_idx]
                child = self._new_entity(dna=list(b.dna))
                self.soup[replace_idx] = child
                self.total_replications += 1
                self._log_event(
                    "replicate",
                    {
                        "parent_id": b.entity_id,
                        "child_id": child.entity_id,
                        "replaced_entity_id": replaced.entity_id,
                    },
                )

        for i, entity in enumerate(self.soup):
            if not entity.alive:
                respawn_ids.append(entity.entity_id)
                self.soup[i] = self._new_entity()
            else:
                entity.upkeep()
        if respawn_ids:
            self._log_event(
                "respawn_burst",
                {
                    "count": len(respawn_ids),
                    "sample_entity_ids": respawn_ids[:10],
                },
            )

    def get_complexity(self) -> int:
        all_dna = bytes(byte for entity in self.soup for byte in entity.dna)
        return len(zlib.compress(all_dna))

    def ops_per_interaction(self) -> float:
        if self.interaction_count == 0:
            return 0.0
        return self.operation_count / self.interaction_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E3 info-computational soup simulation.")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed for reproducible runs.")
    parser.add_argument(
        "--interactions",
        type=int,
        default=TARGET_INTERACTIONS,
        help="Number of pairwise interactions to simulate.",
    )
    parser.add_argument("--soup-size", type=int, default=SOUP_SIZE, help="Population size of the soup.")
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=100_000,
        help="How often to emit metrics checkpoints.",
    )
    parser.add_argument(
        "--metrics-csv",
        type=str,
        default="",
        help="Optional path to write checkpoint metrics as CSV.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=str,
        default="",
        help="Optional directory for genome snapshots and event logs.",
    )
    parser.add_argument(
        "--snapshot-every",
        type=int,
        default=100_000,
        help="Emit genome snapshot every N interactions (0 disables snapshots).",
    )
    parser.add_argument("--snapshot-top-n", type=int, default=16, help="Top entities saved per snapshot.")
    parser.add_argument(
        "--snapshot-sample-n",
        type=int,
        default=48,
        help="Random additional entities saved per snapshot.",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=int,
        default=15,
        help="Print lightweight progress heartbeat every N seconds (0 disables).",
    )
    args = parser.parse_args()

    sim = E3Simulation(seed=args.seed, soup_size=args.soup_size)
    if args.artifact_dir:
        os.makedirs(args.artifact_dir, exist_ok=True)
        sim.configure_observability(
            artifact_dir=args.artifact_dir,
            snapshot_top_n=args.snapshot_top_n,
            snapshot_sample_n=args.snapshot_sample_n,
        )
    print(f"Seed: {args.seed}")
    print(f"Initial Complexity: {sim.get_complexity()}")
    print(f"Configured Interactions: {args.interactions:,}")
    if args.artifact_dir:
        print(f"Artifact Directory: {args.artifact_dir}")
    if args.heartbeat_seconds > 0:
        print(f"Heartbeat: every {args.heartbeat_seconds}s")

    metrics_file: Optional[TextIO] = None
    if args.metrics_csv:
        metrics_file = open(args.metrics_csv, "w", encoding="utf-8")
        metrics_file.write(
            "interaction,zip_size,ops_per_interaction,merge_rate,replication_rate,cooperation_index,"
            "bloodied_branch_rate,mean_hp_ratio,genotype_diversity,opcode_entropy,role_entropy,"
            "striker_frac,defender_frac,leader_frac,hybrid_frac,replicator_frac,"
            "signal_convention_strength,grant_rate\n"
        )

    def emit_metrics(tag: str = "") -> Dict[str, float]:
        metrics = sim.collect_metrics()
        prefix = f"{tag} " if tag else ""
        print(
            f"{prefix}interaction={sim.interaction_count:,} "
            f"zip_size={int(metrics['zip_size'])} "
            f"ops_per_interaction={metrics['ops_per_interaction']:.4f} "
            f"merge_rate={metrics['merge_rate']:.5f} "
            f"cooperation_index={metrics['cooperation_index']:.4f} "
            f"role_entropy={metrics['role_entropy']:.4f} "
            f"genotype_diversity={metrics['genotype_diversity']:.4f}"
        )
        if metrics_file:
            metrics_file.write(
                f"{int(metrics['interaction'])},"
                f"{int(metrics['zip_size'])},"
                f"{metrics['ops_per_interaction']:.6f},"
                f"{metrics['merge_rate']:.8f},"
                f"{metrics['replication_rate']:.8f},"
                f"{metrics['cooperation_index']:.8f},"
                f"{metrics['bloodied_branch_rate']:.8f},"
                f"{metrics['mean_hp_ratio']:.8f},"
                f"{metrics['genotype_diversity']:.8f},"
                f"{metrics['opcode_entropy']:.8f},"
                f"{metrics['role_entropy']:.8f},"
                f"{metrics['striker_frac']:.8f},"
                f"{metrics['defender_frac']:.8f},"
                f"{metrics['leader_frac']:.8f},"
                f"{metrics['hybrid_frac']:.8f},"
                f"{metrics['replicator_frac']:.8f},"
                f"{metrics['signal_convention_strength']:.8f},"
                f"{metrics['grant_rate']:.8f}\n"
            )
        return metrics

    try:
        run_start = time.time()
        last_heartbeat = run_start
        for _ in range(args.interactions):
            sim.run_interaction()
            if args.heartbeat_seconds > 0:
                now = time.time()
                if now - last_heartbeat >= args.heartbeat_seconds:
                    elapsed = max(1e-9, now - run_start)
                    rate = sim.interaction_count / elapsed
                    print(
                        f"[heartbeat] interaction={sim.interaction_count:,} "
                        f"rate={rate:,.0f}/s elapsed={int(elapsed)}s"
                    )
                    last_heartbeat = now
            if args.checkpoint_every > 0 and sim.interaction_count % args.checkpoint_every == 0:
                metrics = emit_metrics(tag="[checkpoint]")
                if sim.snapshot_dir and args.snapshot_every > 0 and sim.interaction_count % args.snapshot_every == 0:
                    sim.write_genome_snapshot(metrics, tag="checkpoint")

        final_metrics = emit_metrics(tag="[final]")
        if sim.snapshot_dir and args.snapshot_every != 0:
            sim.write_genome_snapshot(final_metrics, tag="final")
    finally:
        if metrics_file:
            metrics_file.close()
        sim.close()


if __name__ == "__main__":
    main()