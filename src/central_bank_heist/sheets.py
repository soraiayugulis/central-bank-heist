"""Load, validate, and render character sheets from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_DATA_DIR = Path(__file__).parent / "data"

VALID_ROLE_IDS = {"boss", "traitor", "ghost", "spark", "brick", "wheels", "shade", "manager"}
PLAYABLE_ROLE_IDS = VALID_ROLE_IDS - {"traitor"}

VALID_POWER_TYPES = {"set_die", "min_die", "force_die"}

VALID_WIN_TYPES = {
    "accuse_role", "accused_not_role", "accused_any",
    "no_death", "target_not_executed",
    "fact_found", "fact_not_found",
    "timed_out", "not_timed_out",
}

VALID_FACT_IDS = {
    "money_found", "gps_found", "dirty_cash", "news_clipping",
    "gps_coords", "maldives_tickets", "extra_charge", "pocket_lint",
    "shredded_news",
}


@dataclass
class Power:
    """A character power declaration."""

    type: str
    params: dict[str, Any] = field(default_factory=dict)
    uses: int = 1
    description: str = ""


@dataclass
class WinCondition:
    """A possibly-compound win condition tree."""

    type: str | None = None
    target: str | None = None
    fact: str | None = None
    value: bool | None = None
    children: list[WinCondition] = field(default_factory=list)

    def evaluate(
        self,
        accused_id: str | None,
        executed: bool,
        revealed_facts: set[str],
        timed_out: bool = False,
    ) -> bool:
        """Evaluate this condition against game outcome."""
        if self.type == "all":
            return all(c.evaluate(accused_id, executed, revealed_facts, timed_out) for c in self.children)
        if self.type == "any":
            return any(c.evaluate(accused_id, executed, revealed_facts, timed_out) for c in self.children)
        if self.type == "accuse_role":
            return accused_id == self.target
        if self.type == "accused_not_role":
            return accused_id is not None and accused_id != self.target
        if self.type == "accused_any":
            return accused_id is not None
        if self.type == "no_death":
            return not executed
        if self.type == "target_not_executed":
            return not (executed and accused_id == self.target)
        if self.type == "fact_found":
            return self.fact in revealed_facts if self.fact else False
        if self.type == "fact_not_found":
            return self.fact not in revealed_facts if self.fact else False
        if self.type == "timed_out":
            return timed_out
        if self.type == "not_timed_out":
            return not timed_out
        return False


@dataclass
class CharacterSheet:
    """A fully-loaded character sheet."""

    id: str
    codename: str
    role: str
    personality: str
    speech_style: str
    appearance: str
    knows: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    conceals: list[str] = field(default_factory=list)
    cover_story: str | None = None
    can_lie: bool = False
    suspicion_point: str | None = None
    pocket: list[str] = field(default_factory=list)
    power: Power | None = None
    win_condition: WinCondition | None = None
    intro: str | None = None
    search_results: dict[str, str] = field(default_factory=dict)

    def prompt_sections(self) -> dict[str, str]:
        """Render all sheet data into prompt-friendly sections.

        New fields added to the YAML will automatically flow into the prompt
        as long as they are string or list-of-string.
        """
        sections: dict[str, str] = {}
        sections["codename"] = self.codename
        sections["role"] = self.role
        sections["personality"] = self.personality
        sections["speech_style"] = self.speech_style
        sections["appearance"] = self.appearance
        if self.knows:
            sections["knows"] = "\n".join(f"- {k}" for k in self.knows)
        if self.conceals:
            sections["conceals"] = "\n".join(f"- {c}" for c in self.conceals)
        if self.cover_story:
            sections["cover_story"] = self.cover_story
        if self.suspicion_point:
            sections["suspicion_point"] = self.suspicion_point
        sections["can_lie"] = str(self.can_lie)
        return sections


def _parse_power(data: dict | None) -> Power | None:
    if data is None:
        return None
    ptype = data.get("type", "")
    if ptype not in VALID_POWER_TYPES:
        raise ValueError(
            f"Unknown power type '{ptype}'. Valid: {sorted(VALID_POWER_TYPES)}"
        )
    return Power(
        type=ptype,
        params=data.get("params", {}),
        uses=data.get("uses", 1),
        description=data.get("description", ""),
    )


def _parse_win_condition(data: Any) -> WinCondition | None:
    """Parse a win condition from YAML (supports compound all/any)."""
    if data is None:
        return None

    if isinstance(data, dict):
        if "all" in data:
            children = [_parse_win_condition(c) for c in data["all"]]
            return WinCondition(type="all", children=[c for c in children if c])
        if "any" in data:
            children = [_parse_win_condition(c) for c in data["any"]]
            return WinCondition(type="any", children=[c for c in children if c])

        wtype = data.get("type")
        if wtype and wtype not in VALID_WIN_TYPES:
            raise ValueError(
                f"Unknown win_condition type '{wtype}'. Valid: {sorted(VALID_WIN_TYPES)}"
            )

        target = data.get("target")
        if target and target not in VALID_ROLE_IDS:
            raise ValueError(
                f"Unknown target role '{target}'. Valid: {sorted(VALID_ROLE_IDS)}"
            )

        fact = data.get("fact")
        if fact and fact not in VALID_FACT_IDS:
            raise ValueError(
                f"Unknown fact '{fact}'. Valid: {sorted(VALID_FACT_IDS)}"
            )

        if "no_death" in data and "type" not in data:
            return WinCondition(type="no_death", value=data["no_death"])
        if "accused_not_role" in data and "type" not in data:
            return WinCondition(type="accused_not_role", target=data["accused_not_role"])

        return WinCondition(type=wtype, target=target, fact=fact)

    return None


def _parse_sheet(data: dict) -> CharacterSheet:
    """Parse a single character sheet from YAML dict."""
    sheet_id = data.get("id", "")
    if sheet_id not in VALID_ROLE_IDS:
        raise ValueError(
            f"Unknown character id '{sheet_id}'. Valid: {sorted(VALID_ROLE_IDS)}"
        )

    return CharacterSheet(
        id=sheet_id,
        codename=data.get("codename", sheet_id),
        role=data.get("role", ""),
        personality=data.get("personality", ""),
        speech_style=data.get("speech_style", ""),
        appearance=data.get("appearance", ""),
        knows=data.get("knows", []),
        secrets=data.get("secrets", []),
        conceals=data.get("conceals", []),
        cover_story=data.get("cover_story"),
        can_lie=data.get("can_lie", False),
        suspicion_point=data.get("suspicion_point"),
        pocket=data.get("pocket", []),
        power=_parse_power(data.get("power")),
        win_condition=_parse_win_condition(data.get("win_condition")),
        intro=data.get("intro"),
        search_results=data.get("search_results", {}),
    )


def load_sheets(path: Path | None = None) -> dict[str, CharacterSheet]:
    """Load all character sheets from YAML. Returns dict keyed by id."""
    if path is None:
        path = _DATA_DIR / "characters.yaml"

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, list):
        raise ValueError("characters.yaml must be a YAML list of character sheets")

    sheets: dict[str, CharacterSheet] = {}
    for entry in raw:
        sheet = _parse_sheet(entry)
        if sheet.id in sheets:
            raise ValueError(f"Duplicate character id: '{sheet.id}'")
        sheets[sheet.id] = sheet

    missing = VALID_ROLE_IDS - set(sheets.keys())
    if missing:
        raise ValueError(f"Missing character sheets: {sorted(missing)}")

    return sheets
