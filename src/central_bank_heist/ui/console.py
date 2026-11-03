"""Rich console helpers: typewriter, countdown header, prompts."""

from __future__ import annotations

import sys
import threading
import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.prompt import Prompt, IntPrompt

from central_bank_heist.models import GameState, Round
from central_bank_heist.ui.art import DIE_FACES, PORTRAITS

console = Console()


def clear() -> None:
    console.clear()


def print_title(art: str) -> None:
    console.print(art)


def print_panel(content: str, title: str = "", style: str = "white") -> None:
    console.print(Panel(content, title=title, style=style, expand=False))


def print_die_animation(final_value: int, frames: int = 8, delay: float = 0.12) -> None:
    """Animate a rolling die, landing on final_value."""
    import random as _rng
    for i in range(frames):
        face_val = _rng.randint(1, 6)
        face = DIE_FACES.get(face_val, "")
        console.print(face, end="")
        time.sleep(delay)
        if i < frames - 1:
            # Move cursor up to overwrite
            lines = face.count("\n")
            console.print(f"\033[{lines}A", end="")

    final_face = DIE_FACES.get(final_value, "")
    lines = final_face.count("\n")
    console.print(f"\033[{lines}A", end="")
    console.print(f"[bold yellow]{final_face}[/]")


def print_portrait(npc_id: str) -> None:
    portrait = PORTRAITS.get(npc_id, "")
    if portrait:
        console.print(portrait)


def typewriter(text: str, delay: float = 0.02, style: str = "italic") -> None:
    """Print text with a typewriter effect."""
    for char in text:
        console.print(f"[{style}]{char}[/]", end="", highlight=False)
        time.sleep(delay)
    console.print()


def stream_typewriter(token_iter, style: str = "italic") -> str:
    """Stream tokens with typewriter effect, return full text."""
    full_text = ""
    for token in token_iter:
        full_text += token
        console.print(f"[{style}]{token}[/]", end="", highlight=False)
        time.sleep(0.01)
    console.print()
    return full_text


def print_timer(state: GameState) -> None:
    """Print the countdown timer in the header (skipped while the live bar runs)."""
    if _timer_thread is not None and _timer_thread.is_alive():
        return
    remaining = state.remaining_seconds
    if remaining is None:
        return
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    if remaining <= 120:
        style = "bold red"
    elif remaining <= 300:
        style = "bold yellow"
    else:
        style = "bold green"
    console.print(
        f"  [{style}]POLICE ETA: {minutes:02d}:{seconds:02d}[/]",
        justify="right",
    )


# ---------------------------------------------------------------------------
# Real-time countdown status bar
# ---------------------------------------------------------------------------
#
# Uses the DECSTBM scroll region so the last terminal line is reserved for a
# live countdown that a daemon thread repaints every second. All normal output
# (menus, prompts, input echo) scrolls above it, so the clock keeps ticking
# even while the player is reading or typing.

_timer_thread: threading.Thread | None = None
_timer_stop = threading.Event()
_timer_paint_lock = threading.Lock()


def _bar_color(remaining: float) -> str:
    if remaining <= 120:
        return "31"  # red
    if remaining <= 300:
        return "33"  # yellow
    return "32"  # green


def _paint_timer_bar(state: GameState) -> None:
    remaining = state.remaining_seconds
    rows = console.size.height
    cols = console.size.width
    if remaining is None:
        label = " POLICE ETA --:-- "
    else:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        label = f" POLICE ETA {minutes:02d}:{seconds:02d} "
        if remaining <= 0:
            label = " POLICE AT THE DOOR "

    color = _bar_color(remaining) if remaining is not None else "37"
    text = label.ljust(cols)[:cols]

    with _timer_paint_lock:
        out = sys.stdout
        # save cursor → go to last line → reverse-video colored bar → restore
        out.write(
            f"\x1b7\x1b[{rows};1H\x1b[2K\x1b[7m\x1b[{color}m{text}\x1b[0m\x1b8"
        )
        out.flush()


def _timer_loop(state: GameState) -> None:
    while not _timer_stop.wait(1.0):
        _paint_timer_bar(state)


def start_timer_bar(state: GameState) -> None:
    """Start the real-time countdown bar on the last terminal line."""
    global _timer_thread
    if not console.is_terminal or state.remaining_seconds is None:
        return
    stop_timer_bar()

    _timer_stop.clear()
    rows = console.size.height
    with _timer_paint_lock:
        # Reserve the last line: content scrolls only within rows 1..rows-1
        sys.stdout.write(f"\x1b[1;{rows - 1}r")
        sys.stdout.flush()

    _paint_timer_bar(state)
    _timer_thread = threading.Thread(
        target=_timer_loop, args=(state,), daemon=True, name="heist-timer"
    )
    _timer_thread.start()


def stop_timer_bar() -> None:
    """Stop the countdown bar and restore the full scroll region."""
    global _timer_thread
    if _timer_thread is None:
        return
    _timer_stop.set()
    _timer_thread.join(timeout=2.0)
    _timer_thread = None
    if not console.is_terminal:
        return
    rows = console.size.height
    with _timer_paint_lock:
        sys.stdout.write(f"\x1b[r\x1b[{rows};1H\x1b[2K")
        sys.stdout.flush()


def print_round_header(state: GameState) -> None:
    """Print the current round header with timer."""
    round_name = {
        Round.ROUND_1: "ROUND 1 — INTERROGATION",
        Round.ROUND_2: "ROUND 2 — SEARCH & PRESSURE",
        Round.ACCUSATION: "ACCUSATION",
    }.get(state.current_round, "")

    console.rule(f"[bold]{round_name}[/]")
    print_timer(state)


def print_evidence(state: GameState) -> None:
    """Print discovered evidence."""
    if not state.revealed_facts:
        console.print("[dim]No evidence collected yet.[/]")
        return

    fact_labels = {
        "money_found": "Money stash found in the car's headliner",
        "gps_found": "GPS tracker found under the driver's seat",
        "dirty_cash": "Dogg had $500 cash in his pocket",
        "news_clipping": "Shade had an old heist newspaper clipping; red swollen hand",
        "gps_coords": "Ghost had federal police GPS coordinates",
        "maldives_tickets": "Cap had expensive Maldives travel tickets",
        "extra_charge": "Spark had a spare smoke explosive charge",
        "pocket_lint": "Nothing of interest found",
        "shredded_news": "Trunk bags contained shredded newspaper, not money",
    }

    console.print("\n[bold underline]Evidence Collected:[/]")
    for fact_id in sorted(state.revealed_facts):
        label = fact_labels.get(fact_id, fact_id)
        console.print(f"  [green]>[/] {label}")
    console.print()


def prompt_choice(prompt_text: str, choices: list[str]) -> str:
    """Display numbered choices and return the selected one."""
    console.print()
    for i, choice in enumerate(choices, 1):
        console.print(f"  [bold cyan]{i}[/]) {choice}")
    console.print()

    while True:
        try:
            val = IntPrompt.ask(prompt_text, console=console)
            if 1 <= val <= len(choices):
                return choices[val - 1]
            console.print(f"[red]Choose 1-{len(choices)}[/]")
        except (ValueError, KeyboardInterrupt):
            console.print(f"[red]Choose 1-{len(choices)}[/]")


def prompt_enter(prompt_text: str = "Press Enter to continue") -> None:
    """Wait for the player to press Enter (accepts empty input)."""
    console.input(f"[dim]{prompt_text}[/] ")


def prompt_text(prompt_text: str, max_length: int = 500) -> str:
    """Get free-text input from the player."""
    while True:
        text = Prompt.ask(prompt_text, console=console)
        text = text.strip()
        if text:
            return text[:max_length]
        console.print("[red]Please type something.[/]")


def prompt_yes_no(prompt_text: str) -> bool:
    """Ask a yes/no question."""
    answer = Prompt.ask(f"{prompt_text} [bold](y/n)[/]", console=console)
    return answer.strip().lower() in ("y", "yes")
