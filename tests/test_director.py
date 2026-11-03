"""Tests for the Director: searches, win evaluation, NPC interactions."""

import pytest

from central_bank_heist.config import GameConfig, ProviderConfig
from central_bank_heist.director import Director
from central_bank_heist.models import Round


@pytest.fixture
def director():
    return Director(
        game_config=GameConfig(time_limit_minutes=0),
        provider_config=ProviderConfig(provider="scripted"),
    )


@pytest.fixture
def state(director):
    return director.new_game(force_role="boss")


class TestNewGame:
    def test_player_is_forced_role(self, director):
        state = director.new_game(force_role="spark")
        assert state.player_sheet.id == "spark"

    def test_player_never_traitor(self, director):
        for _ in range(50):
            state = director.new_game()
            assert state.player_sheet.id != "traitor"

    def test_npcs_exclude_player(self, state):
        assert "boss" not in state.npc_sheets
        assert "traitor" in state.npc_sheets


class TestSearches:
    def test_search_person_traitor(self, director, state):
        state.current_round = Round.ROUND_2
        text, fact = director.search_person(state, "traitor")
        assert "$500" in text
        assert fact == "dirty_cash"
        assert "dirty_cash" in state.revealed_facts

    def test_search_person_twice_nothing_new(self, director, state):
        state.current_round = Round.ROUND_2
        director.search_person(state, "traitor")
        text, fact = director.search_person(state, "traitor")
        assert "nothing new" in text.lower()
        assert fact is None

    def test_search_trunk(self, director, state):
        state.current_round = Round.ROUND_2
        text, fact = director.search_trunk(state)
        assert "shredded" in text.lower()
        assert fact == "shredded_news"

    def test_search_trunk_twice(self, director, state):
        state.current_round = Round.ROUND_2
        director.search_trunk(state)
        text, fact = director.search_trunk(state)
        assert "nothing new" in text.lower()

    def test_search_car_low_roll_finds_nothing(self, director, state):
        state.current_round = Round.ROUND_2
        text, fact = director.search_car(state, die_value=1)
        assert fact is None
        assert "nothing" in text.lower() or "can't pin" in text.lower()

    def test_search_car_mid_roll_gives_hint(self, director, state):
        state.current_round = Round.ROUND_2
        state.car_search_order = [0, 1]  # money first for a deterministic hint
        text, fact = director.search_car(state, die_value=3)
        assert fact is None
        assert "loose" in text.lower() or "headliner" in text.lower()

    def test_search_car_high_roll_finds_both_any_order(self, director, state):
        state.current_round = Round.ROUND_2
        found = set()
        texts = []
        for _ in range(2):
            text, fact = director.search_car(state, die_value=6)
            found.add(fact)
            texts.append(text)

        assert found == {"money_found", "gps_found"}
        text3, fact3 = director.search_car(state, die_value=6)
        assert "nothing new" in text3.lower()
        assert fact3 is None

    def test_search_car_order_is_randomized(self, director):
        orders = set()
        for _ in range(20):
            state = director.new_game(force_role="boss")
            orders.add(tuple(state.car_search_order))
        assert len(orders) == 2

    def test_searches_increment_round2_actions(self, director, state):
        state.current_round = Round.ROUND_2
        assert state.round2_actions == 0
        director.search_person(state, "ghost")
        assert state.round2_actions == 1
        director.search_trunk(state)
        assert state.round2_actions == 2
        director.search_car(state, die_value=6)
        assert state.round2_actions == 3


class TestAskNpc:
    def test_ask_returns_response(self, director, state):
        raw, final, ann, text = director.ask_npc(state, "traitor", "Where were you?")
        assert 1 <= raw <= 6
        assert 1 <= final <= 6
        assert isinstance(text, str)
        assert len(text) > 0

    def test_ask_records_statement(self, director, state):
        director.ask_npc(state, "ghost", "What did you see?")
        log = state.get_statement_log("ghost")
        assert len(log) >= 1

    def test_stream_returns_iterator(self, director, state):
        raw, final, ann, token_iter = director.stream_npc(state, "spark", "What happened?")
        tokens = list(token_iter)
        assert len(tokens) > 0


class TestWinEvaluation:
    def test_boss_wins_correct_accusation_with_money(self, director):
        state = director.new_game(force_role="boss")
        state.revealed_facts.add("money_found")
        state.end_game("traitor", False)
        won, key = director.evaluate_win(state)
        assert won is True
        assert key == "win"

    def test_boss_near_miss_no_money(self, director):
        state = director.new_game(force_role="boss")
        state.end_game("traitor", False)
        won, key = director.evaluate_win(state)
        assert won is False
        assert key == "near_miss"

    def test_boss_wrong_accusation(self, director):
        state = director.new_game(force_role="boss")
        state.revealed_facts.add("money_found")
        state.end_game("ghost", False)
        won, key = director.evaluate_win(state)
        assert won is False
        assert key == "wrong_accusation"

    def test_ghost_wins_accusing_boss_with_money(self, director):
        state = director.new_game(force_role="ghost")
        state.revealed_facts.add("money_found")
        state.end_game("boss", False)
        won, key = director.evaluate_win(state)
        assert won is True

    def test_ghost_loses_accusing_traitor(self, director):
        state = director.new_game(force_role="ghost")
        state.revealed_facts.add("money_found")
        state.end_game("traitor", False)
        won, key = director.evaluate_win(state)
        assert won is False

    def test_shade_wins_if_ghost_not_accused(self, director):
        state = director.new_game(force_role="shade")
        state.end_game("traitor", False)
        won, key = director.evaluate_win(state)
        assert won is True

    def test_shade_wins_if_ghost_accused_but_spared(self, director):
        state = director.new_game(force_role="shade")
        state.end_game("ghost", False)
        won, key = director.evaluate_win(state)
        assert won is True

    def test_shade_loses_if_ghost_executed(self, director):
        state = director.new_game(force_role="shade")
        state.end_game("ghost", True)
        won, key = director.evaluate_win(state)
        assert won is False

    def test_manager_loses_on_accusation(self, director):
        state = director.new_game(force_role="manager")
        state.end_game("traitor", False)
        won, key = director.evaluate_win(state)
        assert won is False

    def test_wheels_wins_on_any_accusation(self, director):
        state = director.new_game(force_role="wheels")
        state.end_game("brick", False)
        won, key = director.evaluate_win(state)
        assert won is True

    def test_spark_loses_accusing_boss(self, director):
        state = director.new_game(force_role="spark")
        state.revealed_facts.add("money_found")
        state.end_game("boss", False)
        won, key = director.evaluate_win(state)
        assert won is False

    def test_brick_wins_accusing_ghost_with_money(self, director):
        state = director.new_game(force_role="brick")
        state.revealed_facts.add("money_found")
        state.end_game("ghost", False)
        won, key = director.evaluate_win(state)
        assert won is True

    def test_ghost_loses_executing_boss(self, director):
        state = director.new_game(force_role="ghost")
        state.revealed_facts.add("money_found")
        state.end_game("boss", True)
        won, key = director.evaluate_win(state)
        assert won is False

    def test_no_accusation_loses(self, director):
        state = director.new_game(force_role="boss")
        state.end_game(None, False)
        won, key = director.evaluate_win(state)
        assert won is False
        assert key == "no_accusation"

    def test_timeout_manager_wins(self):
        d = Director(
            game_config=GameConfig(time_limit_minutes=1),
            provider_config=ProviderConfig(provider="scripted"),
        )
        state = d.new_game(force_role="manager")
        state.started_at = 0  # way in the past → timed out
        state.end_game(None, False)
        won, key = d.evaluate_win(state)
        assert won is True
        assert key == "manager_win"

    def test_timeout_ghost_loses(self):
        d = Director(
            game_config=GameConfig(time_limit_minutes=1),
            provider_config=ProviderConfig(provider="scripted"),
        )
        state = d.new_game(force_role="ghost")
        state.started_at = 0
        state.end_game(None, False)
        won, key = d.evaluate_win(state)
        assert won is False
        assert key == "raid"

    def test_timeout_shade_wins(self):
        d = Director(
            game_config=GameConfig(time_limit_minutes=1),
            provider_config=ProviderConfig(provider="scripted"),
        )
        state = d.new_game(force_role="shade")
        state.started_at = 0
        state.end_game(None, False)
        won, key = d.evaluate_win(state)
        assert won is True
        assert key == "raid"

    def test_timeout_others_lose(self):
        d = Director(
            game_config=GameConfig(time_limit_minutes=1),
            provider_config=ProviderConfig(provider="scripted"),
        )
        state = d.new_game(force_role="brick")
        state.started_at = 0
        state.end_game(None, False)
        won, key = d.evaluate_win(state)
        assert won is False
        assert key == "raid"


class TestEpilogue:
    def test_scripted_epilogue(self, director):
        state = director.new_game(force_role="boss")
        state.end_game("traitor", False)
        state.revealed_facts.add("money_found")
        text = director.get_epilogue(state, "win", True)
        assert len(text) > 20
