# E3 D&D Turing Gas

This project is an **Entity-based Evolutionary Environment (E3)** inspired by D&D 4e mechanics.

Think of it like this:

- D&D-like rules are the **physics**.
- DNA tapes (opcode sequences) are the **genomes**.
- The population ("soup") evolves strategies, coordination, and mergers over millions of interactions.

The goal is to observe **emergence**: behaviors and structures not explicitly programmed as fixed classes.

## What This Runs

Each entity has:

- internal state (`hp`, `max_hp`, surges, defenses, markers, signal, etc.)
- a DNA tape of opcodes (`0x01` to `0x0E`)
- a local execution loop with instruction pointer control (including bloodied branching)

Entities interact pairwise. During interactions, they can:

- attack/siphon
- heal and defend
- signal and coordinate
- grant immediate peer action
- replicate
- symbiotically merge (cooperation-gated)

## Core Files

- `main.py` - simulation engine + metrics + snapshots/events output
- `analyze_metrics.py` - per-run phase signal detection
- `genome_viewer.py` - user-friendly emergence report from artifacts
- `sweep_emergence.py` - multi-seed leaderboard
- `run_e3_batch.sh` - end-to-end runner (recommended entrypoint)

## Quick Start

Run one full multi-seed batch:

```bash
./run_e3_batch.sh
```

Run a shorter test:

```bash
./run_e3_batch.sh --seeds 42,1337 --interactions 2000000 --checkpoint-every 50000
```

The runner prints heartbeats and checkpoints so you can tell it is active.

## Outputs

Each batch creates a timestamped run directory in `runs/`.

For each seed:

- `run_seed<seed>.csv` - checkpoint metrics
- `run_seed<seed>.log` - streamed run log
- `analysis_seed<seed>.txt` - phase-signal analysis
- `seed<seed>/events.jsonl` - event stream (`replicate`, `merge`, `respawn_burst`)
- `seed<seed>/snapshots/*.json` - genome snapshots at checkpoints
- `seed<seed>/genome_report_seed<seed>.md` - plain-language genome viewer report

Across all seeds:

- `leaderboard.txt`
- `leaderboard.csv`

## Metrics (Plain English)

- `zip_size`: compressed genome size of the population (lower can indicate higher order)
- `ops_per_interaction`: computational density
- `merge_rate`: symbiogenesis frequency
- `cooperation_index`: mutual cooperation structure
- `role_entropy`: how mixed/specialized the role ecology is
- `genotype_diversity`: fraction of distinct genomes
- `signal_convention_strength`: how dominant a shared signal is

## Emergence Patterns to Watch

- **Monoculture vs ecosystem**: one genome dominates vs diverse stable niches
- **Rule-bending loops**: signatures combining branch + action reset + healing
- **Social conventions**: strong shared signaling and grant-action coordination
- **Parasitic strategies**: replication-heavy genomes with low direct harvesting
- **Symbiogenesis waves**: merge bursts and new hybrid role structures

## Run Components Manually

Single simulation:

```bash
python3 main.py --seed 42 --interactions 1000000 --checkpoint-every 50000 --metrics-csv run_seed42.csv --artifact-dir seed42
```

Analyze one run:

```bash
python3 analyze_metrics.py run_seed42.csv
```

Generate genome report:

```bash
python3 genome_viewer.py --metrics-csv run_seed42.csv --artifact-dir seed42 --seed 42
```

Compare many runs:

```bash
python3 sweep_emergence.py run_seed*.csv --output-csv leaderboard.csv
```

## Tips

- If phase onsets are reported too early, reduce baseline or start detection later.
- If emergence appears "missing", relax thresholds in `analyze_metrics.py` args.
- For quick iteration, run fewer interactions first, then scale up.

## Requirements

- Python 3.10+ (3.13 tested)
- Bash (for `run_e3_batch.sh`)

No external Python packages are required.
To expand the E3 (Entity-based Evolutionary Environment) instruction set to a "full" functional set, we must incorporate the core mechanical loops of D&D 4e that enable the "12 steps" of complexity described by Agüera y Arcas .

This set transitions the environment from a simple "Siphon" loop to a sophisticated **info-computational ecosystem** where entities can anticipate threats, manage internal resources, and undergo revolutionary mergers .

## Expanded 4e Instruction Set (The Genetic Code)

Each byte in an entity's DNA tape maps to one of these primitives. The interaction engine executes these in a stack-based manner, creating a "Virtual Machine" for each creature .

### I. Core Actuation (The "Strikers")

* 
**0x01: Roll_D20**: Generates the fundamental stochastic noise used for all checks .


* **0x02: Target_Defense**: Takes a value from the stack and compares it to a peer's Defense (AC, Fort, Ref, or Will). This is the "Markov Blanket Breach" .


* **0x03: Siphon_HP**: If the breach is successful, transfers 1d6 + Mod HP from Target to Actor. This is the primary energy harvesting mechanism .


* **0x04: Push/Pull**: Relational state change. Moves the "distance" between Actor and Target, affecting the "Niche Overlap" of future instructions.



### II. Homeostasis & Resilience (The "Defenders")

* **0x05: Healing_Surge**: Consumes 1 "Surge" (stored complexity) to restore 25% of max HP. This resists the dissipative effects of random damage .


* 
**0x06: Second_Wind**: Increases the entity's current Defense values for 1 turn, making their Markov Blanket harder to breach.


* **0x07: Mark_Target**: Constraints the Target. Any instruction the Target executes against a peer *other* than the Actor incurs a penalty. This forces "Attractor Landscapes" where predators are forced to focus on robust prey.


* **0x08: Bloodied_Trigger**: A conditional branch. "If HP < 50%, jump to DNA index X." This enables the first stage of **Anticipation** .



### III. Social & Symbiogenetic (The "Leaders")

* **0x09: Grant_Action**: The Actor spends energy to let a Peer execute a portion of their DNA tape immediately. This is the foundation of **Massively Parallel Computation** .


* 
**0x0A: Symbio_Merge**: If two entities have highly correlated "R-Matrices" (they help each other), this instruction triggers a permanent fusion of their DNA tapes .


* **0x0B: Signal_Signalhood**: Broadcasts a specific byte. If a Peer "infers" this signal, they may skip an aggressive instruction. This is the "As-Relation" forming a social convention .



### IV. Autopoiesis & Meta-Computation

* 
**0x0C: Replicate**: Spends 15 HP to create a copy of the current DNA tape in the soup .


* **0x0D: Action_Point**: A rare instruction that resets the DNA execution pointer, allowing for "Burst" computation.
* **0x0E: Rest**: Skips all active instructions to recover a Healing Surge. This is the "House Cleaning" phase that minimizes complexity for better model evidence .



---

## E3 System Architecture Documentation

To help other researchers understand this "D&D Turing Gas," use the following structural map:

| 4e Concept | Info-Computational Role | Source Context |
| --- | --- | --- |
| **HP / Healing Surges** | Free Energy (Negative Entropy) | Agüera y Arcas 

 |
| **Defenses (AC/Fort/Ref/Will)** | Markov Blanket thickness | Friston 

 |
| **Power Keywords** | Functional Constraints (Virtual Machines) | Dodig-Crnkovic 

 |
| **Roles (Striker/Defender/Leader)** | Specialized Niche Attractors | Foster / Agüera y Arcas 

 |
| **Multiclassing** | Symbiogenetic Evolution | Agüera y Arcas 

 |

### Phase 1: The "Kobold" Emergence

In the first million interactions, expect to see the "Kobold" pattern: small, high-DEX entities that use **0x03: Siphon_HP** and **0x0C: Replicate** aggressively. They will be highly compressible and dominate the "Touring Gas" .

### Phase 2: The "Class" Revolution

Watch for the "Zip Drop." Once entities evolve the **0x08: Bloodied_Trigger** to use **0x05: Healing_Surge**, their survival time will skyrocket. This stability allows for the **0x0A: Symbio_Merge** to occur, leading to "Fighter/Cleric" hybrids that are far more computationally complex than the sum of their parts .

Would you like me to update the Python boilerplate to include this **Branching Logic** (Bloodied Triggers) and the **Symbio_Merge** function?

Here is a plan to build an "Entity-based Evolutionary Environment" (E3) using the principles from the four talks.

1. The Substrate: Primitive "DNA" Stat Blocks
In D&D, an entity is defined by its attributes (STR, DEX, etc.) and its actions. In your experiment, these shouldn't be fixed; they should be the embodied code.
+1


The Tape: Instead of a BrainFuck string, an entity's "DNA" is an array of bytes that the system interprets as a sequence of D&D-style "functions" (e.g., Roll_Attack, Heal, Siphon_Energy).
+1


The Processor: The "Game Engine" acts as the CPU, plucking two entities from the pool and letting their "DNA" interact in a "Combat/Social" interaction.
+1

2. Markov Blankets: Defining the "Entity"
Since there is no grid, you need a way to define what constitutes a single creature versus a group or a "virus" in the code.


Statistical Boundaries: Use Karl Friston's Markov Blanket to determine which values are "Internal" (the entity's HP and stats) and which are "Active" (its attacks or buffs affecting others).
+1

Nested Entities: This allows for the emergence of "Party-level" entities. If two entities always "Roll_Help" for each other, the system eventually treats them as a single higher-order organism with a shared Markov Blanket.
+1

3. Evolutionary Dynamics: Symbiogenesis over Bit-Flips
Following Blaise Agüera y Arcas, we won't use random mutations (randomly changing a STR of 10 to 11). Instead, we use Symbiogenesis.
+2


The Merger: When two entities survive an interaction successfully (e.g., they both end with more "Energy" than they started), there is a chance their "DNA" tapes fuse.
+1

Complex Actions: A "Fighter" entity and a "Cleric" entity might fuse into a "Paladin" entity that contains the code for both. This is how you reach the "12 steps" to a phase transition where complex "classes" emerge from primitive values.
+1

4. Resource Economy: The "Free Energy" of D&D
To prevent the "soup" from just becoming a mess of infinite code, you must enforce a strict metabolism.
+1

Action Cost: Every "Roll" or "Instruction" costs a resource (like "XP" or "Soul Energy"). If an entity runs out, it "dies" and its code is recycled back into the soup.
+1


Homeostasis: Entities that evolve to "Rest" or "Efficiently Hunt" will maintain their internal states (HP) against the "dissipative" forces of the environment (the game rules).
+1

5. Cognitive Platonism: Identifying "As" Relations
This is the most "game-like" part of the experiment. We look for when an entity starts treating a "Ground" value (a 0 or 1 in the code) as a "Role" (a Key or a Weapon).


Affordances: Does a "High Strength" value evolve to be used as a tool for "Breaching" rather than just "Hitting"?.


Culture/Convention: If a group of entities all adopt the same "Signal" byte to mean "Don't Attack Me," you have witnessed the emergence of an "Ideal Object"—a social convention that stabilizes their interaction space.
+2

Implementation Strategy: The "D&D Zero" Language
I suggest using a Stack-based Language (similar to Forth) where the "operators" are D&D primitives.

Instruction (Byte)	D&D Primitive Action
0x01	Roll d20 (Push result to stack)
0x02	Target Peer (Set the "Other" for the next action)
0x03	Siphon (If Roll > Target AC, move X Energy from Target to Self)
0x04	Replicate (Spend Energy to create a copy of current DNA in the soup)
0x05	Merge (Fuse a portion of Peer's DNA into my own)
Monitoring the Results

The Life Spike: You are looking for a moment where the "Average Actions per Turn" suddenly spikes—this is your "Phase Transition" into an ecology of autonomous agents.
+1

The Zip Test: Periodically save the "DNA" of the entire population to a file and zip it. If the zip file is 1% of the original size, you have a highly ordered, "alive" civilization of entities.
+1

Would you like me to help you define a more robust "Instruction Set" for these D&D-style entities, or should we look at how to code the "Interaction Engine" that picks them from the pool?