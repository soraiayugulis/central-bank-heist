"""Tests for dice rolling and power handlers."""

import pytest

from central_bank_heist.config import GameConfig
from central_bank_heist.dice import (
    POWER_HANDLERS,
    apply_npc_power,
    apply_player_power,
    roll_d6,
)
from central_bank_heist.models import GameState, Round
from central_bank_heist.sheets import Power, load_sheets


@pytest.fixture
def sheets():
    return load_sheets()


@pytest.fixture
def make_state(sheets):
    def _make(player_id: str = "boss", current_round: Round = Round.ROUND_1):
        player = sheets[player_id]
        npcs = {k: v for k, v in sheets.items() if k != player_id}
        state = GameState(
            config=GameConfig(),
            player_sheet=player,
            npc_sheets=npcs,
            current_round=current_round,
        )
        return state
    return _make


def test_roll_d6_range():
    results = {roll_d6() for _ in range(200)}
    assert results == {1, 2, 3, 4, 5, 6}


class TestPowerHandlers:
    def test_set_die(self):
        handler = POWER_HANDLERS["set_die"]
        assert handler(3, {"value": 6}, None) == 6

    def test_min_die_below(self):
        handler = POWER_HANDLERS["min_die"]
        assert handler(2, {"value": 5}, None) == 5

    def test_min_die_above(self):
        handler = POWER_HANDLERS["min_die"]
        assert handler(6, {"value": 5}, None) == 6

    def test_force_die(self):
        handler = POWER_HANDLERS["force_die"]
        assert handler(5, {"value": 1}, None) == 1


class TestPlayerPower:
    def test_spark_power_round1(self, make_state, sheets):
        state = make_state("spark", Round.ROUND_1)
        final, used = apply_player_power(3, state)
        assert final == 6
        assert used is True
        assert state.player_power_used is True

    def test_spark_power_round2_no_effect(self, make_state):
        state = make_state("spark", Round.ROUND_2)
        final, used = apply_player_power(3, state)
        assert final == 3
        assert used is False

    def test_spark_power_only_once(self, make_state):
        state = make_state("spark", Round.ROUND_1)
        apply_player_power(3, state)
        final, used = apply_player_power(2, state)
        assert final == 2
        assert used is False

    def test_shade_power_round2(self, make_state):
        state = make_state("shade", Round.ROUND_2)
        final, used = apply_player_power(2, state)
        assert final == 5
        assert used is True

    def test_shade_power_round2_already_high(self, make_state):
        state = make_state("shade", Round.ROUND_2)
        final, used = apply_player_power(6, state)
        assert final == 6
        assert used is False

    def test_boss_no_power(self, make_state):
        state = make_state("boss", Round.ROUND_1)
        final, used = apply_player_power(3, state)
        assert final == 3
        assert used is False


class TestNpcPower:
    def test_spark_npc_round1(self, make_state):
        state = make_state("boss", Round.ROUND_1)
        final, used = apply_npc_power(3, "spark", state)
        assert final == 6
        assert used is True

    def test_spark_npc_round2_no_effect(self, make_state):
        state = make_state("boss", Round.ROUND_2)
        final, used = apply_npc_power(3, "spark", state)
        assert final == 3
        assert used is False

    def test_shade_npc_round2(self, make_state):
        state = make_state("boss", Round.ROUND_2)
        final, used = apply_npc_power(2, "shade", state)
        assert final == 5
        assert used is True

    def test_npc_power_only_once(self, make_state):
        state = make_state("boss", Round.ROUND_1)
        apply_npc_power(3, "spark", state)
        final, used = apply_npc_power(2, "spark", state)
        assert final == 2
        assert used is False
