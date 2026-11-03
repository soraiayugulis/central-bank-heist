# Central Bank Heist

> The engine ticks as it cools in the corner of the warehouse. Diesel and
> gunpowder cling to everything — the car, your clothes, your hands.
>
> Outside, the rain is relentless. An hour ago you emptied the vaults of
> the Central Bank. The plan was flawless. The execution... wasn't.
>
> The charge on vault 404 burned for too long, and the world
> went black. Nobody saw what happened in that darkness. **Somebody did.**
>
> Now the money bags sit open in front of the crew — stuffed with shredded
> newspaper. Every single one of them.
>
> Sirens are already threading through the rain, getting closer. The federal
> police are coming, and somebody in this room sold the crew out.
>
> Eight people. One traitor. Twenty minutes on the clock.
>
> **And now?**

Each run, you draw a random role and interrogate seven
AI-driven NPCs in a warehouse while the police close in. Question suspects,
search them and the car, and accuse someone before the clock hits zero.
Every role has its own win condition — figuring out who you are is half
the game.

## Stack

- **Python 3.12+** — dataclasses, type hints, `src/` layout
- **Rich** — CLI rendering: ASCII portraits, die animation, typewriter text,
  live countdown status bar
- **PyYAML** — data-driven character sheets and game tunables
- **Pluggable AI providers** — Anthropic, OpenAI, Ollama, plus an offline
  scripted fallback (no API key needed)
- **pytest** — deterministic test suite (no network)

## Quick Start

```bash
cd central-bank-heist
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e "."

# Play offline — scripted NPCs, no API key needed
heist
```

### AI-powered NPCs (optional)

```bash
pip install -e ".[ai]"

# Anthropic
HEIST_PROVIDER=anthropic HEIST_API_KEY=sk-ant-... heist

# OpenAI
HEIST_PROVIDER=openai HEIST_API_KEY=sk-... heist

# Ollama (local, free — server must be running)
HEIST_PROVIDER=ollama HEIST_MODEL=qwen3:8b heist
```

If the AI call fails mid-game, the game falls back to scripted responses —
you never lose progress.

## Documentation

- **[RULES.md](RULES.md)** — how to play: rounds, die rolls, searches,
  accusations, annoyance, timer, and every role's win condition.
- **[DEVELOPMENT.md](DEVELOPMENT.md)** — dev setup, project structure,
  editing character sheets, tunables, env vars, debug mode, providers.

## License

[PolyForm Noncommercial 1.0](LICENSE) — free to download, play, study and
modify. Commercial use is not permitted without the author's permission.
