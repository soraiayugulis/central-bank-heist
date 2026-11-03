# Central Bank Heist — Development

## Setup

```bash
cd central-bank-heist
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"   # game + AI providers + dev tools
python -m pytest tests/ -v
```

## Design principles

- **Deterministic truth, AI only roleplays.** The mystery's facts are
  fixed in code — the LLM receives only what an NPC's sheet knows and can
  never invent or leak hidden facts. Searches are canned, not generated.
- **Data-driven sheets.** Personality, knowledge, powers and win
  conditions live in YAML — no code changes needed to tweak characters.
- **Registries over hardcoding.** Power handlers and win evaluators are
  named registries; YAML validation fails loudly on unknown IDs.

## Project structure

```
src/central_bank_heist/
├── cli.py              # entry point (`heist` command, also `python -m central_bank_heist`)
├── config.py           # env vars > game.yaml > defaults; is_debug/is_power_up flags
├── models.py           # GameState, Round, Annoyance, timer, statement logs
├── sheets.py           # YAML loader/validator, WinCondition evaluator tree
├── dice.py             # d6 + POWER_HANDLERS registry
├── director.py         # game mediator: questions, searches, powers, win evaluation, epilogues
├── prompts.py          # system/user prompt builders + epilogue prompt
├── data/
│   ├── characters.yaml # 8 character sheets
│   └── game.yaml       # tunables
├── providers/
│   ├── base.py         # LLMProvider protocol + create_provider factory
│   ├── scripted.py     # offline deterministic responses (per sheet × die tier × annoyance)
│   ├── anthropic.py    # Claude
│   ├── openai.py       # GPT
│   └── ollama.py       # local models via HTTP
└── ui/
    ├── art.py          # ASCII portraits, title, die faces
    ├── console.py      # Rich helpers, typewriter, live countdown status bar
    └── screens.py      # menu, intro, rounds, searches, accusation, endings
```

## Editing character sheets

File: `src/central_bank_heist/data/characters.yaml` — one list item per
character. Every field flows into the NPC's prompt automatically, so new
traits (e.g. `tics`, `habits`) work with zero code changes.

Key fields:

| Field | Notes |
|---|---|
| `knows` | Facts the NPC may share (gated by die tier) |
| `secrets` / `conceals` | Never spoken — only exposed by deterministic searches |
| `cover_story` | Fixed alibi — keeps liars consistent across questions |
| `suspicion_point` | Revealed on die 2–3 |
| `search_results.person` | Text shown when this NPC is searched |
| `power` | `{type, params, uses, description}` — see registry below |
| `win_condition` | Evaluator tree — see below |
| `intro` | Player-facing role briefing (null for the unplayable traitor) |

### Power registry

| `type` | Effect | `params` |
|---|---|---|
| `set_die` | Force your own die to a value | `value`, optional `round` (1 or 2) |
| `min_die` | Floor your die at a value | `value`, optional `round` |
| `force_die` | Force an NPC's die to a value | `value` |

Adding a power type = a small handler in `dice.py: POWER_HANDLERS` +
declaring it on the sheet.


### Win condition evaluators

Compose with `all:` / `any:` lists:

| Type | Params | True when… |
|---|---|---|
| `accuse_role` | `target` | the accused has that role id |
| `accused_not_role` | `target` | someone was accused and it's not that role |
| `accused_any` | — | any accusation was made |
| `no_death` | — | nobody was executed |
| `target_not_executed` | `target` | that role wasn't the one executed |
| `fact_found` | `fact` | the fact is in `revealed_facts` |
| `fact_not_found` | `fact` | the fact was never discovered |
| `timed_out` | — | game ended by police raid |
| `not_timed_out` | — | game resolved before police arrived |

Valid role ids: `boss`, `traitor`, `ghost`, `spark`, `brick`, `wheels`,
`shade`, `manager`. Valid fact ids are the ones searches set
(`money_found`, `gps_found`, `dirty_cash`, `news_clipping`, `gps_coords`,
`maldives_tickets`, `extra_charge`, `pocket_lint`, `shredded_news`).

Unknown types/targets/facts raise `ValueError` at startup listing the
valid options — safe to experiment.

## Game tunables

`src/central_bank_heist/data/game.yaml` (precedence: env > yaml > defaults):

```yaml
time_limit_minutes: 20            # 0 = no timer
repeat_question_threshold: 3      # repeats to same NPC before hostility
repeat_penalty_minutes: 2         # minutes lost per hostile repeat
accusation_min_round2_actions: 2  # round-2 actions to unlock accusation
statement_log_max: 10             # NPC memory depth
```

## Environment variables

| Var | Purpose |
|---|---|
| `HEIST_PROVIDER` | `scripted` (default), `anthropic`, `openai`, `ollama` |
| `HEIST_MODEL` | provider model name |
| `HEIST_API_KEY` | API key for cloud providers |
| `HEIST_BASE_URL` | provider endpoint (Ollama default `http://localhost:11434`) |
| `HEIST_TIME_LIMIT_MINUTES` | override timer (`0` = off) |
| `HEIST_REPEAT_PENALTY_MINUTES` | override repeat penalty |
| `HEIST_DEBUG` | show internals: rolls, tiers, counters, THE TRUTH reveal |
| `HEIST_POWER_UP` | enable player powers (off by default) |

`.env` in the project root is read if present (see `.env.example`).

## Scripted vs AI mode

- **Scripted** (default): players pick questions from a pre-written menu;
  answers are canned per sheet × die tier × annoyance. Deterministic —
  used by the whole test suite, no network.
- **AI**: free-text questions; each NPC answers in character, in natural
  language, bounded by its sheet knowledge and a statement log for
  consistency. If a provider call fails, the scripted fallback answers
  that one turn.

## Testing

```bash
python -m pytest tests/ -v
```

~90 deterministic tests covering: config precedence, sheet validation,
win condition trees, die tiers, power handlers, annoyance/penalty
thresholds, timer, accusation gating, searches, win matrix incl. raid
endings, and epilogue generation.
