"""Core game state and enums."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto

from central_bank_heist.config import GameConfig
from central_bank_heist.sheets import CharacterSheet


class Round(Enum):
    ROUND_1 = auto()
    ROUND_2 = auto()
    ACCUSATION = auto()
    ENDED = auto()


class Annoyance(Enum):
    NONE = "none"
    MILD = "mild"
    HOSTILE = "hostile"


class ActionType(Enum):
    QUESTION = "question"
    SEARCH_PERSON = "search_person"
    SEARCH_TRUNK = "search_trunk"
    SEARCH_CAR = "search_car"
    ACCUSE = "accuse"


@dataclass
class StatementLog:
    """Per-NPC statement history (capped)."""

    entries: list[str] = field(default_factory=list)

    def add(self, statement: str, max_entries: int = 10) -> None:
        self.entries.append(statement)
        if len(self.entries) > max_entries:
            self.entries = self.entries[-max_entries:]


@dataclass
class GameState:
    """Mutable game state for a single playthrough."""

    config: GameConfig
    player_sheet: CharacterSheet
    npc_sheets: dict[str, CharacterSheet]
    current_round: Round = Round.ROUND_1
    started_at: float = field(default_factory=time.time)
    penalty_seconds: float = 0.0
    question_counts: dict[str, int] = field(default_factory=dict)
    statement_logs: dict[str, StatementLog] = field(default_factory=dict)
    revealed_facts: set[str] = field(default_factory=set)
    round2_actions: int = 0
    car_search_count: int = 0
    car_search_order: list[int] = field(default_factory=lambda: [0, 1])
    searched_persons: set[str] = field(default_factory=set)
    trunk_searched: bool = False
    accused_id: str | None = None
    executed: bool = False
    player_power_used: bool = False
    npc_power_used: dict[str, bool] = field(default_factory=dict)

    @property
    def deadline(self) -> float | None:
        """Absolute deadline timestamp, or None if timer disabled."""
        if self.config.time_limit_minutes <= 0:
            return None
        return (
            self.started_at
            + self.config.time_limit_minutes * 60
            - self.penalty_seconds
        )

    @property
    def remaining_seconds(self) -> float | None:
        """Seconds remaining, or None if timer disabled."""
        dl = self.deadline
        if dl is None:
            return None
        return max(0.0, dl - time.time())

    @property
    def is_timed_out(self) -> bool:
        """True if the timer has expired."""
        remaining = self.remaining_seconds
        if remaining is None:
            return False
        return remaining <= 0

    @property
    def accusation_unlocked(self) -> bool:
        return (
            self.current_round == Round.ROUND_2
            and self.round2_actions >= self.config.accusation_min_round2_actions
        )

    def get_annoyance(self, npc_id: str) -> Annoyance:
        """Determine annoyance level for an NPC based on question count."""
        count = self.question_counts.get(npc_id, 0)
        if count <= 1:
            return Annoyance.NONE
        if count == 2:
            return Annoyance.MILD
        return Annoyance.HOSTILE

    def record_question(self, npc_id: str) -> Annoyance:
        """Increment question count and return resulting annoyance.

        Applies time penalty if hostile threshold reached.
        """
        self.question_counts[npc_id] = self.question_counts.get(npc_id, 0) + 1
        annoyance = self.get_annoyance(npc_id)
        if annoyance == Annoyance.HOSTILE:
            self.penalty_seconds += self.config.repeat_penalty_minutes * 60
        return annoyance

    def record_statement(self, npc_id: str, statement: str) -> None:
        """Add a statement to an NPC's log."""
        if npc_id not in self.statement_logs:
            self.statement_logs[npc_id] = StatementLog()
        self.statement_logs[npc_id].add(statement, self.config.statement_log_max)

    def get_statement_log(self, npc_id: str) -> list[str]:
        """Get statement history for an NPC."""
        log = self.statement_logs.get(npc_id)
        return log.entries if log else []

    def advance_to_round2(self) -> None:
        self.current_round = Round.ROUND_2

    def advance_to_accusation(self) -> None:
        self.current_round = Round.ACCUSATION

    def end_game(self, accused_id: str | None, executed: bool) -> None:
        self.accused_id = accused_id
        self.executed = executed
        self.current_round = Round.ENDED
