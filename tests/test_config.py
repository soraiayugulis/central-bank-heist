"""Tests for config loading."""

import os

import pytest

from central_bank_heist.config import load_game_config, load_provider_config


def test_load_game_config_defaults():
    cfg = load_game_config()
    assert cfg.time_limit_minutes == 20
    assert cfg.repeat_question_threshold == 3
    assert cfg.repeat_penalty_minutes == 2
    assert cfg.accusation_min_round2_actions == 2
    assert cfg.statement_log_max == 10


def test_load_game_config_env_override(monkeypatch):
    monkeypatch.setenv("HEIST_TIME_LIMIT_MINUTES", "30")
    monkeypatch.setenv("HEIST_REPEAT_PENALTY_MINUTES", "5")
    cfg = load_game_config()
    assert cfg.time_limit_minutes == 30
    assert cfg.repeat_penalty_minutes == 5
    assert cfg.repeat_question_threshold == 3  # unchanged


def test_load_provider_config_defaults():
    cfg = load_provider_config()
    assert cfg.provider == "scripted"


def test_load_provider_config_env(monkeypatch):
    monkeypatch.setenv("HEIST_PROVIDER", "anthropic")
    monkeypatch.setenv("HEIST_MODEL", "claude-sonnet-4-20250514")
    cfg = load_provider_config()
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-sonnet-4-20250514"
