"""Prompt templates for NPC interactions."""

from __future__ import annotations

import random

from central_bank_heist.models import Annoyance
from central_bank_heist.sheets import CharacterSheet

# ---------------------------------------------------------------------------
# Die tier instructions
# ---------------------------------------------------------------------------

_TIER_INSTRUCTIONS: dict[int, str] = {
    1: (
        "IMPORTANT RULE: You rolled a 1. You are confused and evasive. "
        "Give a short, vague, unhelpful answer (1-2 sentences max). "
        "Stammer, trail off, or change the subject. Do NOT provide useful information."
    ),
    2: (
        "You rolled a 2. Answer the question truthfully based on what you know. "
        "Keep it to 2-4 sentences."
    ),
    3: (
        "You rolled a 3. Answer the question truthfully based on what you know. "
        "Keep it to 2-4 sentences."
    ),
    4: (
        "You rolled a 4. Answer the question truthfully based on what you know. "
        "You may also point suspicion at another character you find suspicious, "
        "and explain why. Keep it to 2-4 sentences."
    ),
    5: (
        "You rolled a 5. Answer the question truthfully based on what you know. "
        "You may also point suspicion at another character you find suspicious, "
        "and explain why. Keep it to 2-4 sentences."
    ),
    6: (
        "IMPORTANT RULE: You rolled a 6. Do NOT answer the question directly. "
        "Instead, deflect completely and accuse another specific character by name. "
        "Give a reason why they are more suspicious than you. "
        "Keep it to 2-4 sentences."
    ),
}

# ---------------------------------------------------------------------------
# Annoyance overlays
# ---------------------------------------------------------------------------

_ANNOYANCE_INSTRUCTIONS: dict[str, str] = {
    "mild": (
        "The player has already asked you something similar. "
        "Acknowledge that you already answered ('I already told you...') "
        "but still provide your response. Sound mildly irritated."
    ),
    "hostile": (
        "The player is re-asking things you already answered — this is the "
        "{repeat_count}th time they come to you. You are FURIOUS. "
        "In 2-3 sentences, angrily call out the specific topic they keep repeating "
        "and give them nothing beyond what you already said. "
        "Express the anger as: {hostile_style}. "
        "CRITICAL: write a completely NEW response — do not reuse any words, "
        "phrasing, or structure from your previous statements."
    ),
}

_HOSTILE_STYLES = [
    "explosive and shouting",
    "cold and menacing",
    "sarcastic and biting",
    "dismissive and condescending",
    "threatening to walk away",
    "fed up, mocking the player's detective skills",
]

# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def build_system_prompt(
    npc_sheet: CharacterSheet,
    player_sheet: CharacterSheet,
    statement_log: list[str],
) -> str:
    """Build the NPC system prompt from sheet data."""
    sections = npc_sheet.prompt_sections()

    lines = [
        "You are roleplaying as a character in a crime thriller.",
        "Stay STRICTLY in character at all times. Never break the fourth wall.",
        "Never mention dice, game mechanics, rounds, or anything meta.",
        "Respond in English, 2-5 sentences, in first person.",
        "Output ONLY spoken dialogue. Never describe actions, gestures, or use "
        "narration, stage directions, or quotation marks. Just what you say.",
        "Never invent facts about the crime that are not in your knowledge below.",
        "Never reveal items listed under CONCEALS even if directly asked.",
        "",
        f"=== YOUR CHARACTER: {sections['codename']} ===",
        f"Role: {sections['role']}",
        f"Personality: {sections['personality']}",
        f"Speech style: {sections['speech_style']}",
        f"Appearance: {sections['appearance']}",
    ]

    if "knows" in sections:
        lines.append(f"\nWhat you know:\n{sections['knows']}")

    if npc_sheet.cover_story:
        lines.append(f"\nYour cover story (repeat consistently): {npc_sheet.cover_story}")

    if "conceals" in sections:
        lines.append(f"\nCONCEALS (NEVER reveal these):\n{sections['conceals']}")

    lines.append(f"\n=== THE PLAYER ===")
    lines.append(
        f"The person talking to you is {player_sheet.codename} "
        f"({player_sheet.role}). ALWAYS address them as 'you' — never refer "
        "to them by name or in third person. You may suspect them, but say it TO them."
    )
    if player_sheet.suspicion_point:
        lines.append(f"Their suspicious behavior: {player_sheet.suspicion_point}")
    relationship = npc_sheet.relationships.get(player_sheet.id)
    if relationship:
        lines.append(
            f"Your relationship with them: {relationship} "
            "Stay true to this relationship in EVERY response, even when angry."
        )

    if statement_log:
        lines.append("\n=== YOUR PREVIOUS STATEMENTS (do not contradict) ===")
        for i, stmt in enumerate(statement_log, 1):
            lines.append(f"{i}. {stmt}")

    return "\n".join(lines)


def build_user_prompt(
    question: str,
    die_tier: int,
    annoyance: Annoyance,
    npc_sheet: CharacterSheet,
    repeat_count: int = 0,
) -> str:
    """Build the user-message prompt with die-tier instructions."""
    parts: list[str] = []

    tier_instruction = _TIER_INSTRUCTIONS.get(die_tier, _TIER_INSTRUCTIONS[3])
    if "{suspicion_point}" in tier_instruction:
        sp = npc_sheet.suspicion_point or "nothing obviously suspicious"
        tier_instruction = tier_instruction.replace("{suspicion_point}", sp)
    parts.append(tier_instruction)

    if annoyance != Annoyance.NONE:
        overlay = _ANNOYANCE_INSTRUCTIONS.get(annoyance.value, "")
        if overlay:
            parts.append(
                overlay.replace("{hostile_style}", random.choice(_HOSTILE_STYLES))
                .replace("{repeat_count}", str(repeat_count))
            )

    if npc_sheet.can_lie:
        parts.append(
            "You are the traitor. You may lie freely, but stay consistent with "
            "your cover story and previous statements."
        )

    parts.append(f'\nThe player asks: "{question[:500]}"')

    return "\n\n".join(parts)


def build_epilogue_prompt(
    player_sheet: CharacterSheet,
    accused_codename: str | None,
    executed: bool,
    revealed_facts: set[str],
    won: bool,
) -> str:
    """Build the prompt for the LLM-narrated epilogue."""
    outcome_parts = []
    if accused_codename:
        action = "executed" if executed else "handed to the police"
        outcome_parts.append(f"The player accused {accused_codename} and {action} them.")
    else:
        outcome_parts.append("The player chose not to accuse anyone.")

    if "money_found" in revealed_facts:
        outcome_parts.append("The money was found hidden in the car's headliner.")
    else:
        outcome_parts.append("The money was never found.")

    if "gps_found" in revealed_facts:
        outcome_parts.append("A GPS tracker was found under the driver's seat.")

    result = "VICTORY" if won else "DEFEAT"

    return (
        "Write a short dramatic epilogue (4-6 sentences) for a crime thriller. "
        "Noir tone, English.\n\n"
        f"The player was {player_sheet.codename} ({player_sheet.role}).\n"
        f"Outcome: {' '.join(outcome_parts)}\n"
        f"Result: {result}\n\n"
        "End with a punchy one-liner."
    )
