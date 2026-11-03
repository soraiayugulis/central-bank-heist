"""Tests for GameState: annoyance, penalties, timer, gating."""

import time

import pytest

from central_bank_heist.config import GameConfig
from central_bank_heist.models import Annoyance, GameState, Round, StatementLog
from central_bank_heist.sheets import load_sheets


@pytest.fixture
def sheets():
    return load_sheets()


@pytest.fixture
def state(sheets):
    player = sheets["boss"]
    npcs = {k: v for k, v in sheets.items() if k != "boss"}
    return GameState(
        config=GameConfig(),
        player_sheet=player,
        npc_sheets=npcs,
    )


class TestAnnoyance:
    def test_first_question_no_annoyance(self, state):
        ann = state.record_question("traitor")
        assert ann == Annoyance.NONE

    def test_second_question_mild(self, state):
        state.record_question("traitor")
        ann = state.record_question("traitor")
        assert ann == Annoyance.MILD

    def test_third_question_hostile(self, state):
        state.record_question("traitor")
        state.record_question("traitor")
        ann = state.record_question("traitor")
        assert ann == Annoyance.HOSTILE

    def test_hostile_applies_penalty(self, state):
        assert state.penalty_seconds == 0.0
        state.record_question("traitor")
        state.record_question("traitor")
        state.record_question("traitor")  # hostile
        assert state.penalty_seconds == 2 * 60  # 2 minutes

    def test_fourth_question_more_penalty(self, state):
        for _ in range(4):
            state.record_question("traitor")
        assert state.penalty_seconds == 2 * 2 * 60  # 2 hostile triggers

    def test_different_npcs_independent(self, state):
        state.record_question("traitor")
        state.record_question("traitor")
        ann = state.record_question("ghost")
        assert ann == Annoyance.NONE


class TestTimer:
    def test_deadline_with_timer(self, state):
        assert state.deadline is not None
        assert state.deadline > time.time()

    def test_deadline_disabled(self, sheets):
        player = sheets["boss"]
        npcs = {k: v for k, v in sheets.items() if k != "boss"}
        state = GameState(
            config=GameConfig(time_limit_minutes=0),
            player_sheet=player,
            npc_sheets=npcs,
        )
        assert state.deadline is None
        assert state.remaining_seconds is None
        assert state.is_timed_out is False

    def test_penalty_reduces_remaining(self, state):
        before = state.remaining_seconds
        assert before is not None
        state.penalty_seconds = 300  # 5 min penalty
        after = state.remaining_seconds
        assert after is not None
        assert after < before - 290  # roughly 5 min less

    def test_timed_out(self, sheets):
        player = sheets["boss"]
        npcs = {k: v for k, v in sheets.items() if k != "boss"}
        state = GameState(
            config=GameConfig(time_limit_minutes=1),
            player_sheet=player,
            npc_sheets=npcs,
            started_at=time.time() - 120,  # started 2 min ago
        )
        assert state.is_timed_out is True


class TestAccusationGating:
    def test_not_unlocked_in_round1(self, state):
        assert state.accusation_unlocked is False

    def test_not_unlocked_with_too_few_actions(self, state):
        state.current_round = Round.ROUND_2
        state.round2_actions = 1
        assert state.accusation_unlocked is False

    def test_locked_with_actions_but_no_facts(self, state):
        state.current_round = Round.ROUND_2
        state.round2_actions = 2
        assert state.accusation_unlocked is False

    def test_unlocked_with_actions_and_fact(self, state):
        state.current_round = Round.ROUND_2
        state.round2_actions = 2
        state.revealed_facts.add("dirty_cash")
        assert state.accusation_unlocked is True


class TestStatementLog:
    def test_add_and_retrieve(self):
        log = StatementLog()
        log.add("I was at the door.", 10)
        log.add("I didn't see anything.", 10)
        assert len(log.entries) == 2

    def test_cap(self):
        log = StatementLog()
        for i in range(15):
            log.add(f"Statement {i}", max_entries=10)
        assert len(log.entries) == 10
        assert log.entries[0] == "Statement 5"  # oldest kept

    def test_state_record_and_get(self, state):
        state.record_statement("traitor", "I was loading bags.")
        state.record_statement("traitor", "Couldn't see anything.")
        log = state.get_statement_log("traitor")
        assert len(log) == 2
        assert state.get_statement_log("ghost") == []
