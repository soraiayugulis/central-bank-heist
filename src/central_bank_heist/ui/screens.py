"""Game screens: menu, interrogation, search, accusation, endings."""

from __future__ import annotations

import os
import sys

from central_bank_heist.config import is_debug, is_power_up
from central_bank_heist.director import Director
from central_bank_heist.dice import DIE_TIER_LABELS
from central_bank_heist.models import Annoyance, GameState, Round
from central_bank_heist.providers.scripted import ScriptedProvider
from central_bank_heist.ui.art import TITLE_ART
from central_bank_heist.ui import console as ui

# Pre-programmed questions for scripted (offline) mode
_SCRIPTED_QUESTIONS = [
    "Where were you during the smoke?",
    "What did you see when the smoke cleared?",
    "Why should I trust you?",
    "Did you notice anything suspicious?",
    "Who do you think did this?",
    "What were you doing near the car?",
]


def _check_timeout(state: GameState, director: Director) -> bool:
    """Check if time is up. Returns True if game ended."""
    if state.is_timed_out:
        _show_raid_ending(state, director)
        return True
    return False


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def run_game() -> None:
    """Main entry point: menu loop."""
    while True:
        ui.clear()
        ui.print_title(TITLE_ART)
        ui.console.print(
            "\n[dim]A single-player social deduction game powered by AI[/]\n"
        )

        choice = ui.prompt_choice("Choose", ["New game", "How to play", "Quit"])

        if choice == "Quit":
            ui.console.print("[dim]Goodbye.[/]")
            sys.exit(0)
        elif choice == "How to play":
            _show_how_to_play()
        elif choice == "New game":
            _play_game()


def _show_how_to_play() -> None:
    ui.clear()
    ui.print_panel(
        "[bold]CENTRAL BANK HEIST[/] — How to play\n\n"
        "The gang just pulled off the heist of the century — but the money\n"
        "has vanished from the bags, replaced by shredded newspaper. The\n"
        "federal police are closing in. Someone betrayed the crew.\n\n"
        "[bold yellow]ROUND 1 — INTERROGATION[/]\n"
        "Pick an NPC to question. Roll a die — the result determines how\n"
        "much they reveal:\n"
        "[bold yellow]ROUND 2 — SEARCH & PRESSURE[/]\n"
        "You can still question NPCs, but now you can also:\n"
        "  - Search a person (reveals what's in their pockets)\n"
        "  - Search the trunk\n"
        "  - Search inside the car\n\n"
        "After 2 actions in round 2, you can accuse someone.\n\n"
        "[bold red]ACCUSATION[/]\n"
        "Pick who you think betrayed the crew. Choose to execute them or\n"
        "hand them to the police. Your win condition depends on your role.\n\n"
        "[bold]TIMER[/]: The police are approaching. If time runs out,\n"
        "they raid the hideout.\n\n"
        "[bold]POWERS[/]: Some roles have special abilities — read your\n"
        "intro carefully!",
        title="How to play",
        style="cyan",
    )
    ui.prompt_enter("Press Enter to return")


# ---------------------------------------------------------------------------
# Game flow
# ---------------------------------------------------------------------------

_GAME_INTRO = (
    "The engine ticks as it cools in the corner of the warehouse. Diesel and "
    "gunpowder cling to everything — the car, your clothes, your hands.\n\n"
    "Outside, the rain is relentless. An hour ago you emptied the vaults of "
    "the Central Bank. The plan was flawless. The execution... wasn't.\n\n"
    "The charge on vault 404 burned for too long, and the world "
    "went black. Nobody saw what happened in that darkness. Somebody did.\n\n"
    "Now the money bags sit open in front of the crew — stuffed with shredded "
    "newspaper. Every single one of them.\n\n"
    "Sirens are already threading through the rain, getting closer. The federal "
    "police are coming, and somebody in this room sold the crew out.\n\n"
    "Eight people. One traitor. Twenty minutes on the clock.\n\n"
    "And now?"
)


def _play_game() -> None:
    """Run a single game session."""
    director = Director()
    state = director.new_game()

    if hasattr(director.provider, "warmup"):
        director.provider.warmup()

    ui.clear()
    _show_game_intro()
    ui.clear()
    _show_intro(state)

    ui.start_timer_bar(state)
    try:
        # Round 1
        _run_round_1(state, director)
        if state.current_round == Round.ENDED:
            return

        # Round 2
        state.advance_to_round2()
        _run_round_2(state, director)
        if state.current_round == Round.ENDED:
            return

        # If player exits round 2 without accusing and accusation is unlocked
        if state.accusation_unlocked and state.current_round != Round.ENDED:
            _run_accusation(state, director)
    except KeyboardInterrupt:
        # Deadline watchdog interrupted an input mid-wait — police breach NOW
        if state.is_timed_out and state.current_round != Round.ENDED:
            _show_raid_ending(state, director)
        elif not state.is_timed_out:
            raise
    finally:
        ui.stop_timer_bar()


def _show_game_intro() -> None:
    """Show the narrative intro before role draw."""
    ui.print_title(TITLE_ART)
    ui.console.print()
    ui.typewriter(_GAME_INTRO, delay=0.018)
    ui.console.print()
    ui.prompt_enter("Press Enter to find out who you are")


def _show_intro(state: GameState) -> None:
    """Show the player's role intro."""
    sheet = state.player_sheet
    ui.print_portrait(sheet.id)
    ui.console.print(f"\n[bold]You are [yellow]{sheet.codename}[/yellow] — {sheet.role}[/]\n")

    if sheet.intro:
        ui.typewriter(sheet.intro.strip(), delay=0.015)
    else:
        ui.console.print("[dim]No intro available for this role.[/]")

    if sheet.power and is_power_up():
        ui.console.print(f"\n[bold magenta]POWER:[/] {sheet.power.description}")

    if sheet.pocket:
        ui.console.print(f"[bold]POCKET:[/] {', '.join(sheet.pocket)}")

    if is_debug():
        objective = _get_objective_text(sheet.id)
        ui.console.print(f"\n[bold red]OBJECTIVE:[/] {objective}")
    ui.console.print()
    ui.prompt_enter("Press Enter to begin")


def _get_objective_text(role_id: str) -> str:
    objectives = {
        "boss": "Find the traitor AND the money — before the police arrive.",
        "ghost": "Get Cap accused and handed to police ALIVE (not executed) — plus find the money.",
        "spark": "Find the money and get anyone EXCEPT Cap accused — before the police arrive.",
        "brick": "Find the money and get Ghost or the traitor accused — before the police arrive.",
        "wheels": "Make sure the crew reaches a verdict before the police arrive — and survive.",
        "shade": "Ghost must NOT be executed. Accused and handed over alive is acceptable.",
        "manager": "Stall. Keep them talking until the police breach — you win when they arrive.",
    }
    return objectives.get(role_id, "Discover the truth.")


# ---------------------------------------------------------------------------
# Round 1
# ---------------------------------------------------------------------------

def _run_round_1(state: GameState, director: Director) -> None:
    ui.clear()
    ui.print_round_header(state)
    ui.console.print(
        "\n[bold]Question the crew to find out what happened.[/]\n"
        "[dim]Pick an NPC to interrogate. You'll roll a die for each question.[/]\n"
    )

    while state.current_round == Round.ROUND_1:
        if _check_timeout(state, director):
            return

        npc_ids = sorted(state.npc_sheets.keys())
        unique_questioned = sum(1 for nid in npc_ids if state.question_counts.get(nid, 0) > 0)

        if unique_questioned >= 2:
            ui.console.print(
                "\n[bold yellow]You've heard enough for now. Time to dig deeper.[/]"
            )
            ui.prompt_enter("Press Enter to advance to Round 2")
            break

        npc_labels = [
            f"{state.npc_sheets[nid].codename} ({state.npc_sheets[nid].role})"
            for nid in npc_ids
        ]
        options = npc_labels + ["Review evidence"]

        ui.print_timer(state)
        choice = ui.prompt_choice("Who do you want to talk to?", options)

        if choice == "Review evidence":
            ui.print_evidence(state)
            continue
        else:
            idx = options.index(choice)
            npc_id = npc_ids[idx]
            _do_question(state, director, npc_id)


def _do_question(state: GameState, director: Director, npc_id: str) -> None:
    """Execute a question turn: portrait, die, question, response."""
    npc_sheet = state.npc_sheets[npc_id]
    debug = is_debug()

    ui.console.print(f"\n[bold]Questioning [yellow]{npc_sheet.codename}[/yellow]...[/]")
    ui.print_portrait(npc_id)

    # Powers are disabled by default — offered only with HEIST_POWER_UP=1
    use_power = False
    force_target = None
    if (
        is_power_up()
        and state.player_sheet.power
        and not state.player_power_used
        and _power_available_this_round(state)
    ):
        power = state.player_sheet.power
        if power.type == "force_die":
            if ui.prompt_yes_no(
                f"Use your power ({power.description}) on {npc_sheet.codename}?"
            ):
                use_power = True
                force_target = npc_id
        else:
            if ui.prompt_yes_no(f"Use your power ({power.description})?"):
                use_power = True

    if isinstance(director.provider, ScriptedProvider):
        question = ui.prompt_choice(
            f"[bold cyan]Ask {npc_sheet.codename}[/]",
            _SCRIPTED_QUESTIONS,
        )
    else:
        question = ui.prompt_text(f"[bold cyan]Your question to {npc_sheet.codename}[/]")

    ui.console.print("\n[bold]Rolling the die...[/]")

    raw, final, annoyance, token_iter = director.stream_npc(
        state, npc_id, question,
        use_player_power=use_power,
        player_force_die_target=force_target,
    )

    ui.print_die_animation(final)

    if debug:
        if raw != final:
            ui.console.print(f"[dim]Raw roll: {raw} -> Modified to: {final}[/]")
        tier_label = DIE_TIER_LABELS.get(final, "")
        ui.console.print(f"[dim]Die result: {final} ({tier_label})[/]")

    if annoyance == Annoyance.MILD:
        ui.console.print("[yellow]They seem irritated by the repeated questioning...[/]")
    elif annoyance == Annoyance.HOSTILE:
        ui.console.print(
            "[bold red]They're furious! The argument burns precious minutes![/]"
        )

    ui.console.print(f"\n[bold]{npc_sheet.codename}:[/]")
    full_text = ui.stream_typewriter(token_iter)

    if annoyance != Annoyance.HOSTILE:
        state.record_statement(npc_id, full_text)
    ui.console.print()


def _power_available_this_round(state: GameState) -> bool:
    """Check if the player's power is usable in the current round."""
    power = state.player_sheet.power
    if power is None:
        return False
    target_round = power.params.get("round")
    if target_round is None:
        return True
    current = 1 if state.current_round == Round.ROUND_1 else 2
    return current == target_round


# ---------------------------------------------------------------------------
# Round 2
# ---------------------------------------------------------------------------

def _run_round_2(state: GameState, director: Director) -> None:
    ui.clear()
    ui.print_round_header(state)
    ui.console.print(
        "\n[bold]Time to dig deeper. Question, search, or accuse.[/]\n"
    )
    debug = is_debug()

    while state.current_round == Round.ROUND_2:
        if _check_timeout(state, director):
            return

        npc_ids = sorted(state.npc_sheets.keys())
        options = [
            "Question an NPC",
            "Search a person",
            "Search the trunk",
            "Search inside the car",
            "Review evidence",
        ]

        if state.accusation_unlocked:
            options.append("Accuse a suspect")

        if debug:
            actions_left = max(
                0,
                state.config.accusation_min_round2_actions - state.round2_actions,
            )
            if actions_left > 0:
                ui.console.print(
                    f"[dim]{actions_left} more action(s) before you can accuse.[/]"
                )

        ui.print_timer(state)
        choice = ui.prompt_choice("What do you want to do?", options)

        if choice == "Question an NPC":
            npc_id = _pick_npc(state)
            if npc_id:
                _do_question(state, director, npc_id)

        elif choice == "Search a person":
            npc_id = _pick_npc(state, label="Who do you want to search?")
            if npc_id:
                _do_search_person(state, director, npc_id)

        elif choice == "Search the trunk":
            _do_search_trunk(state, director)

        elif choice == "Search inside the car":
            _do_search_car(state, director)

        elif choice == "Review evidence":
            ui.print_evidence(state)

        elif choice == "Accuse a suspect":
            _run_accusation(state, director)
            return


def _pick_npc(state: GameState, label: str = "Pick an NPC") -> str | None:
    npc_ids = sorted(state.npc_sheets.keys())
    debug = is_debug()
    npc_labels = []
    for nid in npc_ids:
        sheet = state.npc_sheets[nid]
        if debug:
            extras = []
            count = state.question_counts.get(nid, 0)
            if count > 0:
                extras.append(f"asked {count}x")
            if nid in state.searched_persons:
                extras.append("searched")
            suffix = f" [dim]({', '.join(extras)})[/]" if extras else ""
        else:
            suffix = ""
        npc_labels.append(f"{sheet.codename} ({sheet.role}){suffix}")

    options = npc_labels + ["Back"]
    choice = ui.prompt_choice(label, options)
    if choice == "Back":
        return None
    idx = options.index(choice)
    return npc_ids[idx]


def _do_search_person(state: GameState, director: Director, npc_id: str) -> None:
    npc_sheet = state.npc_sheets[npc_id]
    ui.console.print(f"\n[bold]Searching {npc_sheet.codename}...[/]")
    text, fact_id = director.search_person(state, npc_id)
    ui.typewriter(text, delay=0.02)
    if fact_id:
        ui.console.print(f"[green]Evidence recorded: {fact_id}[/]")
    ui.console.print()


def _do_search_trunk(state: GameState, director: Director) -> None:
    ui.console.print("\n[bold]Opening the trunk...[/]")
    text, fact_id = director.search_trunk(state)
    ui.typewriter(text, delay=0.02)
    if fact_id:
        ui.console.print(f"[green]Evidence recorded: {fact_id}[/]")
    ui.console.print()


def _do_search_car(state: GameState, director: Director) -> None:
    from central_bank_heist.dice import roll_d6
    ui.console.print("\n[bold]Searching inside the car...[/]")
    raw = roll_d6()
    ui.print_die_animation(raw)
    if is_debug():
        ui.console.print(f"[dim]Search roll: {raw}[/]")
    text, fact_id = director.search_car(state, raw)
    ui.typewriter(text, delay=0.02)
    if fact_id:
        ui.console.print(f"[green]Evidence recorded: {fact_id}[/]")
    elif raw <= 4 and state.car_search_count < 2:
        ui.console.print("[yellow]Maybe searching again with better luck would reveal more...[/]")
    ui.console.print()


# ---------------------------------------------------------------------------
# Accusation
# ---------------------------------------------------------------------------

def _run_accusation(state: GameState, director: Director) -> None:
    ui.clear()
    ui.console.rule("[bold red]ACCUSATION[/]")
    ui.print_timer(state)
    ui.console.print(
        "\n[bold]Time to point the finger. Who betrayed the crew?[/]\n"
    )

    npc_ids = sorted(state.npc_sheets.keys())
    npc_labels = [
        f"{state.npc_sheets[nid].codename} ({state.npc_sheets[nid].role})"
        for nid in npc_ids
    ]
    options = npc_labels + ["Accuse no one"]

    choice = ui.prompt_choice("Who is the traitor?", options)

    if choice == "Accuse no one":
        accused_id = None
        executed = False
        ui.console.print("\n[dim]You chose not to accuse anyone.[/]")
    else:
        idx = options.index(choice)
        accused_id = npc_ids[idx]
        accused_sheet = state.npc_sheets[accused_id]
        ui.console.print(
            f"\n[bold]You point at [yellow]{accused_sheet.codename}[/yellow].[/]"
        )

        execute_choice = ui.prompt_choice(
            "What do you do with them?",
            ["Execute", "Spare / hand to police"],
        )
        executed = execute_choice == "Execute"

    state.end_game(accused_id, executed)

    won, ending_key = director.evaluate_win(state)
    _show_ending(state, director, won, ending_key)


# ---------------------------------------------------------------------------
# Endings
# ---------------------------------------------------------------------------

def _build_police_arrival(state: GameState) -> str:
    """Build a detailed, context-aware police arrival scene."""
    accused = state.npc_sheets.get(state.accused_id) if state.accused_id else None
    player = state.player_sheet
    facts = state.revealed_facts

    lines: list[str] = []

    # --- Arrival ---
    lines.append(
        "The sirens that have been cutting through the rain all night reach a "
        "deafening pitch. Tires screech on wet asphalt. Doors slam. Boots hit "
        "the ground in rapid succession. The federal police have arrived."
    )
    lines.append("")

    # --- Breach scene (varies by accusation + execution) ---
    if state.executed and accused:
        lines.append(
            f"The warehouse doors burst open under a battering ram. Flashlights "
            f"sweep the darkness and find the crew standing in a half-circle "
            f"around {accused.codename}'s body. The smell of gunpowder mixes "
            f"with the diesel. Nobody moves."
        )
        lines.append("")
        if player.id == "ghost":
            lines.append(
                "You step forward slowly, raising your badge above your head. "
                "\"Federal agent — stand down.\" The agents lower their weapons "
                "toward you. One of them nods. They know the face behind the cover. "
                "The operation you've been building for months ends here, in this "
                "grimy warehouse, standing over a body that shouldn't be there."
            )
        elif "ghost" in state.npc_sheets:
            ghost_alive = state.accused_id != "ghost"
            if ghost_alive:
                lines.append(
                    "From the back of the group, Ghost steps forward — calm, "
                    "unhurried. A federal badge catches the flashlight beam. "
                    "\"Agent reporting. Situation contained.\" The crew stares, "
                    "jaws slack. The quiet one was a cop the entire time."
                )
            else:
                lines.append(
                    "The agents sweep in and cuff everyone still breathing. "
                    "One of them crouches by Ghost's body and finds a federal "
                    "badge tucked inside the jacket. The room goes silent. "
                    "They just killed one of their own informants."
                )
        else:
            lines.append(
                "The agents sweep in with trained precision, cuffing everyone "
                "still standing. The body tells its own story."
            )
    elif accused and not state.executed:
        lines.append(
            f"The warehouse doors explode inward. Federal agents pour in, "
            f"weapons drawn, barking orders. They find {accused.codename} "
            f"bound and restrained by the crew — alive, bruised, but breathing."
        )
        lines.append("")
        if player.id == "ghost":
            lines.append(
                "You raise your hands, then slowly pull out your badge. "
                "\"I'm the inside man. This is my operation.\" The lead agent "
                "holsters his weapon. You hand over the suspect and watch "
                "as the rest of the crew — your crew, for a while — gets "
                "lined up against the wall in cuffs."
            )
        elif "ghost" in state.npc_sheets:
            lines.append(
                "Ghost walks toward the agents without being told. Reaches "
                "into a pocket and produces a federal badge. The crew watches "
                "in stunned silence as Ghost shakes hands with the lead agent. "
                "\"Been a long few months,\" Ghost mutters. The betrayal cuts "
                "deeper than the heist ever did."
            )
        else:
            lines.append(
                "The agents cuff everyone methodically. The suspect is separated "
                "and led to an armored van. The rest of the crew gets lined up "
                "against the warehouse wall, faces to the concrete."
            )
    else:
        lines.append(
            "The doors blow open. Flashbang grenades light up the darkness. "
            "The crew is caught in a tense standoff — no resolution, no answers, "
            "just a circle of armed, paranoid criminals pointing fingers at each "
            "other. The agents don't need to fire a shot. Everyone goes face-down "
            "on the cold concrete."
        )
    lines.append("")

    # --- Evidence aftermath ---
    money_found = "money_found" in facts
    gps_found = "gps_found" in facts
    dirty_cash = "dirty_cash" in facts

    lines.append("[bold]AFTERMATH[/]")
    lines.append("")

    if money_found:
        lines.append(
            "The stacks of cash ripped from the car's headliner are bagged "
            "and tagged — every bill accounted for. The heist money is recovered."
        )
    else:
        lines.append(
            "In the days that follow, forensics tears the car apart piece by "
            "piece. Behind the headliner fabric, they find it — every last bill "
            "from the Central Bank vault, neatly stacked. A hiding spot nobody "
            "thought to check."
        )

    if gps_found:
        lines.append(
            "The GPS tracker under the driver's seat is logged as evidence. "
            "It had been transmitting the car's location to federal headquarters "
            "the entire time — that's how they found the warehouse so fast."
        )
    else:
        lines.append(
            "Under the driver's seat, forensics discovers a small GPS beacon, "
            "still blinking. It had been broadcasting the car's position to "
            "the federal police since the bank. Nobody in the crew ever noticed it."
        )

    if dirty_cash:
        lines.append(
            "The $500 found in Dogg's pocket is matched to the vault's serial "
            "numbers. A direct link between the traitor and the stolen money."
        )
    else:
        lines.append(
            "During processing, a rolled-up wad of $500 is found in Dogg's "
            "pocket — bills that match the vault's serial numbers. The smoking "
            "gun nobody thought to look for."
        )

    # --- Undiscovered clues ---
    missed: list[str] = []
    if "news_clipping" not in facts:
        missed.append(
            "Shade's red, swollen hand and the newspaper clipping about a past "
            "heist in his pocket"
        )
    if "gps_coords" not in facts:
        missed.append(
            "Ghost's slip of paper with GPS coordinates pointing to federal "
            "police headquarters"
        )
    if "maldives_tickets" not in facts:
        missed.append(
            "Cap's one-way ticket to the Maldives — his planned escape"
        )
    if "extra_charge" not in facts:
        missed.append(
            "Spark's spare smoke charge, hinting at the explosives mishap"
        )
    if "shredded_news" not in facts:
        missed.append(
            "the trunk full of shredded newspaper where the money should have been"
        )

    if missed:
        lines.append("")
        lines.append(
            "The investigation later uncovers what you missed:"
        )
        for clue in missed:
            lines.append(f"  - {clue}")

    return "\n".join(lines)


def _show_ending(
    state: GameState,
    director: Director,
    won: bool,
    ending_key: str,
) -> None:
    ui.clear()
    if won:
        ui.console.print("\n[bold green]*** VICTORY ***[/]\n")
    else:
        ui.console.print("\n[bold red]*** DEFEAT ***[/]\n")

    epilogue = director.get_epilogue(state, ending_key, won)
    ui.typewriter(epilogue, delay=0.025)

    # Police arrival (non-timeout endings)
    ui.console.print()
    police_scene = _build_police_arrival(state)
    ui.typewriter(police_scene, delay=0.02)

    if is_debug():
        ui.console.print("\n[bold underline]THE TRUTH:[/]")
        ui.console.print(
            "  [yellow]Dogg[/] was the traitor. He swapped the money for shredded\n"
            "  newspaper during the extended smoke and hid it in the car's headliner.\n"
            "  He kept $500 in his pocket.\n\n"
            "  [cyan]Ghost[/] was an undercover federal cop who planted a GPS tracker\n"
            "  under the driver's seat.\n\n"
            "  [dim]Shade[/] was the accomplice — he altered the gas charge to give\n"
            "  Ghost extra time and knocked out the bank manager.\n"
        )
        ui.print_evidence(state)
    ui.console.print(f"[bold]Your role:[/] {state.player_sheet.codename} ({state.player_sheet.role})")
    ui.console.print(f"[bold]Ending:[/] {ending_key.replace('_', ' ').title()}")
    ui.console.print()
    ui.prompt_enter("Press Enter to return to menu")


def _show_raid_ending(state: GameState, director: Director) -> None:
    """Show the police raid timeout ending."""
    ui.clear()
    ui.console.print("\n[bold red]*** TIME'S UP ***[/]\n")
    ui.console.print(
        "[bold red]The warehouse doors explode inward![/]\n"
        "[bold]Flashbang grenades light up the darkness. Federal agents\n"
        "pour in, weapons drawn. The crew is taken down one by one.[/]\n"
    )

    state.end_game(accused_id=None, executed=False)
    won, ending_key = director.evaluate_win(state)

    epilogue = director.get_epilogue(state, ending_key, won)
    ui.typewriter(epilogue, delay=0.025)

    if won:
        ui.console.print("\n[bold green]*** VICTORY ***[/]")
    else:
        ui.console.print("\n[bold red]*** DEFEAT ***[/]")

    if is_debug():
        ui.console.print("\n[bold underline]THE TRUTH:[/]")
        ui.console.print(
            "  [yellow]Dogg[/] was the traitor. He swapped the money for shredded\n"
            "  newspaper during the extended smoke and hid it in the car's headliner.\n\n"
            "  [cyan]Ghost[/] was an undercover federal cop who planted a GPS tracker\n"
            "  under the driver's seat.\n\n"
            "  [dim]Shade[/] was the accomplice who altered the gas charge.\n"
        )
        ui.print_evidence(state)

    ui.console.print(f"\n[bold]Your role:[/] {state.player_sheet.codename} ({state.player_sheet.role})")
    ui.console.print()
    ui.prompt_enter("Press Enter to return to menu")
