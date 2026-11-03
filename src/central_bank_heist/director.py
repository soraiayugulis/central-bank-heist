"""Game director / mediator: orchestrates NPC interactions, powers, and win evaluation."""

from __future__ import annotations

import random
from typing import Iterator

from central_bank_heist.config import GameConfig, ProviderConfig, load_game_config, load_provider_config
from central_bank_heist.dice import apply_npc_power, apply_player_power, roll_d6
from central_bank_heist.models import Annoyance, GameState, Round
from central_bank_heist.prompts import build_epilogue_prompt, build_system_prompt, build_user_prompt
from central_bank_heist.providers.base import LLMProvider, create_provider
from central_bank_heist.providers.scripted import ScriptedProvider
from central_bank_heist.sheets import CharacterSheet, PLAYABLE_ROLE_IDS, load_sheets

# ---------------------------------------------------------------------------
# Search result texts (deterministic)
# ---------------------------------------------------------------------------

_TRUNK_SEARCH_TEXT = (
    "You pop the trunk and pull out the bags. One by one you tear them open — "
    "shredded newspaper. Every single bag. Not a dollar bill in sight. "
    "Someone swapped the money before the bags reached the trunk."
)

_CAR_SEARCH_RESULTS: dict[int, list[tuple[str, str | None]]] = {
    # index 0 = first discovery (money), index 1 = second (GPS)
    # Each tier maps to (text, fact_id_or_none)
    0: [  # money_found target
        # low (1-2): nothing
        ("You tear apart the seats, check the floor mats, glove box — nothing. "
         "Something feels off about the interior but you can't pin it down.", None),
        # mid (3-4): suspicious hint
        ("You search the car methodically. The headliner fabric looks slightly "
         "loose — like someone pulled it and put it back. Could be nothing, "
         "could be worth another look.", None),
        # high (5-6): discovery
        ("You tear apart the car interior — seats, floor mats, glove box. "
         "Then you notice the headliner is bulging. You rip it open and stacks "
         "of cash cascade out. The money was hidden inside the car's headliner "
         "the entire time.", "money_found"),
    ],
    1: [  # gps_found target
        # low (1-2): nothing
        ("You check under the seats, the dash, the sun visors — nothing new. "
         "But there's a faint electronic hum you can't quite locate.", None),
        # mid (3-4): suspicious hint
        ("Searching under the seats, your fingers brush something small and hard "
         "attached to the frame. It's too dark to see clearly — you'd need to "
         "look again more carefully.", None),
        # high (5-6): discovery
        ("You keep searching the car. Under the driver's seat your hand closes "
         "around a small electronic device — a GPS tracker, blinking steadily. "
         "Someone planted a beacon to lead the feds straight here.", "gps_found"),
    ],
}

_NOTHING_NEW = "You search again carefully, but find nothing new."

# ---------------------------------------------------------------------------
# Canned epilogues for scripted fallback
# ---------------------------------------------------------------------------

def _build_epilogue(ending_key: str, revealed_facts: set[str]) -> str:
    """Build a context-aware canned epilogue."""
    money_found = "money_found" in revealed_facts

    if ending_key == "win":
        return (
            "The rain hammers the warehouse roof as the truth comes to light. "
            "The right person pays for the betrayal, and the money is accounted for. "
            "The sirens wail closer — but you've already played your hand. "
            "The feds breach the door moments later. "
            "In this game, the sharpest mind wins — and tonight, that was you."
        )
    if ending_key == "near_miss":
        return (
            "You found the rat — but the money slipped through your fingers. "
            "The feds breach the warehouse and seize everything. Forensics will "
            "eventually find the stash hidden in the car's headliner. "
            "You'll get credit for the collar, but not the score. "
            "Close only counts in horseshoes and hand grenades."
        )
    if ending_key == "wrong_accusation":
        money_line = (
            "The money you found won't save you from this mistake. "
            if money_found else
            "The money stays hidden in the headliner — nobody thought to look there. "
        )
        return (
            "The wrong person takes the fall. The real traitor watches in silence, "
            "a ghost of a smile crossing their face. " + money_line +
            "The feds breach the warehouse moments later and everyone goes down. "
            "Justice has a cruel sense of humor."
        )
    if ending_key == "no_accusation":
        money_line = (
            "At least you found the money — but without naming the traitor, it doesn't matter. "
            if money_found else
            "The money sits in the headliner, undiscovered. A perfect crime — wasted. "
        )
        return (
            "Nobody points the finger. The crew stares at each other in the dim light "
            "as the sirens grow deafening. The feds breach the door and everyone goes down. "
            + money_line
        )
    if ending_key == "raid":
        return (
            "Time's up. The warehouse doors explode inward and flashbang grenades "
            "light up the darkness. Federal agents pour in, weapons drawn. "
            "The crew is taken down one by one. In the aftermath, forensics will "
            "find the money in the headliner and piece together the whole ugly truth."
        )
    if ending_key == "manager_win":
        return (
            "The standoff ends without bloodshed. The feds breach the door and "
            "everyone is taken alive — bruised, angry, but breathing. The bank manager is pulled "
            "to safety, shaking but intact. Sometimes survival is its own victory."
        )
    return "The rain falls. The sirens close in. The story ends."

# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------

class Director:
    """Central game mediator that wires prompts, dice, powers, and outcomes."""

    def __init__(
        self,
        game_config: GameConfig | None = None,
        provider_config: ProviderConfig | None = None,
    ) -> None:
        self.game_config = game_config or load_game_config()
        self.provider_config = provider_config or load_provider_config()
        self.sheets = load_sheets()
        self.provider: LLMProvider = create_provider(self.provider_config)

    def new_game(self, force_role: str | None = None) -> GameState:
        """Create a new GameState with a randomly-drawn player role."""
        if force_role and force_role in PLAYABLE_ROLE_IDS:
            player_id = force_role
        else:
            player_id = random.choice(sorted(PLAYABLE_ROLE_IDS))

        player_sheet = self.sheets[player_id]
        npc_sheets = {k: v for k, v in self.sheets.items() if k != player_id}

        state = GameState(
            config=self.game_config,
            player_sheet=player_sheet,
            npc_sheets=npc_sheets,
        )
        # Randomize which discovery the car yields first (money vs GPS)
        state.car_search_order = random.sample([0, 1], 2)
        return state

    # ----- Interrogation -----

    def ask_npc(
        self,
        state: GameState,
        npc_id: str,
        question: str,
        use_player_power: bool = False,
        player_force_die_target: str | None = None,
    ) -> tuple[int, int, Annoyance, str]:
        """Run a full question turn.

        Returns (raw_roll, final_roll, annoyance, response_text).
        """
        npc_sheet = state.npc_sheets[npc_id]

        raw = roll_d6()
        final = raw

        if use_player_power and state.player_sheet.power:
            if state.player_sheet.power.type == "force_die" and player_force_die_target == npc_id:
                from central_bank_heist.dice import POWER_HANDLERS
                handler = POWER_HANDLERS["force_die"]
                final = handler(final, state.player_sheet.power.params, state)
                state.player_power_used = True
            else:
                final, _ = apply_player_power(final, state)

        final, npc_power_used = apply_npc_power(final, npc_id, state)

        annoyance = state.record_question(npc_id)

        if state.current_round == Round.ROUND_2:
            state.round2_actions += 1

        system = build_system_prompt(
            npc_sheet=npc_sheet,
            player_sheet=state.player_sheet,
            statement_log=state.get_statement_log(npc_id),
        )

        user_msg = build_user_prompt(
            question=question,
            die_tier=final,
            annoyance=annoyance,
            npc_sheet=npc_sheet,
        )

        if isinstance(self.provider, ScriptedProvider):
            self.provider.set_context(npc_id, final, annoyance.value)

        try:
            response = self.provider.complete(system, user_msg)
        except Exception:
            if not isinstance(self.provider, ScriptedProvider):
                fallback = ScriptedProvider()
                fallback.set_context(npc_id, final, annoyance.value)
                response = fallback.complete(system, user_msg)
            else:
                response = "..."

        state.record_statement(npc_id, response)
        return raw, final, annoyance, response

    def stream_npc(
        self,
        state: GameState,
        npc_id: str,
        question: str,
        use_player_power: bool = False,
        player_force_die_target: str | None = None,
    ) -> tuple[int, int, Annoyance, Iterator[str]]:
        """Like ask_npc but returns a streaming iterator instead of full text.

        Caller must collect the full text for statement logging.
        """
        npc_sheet = state.npc_sheets[npc_id]

        raw = roll_d6()
        final = raw

        if use_player_power and state.player_sheet.power:
            if state.player_sheet.power.type == "force_die" and player_force_die_target == npc_id:
                from central_bank_heist.dice import POWER_HANDLERS
                handler = POWER_HANDLERS["force_die"]
                final = handler(final, state.player_sheet.power.params, state)
                state.player_power_used = True
            else:
                final, _ = apply_player_power(final, state)

        final, _ = apply_npc_power(final, npc_id, state)

        annoyance = state.record_question(npc_id)

        if state.current_round == Round.ROUND_2:
            state.round2_actions += 1

        system = build_system_prompt(
            npc_sheet=npc_sheet,
            player_sheet=state.player_sheet,
            statement_log=state.get_statement_log(npc_id),
        )
        user_msg = build_user_prompt(
            question=question,
            die_tier=final,
            annoyance=annoyance,
            npc_sheet=npc_sheet,
        )

        if isinstance(self.provider, ScriptedProvider):
            self.provider.set_context(npc_id, final, annoyance.value)

        try:
            token_iter = self.provider.stream(system, user_msg)
        except Exception:
            fallback = ScriptedProvider()
            fallback.set_context(npc_id, final, annoyance.value)
            token_iter = fallback.stream(system, user_msg)

        return raw, final, annoyance, token_iter

    # ----- Searches (deterministic) -----

    def search_person(self, state: GameState, npc_id: str) -> tuple[str, str | None]:
        """Search an NPC's pockets. Returns (text, fact_id_or_none)."""
        if state.current_round == Round.ROUND_2:
            state.round2_actions += 1

        if npc_id in state.searched_persons:
            return _NOTHING_NEW, None

        state.searched_persons.add(npc_id)
        sheet = state.npc_sheets.get(npc_id)
        if sheet is None:
            return "You can't search yourself.", None

        text = sheet.search_results.get("person", "Empty pockets. Nothing to find.")

        fact_map = {
            "traitor": "dirty_cash",
            "shade": "news_clipping",
            "ghost": "gps_coords",
            "boss": "maldives_tickets",
            "spark": "extra_charge",
            "wheels": "pocket_lint",
            "brick": "pocket_lint",
            "manager": "pocket_lint",
        }
        fact_id = fact_map.get(npc_id)
        if fact_id:
            state.revealed_facts.add(fact_id)
        return text, fact_id

    def search_trunk(self, state: GameState) -> tuple[str, str | None]:
        """Search the trunk."""
        if state.current_round == Round.ROUND_2:
            state.round2_actions += 1

        if state.trunk_searched:
            return _NOTHING_NEW, None

        state.trunk_searched = True
        state.revealed_facts.add("shredded_news")
        return _TRUNK_SEARCH_TEXT, "shredded_news"

    def search_car(self, state: GameState, die_value: int) -> tuple[str, str | None]:
        """Search inside the car with a die roll determining success.

        Progressive targets: 0=money, 1=GPS. Die determines tier:
        1-2=nothing, 3-4=suspicious hint, 5-6=actual discovery.
        """
        if state.current_round == Round.ROUND_2:
            state.round2_actions += 1

        if state.car_search_count >= len(state.car_search_order):
            return _NOTHING_NEW, None
        target_idx = state.car_search_order[state.car_search_count]

        results = _CAR_SEARCH_RESULTS[target_idx]
        if die_value <= 2:
            tier = 0  # low: nothing
        elif die_value <= 4:
            tier = 1  # mid: hint
        else:
            tier = 2  # high: discovery

        text, fact_id = results[tier]
        if fact_id:
            state.car_search_count += 1
            state.revealed_facts.add(fact_id)
        return text, fact_id

    # ----- Win evaluation -----

    def evaluate_win(self, state: GameState) -> tuple[bool, str]:
        """Evaluate win/loss and return (won, ending_key)."""
        wc = state.player_sheet.win_condition
        if wc is None:
            return False, "wrong_accusation"

        timed_out = state.is_timed_out

        if state.accused_id is None:
            if timed_out:
                # Police raid — evaluate condition with timed_out=True
                won = wc.evaluate(None, False, state.revealed_facts, timed_out=True)
                if won and state.player_sheet.id == "manager":
                    return True, "manager_win"
                return won, "raid"
            # Player chose "accuse no one" or forced ending without accusation
            won = wc.evaluate(None, False, state.revealed_facts, timed_out=False)
            if won:
                return True, "win"
            return False, "no_accusation"

        won = wc.evaluate(
            state.accused_id, state.executed, state.revealed_facts, timed_out=timed_out
        )

        if won:
            return True, "win"

        if wc.type == "all" and wc.children:
            fact_children = [
                c for c in wc.children
                if c.type in ("fact_found", "fact_not_found")
            ]
            other_children = [c for c in wc.children if c not in fact_children]
            accuse_ok = all(
                c.evaluate(
                    state.accused_id, state.executed,
                    state.revealed_facts, timed_out,
                )
                for c in other_children
            )
            fact_missing = any(
                not c.evaluate(
                    state.accused_id, state.executed,
                    state.revealed_facts, timed_out,
                )
                for c in fact_children
            )
            if fact_children and accuse_ok and fact_missing:
                return False, "near_miss"

        return False, "wrong_accusation"

    def get_epilogue(self, state: GameState, ending_key: str, won: bool) -> str:
        """Get the epilogue text, using LLM if available, else canned."""
        if isinstance(self.provider, ScriptedProvider):
            return _build_epilogue(ending_key, state.revealed_facts)

        accused_codename = None
        if state.accused_id:
            accused_sheet = self.sheets.get(state.accused_id)
            accused_codename = accused_sheet.codename if accused_sheet else state.accused_id

        prompt = build_epilogue_prompt(
            player_sheet=state.player_sheet,
            accused_codename=accused_codename,
            executed=state.executed,
            revealed_facts=state.revealed_facts,
            won=won,
        )

        try:
            return self.provider.complete(
                "You are a noir crime fiction narrator. Write dramatic, punchy prose.",
                prompt,
            )
        except Exception:
            return _build_epilogue(ending_key, state.revealed_facts)
