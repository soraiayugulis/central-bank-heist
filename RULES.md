# Central Bank Heist — Game Rules

> **Spoiler note:** this document lists every role's objective. It does NOT
> reveal the mystery's solution — but if you'd rather discover the roles by
> playing, stop here and just run `heist`!

## The setup

Eight people in a warehouse: seven crew members and one hostage. The money
from the heist is gone. The federal police arrive in **20 minutes** (real
time, always ticking — watch the status bar at the bottom of your screen).

You play one randomly-drawn role. The other seven characters are NPCs.

## Round 1 — Interrogation

Pick an NPC to question, then a **d6 is rolled** — the result controls how
much truth they give:

| Roll | NPC behavior |
|---|---|
| **1** | Confused — rambles, says nothing useful |
| **2–3** | Answers your question + reveals their own suspicious point |
| **4–5** | Answers + offers a suspicion about someone else |
| **6** | Refuses to answer — accuses another NPC and says why |

After questioning **2 different NPCs**, the game moves to Round 2.

### Annoyance

Asking the same NPC repeatedly has consequences:

- **1st question** — normal answer
- **2nd question** — they notice you're circling back ("I already told you…")
- **3rd question onward** — they snap. **Each repeat costs 2 minutes** off
  the countdown.

## Round 2 — Search & Pressure

Everything from Round 1 still applies, plus search actions:

- **Search a person** — reveals what's in their pockets (once per NPC)
- **Search the trunk** — what happened to the money bags? (once)
- **Search inside the car** — **roll a d6 first**:
  - **1–2**: nothing found (though something feels off)
  - **3–4**: a suspicious hint — worth another look
  - **5–6**: a real discovery
  
  The car hides **two secrets**, revealed one per successful roll, in
  random order. Keep searching.

## Accusation

After **2 actions in Round 2 AND at least 1 real discovery** (a successful
search that reveals evidence), "Accuse a suspect" unlocks. Pick who you
think betrayed the crew — then decide:

- **Execute** — the crew handles it internally
- **Spare / hand to police** — they face justice alive

Who you accuse — and whether they live — changes the outcome, and every
role scores it differently.

## Win conditions per role
> **SPOILER WARNING:** the section below — and the win conditions inside
> `characters.yaml` — reveal hidden game truths (roles, clues, and what
> each secret actually means). If you haven't finished a playthrough yet,
> stop here and go play!

| Codename | Role | You win if… |
|---|---|---|
| **Cap** | Gang boss | the traitor is accused AND the money is found — before police |
| **Ghost** | Undercover cop | Cap is accused AND handed over **alive** AND the money is found |
| **Spark** | Demolitions expert | the money is found AND anyone **except** Cap is accused — before police |
| **Brick** | Gang member | the money is found AND Ghost or the traitor is accused — before police |
| **Wheels** | Driver | any verdict is reached before the police arrive |
| **Shade** | Accomplice | Ghost is **not executed** (accused + spared is fine) |
| **Mr. Whitfield** | Hostage | the police breach before any verdict — your job is to **stall** |

Notice: some objectives collide. The cop needs the boss alive, the
accomplice quietly protects the cop, and the hostage is hoping you all
keep arguing until the door comes down.

## Role powers (optional)

Each role has a unique power defined on its sheet. Powers are **off by
default** — enable them with:

```bash
HEIST_POWER_UP=1 heist
```

When enabled, your power is shown in your intro and offered at the right
moment (e.g., Spark's goggles force a die to 6 in Round 1, Mr. Whitfield's
panic attack forces an NPC's die to 1).

### Relationships

NPCs treat you differently depending on who you are. Cap, for example,
has a soft spot for his longtime friend — play that role and the boss's
anger is aimed at the situation, never at you.

## Endings

- **Timeout** — the countdown hits zero and the police breach
  **immediately**, interrupting whatever you're doing (even mid-typing).
  For most roles this is a loss… but not for everyone.
- **Accusation** — the game evaluates your role's objective, then narrates
  what the police find when they breach: the scene varies with who you
  accused, whether they were executed, and which evidence you uncovered
  (including the clues you *missed*).
