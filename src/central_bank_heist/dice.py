"""Dice rolling and power handler registry."""

from __future__ import annotations

import random
from typing import Any, Callable

from central_bank_heist.models import GameState, Round

PowerHandler = Callable[[int, dict[str, Any], GameState], int]

# ---------------------------------------------------------------------------
# Power handlers
# ---------------------------------------------------------------------------

def _set_die(roll: int, params: dict[str, Any], state: GameState) -> int:
    """Override the die to a fixed value."""
    return int(params.get("value", roll))


def _min_die(roll: int, params: dict[str, Any], state: GameState) -> int:
    """Floor the die at a minimum value."""
    return max(roll, int(params.get("value", roll)))


def _force_die(roll: int, params: dict[str, Any], state: GameState) -> int:
    """Force the die to a specific value (used by the bank manager's panic attack)."""
    return int(params.get("value", 1))


POWER_HANDLERS: dict[str, PowerHandler] = {
    "set_die": _set_die,
    "min_die": _min_die,
    "force_die": _force_die,
}

# ---------------------------------------------------------------------------
# Die tier labels (for UI / prompts)
# ---------------------------------------------------------------------------

DIE_TIER_LABELS: dict[int, str] = {
    1: "confused / evasive",
    2: "answers + reveals own suspicion point",
    3: "answers + reveals own suspicion point",
    4: "answers + offers own suspicion of others",
    5: "answers + offers own suspicion of others",
    6: "deflects — accuses someone else instead",
}


def roll_d6() -> int:
    """Roll a standard six-sided die."""
    return random.randint(1, 6)


def apply_player_power(
    raw_roll: int,
    state: GameState,
) -> tuple[int, bool]:
    """Apply the player's power to a die roll if applicable.

    Returns (final_roll, power_was_used).
    """
    power = state.player_sheet.power
    if power is None or state.player_power_used:
        return raw_roll, False

    handler = POWER_HANDLERS.get(power.type)
    if handler is None:
        return raw_roll, False

    target_round = power.params.get("round")
    if target_round is not None:
        current = 1 if state.current_round == Round.ROUND_1 else 2
        if current != target_round:
            return raw_roll, False

    modified = handler(raw_roll, power.params, state)
    if modified != raw_roll:
        state.player_power_used = True
        return modified, True
    return raw_roll, False


def apply_npc_power(
    raw_roll: int,
    npc_id: str,
    state: GameState,
) -> tuple[int, bool]:
    """Apply an NPC's power to their own die result.

    Returns (final_roll, power_was_used).
    """
    sheet = state.npc_sheets.get(npc_id)
    if sheet is None or sheet.power is None:
        return raw_roll, False
    if state.npc_power_used.get(npc_id, False):
        return raw_roll, False

    handler = POWER_HANDLERS.get(sheet.power.type)
    if handler is None:
        return raw_roll, False

    target_round = sheet.power.params.get("round")
    if target_round is not None:
        current = 1 if state.current_round == Round.ROUND_1 else 2
        if current != target_round:
            return raw_roll, False

    modified = handler(raw_roll, sheet.power.params, state)
    if modified != raw_roll:
        state.npc_power_used[npc_id] = True
        return modified, True
    return raw_roll, False
