"""Tests for sheet loading and validation."""

import pytest

from central_bank_heist.sheets import (
    CharacterSheet,
    WinCondition,
    load_sheets,
    VALID_ROLE_IDS,
    PLAYABLE_ROLE_IDS,
)


def test_load_all_sheets():
    sheets = load_sheets()
    assert set(sheets.keys()) == VALID_ROLE_IDS


def test_traitor_is_not_playable():
    assert "traitor" not in PLAYABLE_ROLE_IDS
    assert "traitor" in VALID_ROLE_IDS


def test_all_playable_have_intro():
    sheets = load_sheets()
    for role_id in PLAYABLE_ROLE_IDS:
        sheet = sheets[role_id]
        assert sheet.intro is not None, f"{role_id} is missing an intro"


def test_traitor_can_lie():
    sheets = load_sheets()
    assert sheets["traitor"].can_lie is True


def test_traitor_has_cover_story():
    sheets = load_sheets()
    assert sheets["traitor"].cover_story is not None
    assert len(sheets["traitor"].cover_story) > 10


def test_all_sheets_have_search_results():
    sheets = load_sheets()
    for sheet in sheets.values():
        assert "person" in sheet.search_results, f"{sheet.id} missing search_results.person"


def test_prompt_sections():
    sheets = load_sheets()
    boss = sheets["boss"]
    sections = boss.prompt_sections()
    assert sections["codename"] == "Cap"
    assert "knows" in sections
    assert "suspicion_point" in sections


# --- WinCondition evaluation ---

class TestWinCondition:
    def test_accuse_role_match(self):
        wc = WinCondition(type="accuse_role", target="traitor")
        assert wc.evaluate("traitor", False, set()) is True
        assert wc.evaluate("boss", False, set()) is False

    def test_accused_not_role(self):
        wc = WinCondition(type="accused_not_role", target="ghost")
        assert wc.evaluate("traitor", False, set()) is True
        assert wc.evaluate("ghost", False, set()) is False
        assert wc.evaluate(None, False, set()) is False

    def test_no_death(self):
        wc = WinCondition(type="no_death")
        assert wc.evaluate("traitor", False, set()) is True
        assert wc.evaluate("traitor", True, set()) is False

    def test_fact_found(self):
        wc = WinCondition(type="fact_found", fact="money_found")
        assert wc.evaluate(None, False, {"money_found"}) is True
        assert wc.evaluate(None, False, set()) is False

    def test_compound_all(self):
        wc = WinCondition(
            type="all",
            children=[
                WinCondition(type="accuse_role", target="traitor"),
                WinCondition(type="fact_found", fact="money_found"),
            ],
        )
        assert wc.evaluate("traitor", False, {"money_found"}) is True
        assert wc.evaluate("traitor", False, set()) is False
        assert wc.evaluate("boss", False, {"money_found"}) is False

    def test_compound_any(self):
        wc = WinCondition(
            type="any",
            children=[
                WinCondition(type="accuse_role", target="traitor"),
                WinCondition(type="fact_found", fact="money_found"),
            ],
        )
        assert wc.evaluate("traitor", False, set()) is True
        assert wc.evaluate("boss", False, {"money_found"}) is True
        assert wc.evaluate("boss", False, set()) is False

    def test_loaded_boss_win_condition(self):
        sheets = load_sheets()
        wc = sheets["boss"].win_condition
        assert wc is not None
        assert wc.evaluate("traitor", False, {"money_found"}) is True
        assert wc.evaluate("traitor", False, set()) is False
        assert wc.evaluate("traitor", False, {"money_found"}, timed_out=True) is False

    def test_loaded_manager_win_condition(self):
        sheets = load_sheets()
        wc = sheets["manager"].win_condition
        assert wc is not None
        assert wc.evaluate(None, False, set(), timed_out=True) is True
        assert wc.evaluate("traitor", False, {"money_found"}, timed_out=False) is False

    def test_loaded_shade_win_condition(self):
        sheets = load_sheets()
        wc = sheets["shade"].win_condition
        assert wc is not None
        assert wc.evaluate("traitor", False, set()) is True
        assert wc.evaluate("ghost", False, set()) is True   # accused but spared: OK
        assert wc.evaluate("ghost", True, set()) is False   # ghost executed: lose
        assert wc.evaluate(None, False, set(), timed_out=True) is True  # raid: ghost survives

    def test_loaded_ghost_win_condition(self):
        sheets = load_sheets()
        wc = sheets["ghost"].win_condition
        assert wc is not None
        assert wc.evaluate("boss", False, {"money_found"}) is True
        assert wc.evaluate("boss", True, {"money_found"}) is False   # Cap executed: lose
        assert wc.evaluate("traitor", False, {"money_found"}) is False
        assert wc.evaluate("boss", False, set()) is False

    def test_loaded_spark_win_condition(self):
        sheets = load_sheets()
        wc = sheets["spark"].win_condition
        assert wc is not None
        assert wc.evaluate("traitor", False, {"money_found"}) is True
        assert wc.evaluate("boss", False, {"money_found"}) is False  # can't accuse boss
        assert wc.evaluate("traitor", False, set()) is False
        assert wc.evaluate("traitor", False, {"money_found"}, timed_out=True) is False

    def test_loaded_brick_win_condition(self):
        sheets = load_sheets()
        wc = sheets["brick"].win_condition
        assert wc is not None
        assert wc.evaluate("traitor", False, {"money_found"}) is True
        assert wc.evaluate("ghost", False, {"money_found"}) is True   # ghost or traitor
        assert wc.evaluate("shade", False, {"money_found"}) is False
        assert wc.evaluate("traitor", False, set()) is False

    def test_loaded_wheels_win_condition(self):
        sheets = load_sheets()
        wc = sheets["wheels"].win_condition
        assert wc is not None
        assert wc.evaluate("brick", False, set()) is True   # any accusation before raid
        assert wc.evaluate("brick", False, set(), timed_out=True) is False
