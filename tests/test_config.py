"""Tests for ThemeConfig and ThemeLoader (tasks 3.1 & 3.2).

Unit tests cover specific examples and edge cases.
Property-based tests cover Properties 6 and 7 from the design doc.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.config import ThemeConfig, ThemeLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Unit tests — ThemeConfig defaults
# ---------------------------------------------------------------------------

def test_theme_config_defaults():
    cfg = ThemeConfig()
    assert cfg.background_color == "#1a1a2e"
    assert cfg.card_gradient_start == "#16213e"
    assert cfg.card_gradient_end == "#0f3460"
    assert cfg.accent_color == "#e94560"
    assert cfg.text_color == "#e0e0e0"
    assert cfg.font_family == "Segoe UI"
    assert cfg.font_size == 12
    assert cfg.logo_path == "images/logo.png"


# ---------------------------------------------------------------------------
# Unit tests — ThemeLoader.load()
# ---------------------------------------------------------------------------

def test_load_valid_theme_json(tmp_path):
    p = tmp_path / "theme.json"
    data = {
        "background_color": "#000000",
        "card_gradient_start": "#111111",
        "card_gradient_end": "#222222",
        "accent_color": "#ff0000",
        "text_color": "#ffffff",
        "font_family": "Arial",
        "font_size": 14,
        "logo_path": "images/custom.png",
    }
    p.write_text(json.dumps(data), encoding="utf-8")

    loader = ThemeLoader()
    cfg = loader.load(str(p))

    assert cfg.background_color == "#000000"
    assert cfg.font_size == 14
    assert cfg.font_family == "Arial"
    assert cfg.logo_path == "images/custom.png"


def test_load_missing_file_returns_defaults(tmp_path):
    loader = ThemeLoader()
    cfg = loader.load(str(tmp_path / "nonexistent.json"))
    assert cfg == ThemeConfig()


def test_load_empty_file_returns_defaults(tmp_path):
    p = tmp_path / "theme.json"
    _write(str(p), "")
    loader = ThemeLoader()
    cfg = loader.load(str(p))
    assert cfg == ThemeConfig()


def test_load_invalid_json_returns_defaults(tmp_path):
    p = tmp_path / "theme.json"
    _write(str(p), "{not valid json")
    loader = ThemeLoader()
    cfg = loader.load(str(p))
    assert cfg == ThemeConfig()


def test_load_json_array_returns_defaults(tmp_path):
    p = tmp_path / "theme.json"
    _write(str(p), "[1, 2, 3]")
    loader = ThemeLoader()
    cfg = loader.load(str(p))
    assert cfg == ThemeConfig()


def test_load_partial_json_uses_defaults_for_missing_keys(tmp_path):
    p = tmp_path / "theme.json"
    _write(str(p), json.dumps({"background_color": "#abcdef"}))
    loader = ThemeLoader()
    cfg = loader.load(str(p))
    assert cfg.background_color == "#abcdef"
    assert cfg.font_family == ThemeConfig.font_family  # default preserved


# ---------------------------------------------------------------------------
# Unit tests — ThemeLoader.to_dict()
# ---------------------------------------------------------------------------

def test_to_dict_contains_all_fields():
    loader = ThemeLoader()
    cfg = ThemeConfig()
    d = loader.to_dict(cfg)
    assert set(d.keys()) == {
        "background_color", "card_gradient_start", "card_gradient_end",
        "accent_color", "text_color", "font_family", "font_size", "logo_path",
    }


def test_to_dict_values_match_config():
    loader = ThemeLoader()
    cfg = ThemeConfig(background_color="#aabbcc", font_size=16)
    d = loader.to_dict(cfg)
    assert d["background_color"] == "#aabbcc"
    assert d["font_size"] == 16


# ---------------------------------------------------------------------------
# Property 6: ThemeLoader.load() never raises for any input
# **Validates: Requirements 8.3**
# ---------------------------------------------------------------------------

@given(bad_content=st.text())
@settings(max_examples=200)
def test_theme_loader_never_raises_for_any_file_content(bad_content):
    """Property 6: ThemeLoader.load() must NEVER raise exception for any input."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "theme.json"
        _write(str(p), bad_content)
        loader = ThemeLoader()
        result = loader.load(str(p))
        assert isinstance(result, ThemeConfig)


@given(bad_content=st.text())
@settings(max_examples=100)
def test_theme_loader_never_raises_for_missing_file(bad_content):
    """Property 6 (missing file variant): load() on a non-existent path returns defaults."""
    with tempfile.TemporaryDirectory() as tmp:
        loader = ThemeLoader()
        result = loader.load(os.path.join(tmp, "does_not_exist.json"))
        assert result == ThemeConfig()


# ---------------------------------------------------------------------------
# Property 7: Round-trip serialization preserves all field values
# **Validates: Requirements 8.1, 8.2, 7.5**
# ---------------------------------------------------------------------------

_theme_config_strategy = st.builds(
    ThemeConfig,
    background_color=st.text(min_size=1, max_size=50),
    card_gradient_start=st.text(min_size=1, max_size=50),
    card_gradient_end=st.text(min_size=1, max_size=50),
    accent_color=st.text(min_size=1, max_size=50),
    text_color=st.text(min_size=1, max_size=50),
    font_family=st.text(min_size=1, max_size=50),
    font_size=st.integers(min_value=1, max_value=72),
    logo_path=st.text(min_size=1, max_size=200),
)


@given(config=_theme_config_strategy)
@settings(max_examples=200)
def test_theme_config_roundtrip(config):
    """Property 7: serialize → write JSON → load must reproduce identical ThemeConfig."""
    loader = ThemeLoader()
    d = loader.to_dict(config)

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "theme.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        restored = loader.load(str(p))

    assert restored.background_color == config.background_color
    assert restored.card_gradient_start == config.card_gradient_start
    assert restored.card_gradient_end == config.card_gradient_end
    assert restored.accent_color == config.accent_color
    assert restored.text_color == config.text_color
    assert restored.font_family == config.font_family
    assert restored.font_size == config.font_size
    assert restored.logo_path == config.logo_path
